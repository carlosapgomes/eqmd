"""
MediaFiles Models

This module implements the database models for the MediaFiles app in EquipeMed.
It provides secure media file management for medical images and videos.

Models:
- MediaFile: Core file storage and metadata
- Photo: Single photo events (inherits from Event)

Security Features:
- UUID-based filenames prevent enumeration attacks
- Original filenames stored in database only
- File extension and MIME type validation
- File hash calculation for deduplication
- Path traversal protection
- Secure file serving through Django views
"""

import os
import uuid
from pathlib import Path

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.urls import reverse

from apps.events.models import Event
from .utils import (
    get_secure_upload_path,
    get_thumbnail_upload_path,
    normalize_filename,
    calculate_file_hash,
    validate_file_extension,
)
from .security import FileValidator


class MediaFileManager(models.Manager):
    """Custom manager for MediaFile model."""

    def create_from_upload(self, uploaded_file: UploadedFile, **kwargs):
        """
        Create MediaFile instance from uploaded file with security validation.

        Args:
            uploaded_file: Django UploadedFile object
            **kwargs: Additional fields for MediaFile

        Returns:
            MediaFile instance

        Raises:
            ValidationError: If file validation fails
        """
        # Validate file
        FileValidator.validate_image_file(uploaded_file)

        # Calculate file hash for deduplication
        file_hash = calculate_file_hash(uploaded_file)

        # Check for existing file with same hash
        if getattr(settings, 'MEDIA_ENABLE_FILE_DEDUPLICATION', True):
            existing_file = self.filter(file_hash=file_hash).first()
            if existing_file:
                return existing_file

        # Create new MediaFile instance
        media_file = self.model(
            original_filename=normalize_filename(uploaded_file.name),
            file_size=uploaded_file.size,
            mime_type=uploaded_file.content_type,
            file_hash=file_hash,
            **kwargs
        )

        # Save file to storage
        media_file.file.save(uploaded_file.name, uploaded_file, save=False)

        # Extract metadata and generate thumbnails
        media_file._extract_metadata()
        media_file._generate_thumbnail()

        # Save to database
        media_file.save()

        return media_file


class MediaFile(models.Model):
    """
    Core model for storing file metadata and managing secure file storage.

    This model handles:
    - Secure file storage with UUID-based filenames
    - File metadata extraction and storage
    - Thumbnail generation
    - File validation and security checks
    - Deduplication based on SHA-256 hash
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the media file"
    )

    file = models.FileField(
        upload_to=get_secure_upload_path,
        verbose_name="Arquivo",
        help_text="The actual file stored securely with UUID filename"
    )

    original_filename = models.CharField(
        max_length=255,
        verbose_name="Nome Original",
        help_text="Original filename as uploaded by user"
    )

    file_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Hash do Arquivo",
        help_text="SHA-256 hash for file deduplication"
    )

    file_size = models.PositiveIntegerField(
        verbose_name="Tamanho do Arquivo",
        help_text="File size in bytes"
    )

    mime_type = models.CharField(
        max_length=100,
        verbose_name="Tipo MIME",
        help_text="MIME type of the file"
    )

    width = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Largura",
        help_text="Image width in pixels"
    )

    height = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Altura",
        help_text="Image height in pixels"
    )

    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Duração",
        help_text="Video duration in seconds"
    )

    thumbnail = models.ImageField(
        upload_to=get_thumbnail_upload_path,
        blank=True,
        null=True,
        verbose_name="Miniatura",
        help_text="Generated thumbnail image"
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadados",
        help_text="Additional file metadata"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )

    objects = MediaFileManager()

    class Meta:
        verbose_name = "Arquivo de Mídia"
        verbose_name_plural = "Arquivos de Mídia"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['file_hash'], name='mediafile_hash_idx'),
            models.Index(fields=['mime_type'], name='mediafile_mime_idx'),
            models.Index(fields=['created_at'], name='mediafile_created_idx'),
        ]

    def __str__(self):
        """Return original filename for string representation."""
        return self.original_filename

    def clean(self):
        """Validate the media file."""
        super().clean()

        if self.file:
            # Validate file extension
            if not validate_file_extension(self.original_filename, 'image'):
                raise ValidationError(
                    f"File extension not allowed: {Path(self.original_filename).suffix}"
                )

            # Validate file size
            max_size = getattr(settings, 'MEDIA_IMAGE_MAX_SIZE', 5 * 1024 * 1024)
            if self.file_size > max_size:
                raise ValidationError(
                    f"File size ({self.file_size} bytes) exceeds maximum allowed ({max_size} bytes)"
                )

    def save(self, *args, **kwargs):
        """Override save to generate secure filename and extract metadata."""
        if self.file and not self.file_hash:
            # Calculate file hash if not already set
            self.file_hash = calculate_file_hash(self.file)

        # Extract metadata before saving
        if self.file and not self.width:
            self._extract_metadata()

        super().save(*args, **kwargs)

        # Generate thumbnail after saving
        if self.file and not self.thumbnail:
            self._generate_thumbnail()
            # Save again to update thumbnail field
            super().save(update_fields=['thumbnail'])

    def _extract_metadata(self):
        """Extract metadata from image file."""
        if not self.file:
            return

        try:
            from PIL import Image

            # Open image and extract dimensions
            with Image.open(self.file.path) as img:
                self.width, self.height = img.size

                # Extract EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    exif_data = img._getexif()
                    if exif_data:
                        self.metadata['exif'] = {
                            str(k): str(v) for k, v in exif_data.items()
                            if isinstance(v, (str, int, float))
                        }

        except Exception as e:
            # Log error but don't fail the save
            self.metadata['extraction_error'] = str(e)

    def _generate_thumbnail(self):
        """Generate thumbnail for the image."""
        if not self.file or self.thumbnail:
            return

        try:
            from PIL import Image
            import tempfile

            # Open original image
            with Image.open(self.file.path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Create thumbnail
                thumbnail_size = (300, 300)
                img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

                # Save thumbnail to temporary file
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    img.save(temp_file.name, 'JPEG', quality=85)

                    # Save thumbnail to model using structured path
                    thumbnail_name = f"{self.id}_thumb.jpg"
                    with open(temp_file.name, 'rb') as thumb_file:
                        from django.core.files import File
                        self.thumbnail.save(thumbnail_name, File(thumb_file), save=False)

                    # Clean up temporary file
                    os.unlink(temp_file.name)

        except Exception as e:
            # Log error but don't fail the save
            self.metadata['thumbnail_error'] = str(e)

    def get_thumbnail_url(self):
        """Return thumbnail URL with fallback."""
        if self.thumbnail:
            return self.thumbnail.url
        return None

    def get_display_size(self):
        """Return human-readable file size."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def get_secure_url(self):
        """Return secure file URL for authorized access."""
        return reverse('mediafiles:serve_file', kwargs={'file_id': self.id})

    def get_dimensions_display(self):
        """Return formatted dimensions string."""
        if self.width and self.height:
            return f"{self.width} × {self.height}"
        return "Unknown"


class PhotoManager(models.Manager):
    """Custom manager for Photo model."""

    def get_queryset(self):
        """Return queryset with optimized queries."""
        return super().get_queryset().select_related('media_file', 'patient', 'created_by')


class Photo(Event):
    """
    Photo model for single image uploads.

    Extends the base Event model and uses PHOTO_EVENT type.
    Each photo has a single associated MediaFile.
    """

    media_file = models.OneToOneField(
        MediaFile,
        on_delete=models.CASCADE,
        verbose_name="Arquivo de Mídia",
        help_text="The media file containing the photo"
    )

    caption = models.TextField(
        blank=True,
        verbose_name="Legenda",
        help_text="Optional caption for the photo"
    )

    objects = PhotoManager()

    class Meta:
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"

    def save(self, *args, **kwargs):
        """Override save to set the correct event type."""
        self.event_type = Event.PHOTO_EVENT
        super().save(*args, **kwargs)

    def clean(self):
        """Validate the photo."""
        super().clean()

        if self.media_file and not self.media_file.mime_type.startswith('image/'):
            raise ValidationError("Media file must be an image")

    def get_absolute_url(self):
        """Return the absolute URL for this photo."""
        return reverse('mediafiles:photo_detail', kwargs={'pk': self.pk})

    def get_edit_url(self):
        """Return the edit URL for this photo."""
        return reverse('mediafiles:photo_update', kwargs={'pk': self.pk})

    def get_thumbnail(self):
        """Delegate to media_file.get_thumbnail_url()."""
        if self.media_file:
            return self.media_file.get_thumbnail_url()
        return None

    def get_file_info(self):
        """Return formatted file information."""
        if self.media_file:
            return {
                'size': self.media_file.get_display_size(),
                'dimensions': self.media_file.get_dimensions_display(),
                'filename': self.media_file.original_filename,
            }
        return {}
