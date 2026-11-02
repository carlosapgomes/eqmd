"""Requester-aware projections for every tag read surface.

Read visibility is decided per request from the current catalogue row and the
union of the actor's active team memberships (design D4/D7). Nothing here is
memoised across requests, so a revocation or a reclassification applies to the
very next response, including responses built from a shared cache payload.

Readers must serialise what these functions return instead of walking the ORM
relations themselves: hiding metadata in CSS or client-side code is not a
privacy control.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet

from apps.patients.models import AllowedTag, Tag
from apps.patients.services import tag_policy

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from apps.accounts.models import EqmdCustomUser
    from apps.patients.models import Patient

INVALID_TAG_FILTER_MESSAGE = "Filtro de tag inválido."

STATE_LABELS = {
    AllowedTag.LifecycleState.INACTIVE: "Inativa",
    AllowedTag.LifecycleState.ARCHIVED: "Arquivada",
}


class InvalidTagFilter(ValidationError):
    """The requested single-tag filter is not a visible catalogue identity.

    The message is deliberately generic: distinguishing unknown, archived and
    inaccessible identifiers would turn the filter into an existence oracle.
    """


@dataclass(frozen=True)
class Visibility:
    """The requesting actor's tag visibility for one request."""

    team_ids: frozenset[uuid.UUID]
    is_administrator: bool

    @classmethod
    def for_actor(cls, actor: EqmdCustomUser | None) -> Visibility:
        """Snapshot current membership-derived visibility for this request."""
        return cls(
            team_ids=tag_policy.member_team_ids(actor),
            is_administrator=tag_policy.is_catalogue_administrator(actor),
        )

    def can_read(self, tag: AllowedTag) -> bool:
        """Return whether this actor may read the tag's metadata now."""
        if self.is_administrator:
            return True
        if tag.visibility == AllowedTag.Visibility.PUBLIC:
            return True
        return tag.specialty_id is not None and tag.specialty_id in self.team_ids

    def can_remove(self, actor: EqmdCustomUser | None, tag: AllowedTag) -> bool:
        """Return whether this actor may remove an association of this tag."""
        return tag_policy.can_remove_tag(actor, tag, read_team_ids=self.team_ids)


@dataclass(frozen=True)
class TagBadge:
    """One requester-visible catalogue entry with lifecycle context."""

    tag_id: int
    name: str
    display_name: str
    color: str
    state: str
    state_label: str
    team_abbreviation: str
    is_restricted: bool


@dataclass(frozen=True)
class PatientTagBadge:
    """One requester-visible patient association with lifecycle context."""

    association_id: uuid.UUID
    tag_id: int
    name: str
    display_name: str
    color: str
    state: str
    state_label: str
    team_abbreviation: str
    is_restricted: bool
    can_remove: bool
    notes: str
    created_at: datetime
    created_by_name: str


def _team_abbreviation(tag: AllowedTag) -> str:
    """Return the owning team's abbreviation, empty for the global namespace."""
    if tag.specialty_id is None or tag.specialty is None:
        return ""
    return str(tag.specialty.abbreviation)


def tag_badge(tag: AllowedTag) -> TagBadge:
    """Project one catalogue row the caller is already allowed to read."""
    return TagBadge(
        tag_id=tag.pk,
        name=tag.name,
        display_name=tag.display_name,
        color=tag.color,
        state=tag.lifecycle_state,
        state_label=STATE_LABELS.get(tag.lifecycle_state, ""),
        team_abbreviation=_team_abbreviation(tag),
        is_restricted=tag.visibility == AllowedTag.Visibility.RESTRICTED,
    )


def visible_catalogue(actor: EqmdCustomUser | None) -> QuerySet[AllowedTag]:
    """Return every readable catalogue row, archived rows included."""
    queryset = AllowedTag.all_objects.select_related("specialty")
    visibility = Visibility.for_actor(actor)
    if visibility.is_administrator:
        return queryset
    condition = Q(visibility=AllowedTag.Visibility.PUBLIC)
    if visibility.team_ids:
        condition |= Q(
            visibility=AllowedTag.Visibility.RESTRICTED,
            specialty_id__in=visibility.team_ids,
        )
    return queryset.filter(condition)


def filter_tag_options(actor: EqmdCustomUser | None) -> list[TagBadge]:
    """Return the single-tag filter options this actor may select.

    Keeps the legacy list behaviour (active tags already used by a patient)
    while removing every catalogue entry the actor may not read.
    """
    queryset = (
        visible_catalogue(actor)
        .filter(is_active=True, tag_instances__isnull=False)
        .distinct()
        .order_by("name")
    )
    return [tag_badge(tag) for tag in queryset]


def map_tag_options(actor: EqmdCustomUser | None) -> list[dict[str, object]]:
    """Return the ward-map tag selector options from the current catalogue."""
    return [
        {"id": tag.pk, "name": tag.name, "color": tag.color}
        for tag in visible_catalogue(actor).order_by("name")
    ]


def resolve_tag_filter(actor: EqmdCustomUser | None, raw_value: str) -> AllowedTag:
    """Resolve a legacy ``tag=<id>`` value against the visible catalogue.

    Raises :class:`InvalidTagFilter` for a malformed value, an unknown identity
    and an identity the actor may not read. Callers must render an empty result
    set plus the generic message instead of silently widening the search.
    """
    try:
        tag_pk = int(str(raw_value).strip())
    except (TypeError, ValueError) as error:
        raise InvalidTagFilter(INVALID_TAG_FILTER_MESSAGE) from error
    tag = visible_catalogue(actor).filter(pk=tag_pk).first()
    if tag is None:
        raise InvalidTagFilter(INVALID_TAG_FILTER_MESSAGE)
    return tag


def _association_badge(
    actor: EqmdCustomUser | None,
    association: Tag,
    *,
    visibility: Visibility,
) -> PatientTagBadge | None:
    """Project one association, or return ``None`` when it must stay hidden."""
    tag = association.allowed_tag
    if not visibility.can_read(tag):
        return None
    badge = tag_badge(tag)
    creator = association.created_by
    return PatientTagBadge(
        association_id=association.pk,
        tag_id=badge.tag_id,
        name=badge.name,
        display_name=badge.display_name,
        color=badge.color,
        state=badge.state,
        state_label=badge.state_label,
        team_abbreviation=badge.team_abbreviation,
        is_restricted=badge.is_restricted,
        can_remove=visibility.can_remove(actor, tag),
        notes=association.notes,
        created_at=association.created_at,
        created_by_name=creator.get_full_name() or creator.username,
    )


def patient_tag_badges_by_patient(
    actor: EqmdCustomUser | None, patient_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, list[PatientTagBadge]]:
    """Return visible association badges for a bounded set of patients."""
    if not patient_ids:
        return {}
    visibility = Visibility.for_actor(actor)
    associations = (
        Tag.objects.filter(patient_id__in=patient_ids)
        .select_related("allowed_tag__specialty", "created_by")
        .order_by("created_at", "pk")
    )
    badges: dict[uuid.UUID, list[PatientTagBadge]] = {}
    for association in associations:
        badge = _association_badge(actor, association, visibility=visibility)
        if badge is None:
            continue
        badges.setdefault(association.patient_id, []).append(badge)
    return badges


def patient_tag_badges(
    actor: EqmdCustomUser | None, patient: Patient
) -> list[PatientTagBadge]:
    """Return the current associations the actor may read, in creation order."""
    return patient_tag_badges_by_patient(actor, [patient.pk]).get(patient.pk, [])


def attach_patient_tag_badges(
    patients: Iterable[Patient], *, actor: EqmdCustomUser | None
) -> None:
    """Attach ``tag_badges`` to each patient from one batched projection."""
    rows = list(patients)
    badges = patient_tag_badges_by_patient(actor, [row.pk for row in rows])
    for patient in rows:
        patient.tag_badges = badges.get(patient.pk, [])


def patient_tag_json(
    actor: EqmdCustomUser | None, patient: Patient
) -> list[dict[str, object]]:
    """Serialize the requester-visible associations for the tag JSON API."""
    return [
        {
            "id": str(badge.association_id),
            "name": badge.name,
            "display_name": badge.display_name,
            "color": badge.color,
            "allowed_tag_id": badge.tag_id,
            "notes": badge.notes,
            "state": badge.state,
            "state_label": badge.state_label,
            "team_abbreviation": badge.team_abbreviation,
            "can_remove": badge.can_remove,
            "created_at": badge.created_at.isoformat(),
            "created_by": badge.created_by_name,
        }
        for badge in patient_tag_badges(actor, patient)
    ]


def available_tag_json(
    actor: EqmdCustomUser | None, patient: Patient
) -> list[dict[str, object]]:
    """Serialize the readable, active, not-yet-assigned catalogue entries."""
    assigned_tag_ids = patient.patient_tags.values_list("allowed_tag_id", flat=True)
    queryset = (
        visible_catalogue(actor)
        .filter(is_active=True)
        .exclude(pk__in=assigned_tag_ids)
        .order_by("name")
    )
    return [
        {
            "id": tag.pk,
            "name": tag.name,
            "display_name": tag.display_name,
            "color": tag.color,
            "description": tag.description,
            "state": tag.lifecycle_state,
            "team_abbreviation": _team_abbreviation(tag),
        }
        for tag in queryset
    ]
