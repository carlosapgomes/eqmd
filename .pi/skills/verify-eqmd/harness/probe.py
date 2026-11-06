# Read-only probe: dump the rows a journey should have produced.
# Used as side-effect evidence next to the screenshots.
import json
import os

from apps.events.models import Event
from apps.patients.models import Patient

PATIENT_ID = os.environ.get("EQMD_VERIFY_PROBE_PATIENT", "")
PROBE_FILE = os.environ.get("EQMD_VERIFY_PROBE_FILE", "")

patient = Patient.all_objects.filter(pk=PATIENT_ID).first()
if patient is None:
    print("EQMD_VERIFY_PROBE=" + json.dumps({"patient_found": False}))
else:
    events = Event.all_objects.filter(patient_id=patient.pk).order_by("created_at")
    rows = []
    for event in events:
        promoted_by = getattr(event, "draft_promoted_by", None)
        finalized_by = getattr(event, "finalized_by", None)
        rows.append(
            {
                "id": str(event.pk),
                "event_type": event.event_type,
                "event_type_label": event.get_event_type_display(),
                "is_draft": event.is_draft,
                "is_deleted": event.is_deleted,
                "created_by": getattr(event.created_by, "email", None),
                "updated_by": getattr(event.updated_by, "email", None),
                "draft_promoted_by": getattr(promoted_by, "email", None),
                "draft_promoted_at": event.draft_promoted_at.isoformat()
                if event.draft_promoted_at
                else None,
                "finalized_by": getattr(finalized_by, "email", None),
                "finalized_at": event.finalized_at.isoformat()
                if getattr(event, "finalized_at", None)
                else None,
            }
        )

    payload = {
        "patient_found": True,
        "patient": {"id": str(patient.pk), "name": patient.name},
        "events": rows,
    }

    # Photo drafts additionally expose the stored file path, so a journey can
    # prove the hard delete removed the file from storage (read-only check).
    try:
        from pathlib import Path

        from django.conf import settings

        from apps.mediafiles.models import Photo

        photos = []
        for photo in Photo.objects.filter(patient_id=patient.pk):
            file_dir = Path(settings.MEDIA_ROOT) / (
                f"photos/{photo.created_at.strftime('%Y/%m')}/originals"
            )
            matches = sorted(file_dir.glob(f"{photo.file_id}.*")) if file_dir.exists() else []
            photos.append(
                {
                    "id": str(photo.pk),
                    "is_draft": photo.is_draft,
                    "file_id": str(photo.file_id),
                    "stored_files": [str(match) for match in matches],
                }
            )
        payload["photos"] = photos
    except Exception as error:  # photo app is optional for most journeys
        payload["photos_error"] = str(error)

    if PROBE_FILE:
        from pathlib import Path

        payload["probe_file"] = {
            "path": PROBE_FILE,
            "exists": Path(PROBE_FILE).exists(),
        }

    print("EQMD_VERIFY_PROBE=" + json.dumps(payload))
