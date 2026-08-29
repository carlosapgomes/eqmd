"""
Test file upload fix to ensure original files are saved correctly.

This test verifies that the critical fix for file saving works properly:
- ``MediaFile.create_from_upload`` persists the original file with a
  UUID-based name (same UUID for original and thumbnail).
- The current photo-creation form (``PhotoCreateFormNew``) stores the
  FilePond original under ``photos/YYYY/MM/originals/<file_id>.<ext>`` and
  records the FilePond metadata on the Photo row.
- The secure serving view resolves and serves those stored files.
"""

import tempfile
import uuid
from pathlib import Path

import shortuuid
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django_drf_filepond.models import TemporaryUpload
from PIL import Image

from apps.events.models import Event
from apps.mediafiles.forms import PhotoCreateFormNew
from apps.mediafiles.models import MediaFile, Photo

from .factories import create_patient, create_user

# PhotoCreateFormNew builds paths with ``MEDIA_ROOT / "photos/..."``, so the
# override must be a Path (the string MEDIA_ROOT in test_settings would fail).
TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="mediafiles_upload_fix_"))


class FileUploadFixTestCase(TestCase):
    """Test case for file upload fix."""

    def setUp(self):
        """Set up test data."""
        self.user = create_user(
            username="testuser", password_change_required=False, terms_accepted=True
        )

        self.patient = create_patient(self.user)

    def create_test_image(self, filename="test_image.jpg", size=(100, 100)):
        """Create a test image file."""
        # Create a simple test image and stream it into memory
        from io import BytesIO

        image = Image.new("RGB", size, color="red")
        buffer = BytesIO()
        image.save(buffer, "JPEG")

        return SimpleUploadedFile(
            filename, buffer.getvalue(), content_type="image/jpeg"
        )

    def test_media_file_creation_saves_original_file(self):
        """Test that MediaFile.create_from_upload saves the original file to disk."""
        # Create test image
        uploaded_file = self.create_test_image("test_upload.jpg")

        # Create MediaFile using the fixed method
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # Verify MediaFile was created
        self.assertIsNotNone(media_file.id)
        self.assertEqual(
            media_file.original_filename, "test_upload.jpg"
        )  # Normalized filename
        self.assertEqual(media_file.mime_type, "image/jpeg")
        self.assertGreater(media_file.file_size, 0)

        # CRITICAL TEST: Verify original file exists on disk
        file_path = Path(settings.MEDIA_ROOT) / media_file.file.name
        self.assertTrue(
            file_path.exists(), f"Original file should exist at {file_path}"
        )
        self.assertTrue(file_path.is_file(), "Original file should be a regular file")

        # Verify file has content
        self.assertGreater(
            file_path.stat().st_size, 0, "Original file should not be empty"
        )

        # Verify metadata was extracted
        self.assertIsNotNone(media_file.width)
        self.assertIsNotNone(media_file.height)
        self.assertEqual(media_file.width, 100)
        self.assertEqual(media_file.height, 100)

        # Verify thumbnail was generated
        if media_file.thumbnail:
            thumbnail_path = Path(settings.MEDIA_ROOT) / media_file.thumbnail.name
            self.assertTrue(thumbnail_path.exists(), "Thumbnail should exist on disk")

    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    def test_photo_creation_with_filepond(self):
        """Test that the current PhotoCreateFormNew saves the original file."""

        # Create a FilePond temporary upload (synthetic, shortuuid id format)
        uploaded_file = self.create_test_image("photo_test.jpg")
        upload_id = shortuuid.uuid()
        TemporaryUpload.objects.create(
            upload_id=upload_id,
            upload_name="photo_test.jpg",
            upload_type="F",
            file=uploaded_file,
        )

        # Simulate form data
        past_local = timezone.localtime(timezone.now() - timezone.timedelta(hours=2))
        form_data = {
            "description": "Test photo upload",
            "event_datetime": past_local.strftime("%Y-%m-%dT%H:%M"),
            "caption": "Test caption",
            "upload_id": upload_id,
        }

        # Create form and validate
        form = PhotoCreateFormNew(data=form_data, user=self.user, patient=self.patient)

        self.assertTrue(form.is_valid(), f"Form should be valid. Errors: {form.errors}")

        # Save the photo
        photo = form.save()

        # Verify Photo was created with FilePond metadata
        self.assertIsNotNone(photo.id)
        self.assertEqual(photo.event_type, Event.PHOTO_EVENT)
        self.assertEqual(photo.patient, self.patient)
        self.assertEqual(photo.created_by, self.user)
        self.assertIsNotNone(photo.file_id)
        self.assertEqual(photo.original_filename, "photo_test.jpg")
        self.assertEqual(photo.width, 100)
        self.assertEqual(photo.height, 100)

        # CRITICAL TEST: Verify original file exists on disk at the FilePond
        # storage location photos/YYYY/MM/originals/<file_id>.jpg
        file_path = (
            Path(settings.MEDIA_ROOT)
            / f"photos/{photo.created_at.strftime('%Y/%m')}/originals"
            / f"{photo.file_id}.jpg"
        )
        self.assertTrue(
            file_path.exists(), f"Original file should exist at {file_path}"
        )

        # Verify file can be opened and read
        with open(file_path, "rb") as f:
            content = f.read()
            self.assertGreater(len(content), 0, "File should have content")

        # Thumbnail path points at the FilePond thumbnails directory
        self.assertIn("/thumbnails/", photo.thumbnail_path)

    def test_secure_url_generation(self):
        """Test that secure URLs are generated correctly."""
        # Create test image and MediaFile
        uploaded_file = self.create_test_image("url_test.jpg")
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # Test secure URL generation
        secure_url = media_file.get_secure_url()
        self.assertIn("/mediafiles/serve/", secure_url)
        self.assertIn(str(media_file.id), secure_url)

    def test_file_serving_view_access(self):
        """Test that file serving views can access the saved files."""
        from django.test import Client

        # Create test image and Photo whose FilePond original exists on disk
        content = self.create_test_image("serve_test.jpg").read()
        file_id = str(uuid.uuid4())
        photo = Photo.objects.create(
            file_id=file_id,
            original_filename="serve_test.jpg",
            file_size=len(content),
            width=100,
            height=100,
            patient=self.patient,
            created_by=self.user,
            description="Test photo for serving",
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            updated_by=self.user,
        )
        original_dir = (
            Path(settings.MEDIA_ROOT)
            / f"photos/{photo.created_at.strftime('%Y/%m')}/originals"
        )
        original_dir.mkdir(parents=True, exist_ok=True)
        (original_dir / f"{file_id}.jpg").write_bytes(content)

        # Login user
        client = Client()
        client.force_login(self.user)

        # Test file serving URL
        serve_url = reverse("mediafiles:serve_file", kwargs={"file_id": file_id})

        # Make request (this should not return 404 anymore)
        response = client.get(serve_url)

        # Should not be 404 (the original problem): the stored file is served
        self.assertEqual(
            response.status_code, 200, "File serving should return 200 when file exists"
        )
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
