"""Focused services for durable specialty team membership."""

from __future__ import annotations

import uuid

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts.models import (
    EqmdCustomUser,
    MedicalSpecialty,
    UserProfile,
    UserSpecialty,
)

MEMBERSHIP_CHANGE_PERMISSION = "accounts.change_userspecialty"
MEMBERSHIP_ADD_PERMISSION = "accounts.add_userspecialty"


def eligible_memberships(user: EqmdCustomUser) -> QuerySet[UserSpecialty]:
    """Return active memberships whose specialty is also active."""
    return UserSpecialty.objects.filter(
        user=user, is_active=True, specialty__is_active=True
    ).select_related("specialty")


def eligible_specialties(user: EqmdCustomUser) -> list[MedicalSpecialty]:
    """Return the specialty teams the user may currently act for."""
    return [membership.specialty for membership in eligible_memberships(user)]


def leader_specialties(user: EqmdCustomUser) -> list[MedicalSpecialty]:
    """Return the teams the user currently leads."""
    return [
        membership.specialty
        for membership in eligible_memberships(user)
        if membership.is_leader
    ]


def is_team_leader(user: EqmdCustomUser, specialty: MedicalSpecialty) -> bool:
    """Return whether the user currently leads an active team."""
    return eligible_memberships(user).filter(
        specialty_id=specialty.pk, is_leader=True
    ).exists()


def eligible_specialty_queryset(user: EqmdCustomUser) -> QuerySet[MedicalSpecialty]:
    """Return selectable current specialties for a profile form."""
    return MedicalSpecialty.objects.filter(
        users__user=user, users__is_active=True, is_active=True
    ).distinct().order_by("name")


def is_eligible(user: EqmdCustomUser, specialty_id: uuid.UUID) -> bool:
    """Return whether the user has an active membership in an active specialty."""
    return eligible_memberships(user).filter(specialty_id=specialty_id).exists()


def get_eligible_specialty(
    user: EqmdCustomUser, specialty_id: uuid.UUID
) -> MedicalSpecialty:
    """Resolve a specialty only when the user may currently select it."""
    membership = eligible_memberships(user).filter(specialty_id=specialty_id).first()
    if membership is None:
        raise ValidationError("Specialty is not available for this user.")
    return membership.specialty


def resolve_current_specialty(profile: UserProfile) -> MedicalSpecialty | None:
    """Return the valid current context, clearing a revoked selection."""
    current = profile.current_specialty
    if current is None:
        return None
    if is_eligible(profile.user, current.pk):
        return current
    UserProfile.objects.filter(pk=profile.pk).update(current_specialty=None)
    profile.current_specialty = None
    return None


def set_current_specialty(
    *, profile: UserProfile, specialty: MedicalSpecialty
) -> None:
    """Persist a current specialty after request-time eligibility validation."""
    if not is_eligible(profile.user, specialty.pk):
        raise ValidationError("Specialty is not available for this user.")
    profile.current_specialty = specialty
    profile.save(update_fields=["current_specialty"])


def require_membership_administrator(
    actor: EqmdCustomUser | None, *, adding: bool = False
) -> None:
    """Deny membership mutations to anyone without administrator authority."""
    if actor is None or not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("Membership administration requires an administrator.")
    if actor.is_superuser:
        return
    if not actor.is_staff:
        raise PermissionDenied("Membership administration requires an administrator.")
    required = {MEMBERSHIP_CHANGE_PERMISSION}
    if adding:
        required.add(MEMBERSHIP_ADD_PERMISSION)
    if not required.issubset(actor.get_all_permissions()):
        raise PermissionDenied("Membership administration permission is missing.")


def _clear_current_context(membership: UserSpecialty) -> None:
    UserProfile.objects.filter(
        user=membership.user, current_specialty=membership.specialty
    ).update(current_specialty=None)


@transaction.atomic
def grant_membership(
    *, actor: EqmdCustomUser, user: EqmdCustomUser, specialty: MedicalSpecialty
) -> UserSpecialty:
    """Grant or reactivate a retained membership without restoring leadership."""
    existing = (
        UserSpecialty.objects.select_for_update()
        .filter(user=user, specialty=specialty)
        .first()
    )
    require_membership_administrator(actor, adding=existing is None)
    if not specialty.is_active:
        raise ValidationError("Cannot grant membership in an inactive specialty.")
    if existing is None:
        return UserSpecialty.objects.create(
            user=user, specialty=specialty, is_active=True, assigned_by=actor
        )
    if not existing.is_active:
        existing.is_active = True
        existing.deactivated_at = None
        existing.deactivated_by = None
        existing.reactivated_at = timezone.now()
        existing.reactivated_by = actor
        existing.save(
            update_fields=[
                "is_active",
                "deactivated_at",
                "deactivated_by",
                "reactivated_at",
                "reactivated_by",
            ]
        )
    return existing


@transaction.atomic
def revoke_membership(*, actor: EqmdCustomUser, membership: UserSpecialty) -> UserSpecialty:
    """Deactivate a membership, dropping leadership but retaining the row."""
    require_membership_administrator(actor)
    locked = UserSpecialty.objects.select_for_update().get(pk=membership.pk)
    if locked.is_active:
        now = timezone.now()
        locked.is_active = False
        locked.deactivated_at = now
        locked.deactivated_by = actor
        if locked.is_leader:
            locked.is_leader = False
            locked.leadership_revoked_at = now
            locked.leadership_revoked_by = actor
        locked.save(
            update_fields=[
                "is_active",
                "deactivated_at",
                "deactivated_by",
                "is_leader",
                "leadership_revoked_at",
                "leadership_revoked_by",
            ]
        )
    _clear_current_context(locked)
    membership.refresh_from_db()
    return membership


@transaction.atomic
def grant_leadership(
    *, actor: EqmdCustomUser, membership: UserSpecialty
) -> UserSpecialty:
    """Grant leadership to an active member of an active specialty."""
    require_membership_administrator(actor)
    locked = UserSpecialty.objects.select_for_update().get(pk=membership.pk)
    if not locked.is_active or not locked.specialty.is_active:
        raise ValidationError(
            "Leadership requires active membership in an active specialty."
        )
    locked.is_leader = True
    locked.leadership_granted_at = timezone.now()
    locked.leadership_granted_by = actor
    locked.leadership_revoked_at = None
    locked.leadership_revoked_by = None
    locked.save(
        update_fields=[
            "is_leader",
            "leadership_granted_at",
            "leadership_granted_by",
            "leadership_revoked_at",
            "leadership_revoked_by",
        ]
    )
    membership.refresh_from_db()
    return membership


@transaction.atomic
def revoke_leadership(
    *, actor: EqmdCustomUser, membership: UserSpecialty
) -> UserSpecialty:
    """Remove leadership while keeping the membership active."""
    require_membership_administrator(actor)
    locked = UserSpecialty.objects.select_for_update().get(pk=membership.pk)
    if locked.is_leader:
        locked.is_leader = False
        locked.leadership_revoked_at = timezone.now()
        locked.leadership_revoked_by = actor
        locked.save(
            update_fields=[
                "is_leader",
                "leadership_revoked_at",
                "leadership_revoked_by",
            ]
        )
    membership.refresh_from_db()
    return membership
