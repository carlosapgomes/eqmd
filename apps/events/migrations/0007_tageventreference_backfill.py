"""Conservatively link legacy tag snapshots to stable catalogue identities.

Legacy tag events only kept the tag name (and, for bulk events, a comma
separated list of names). This backfill creates references only where the
retained catalogue history proves exactly one identity carried that name when
the event happened. Ambiguous or unresolvable events stay untouched: their
snapshots, descriptions and event ids are never rewritten or guessed.

The classification rules live in ``apps.events.services.tag_audit`` and are
called here with the historical migration models, so the migration depends on
the frozen schema instead of today's runtime model state.
"""

from typing import Any, ClassVar

from django.db import migrations

ADDED = "added"
REMOVED = "removed"


def _legacy_snapshot(
    *,
    event: Any,
    action: str,
    tag_id: int,
    tag_name: str,
    tag_color: str,
    tag_notes: str,
    history: Any,
    abbreviations: dict[Any, str],
) -> dict[str, Any]:
    """Build the action-time reference payload from retained catalogue history."""
    from apps.events.services import tag_audit

    version = tag_audit.historical_version(
        tag_id=tag_id, occurred_at=event.event_datetime, history=history
    )
    specialty_id = version.specialty_id if version is not None else None
    return {
        "event_id": event.pk,
        "action": action,
        "tag_id": tag_id,
        "tag_name": tag_name,
        "tag_color": version.color if version is not None else tag_color,
        "tag_notes": tag_notes,
        "tag_visibility": version.visibility if version is not None else "public",
        "specialty_id": specialty_id,
        "specialty_abbreviation": abbreviations.get(specialty_id, ""),
    }


def backfill_tag_event_references(apps, schema_editor):
    """Create references for unambiguous legacy events only."""
    from apps.events.services import tag_audit

    reference_model = apps.get_model("events", "TagEventReference")
    added_model = apps.get_model("events", "TagAddedEvent")
    removed_model = apps.get_model("events", "TagRemovedEvent")
    bulk_model = apps.get_model("events", "TagBulkRemoveEvent")
    tag_model = apps.get_model("patients", "AllowedTag")
    history_model = apps.get_model("patients", "HistoricalAllowedTag")
    specialty_model = apps.get_model("accounts", "MedicalSpecialty")

    tags = tag_model.objects.all()
    history = history_model.objects.all()
    referenced_ids = set(reference_model.objects.values_list("event_id", flat=True))
    abbreviations = dict(specialty_model.objects.values_list("pk", "abbreviation"))

    for action, model in ((ADDED, added_model), (REMOVED, removed_model)):
        for event in model.objects.exclude(pk__in=referenced_ids).order_by("pk"):
            resolution = tag_audit.resolve_legacy_event(
                event, tags=tags, history=history
            )
            if resolution.status != "known":
                continue
            reference_model.objects.create(
                **_legacy_snapshot(
                    event=event,
                    action=action,
                    tag_id=resolution.tag_ids[0],
                    tag_name=event.tag_name,
                    tag_color=event.tag_color,
                    tag_notes=event.tag_notes,
                    history=history,
                    abbreviations=abbreviations,
                )
            )

    for event in bulk_model.objects.exclude(pk__in=referenced_ids).order_by("pk"):
        resolution = tag_audit.resolve_legacy_event(event, tags=tags, history=history)
        if resolution.status != "known":
            continue
        names = tag_audit.legacy_event_names(event)
        for tag_id, tag_name in zip(resolution.tag_ids, names):
            reference_model.objects.create(
                **_legacy_snapshot(
                    event=event,
                    action=REMOVED,
                    tag_id=tag_id,
                    tag_name=tag_name,
                    tag_color=tags.get(pk=tag_id).color,
                    tag_notes="",
                    history=history,
                    abbreviations=abbreviations,
                )
            )


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str]]] = [
        ("accounts", "0007_medicalspecialty_principal_tag"),
        ("events", "0006_tageventreference"),
        ("patients", "0005_allowedtag_lifecycle_responsibility"),
    ]

    operations: ClassVar[list[Any]] = [
        migrations.RunPython(backfill_tag_event_references, migrations.RunPython.noop),
    ]
