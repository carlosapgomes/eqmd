"""Retained per-specialty tag filter preferences (design D6).

One preference belongs to the retained ``UserSpecialty`` membership. The
record's absence means "not configured yet"; a record without tags means an
intentionally empty selection. Automatic defaults are recomputed on every
request from the current valid specialty, so an inactive, archived or
inaccessible tag is omitted with a generic warning and a temporarily invalid
saved identity is never rewritten.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.accounts.models import (
    MedicalSpecialty,
    UserProfile,
    UserSpecialty,
    UserSpecialtyTagPreference,
)
from apps.accounts.services import team_membership
from apps.patients.models import AllowedTag
from apps.patients.services import tag_filters, tag_projection

if TYPE_CHECKING:
    from django.http import QueryDict

    from apps.accounts.models import EqmdCustomUser
    from apps.patients.services.tag_projection import TagBadge

UNAVAILABLE_DEFAULTS_WARNING = (
    "Alguns filtros padrão da especialidade estão indisponíveis e foram ignorados."
)
SAVE_REJECTED_MESSAGE = (
    "Não foi possível salvar a preferência: a seleção contém tags indisponíveis."
)
STALE_CONTEXT_MESSAGE = (
    "A especialidade ativa mudou; recarregue a página e tente novamente."
)
SAVE_SUCCESS_MESSAGE = "Preferência de tags salva para a especialidade ativa."


@dataclass(frozen=True)
class TagPreferenceState:
    """The automatic or explicit filter state for one patient-list request."""

    selection: tag_filters.TagFilterSelection
    specialty: MedicalSpecialty | None
    has_saved_preference: bool = False
    warning: str = ""
    error: str = ""


@dataclass(frozen=True)
class TagPreferenceSummary:
    """One retained membership rendered on the preference overview page."""

    membership: UserSpecialty
    has_preference: bool
    tags: tuple[TagBadge, ...]
    mode: str
    mode_label: str
    omitted_count: int


def current_specialty(actor: EqmdCustomUser | None) -> MedicalSpecialty | None:
    """Return the request-time valid current specialty, if any."""
    if actor is None or not actor.is_authenticated:
        return None
    profile = UserProfile.objects.filter(user=actor).first()
    if profile is None:
        return None
    return profile.effective_current_specialty


def _eligible_membership(
    actor: EqmdCustomUser, specialty: MedicalSpecialty
) -> UserSpecialty | None:
    return (
        team_membership.eligible_memberships(actor)
        .filter(specialty_id=specialty.pk)
        .first()
    )


def _saved_tag_ids(preference: UserSpecialtyTagPreference) -> tuple[int, ...]:
    """Return every stored identity, archived rows included."""
    return tuple(
        AllowedTag.all_objects.filter(specialty_preferences=preference)
        .order_by("pk")
        .values_list("pk", flat=True)
    )


def _visible_active_tags(
    actor: EqmdCustomUser | None, tag_ids: tuple[int, ...]
) -> tuple[AllowedTag, ...]:
    """Keep only identities that are currently readable and active."""
    if not tag_ids:
        return ()
    rows = {
        tag.pk: tag
        for tag in tag_projection.visible_catalogue(actor).filter(
            pk__in=tag_ids, is_active=True
        )
    }
    return tuple(rows[tag_id] for tag_id in tag_ids if tag_id in rows)


def automatic_state(actor: EqmdCustomUser | None) -> TagPreferenceState:
    """Return the saved preference, principal fallback or no default."""
    specialty = current_specialty(actor)
    empty = tag_filters.TagFilterSelection()
    if actor is None or specialty is None:
        return TagPreferenceState(selection=empty, specialty=None)
    membership = _eligible_membership(actor, specialty)
    preference = (
        getattr(membership, "tag_preference", None) if membership is not None else None
    )
    if preference is not None:
        saved_ids = _saved_tag_ids(preference)
        tags = _visible_active_tags(actor, saved_ids)
        mode = (
            preference.mode
            if preference.mode in tag_filters.MATCH_MODES
            else tag_filters.DEFAULT_MODE
        )
        return TagPreferenceState(
            selection=tag_filters.TagFilterSelection(
                tags=tags, mode=mode, source=tag_filters.SOURCE_SAVED
            ),
            specialty=specialty,
            has_saved_preference=True,
            warning=(
                UNAVAILABLE_DEFAULTS_WARNING
                if len(tags) != len(saved_ids)
                else ""
            ),
        )
    if specialty.principal_tag is None:
        return TagPreferenceState(selection=empty, specialty=specialty)
    tags = _visible_active_tags(actor, (specialty.principal_tag.pk,))
    if not tags:
        return TagPreferenceState(
            selection=empty,
            specialty=specialty,
            warning=UNAVAILABLE_DEFAULTS_WARNING,
        )
    return TagPreferenceState(
        selection=tag_filters.TagFilterSelection(
            tags=tags,
            mode=tag_filters.DEFAULT_MODE,
            source=tag_filters.SOURCE_PRINCIPAL,
        ),
        specialty=specialty,
    )


def resolve_request_state(
    actor: EqmdCustomUser | None, query: QueryDict
) -> TagPreferenceState:
    """Apply D6 precedence: manual state, saved preference, principal, none."""
    automatic = automatic_state(actor)
    try:
        explicit = tag_filters.parse_tag_selection(actor, query)
    except tag_projection.InvalidTagFilter:
        return TagPreferenceState(
            selection=tag_filters.TagFilterSelection(),
            specialty=automatic.specialty,
            has_saved_preference=automatic.has_saved_preference,
            error=tag_projection.INVALID_TAG_FILTER_MESSAGE,
        )
    if not explicit.is_manual:
        return automatic
    return TagPreferenceState(
        selection=explicit,
        specialty=automatic.specialty,
        has_saved_preference=automatic.has_saved_preference,
    )


@transaction.atomic
def save_preference(
    *,
    actor: EqmdCustomUser,
    specialty_id: uuid.UUID,
    tag_ids: tuple[int, ...],
    mode: str,
) -> UserSpecialtyTagPreference:
    """Persist tags and mode for the actor's still-current membership only."""
    if mode not in tag_filters.MATCH_MODES:
        raise ValidationError(SAVE_REJECTED_MESSAGE)
    specialty = current_specialty(actor)
    if specialty is None or specialty.pk != specialty_id:
        raise PermissionDenied(STALE_CONTEXT_MESSAGE)
    membership = (
        team_membership.eligible_memberships(actor)
        .select_for_update()
        .filter(specialty_id=specialty.pk)
        .first()
    )
    if membership is None:
        raise PermissionDenied(STALE_CONTEXT_MESSAGE)
    identifiers = tag_filters.parse_tag_ids(tag_ids)
    tags = list(
        tag_projection.visible_catalogue(actor).filter(
            pk__in=identifiers, is_active=True
        )
    )
    if len(tags) != len(identifiers):
        raise ValidationError(SAVE_REJECTED_MESSAGE)

    preference, _ = UserSpecialtyTagPreference.objects.select_for_update().get_or_create(
        membership=membership
    )
    preference.mode = mode
    preference.save(update_fields=["mode", "updated_at"])
    preference.tags.set(tags)
    return preference


def preference_summaries(actor: EqmdCustomUser) -> list[TagPreferenceSummary]:
    """Return retained memberships with their stored, readable settings."""
    memberships = (
        UserSpecialty.objects.filter(user=actor)
        .select_related("specialty")
        .prefetch_related("tag_preference__tags")
        .order_by("-is_active", "specialty__name")
    )
    visibility = tag_projection.Visibility.for_actor(actor)
    summaries: list[TagPreferenceSummary] = []
    for membership in memberships:
        preference = getattr(membership, "tag_preference", None)
        mode = tag_filters.DEFAULT_MODE
        saved: list[AllowedTag] = []
        if preference is not None:
            saved = list(
                AllowedTag.all_objects.filter(specialty_preferences=preference).order_by(
                    "pk"
                )
            )
            if preference.mode in tag_filters.MATCH_MODES:
                mode = preference.mode
        visible = tuple(tag for tag in saved if visibility.can_read(tag))
        summaries.append(
            TagPreferenceSummary(
                membership=membership,
                has_preference=preference is not None,
                tags=tuple(tag_projection.tag_badge(tag) for tag in visible),
                mode=mode,
                mode_label=tag_filters.MODE_LABELS[mode],
                omitted_count=len(saved) - len(visible),
            )
        )
    return summaries
