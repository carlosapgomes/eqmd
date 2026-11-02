"""Creation, edit and lifecycle services for the namespaced tag catalogue."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.db.models.functions import Lower, Trim
from django.utils import timezone

from apps.patients.models import AllowedTag, AllowedTagTransition

from . import tag_policy

if TYPE_CHECKING:
    from apps.accounts.models import EqmdCustomUser, MedicalSpecialty

DEFAULT_TAG_COLOR: Final[str] = "#007bff"


class _UnsetType:
    """Sentinel type distinguishing an omitted field from an explicit null."""


UNSET: Final[_UnsetType] = _UnsetType()


def canonical_name(name: str) -> str:
    """Mirror the PostgreSQL ``Lower(Trim(name))`` reservation key."""
    return name.strip().lower()


def names_reserved_in_namespace(
    name: str, *, specialty_id: object, exclude_pk: int | None = None
) -> QuerySet[AllowedTag]:
    """Return catalogue rows occupying the normalized name in a namespace."""
    rows = AllowedTag.all_objects.annotate(canonical_name=Lower(Trim("name"))).filter(
        canonical_name=canonical_name(name), specialty_id=specialty_id
    )
    if exclude_pk is not None:
        rows = rows.exclude(pk=exclude_pk)
    return rows


def name_is_reserved(
    name: str, *, specialty_id: object, exclude_pk: int | None = None
) -> bool:
    """Return whether any row, in any state, already holds the namespace name."""
    if not name or not name.strip():
        return False
    return names_reserved_in_namespace(
        name, specialty_id=specialty_id, exclude_pk=exclude_pk
    ).exists()


@transaction.atomic
def create_tag(
    *,
    actor: EqmdCustomUser,
    name: str,
    description: str = "",
    color: str = DEFAULT_TAG_COLOR,
    is_active: bool = True,
    origin: str = AllowedTag.Origin.CUSTOM,
    visibility: str = AllowedTag.Visibility.PUBLIC,
    specialty: MedicalSpecialty | None = None,
) -> AllowedTag:
    """Create a catalogue row with an attributable, immutable creator."""
    tag_policy.require_catalogue_administrator(
        actor, permission=tag_policy.CATALOGUE_ADD_PERMISSION
    )
    tag = AllowedTag(
        name=name,
        description=description,
        color=color,
        is_active=is_active,
        origin=origin,
        visibility=visibility,
        specialty=specialty,
        created_by=actor,
        updated_by=actor,
    )
    tag.full_clean()
    tag._change_reason = f"Catalogue creation by {actor.username}"
    tag.save()
    return tag


@transaction.atomic
def update_tag(
    *,
    actor: EqmdCustomUser,
    tag: AllowedTag,
    name: str | None = None,
    description: str | None = None,
    color: str | None = None,
    is_active: bool | None = None,
    origin: str | None = None,
    visibility: str | None = None,
    specialty: MedicalSpecialty | None | _UnsetType = UNSET,
) -> AllowedTag:
    """Edit a catalogue row without allowing creator or principal bypasses."""
    tag_policy.require_catalogue_administrator(
        actor, permission=tag_policy.CATALOGUE_CHANGE_PERMISSION
    )
    locked = AllowedTag.all_objects.select_for_update().get(pk=tag.pk)
    original = (locked.visibility, locked.specialty_id)
    if name is not None:
        locked.name = name
    if description is not None:
        locked.description = description
    if color is not None:
        locked.color = color
    if is_active is not None and is_active != locked.is_active:
        raise ValidationError(
            {
                "is_active": (
                    "Use the catalogue lifecycle operations to deactivate or "
                    "reactivate a tag so the actor and history are recorded."
                )
            }
        )
    if origin is not None:
        locked.origin = origin
    if visibility is not None:
        locked.visibility = visibility
    if not isinstance(specialty, _UnsetType):
        locked.specialty = specialty
    tag_policy.validate_namespace_change(
        tag_pk=locked.pk,
        original_visibility=original[0],
        original_specialty_id=original[1],
        visibility=locked.visibility,
        specialty_id=locked.specialty_id,
    )
    locked.updated_by = actor
    locked._history_user = actor
    locked.full_clean()
    locked._change_reason = f"Catalogue update by {actor.username}"
    locked.save()
    return locked


def _lock_tag(tag: AllowedTag) -> AllowedTag:
    """Re-read the catalogue row under a row lock for authorization races."""
    return AllowedTag.all_objects.select_for_update().get(pk=tag.pk)


@transaction.atomic
def deactivate_tag(
    *, actor: EqmdCustomUser, tag: AllowedTag, reason: str = ""
) -> AllowedTag:
    """Move an active tag to the reversible inactive state."""
    locked = _lock_tag(tag)
    tag_policy.require_tag_manager(actor, locked)
    if locked.is_deleted:
        raise ValidationError("Archived tags cannot be deactivated.")
    if not locked.is_active:
        raise ValidationError("The tag is already inactive.")
    previous_state = locked.lifecycle_state
    now = timezone.now()
    locked.is_active = False
    locked.deactivated_at = now
    locked.deactivated_by = actor
    locked.updated_by = actor
    locked._history_user = actor
    locked._change_reason = f"Catalogue deactivation by {actor.username}"
    locked.save(
        update_fields=[
            "is_active",
            "deactivated_at",
            "deactivated_by",
            "updated_by",
            "updated_at",
        ]
    )
    locked._record_transition(
        action=AllowedTagTransition.Action.DEACTIVATE,
        actor=actor,
        from_state=previous_state,
        to_state=AllowedTag.LifecycleState.INACTIVE,
        reason=reason,
    )
    return locked


@transaction.atomic
def reactivate_tag(
    *, actor: EqmdCustomUser, tag: AllowedTag, reason: str = ""
) -> AllowedTag:
    """Move an inactive tag back to the active state."""
    locked = _lock_tag(tag)
    tag_policy.require_tag_manager(actor, locked)
    if locked.is_deleted:
        raise ValidationError("Archived tags cannot be reactivated; restore first.")
    if locked.is_active:
        raise ValidationError("The tag is already active.")
    previous_state = locked.lifecycle_state
    now = timezone.now()
    locked.is_active = True
    locked.reactivated_at = now
    locked.reactivated_by = actor
    locked.updated_by = actor
    locked._history_user = actor
    locked._change_reason = f"Catalogue reactivation by {actor.username}"
    locked.save(
        update_fields=[
            "is_active",
            "reactivated_at",
            "reactivated_by",
            "updated_by",
            "updated_at",
        ]
    )
    locked._record_transition(
        action=AllowedTagTransition.Action.ACTIVATE,
        actor=actor,
        from_state=previous_state,
        to_state=AllowedTag.LifecycleState.ACTIVE,
        reason=reason,
    )
    return locked


@transaction.atomic
def archive_tag(
    *, actor: EqmdCustomUser, tag: AllowedTag, reason: str = ""
) -> AllowedTag:
    """Soft-delete a catalogue row; administrator-only, never a hard delete."""
    tag_policy.require_catalogue_administrator(
        actor, permission=tag_policy.CATALOGUE_DELETE_PERMISSION
    )
    locked = _lock_tag(tag)
    if locked.is_deleted:
        raise ValidationError("The tag is already archived.")
    locked.delete(deleted_by=actor, reason=reason)
    return locked


@transaction.atomic
def restore_tag(*, actor: EqmdCustomUser, tag: AllowedTag) -> AllowedTag:
    """Restore an archived row into the same identity, inactive."""
    tag_policy.require_catalogue_administrator(
        actor, permission=tag_policy.CATALOGUE_CHANGE_PERMISSION
    )
    locked = _lock_tag(tag)
    if not locked.is_deleted:
        raise ValidationError("Only archived tags can be restored.")
    locked.restore(restored_by=actor)
    return locked


@transaction.atomic
def transfer_responsibility(
    *, actor: EqmdCustomUser, tag: AllowedTag, recipient: EqmdCustomUser
) -> AllowedTag:
    """Transfer management to a current leader of the tag's own team."""
    tag_policy.require_catalogue_administrator(
        actor, permission=tag_policy.CATALOGUE_CHANGE_PERMISSION
    )
    locked = _lock_tag(tag)
    if locked.is_deleted:
        raise ValidationError("Archived tags must be restored before transfer.")
    if (
        locked.visibility != AllowedTag.Visibility.RESTRICTED
        or locked.specialty_id is None
    ):
        raise ValidationError(
            "Responsibility can only be transferred for a restricted team tag."
        )
    if locked.responsible_user_id == recipient.pk:
        raise ValidationError("The recipient is already the responsible leader.")
    if not tag_policy.is_eligible_transfer_recipient(
        recipient, locked.specialty
    ):
        raise ValidationError(
            "The recipient must currently lead this tag's specialty team."
        )
    previous_responsible = locked.responsible_user
    locked.responsible_user = recipient
    locked.updated_by = actor
    locked._history_user = actor
    locked._change_reason = (
        f"Catalogue responsibility transfer by {actor.username}"
    )
    locked.save(
        update_fields=[
            "responsible_user",
            "updated_by",
            "updated_at",
        ]
    )
    locked._record_transition(
        action=AllowedTagTransition.Action.TRANSFER,
        actor=actor,
        from_state=locked.lifecycle_state,
        to_state=locked.lifecycle_state,
        previous_responsible=previous_responsible,
        new_responsible=recipient,
    )
    return locked


@transaction.atomic
def edit_tag(
    *,
    actor: EqmdCustomUser,
    tag: AllowedTag,
    name: str | None = None,
    description: str | None = None,
    color: str | None = None,
) -> AllowedTag:
    """Edit descriptive fields for an administrator or responsible leader."""
    locked = _lock_tag(tag)
    tag_policy.require_tag_manager(actor, locked)
    if locked.is_deleted:
        raise ValidationError("Archived tags cannot be edited.")
    if name is not None:
        locked.name = name
    if description is not None:
        locked.description = description
    if color is not None:
        locked.color = color
    locked.updated_by = actor
    locked._history_user = actor
    locked.full_clean()
    locked._change_reason = f"Catalogue edit by {actor.username}"
    locked.save()
    return locked
