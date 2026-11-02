"""Policy-checked, atomic patient tag assignment and removal.

Every patient tag write goes through this module, whatever the entry point
(patient views, Django Admin or bulk removal). Each operation runs in a single
transaction that locks and revalidates the catalogue row, the association, the
actor's membership and the actor's authority, then writes the association and
its timeline event with one stable catalogue reference per acted-on tag. A
failed event write therefore leaves no changed association, and a denied write
leaves no side effect.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from apps.core.permissions.utils import can_manage_patient_tags
from apps.events.services import tag_audit

from . import tag_policy

if TYPE_CHECKING:
    import uuid
    from collections.abc import Iterable

    from apps.accounts.models import EqmdCustomUser, UserSpecialty
    from apps.events.models import TagBulkRemoveEvent, TagRemovedEvent
    from apps.patients.models import AllowedTag, Patient, Tag


class TagAssignmentRejected(ValidationError):
    """The association or catalogue state does not allow the operation."""


class TagAlreadyAssociated(TagAssignmentRejected):
    """The patient already carries this tag; the duplicate is not re-audited."""


class TagNotAssociated(TagAssignmentRejected):
    """The association does not exist for this patient any more."""


@dataclass(frozen=True)
class BulkRemovalResult:
    """Outcome of an authorized bulk removal."""

    removed: tuple[AllowedTag, ...]
    preserved: int
    event: TagBulkRemoveEvent


def require_patient_tag_mutation(actor: EqmdCustomUser, patient: Patient) -> None:
    """Keep the existing patient-access and clinical mutation gates."""
    if not can_manage_patient_tags(actor, patient):
        raise PermissionDenied("Patient tag management requires clinical access.")


def _lock_tag(tag_id: object) -> AllowedTag:
    """Re-read the catalogue row under a row lock, including archived rows."""
    from apps.patients.models import AllowedTag

    return AllowedTag.all_objects.select_for_update().get(pk=tag_id)


def _lock_memberships(
    actor: EqmdCustomUser, tags: Iterable[AllowedTag]
) -> dict[uuid.UUID, UserSpecialty]:
    """Lock the actor's membership rows for the teams these tags belong to."""
    specialty_ids = {tag.specialty_id for tag in tags if tag.specialty_id is not None}
    return tag_policy.lock_team_memberships(actor, specialty_ids)


@transaction.atomic
def assign_tag(
    *,
    actor: EqmdCustomUser,
    patient: Patient,
    tag: AllowedTag,
    notes: str = "",
) -> Tag:
    """Assign one active, authorized tag and audit it atomically."""
    from apps.patients.models import Tag

    locked_tag = _lock_tag(tag.pk)
    require_patient_tag_mutation(actor, patient)
    locked_memberships = _lock_memberships(actor, (locked_tag,))
    tag_policy.require_tag_authority(
        actor, locked_tag, locked_memberships=locked_memberships
    )
    if locked_tag.lifecycle_state != locked_tag.LifecycleState.ACTIVE:
        raise TagAssignmentRejected("Only active tags can be newly assigned.")
    if Tag.objects.filter(allowed_tag_id=locked_tag.pk, patient=patient).exists():
        raise TagAlreadyAssociated("The patient already carries this tag.")
    try:
        with transaction.atomic():
            association = Tag.objects.create(
                allowed_tag_id=locked_tag.pk,
                patient=patient,
                notes=notes,
                created_by=actor,
                updated_by=actor,
            )
    except IntegrityError as error:
        raise TagAlreadyAssociated("The patient already carries this tag.") from error
    tag_audit.record_tag_added(
        actor=actor, patient=patient, tag=locked_tag, notes=notes
    )
    return association


@transaction.atomic
def remove_tag(
    *,
    actor: EqmdCustomUser,
    patient: Patient,
    association: Tag,
) -> TagRemovedEvent:
    """Remove one authorized association and append the opposing event."""
    from apps.patients.models import Tag

    locked = (
        Tag.objects.select_for_update()
        .filter(pk=association.pk, patient=patient)
        .first()
    )
    if locked is None:
        raise TagNotAssociated("The association no longer exists for this patient.")
    locked_tag = _lock_tag(locked.allowed_tag_id)
    require_patient_tag_mutation(actor, patient)
    locked_memberships = _lock_memberships(actor, (locked_tag,))
    tag_policy.require_tag_authority(
        actor, locked_tag, locked_memberships=locked_memberships
    )
    notes = locked.notes
    locked.delete()
    return tag_audit.record_tag_removed(
        actor=actor, patient=patient, tag=locked_tag, notes=notes
    )


@transaction.atomic
def remove_authorized_tags(
    *, actor: EqmdCustomUser, patient: Patient
) -> BulkRemovalResult:
    """Remove only the caller's authorized associations and audit each tag.

    Associations the caller may not manage are preserved, so another team's
    classification is never erased by a bulk request.
    """
    from apps.patients.models import AllowedTag, Tag

    require_patient_tag_mutation(actor, patient)
    associations = list(
        Tag.objects.select_for_update()
        .filter(patient=patient)
        .order_by("created_at", "pk")
    )
    if not associations:
        raise TagAssignmentRejected("Nenhuma tag para remover")
    tag_ids = {association.allowed_tag_id for association in associations}
    catalogue = {
        row.pk: row
        for row in AllowedTag.all_objects.select_for_update().filter(pk__in=tag_ids)
    }
    locked_memberships = _lock_memberships(actor, catalogue.values())
    removed: list[tuple[AllowedTag, str]] = []
    removed_pks: list[object] = []
    preserved = 0
    for association in associations:
        catalogue_tag = catalogue.get(association.allowed_tag_id)
        if catalogue_tag is not None and tag_policy.can_remove_tag(
            actor, catalogue_tag, locked_memberships=locked_memberships
        ):
            removed.append((catalogue_tag, association.notes))
            removed_pks.append(association.pk)
        else:
            preserved += 1
    if not removed:
        raise TagAssignmentRejected("Nenhuma tag para remover")
    Tag.objects.filter(pk__in=removed_pks).delete()
    event = tag_audit.record_bulk_removed(actor=actor, patient=patient, removed=removed)
    return BulkRemovalResult(
        removed=tuple(catalogue_tag for catalogue_tag, _ in removed),
        preserved=preserved,
        event=event,
    )
