from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError

from apps.mediafiles.security import FileValidator


ALLOWED_IMAGE_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
    ".heif",
]

ALLOWED_IMAGE_MIME_TYPES = [
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
]


def _validate_heic_header(uploaded_file):
    uploaded_file.seek(0)
    header = uploaded_file.read(32)
    uploaded_file.seek(0)
    if b"ftypheic" not in header and b"ftypheif" not in header:
        raise ValidationError("Invalid HEIC/HEIF file format")


def validate_consent_image_file(uploaded_file):
    max_size = getattr(settings, "MEDIA_IMAGE_MAX_SIZE", 5 * 1024 * 1024)
    if uploaded_file.size > max_size:
        raise ValidationError(
            f"File size ({uploaded_file.size} bytes) exceeds maximum allowed ({max_size} bytes)"
        )

    ext = Path(uploaded_file.name).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"File extension {ext} not allowed")

    if uploaded_file.content_type and uploaded_file.content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError(f"File type {uploaded_file.content_type} not allowed")

    if ext in (".heic", ".heif"):
        _validate_heic_header(uploaded_file)
        return True

    FileValidator.validate_image_file(uploaded_file)
    return True


def _is_image_file(uploaded_file):
    ext = Path(uploaded_file.name).suffix.lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS or (uploaded_file.content_type or "").startswith("image/")


def validate_consent_attachment_files(files, existing_attachments=None):
    if not files:
        raise ValidationError("Selecione pelo menos um arquivo")

    existing_attachments = existing_attachments or []
    existing_types = {att.file_type for att in existing_attachments}
    existing_count = len(existing_attachments)

    has_image = any(_is_image_file(f) for f in files)

    if "pdf" in existing_types:
        raise ValidationError("Remova o PDF existente antes de enviar imagens")

    if has_image:
        total_images = existing_count + len(files)
        if total_images > 8:
            raise ValidationError("Você pode enviar no máximo 8 imagens")
        for file_obj in files:
            validate_consent_image_file(file_obj)
        return "image"

    raise ValidationError("Envie apenas imagens (fotos) válidas")
