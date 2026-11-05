"""Media draft deletion: stored-file cleanup on top of the generic helper.

``delete_event_record`` owns the method decision (hard delete only for drafts
that were never finalized; design D7) but deliberately knows nothing about
stored files. Media types add removal of the artifacts a hard delete would
otherwise leave behind:

- photo: the single FilePond original plus the thumbnail when present;
- photo series: every member original plus its thumbnail (the parent row alone
  is not enough — members are separate rows holding separate files);
- video clip: the FilePond original only (video thumbnails do not exist).

Cleanup resolves the FilePond layout the upload forms write
(``<media_type>/YYYY/MM/originals/<file_id>.<ext>``) and the thumbnail path
recorded on the row, and removes only artifacts that exist, so a missing file
never blocks the deletion. The soft-delete path keeps every file: those rows
stay recoverable.
"""

from pathlib import Path

from django.conf import settings

from apps.events.services.event_deletion import delete_event_record

from ..models import Photo, PhotoSeries, VideoClip


def delete_media_event_record(event, *, deleted_by=None, reason=""):
    """Delete ``event`` by the path its state and history require.

    Args:
        event: The Photo, PhotoSeries, or VideoClip to delete.
        deleted_by: The acting user recorded on the soft-delete path.
        reason: Optional soft-delete reason.

    Returns:
        bool: True when the row was hard-deleted (row and artifacts removed),
        False when it was soft-deleted (artifacts stay on disk).
    """
    # Collect first: hard-deleting a series cascades its member rows.
    artifact_paths = collect_media_artifact_paths(event)
    hard_deleted = delete_event_record(event, deleted_by=deleted_by, reason=reason)

    if hard_deleted:
        for path in artifact_paths:
            path.unlink(missing_ok=True)

    return hard_deleted


def collect_media_artifact_paths(event):
    """Return the stored artifacts that exist on disk for ``event``."""
    if isinstance(event, Photo):
        return _file_id_artifacts(
            "photos", event.created_at, event.file_id
        ) + _thumbnail_artifact(event.thumbnail_path)

    if isinstance(event, PhotoSeries):
        paths = []
        for member in event.photoseriesfile_set.all():
            paths.extend(
                _file_id_artifacts(
                    "photo_series", event.created_at, member.file_id
                )
            )
            paths.extend(_thumbnail_artifact(member.thumbnail_path))
        return paths

    if isinstance(event, VideoClip):
        return _file_id_artifacts("videos", event.created_at, event.file_id)

    return []


def _file_id_artifacts(media_dir, anchor, file_id):
    """Return the existing FilePond originals stored for ``file_id``."""
    if not file_id:
        return []

    originals_dir = (
        Path(settings.MEDIA_ROOT)
        / media_dir
        / anchor.strftime("%Y/%m")
        / "originals"
    )
    if not originals_dir.is_dir():
        return []

    return [path for path in originals_dir.glob(f"{file_id}.*") if path.is_file()]


def _thumbnail_artifact(thumbnail_path):
    """Return the existing thumbnail file recorded on a row, if any."""
    if not thumbnail_path:
        return []

    path = Path(settings.MEDIA_ROOT) / thumbnail_path
    return [path] if path.is_file() else []
