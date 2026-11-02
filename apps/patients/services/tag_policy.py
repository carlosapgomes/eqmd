"""Authorization and invariant rules for the namespaced tag catalogue."""

from __future__ import annotations

import uuid
from collections.abc import Collection, Mapping
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import QuerySet

from apps.patients.models import AllowedTag

if TYPE_CHECKING:
    from apps.accounts.models import EqmdCustomUser, MedicalSpecialty, UserSpecialty

CATALOGUE_ADD_PERMISSION = "patients.add_allowedtag"
CATALOGUE_CHANGE_PERMISSION = "patients.change_allowedtag"
CATALOGUE_DELETE_PERMISSION = "patients.delete_allowedtag"
CATALOGUE_PERMISSIONS = frozenset(
    {
        CATALOGUE_ADD_PERMISSION,
        CATALOGUE_CHANGE_PERMISSION,
        CATALOGUE_DELETE_PERMISSION,
    }
)


def is_catalogue_administrator(actor: EqmdCustomUser | None) -> bool:
    """Return whether the actor holds administrative catalogue authority.

    Staff status alone is insufficient: a delegated operator also needs one of
    the existing Django-admin catalogue permissions.
    """
    if actor is None or not actor.is_authenticated or not actor.is_active:
        return False
    if actor.is_superuser:
        return True
    if not actor.is_staff:
        return False
    return bool(actor.get_all_permissions() & CATALOGUE_PERMISSIONS)


def require_catalogue_administrator(
    actor: EqmdCustomUser | None, *, permission: str | None = None
) -> None:
    """Deny catalogue mutations without administrative authority."""
    if actor is None or not is_catalogue_administrator(actor):
        raise PermissionDenied(
            "Catalogue administration requires an authorized administrator."
        )
    if permission is not None and not actor.has_perm(permission):
        raise PermissionDenied("Catalogue administration permission is missing.")


def can_manage_tag(actor: EqmdCustomUser | None, tag: AllowedTag) -> bool:
    """Return whether a responsible leader may edit/deactivate this tag.

    Leadership alone is insufficient: the actor must be the current responsible
    leader of the tag's active team and the tag must remain a custom restricted
    row in that team. Archived rows and authorship confer no authority.
    """
    if actor is None or not actor.is_authenticated or not actor.is_active:
        return False
    if tag.is_deleted:
        return False
    if tag.origin != AllowedTag.Origin.CUSTOM:
        return False
    if tag.visibility != AllowedTag.Visibility.RESTRICTED:
        return False
    if tag.specialty_id is None or tag.responsible_user_id != actor.pk:
        return False
    from apps.accounts.services import team_membership

    return team_membership.is_team_leader(actor, tag.specialty)


def require_tag_manager(
    actor: EqmdCustomUser | None,
    tag: AllowedTag,
    *,
    permission: str = CATALOGUE_CHANGE_PERMISSION,
) -> None:
    """Allow the responsible leader or an administrator with the permission."""
    if can_manage_tag(actor, tag):
        return
    require_catalogue_administrator(actor, permission=permission)


def lock_team_memberships(
    actor: EqmdCustomUser | None, specialty_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, UserSpecialty]:
    """Lock the actor's membership rows for these teams inside a transaction.

    Call this from the write transaction that performs the audited change: the
    row locks make a concurrent membership change wait until that transaction
    commits, so the authority read below cannot be invalidated before the write.
    Rows are returned regardless of state; the caller validates the state from
    the locked row.
    """
    if actor is None or not actor.is_active or not specialty_ids:
        return {}
    from apps.accounts.models import UserSpecialty

    rows = (
        UserSpecialty.objects.select_for_update(of=("self",))
        .filter(user=actor, specialty_id__in=specialty_ids)
        .select_related("specialty")
    )
    return {row.specialty_id: row for row in rows}


def _is_active_membership(membership: UserSpecialty) -> bool:
    """Return whether a locked membership row still grants team authority."""
    return membership.is_active and membership.specialty.is_active


def member_team_ids(actor: EqmdCustomUser | None) -> frozenset[uuid.UUID]:
    """Return the team ids whose restricted metadata the actor may read now.

    Read visibility is the union of every active membership in an active team,
    not just the selected current specialty. One query per request; never
    cached, so a revocation applies to the next response.
    """
    if actor is None or not actor.is_authenticated or not actor.is_active:
        return frozenset()
    from apps.accounts.services import team_membership

    return frozenset(
        team_membership.eligible_memberships(actor).values_list(
            "specialty_id", flat=True
        )
    )


def is_team_member(
    actor: EqmdCustomUser | None,
    tag: AllowedTag,
    *,
    locked_memberships: Mapping[uuid.UUID, UserSpecialty] | None = None,
    read_team_ids: Collection[uuid.UUID] | None = None,
) -> bool:
    """Return whether the actor currently belongs to the tag's own team.

    Write paths pass ``locked_memberships`` (see ``lock_team_memberships``) so
    membership is decided from the locked row instead of an unlocked read. Read
    projections may pass a ``read_team_ids`` snapshot instead; never pass it on
    a write path, where the locked row is the authority.
    """
    if actor is None or not actor.is_authenticated or not actor.is_active:
        return False
    if tag.specialty_id is None:
        return False
    if read_team_ids is not None:
        return tag.specialty_id in read_team_ids
    if locked_memberships is not None:
        membership = locked_memberships.get(tag.specialty_id)
        return membership is not None and _is_active_membership(membership)
    from apps.accounts.services import team_membership

    return (
        team_membership.eligible_memberships(actor)
        .filter(specialty_id=tag.specialty_id)
        .exists()
    )


def is_principal_tag(tag: AllowedTag) -> bool:
    """Return whether a team configured this tag as its principal tag."""
    if tag.specialty_id is None or tag.pk is None:
        return False
    from apps.accounts.models import MedicalSpecialty

    return MedicalSpecialty.objects.filter(principal_tag_id=tag.pk).exists()


def can_assign_tag(
    actor: EqmdCustomUser | None,
    tag: AllowedTag,
    *,
    locked_memberships: Mapping[uuid.UUID, UserSpecialty] | None = None,
) -> bool:
    """Return whether the actor may newly assign this tag to a patient.

    Principal and restricted tags need current team membership; non-principal
    public tags stay on the clinical mutation baseline. Catalogue
    administrators override team membership, and archived or inactive tags can
    never be newly assigned.
    """
    if tag.lifecycle_state != AllowedTag.LifecycleState.ACTIVE:
        return False
    return has_tag_authority(actor, tag, locked_memberships=locked_memberships)


def can_remove_tag(
    actor: EqmdCustomUser | None,
    tag: AllowedTag,
    *,
    locked_memberships: Mapping[uuid.UUID, UserSpecialty] | None = None,
    read_team_ids: Collection[uuid.UUID] | None = None,
) -> bool:
    """Return whether the actor may remove this tag from a patient.

    Removal uses the same per-tag authority as assignment but works in every
    lifecycle state, so historical associations stay removable. Read
    projections pass ``read_team_ids`` instead of locking membership rows.
    """
    return has_tag_authority(
        actor,
        tag,
        locked_memberships=locked_memberships,
        read_team_ids=read_team_ids,
    )


def has_tag_authority(
    actor: EqmdCustomUser | None,
    tag: AllowedTag,
    *,
    locked_memberships: Mapping[uuid.UUID, UserSpecialty] | None = None,
    read_team_ids: Collection[uuid.UUID] | None = None,
) -> bool:
    """Return whether the actor holds authority for this specific tag."""
    if actor is None or not actor.is_authenticated or not actor.is_active:
        return False
    if is_catalogue_administrator(actor):
        return True
    if tag.visibility == AllowedTag.Visibility.RESTRICTED:
        return is_team_member(
            actor,
            tag,
            locked_memberships=locked_memberships,
            read_team_ids=read_team_ids,
        )
    if is_principal_tag(tag):
        return is_team_member(
            actor,
            tag,
            locked_memberships=locked_memberships,
            read_team_ids=read_team_ids,
        )
    return True


def require_tag_authority(
    actor: EqmdCustomUser | None,
    tag: AllowedTag,
    *,
    locked_memberships: Mapping[uuid.UUID, UserSpecialty] | None = None,
) -> None:
    """Deny patient tag writes without per-tag authority."""
    if not has_tag_authority(actor, tag, locked_memberships=locked_memberships):
        raise PermissionDenied(
            "Tag assignment requires team membership or administrator authority."
        )


def is_eligible_transfer_recipient(
    recipient: EqmdCustomUser | None, specialty: MedicalSpecialty | None
) -> bool:
    """Return whether the recipient currently leads the tag's own team."""
    if recipient is None or not recipient.is_active or specialty is None:
        return False
    from apps.accounts.services import team_membership

    return team_membership.is_team_leader(recipient, specialty)


def eligible_transfer_recipient_queryset(
    *, include_user_id: int | None = None
) -> QuerySet[EqmdCustomUser]:
    """Return active users who currently lead at least one active team.

    ``include_user_id`` keeps a stale responsible reference selectable so an
    unrelated edit cannot silently clear historical attribution.
    """
    from django.db.models import Q

    from apps.accounts.models import EqmdCustomUser

    condition = Q(
        is_active=True,
        user_specialties__is_active=True,
        user_specialties__is_leader=True,
        user_specialties__specialty__is_active=True,
    )
    if include_user_id is not None:
        condition |= Q(pk=include_user_id)
    return EqmdCustomUser.objects.filter(condition).distinct()


def validate_principal_tag(
    *, specialty: MedicalSpecialty, tag: AllowedTag | None
) -> None:
    """Require a public tag from the specialty's own namespace."""
    if tag is None:
        return
    if tag.visibility != AllowedTag.Visibility.PUBLIC:
        raise ValidationError({"principal_tag": "The principal tag must be public."})
    if tag.specialty_id != specialty.pk:
        raise ValidationError(
            {
                "principal_tag": (
                    "The principal tag must belong to this specialty namespace."
                )
            }
        )


def validate_namespace_change(
    *,
    tag_pk: int,
    original_visibility: str,
    original_specialty_id: object,
    visibility: str,
    specialty_id: object,
) -> None:
    """Reject reclassification or moves while a tag is a principal reference."""
    from apps.accounts.models import MedicalSpecialty

    if not MedicalSpecialty.objects.filter(principal_tag_id=tag_pk).exists():
        return
    if visibility != AllowedTag.Visibility.PUBLIC:
        raise ValidationError(
            {
                "visibility": (
                    "A tag configured as a principal tag cannot be made "
                    "restricted while referenced."
                )
            }
        )
    if specialty_id != original_specialty_id:
        raise ValidationError(
            {
                "specialty": (
                    "A tag configured as a principal tag cannot change "
                    "namespace while referenced."
                )
            }
        )
