from pathlib import Path
from django.conf import settings
from django.utils import timezone
from apps.mediafiles.utils import normalize_filename as mediafiles_normalize_filename


def get_consent_upload_path(instance, filename: str) -> str:
    if not filename:
        raise ValueError("Filename cannot be empty")

    ext = Path(filename).suffix.lower()
    if not ext:
        raise ValueError("File must have an extension")

    allowed_extensions = (
        getattr(settings, "MEDIA_ALLOWED_IMAGE_EXTENSIONS", [])
        + [".pdf", ".heic", ".heif"]
    )
    if ext not in allowed_extensions:
        raise ValueError(f"File extension {ext} not allowed")

    secure_filename = f"{instance.id}{ext}"
    year_month = timezone.now().strftime("%Y/%m")
    secure_path = f"consent_forms/{year_month}/attachments/{secure_filename}"

    if ".." in secure_path or secure_path.startswith("/"):
        raise ValueError("Invalid path detected")

    return secure_path


def normalize_filename(filename: str) -> str:
    return mediafiles_normalize_filename(filename)
