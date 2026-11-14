"""Atomic association writes for report template tags (S1, design D2).

Template fields and tag deltas persist in one transaction. The template,
affected catalogue rows and relevant memberships are locked before
authorization is revalidated, so a concurrent revocation or lifecycle
change cannot slip between the check and the write. A rejected request
saves nothing: no partial text, visibility, associations or audit rows.

The persisted set E is read through the association table (never through
the default catalogue manager, which would hide archived links). From E
the service computes the removable-by-actor set R and the submitted
editable set S, then persists ``(E - R) union S``. Hidden or otherwise
non-removable links are preserved. ModelForm's unrestricted M2M ``set()``
is never used for this relation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.patients.models import AllowedTag
from apps.patients.services import tag_policy
from apps.reports.services.permissions import can_manage_report_templates

if TYPE_CHECKING:
    import uuid

    from apps.accounts.models import EqmdCustomUser, UserSpecialty
    from apps.reports.models import ReportTemplate

GENERIC_TAG_ERROR_MESSAGE = "One or more selected tags are invalid."
TAGS_PRESENT_MARKER = "tags_present"
TAG_IDS_FIELD = "tag_ids"

_TEMPLATE_FIELD_NAMES = ("name", "markdown_body", "is_active", "is_public")


@dataclass(frozen=True)
class TemplateTagChange:
    """Association delta persisted by :func:`save_template_with_tags`."""

    added: frozenset[int]
    removed: frozenset[int]
    preserved: frozenset[int]


def parse_tag_submission(data: Mapping[str, object]) -> frozenset[int] | None:
    """Return the submitted editable tag identities, or ``None`` when absent.

    A missing ``tags_present=1`` marker means a legacy submission that
    makes no association edit (not a clear-all). With the marker present,
    an empty selection means "clear only authorized editable links".
    Malformed identities raise the generic validation error.
    """
    if data.get(TAGS_PRESENT_MARKER) != "1":
        return None
    getlist = getattr(data, "getlist", None)
    raw_values: list[object]
    if callable(getlist):
        raw_values = list(getlist(TAG_IDS_FIELD))
    else:
        raw = data.get(TAG_IDS_FIELD, [])
        raw_values = list(raw) if isinstance(raw, (list, tuple)) else [raw]
    parsed: set[int] = set()
    for value in raw_values:
        try:
            parsed.add(int(value))  # type: ignore[call-overload]
        except (TypeError, ValueError):
            raise ValidationError(GENERIC_TAG_ERROR_MESSAGE) from None
    return frozenset(parsed)


def persisted_tag_ids(template: ReportTemplate) -> frozenset[int]:
    """Return associated tag identities read through the association table."""
    if template.pk is None:
        return frozenset()
    through = type(template).tags.through
    return frozenset(
        through.objects.filter(reporttemplate_id=template.pk).values_list(
            "allowedtag_id", flat=True
        )
    )


def _require_template_write_authority(
    actor: EqmdCustomUser | None, template: ReportTemplate
) -> None:
    """Enforce template gates before any tag authority is considered."""
    if not can_manage_report_templates(actor):
        raise PermissionDenied("You don't have permission to manage report templates")
    if template._state.adding:
        return
    creator = template.created_by
    is_creator = creator is not None and creator.pk == getattr(actor, "pk", None)
    is_admin = bool(
        getattr(actor, "is_staff", False) or getattr(actor, "is_superuser", False)
    )
    if not is_creator and not is_admin:
        raise PermissionDenied("You can only edit your own templates")


def _lock_template(
    actor: EqmdCustomUser, template: ReportTemplate
) -> tuple[ReportTemplate, bool, frozenset[int]]:
    """Return the locked template row, its newness and its persisted set E."""
    from apps.reports.models import ReportTemplate

    _require_template_write_authority(actor, template)
    if template._state.adding:
        return template, True, frozenset()
    locked = ReportTemplate.objects.select_for_update(of=("self",)).get(pk=template.pk)
    # Ownership is decided from the persisted row, not the caller's copy.
    _require_template_write_authority(actor, locked)
    return locked, False, persisted_tag_ids(locked)


def _lock_affected_tags(
    actor: EqmdCustomUser, affected_ids: set[int]
) -> tuple[dict[int, AllowedTag], dict[uuid.UUID, UserSpecialty]]:
    """Lock affected catalogue, team and membership rows.

    Lock coverage: the template (locked by the caller), the affected
    catalogue rows, the owning ``MedicalSpecialty`` (team) rows and the
    actor's membership rows are all locked in this transaction before
    any authority is revalidated. ``tag_policy`` reads
    ``specialty.is_active`` — via the locked memberships and catalogue
    rows — and ``membership.is_active`` from those rows, so locking the
    team rows here, on the reports side, serialises a concurrent team
    deactivation against the authority read: it either commits before
    these locks (and is seen by the read) or waits until this
    transaction commits.
    """
    from apps.accounts.models import MedicalSpecialty

    # Resolve owning teams first so their rows can be locked before any
    # authority read below fetches a specialty via ``select_related``.
    specialty_ids = set(
        AllowedTag.all_objects.filter(pk__in=affected_ids)
        .exclude(specialty_id__isnull=True)
        .values_list("specialty_id", flat=True)
    )
    if specialty_ids:
        # Consume the queryset to acquire the team row locks.
        list(
            MedicalSpecialty.objects.select_for_update(of=("self",)).filter(
                pk__in=specialty_ids
            )
        )
    tags_by_id = {
        tag.pk: tag
        for tag in AllowedTag.all_objects.select_for_update(of=("self",))
        .select_related("specialty")
        .filter(pk__in=affected_ids)
    }
    locked_memberships = tag_policy.lock_team_memberships(actor, specialty_ids)
    return tags_by_id, locked_memberships


def _validate_submitted_assignments(
    actor: EqmdCustomUser,
    submitted: frozenset[int],
    existing: frozenset[int],
    tags_by_id: dict[int, AllowedTag],
    locked_memberships: dict[uuid.UUID, UserSpecialty],
) -> None:
    """Reject unauthorized submitted identities under the write locks.

    New identities need assignment authority and an active lifecycle.
    Submitted identities that are already linked need current
    removal/retention authority, which works in every lifecycle state
    so inactive/archived links can be retained. Existing identities
    that were omitted are not validated here; they are preserved by
    :func:`_compute_delta`.
    """
    for tag_id in submitted - existing:
        tag = tags_by_id.get(tag_id)
        if tag is None or not tag_policy.can_assign_tag(
            actor, tag, locked_memberships=locked_memberships
        ):
            raise ValidationError(GENERIC_TAG_ERROR_MESSAGE)
    for tag_id in submitted & existing:
        tag = tags_by_id.get(tag_id)
        if tag is None or not tag_policy.can_remove_tag(
            actor, tag, locked_memberships=locked_memberships
        ):
            raise ValidationError(GENERIC_TAG_ERROR_MESSAGE)


def _compute_delta(
    actor: EqmdCustomUser,
    submitted: frozenset[int] | None,
    existing: frozenset[int],
    tags_by_id: dict[int, AllowedTag],
    locked_memberships: dict[uuid.UUID, UserSpecialty],
) -> tuple[set[int], set[int], frozenset[int]]:
    """Return ``(removals, additions, preserved)`` for the submitted set S."""
    if submitted is None:
        return set(), set(), existing
    removable = {
        tag_id
        for tag_id in existing
        if tag_id in tags_by_id
        and tag_policy.can_remove_tag(
            actor, tags_by_id[tag_id], locked_memberships=locked_memberships
        )
    }
    removals = {tag_id for tag_id in existing - submitted if tag_id in removable}
    final = (set(existing) - removals) | set(submitted)
    additions = final - set(existing)
    preserved = frozenset(final - set(submitted))
    return removals, additions, preserved


def _persist_fields(
    actor: EqmdCustomUser,
    locked: ReportTemplate,
    template: ReportTemplate,
    is_new: bool,
) -> None:
    """Save the intended field values with actor attribution for history."""
    if is_new:
        locked.created_by = actor
    else:
        for field_name in _TEMPLATE_FIELD_NAMES:
            setattr(locked, field_name, getattr(template, field_name))
    locked.updated_by = actor
    # simple_history attributes; not known to mypy without django-stubs.
    locked._history_user = actor  # type: ignore[attr-defined]
    locked._change_reason = f"Report template save by {actor.username}"  # type: ignore[attr-defined]
    locked.save()


def _apply_removals(locked: ReportTemplate, removals: set[int]) -> None:
    """Delete through rows for archived-safe removal, emitting M2M signals.

    The related manager's ``remove()`` resolves targets through the
    default catalogue manager, which hides archived rows and would
    silently keep archived links. Deleting through rows directly and
    emitting the same ``m2m_changed`` signals Django would send keeps
    native M2M history recording the removal.
    """
    from django.db.models.signals import m2m_changed

    through = type(locked).tags.through
    removal_ids = set(removals)
    db = locked._state.db or "default"
    m2m_changed.send(
        sender=through,
        action="pre_remove",
        instance=locked,
        reverse=False,
        model=AllowedTag,
        pk_set=removal_ids,
        using=db,
    )
    through.objects.filter(
        reporttemplate_id=locked.pk, allowedtag_id__in=removal_ids
    ).delete()
    m2m_changed.send(
        sender=through,
        action="post_remove",
        instance=locked,
        reverse=False,
        model=AllowedTag,
        pk_set=removal_ids,
        using=db,
    )


@transaction.atomic
def save_template_with_tags(
    *,
    actor: EqmdCustomUser,
    template: ReportTemplate,
    submitted_tag_ids: frozenset[int] | None,
) -> TemplateTagChange:
    """Persist template fields and the tag delta atomically (design D2).

    ``template`` carries the intended field values (for a new template it
    is unsaved). ``submitted_tag_ids=None`` leaves associations untouched;
    otherwise the final set is ``(E - R) union S`` as described above.
    Raises :class:`ValidationError` with the generic message — saving
    nothing — when any new identity is unknown, inactive, archived or
    outside the actor's per-tag authority, or when a submitted existing
    identity lacks current removal/retention authority.
    """
    locked, is_new, existing = _lock_template(actor, template)
    submitted = submitted_tag_ids
    affected_ids = set(existing)
    if submitted is not None:
        affected_ids.update(submitted)
    tags_by_id, locked_memberships = _lock_affected_tags(actor, affected_ids)
    if submitted is not None:
        _validate_submitted_assignments(
            actor, submitted, existing, tags_by_id, locked_memberships
        )
    removals, additions, preserved = _compute_delta(
        actor, submitted, existing, tags_by_id, locked_memberships
    )
    _persist_fields(actor, locked, template, is_new)
    if submitted is not None and (additions or removals):
        if removals:
            _apply_removals(locked, removals)
        if additions:
            locked.tags.add(*[tags_by_id[tag_id] for tag_id in sorted(additions)])
    return TemplateTagChange(
        added=frozenset(additions),
        removed=frozenset(removals),
        preserved=preserved,
    )
