"""
Shared synthetic fixtures for mediafiles tests.

Centralizes the supported user/patient setup (Hospital was removed in the
single-hospital refactor) and the FilePond storage layout
(``photos/YYYY/MM/originals/<file_id>.<ext>``) so the model, form, and
security tests exercise the same current contracts.

All values are synthetic; no real patient or media data is used.
"""

import uuid
from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.patients.models import Patient

User = get_user_model()

TEST_MEDIA_DIR = Path(__file__).parent / "test_media"


def load_test_image_bytes(filename="small_image.jpg"):
    """Return the bytes of a synthetic test image from ``test_media/``."""
    return (TEST_MEDIA_DIR / filename).read_bytes()


def make_uploaded_image(filename="test.jpg", content=None):
    """Build a synthetic JPEG ``SimpleUploadedFile``."""
    if content is None:
        content = load_test_image_bytes()
    return SimpleUploadedFile(filename, content, content_type="image/jpeg")


def create_user(username="testuser", **kwargs):
    """Create a lifecycle-navigation-ready synthetic user.

    ``password_change_required=False`` and ``terms_accepted=True`` keep the
    core lifecycle middleware from redirecting view requests (same contract
    as the green ``NavigationReadyUserFactory`` usage in drugtemplates).
    """
    # Accept-and-drop caller-passed lifecycle flags: this factory is
    # lifecycle-navigation-ready by contract (flags forced below).
    kwargs.pop("password_change_required", None)
    kwargs.pop("terms_accepted", None)
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        password_change_required=False,
        terms_accepted=True,
        **kwargs,
    )


def create_patient(user, name="Test Patient"):
    """Create a synthetic patient linked to a creator."""
    return Patient.objects.create(
        name=name,
        birthday=date(1990, 1, 1),
        status=Patient.Status.OUTPATIENT,
        created_by=user,
        updated_by=user,
    )


def photo_original_dir(created_at=None):
    """Relative directory where FilePond stores photo originals."""
    created_at = created_at or timezone.now()
    return f"photos/{created_at.strftime('%Y/%m')}/originals"


def write_filepond_file(relative_dir, file_id, ext, content):
    """Write a synthetic file at the FilePond storage location.

    Returns the absolute path written so tests can assert on-disk state.
    """
    media_root = Path(settings.MEDIA_ROOT)
    target_dir = media_root / relative_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{file_id}{ext}"
    target.write_bytes(content)
    return target


def create_photo_on_disk(patient, user, content=None, filename="foto.jpg", **kwargs):
    """Create a Photo whose FilePond original exists on disk (servable)."""
    from apps.mediafiles.models import Photo

    content = load_test_image_bytes() if content is None else content
    file_id = str(uuid.uuid4())
    photo = Photo.objects.create(
        file_id=file_id,
        original_filename=filename,
        file_size=len(content),
        width=kwargs.pop("width", 100),
        height=kwargs.pop("height", 100),
        patient=patient,
        created_by=user,
        updated_by=user,
        description=kwargs.pop("description", "Test photo"),
        event_datetime=kwargs.pop(
            "event_datetime", timezone.now() - timezone.timedelta(hours=1)
        ),
        **kwargs,
    )
    write_filepond_file(photo_original_dir(photo.created_at), file_id, ".jpg", content)
    return photo


def create_videoclip_on_disk(
    patient, user, content=None, filename="test.mp4", **kwargs
):
    """Create a VideoClip whose FilePond original exists on disk (servable)."""
    from apps.mediafiles.models import VideoClip

    if content is None:
        content = (TEST_MEDIA_DIR / "test_video.mp4").read_bytes()
    file_id = str(uuid.uuid4())
    clip = VideoClip.objects.create(
        file_id=file_id,
        original_filename=filename,
        file_size=len(content),
        duration=kwargs.pop("duration", 30),
        width=kwargs.pop("width", 320),
        height=kwargs.pop("height", 240),
        video_codec=kwargs.pop("video_codec", "h264"),
        patient=patient,
        created_by=user,
        updated_by=user,
        description=kwargs.pop("description", "Test video"),
        event_datetime=kwargs.pop(
            "event_datetime", timezone.now() - timezone.timedelta(hours=1)
        ),
        **kwargs,
    )
    write_filepond_file(
        f"videos/{clip.created_at.strftime('%Y/%m')}/originals",
        file_id,
        ".mp4",
        content,
    )
    return clip
