"""Authorization and invariant rules for the namespaced tag catalogue."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import QuerySet

from apps.patients.models import AllowedTag

if TYPE_CHECKING:
    from apps.accounts.models import EqmdCustomUser, MedicalSpecialty

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
