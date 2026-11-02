"""Atomic tag audit event writes and conservative legacy snapshot resolution.

Every patient tag write records its timeline event together with one
``TagEventReference`` per acted-on tag. The reference holds the catalogue
identity plus the action-time snapshot (name, color, notes, visibility and team
attribution) so later renames, transfers or archival cannot detach history.

Legacy events only carry name snapshots. ``resolve_legacy_event`` classifies
them against the retained catalogue history; ambiguous or unresolvable rows stay
untouched and are never guessed. The same functions are used by the read-only
preflight command and by the data migration (which passes the historical
migration models).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from django.utils import timezone

from apps.events.models import (
    Event,
    TagAddedEvent,
    TagBulkRemoveEvent,
    TagEventReference,
    TagRemovedEvent,
)
from apps.patients.models import AllowedTag

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from apps.accounts.models import EqmdCustomUser
    from apps.patients.models import Patient

LegacyStatus = Literal["known", "ambiguous", "unresolved"]


@dataclass(frozen=True)
class LegacyTagResolution:
    """One legacy name snapshot resolved to at most one catalogue identity."""

    status: LegacyStatus
    tag_id: int | None = None


@dataclass(frozen=True)
class LegacyEventResolution:
    """Resolution of a whole legacy event, per-tag for bulk operations."""

    status: LegacyStatus
    tag_ids: tuple[int, ...] = ()


def _reference_defaults(tag: AllowedTag) -> dict[str, Any]:
    """Return the action-time snapshot fields stored on a new reference."""
    specialty = tag.specialty if tag.specialty_id is not None else None
    return {
        "tag_name": tag.name,
        "tag_color": tag.color,
        "tag_visibility": tag.visibility,
        "specialty_id": tag.specialty_id,
        "specialty_abbreviation": specialty.abbreviation if specialty else "",
    }


def _add_reference(
    *,
    event: Event,
    tag: AllowedTag,
    action: str,
    notes: str,
) -> TagEventReference:
    """Append the immutable catalogue reference for one audited action."""
    return TagEventReference.objects.create(
        event=event,
        tag=tag,
        action=action,
        tag_notes=notes,
        **_reference_defaults(tag),
    )


def record_tag_added(
    *, actor: EqmdCustomUser, patient: Patient, tag: AllowedTag, notes: str = ""
) -> TagAddedEvent:
    """Create the addition event and its catalogue reference."""
    event = TagAddedEvent.objects.create(
        patient=patient,
        event_datetime=timezone.now(),
        description=f"Tag '{tag.name}' adicionada",
        tag_name=tag.name,
        tag_color=tag.color,
        tag_notes=notes,
        created_by=actor,
        updated_by=actor,
    )
    _add_reference(
        event=event, tag=tag, action=TagEventReference.Action.ADDED, notes=notes
    )
    return event


def record_tag_removed(
    *, actor: EqmdCustomUser, patient: Patient, tag: AllowedTag, notes: str = ""
) -> TagRemovedEvent:
    """Create the removal event and its catalogue reference."""
    event = TagRemovedEvent.objects.create(
        patient=patient,
        event_datetime=timezone.now(),
        description=f"Tag '{tag.name}' removida",
        tag_name=tag.name,
        tag_color=tag.color,
        tag_notes=notes,
        created_by=actor,
        updated_by=actor,
    )
    _add_reference(
        event=event, tag=tag, action=TagEventReference.Action.REMOVED, notes=notes
    )
    return event


def record_bulk_removed(
    *,
    actor: EqmdCustomUser,
    patient: Patient,
    removed: Iterable[tuple[AllowedTag, str]],
) -> TagBulkRemoveEvent:
    """Create one bulk event with a per-tag reference for every removal."""
    removed_items = list(removed)
    names = [tag.name for tag, _ in removed_items]
    event = TagBulkRemoveEvent.objects.create(
        patient=patient,
        event_datetime=timezone.now(),
        description=f"{len(removed_items)} tag(s) removida(s) em lote",
        tag_count=len(removed_items),
        tag_names=", ".join(names),
        created_by=actor,
        updated_by=actor,
    )
    for tag, notes in removed_items:
        _add_reference(
            event=event, tag=tag, action=TagEventReference.Action.REMOVED, notes=notes
        )
    return event


def legacy_event_names(event: Any) -> list[str]:
    """Return the action-time names a legacy event snapshot kept."""
    bulk_names = getattr(event, "tag_names", None)
    if bulk_names is not None:
        return [name.strip() for name in str(bulk_names).split(",") if name.strip()]
    single_name = str(getattr(event, "tag_name", "") or "").strip()
    return [single_name] if single_name else []


def resolve_legacy_tag(
    *,
    snapshot_name: str,
    occurred_at: datetime | None,
    tags: QuerySet[AllowedTag] | None = None,
    history: QuerySet[Any] | None = None,
) -> LegacyTagResolution:
    """Match one legacy name snapshot to a single catalogue identity.

    Only rows that already carried the name when the event happened count as
    evidence, so a later rename cannot fabricate a match.
    """
    name = (snapshot_name or "").strip()
    if not name:
        return LegacyTagResolution("unresolved")
    tag_rows = tags if tags is not None else AllowedTag.all_objects.all()
    history_rows = (
        history if history is not None else AllowedTag.history.model.objects.all()
    )
    candidate_ids = set(tag_rows.filter(name=name).values_list("pk", flat=True))
    candidate_ids |= set(history_rows.filter(name=name).values_list("id", flat=True))
    if not candidate_ids:
        return LegacyTagResolution("unresolved")
    confirmed = [
        tag_id
        for tag_id in sorted(candidate_ids)
        if _historical_name(history_rows, tag_id=tag_id, occurred_at=occurred_at)
        == name
    ]
    if len(confirmed) == 1:
        return LegacyTagResolution("known", confirmed[0])
    if len(confirmed) > 1:
        return LegacyTagResolution("ambiguous")
    return LegacyTagResolution("unresolved")


def historical_version(
    *, tag_id: int, occurred_at: datetime | None, history: QuerySet[Any] | None = None
) -> Any | None:
    """Return the catalogue row version that identity had at the action time."""
    rows = history if history is not None else AllowedTag.history.model.objects.all()
    rows = rows.filter(id=tag_id)
    if occurred_at is not None:
        rows = rows.filter(history_date__lte=occurred_at)
    return rows.order_by("-history_date", "-pk").first()


def _historical_name(
    history_rows: QuerySet[Any], *, tag_id: int, occurred_at: datetime | None
) -> str | None:
    """Return the catalogue name that identity held at the action time."""
    version = historical_version(
        tag_id=tag_id, occurred_at=occurred_at, history=history_rows
    )
    if version is None:
        return None
    return str(version.name) if version.name is not None else None


def resolve_legacy_event(
    event: Any,
    *,
    tags: QuerySet[AllowedTag] | None = None,
    history: QuerySet[Any] | None = None,
) -> LegacyEventResolution:
    """Resolve every name snapshot of one legacy tag audit event."""
    names = legacy_event_names(event)
    if not names:
        return LegacyEventResolution("unresolved")
    resolutions = [
        resolve_legacy_tag(
            snapshot_name=name,
            occurred_at=getattr(event, "event_datetime", None),
            tags=tags,
            history=history,
        )
        for name in names
    ]
    statuses = {resolution.status for resolution in resolutions}
    if "ambiguous" in statuses:
        return LegacyEventResolution("ambiguous")
    if "unresolved" in statuses:
        return LegacyEventResolution("unresolved")
    tag_ids = tuple(
        resolution.tag_id for resolution in resolutions if resolution.tag_id is not None
    )
    if len(set(tag_ids)) != len(tag_ids):
        return LegacyEventResolution("ambiguous")
    return LegacyEventResolution("known", tag_ids)


def _tag_audit_events() -> QuerySet[Event]:
    return (
        Event.objects.filter(event_type__in=Event.TAG_AUDIT_EVENT_TYPES)
        .select_subclasses()
        .order_by("event_datetime", "pk")
    )


def all_tag_audit_events() -> QuerySet[Event]:
    """Return every live tag audit event, referenced or not."""
    return _tag_audit_events()


def unreferenced_tag_audit_events() -> QuerySet[Event]:
    """Return tag audit events that still have no catalogue reference."""
    referenced_ids = TagEventReference.objects.values("event_id")
    return _tag_audit_events().exclude(pk__in=referenced_ids)


def referenced_event_count() -> int:
    """Return how many tag audit events already carry catalogue references."""
    return TagEventReference.objects.values("event_id").distinct().count()
