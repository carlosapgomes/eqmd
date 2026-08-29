# MediaFiles Model Tests
# Tests for the current FilePond-based media models (Photo, PhotoSeries,
# PhotoSeriesFile, VideoClip) and the legacy MediaFile model.

import os
import re
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.events.models import Event
from apps.mediafiles.models import (
    MediaFile,
    Photo,
    PhotoSeries,
    PhotoSeriesFile,
    VideoClip,
)
from apps.mediafiles.utils import (
    calculate_file_hash,
    get_secure_series_upload_path,
    validate_series_files,
)

from .factories import (
    create_patient,
    create_user,
    load_test_image_bytes,
    make_uploaded_image,
)

User = get_user_model()

TEST_MEDIA_DIR = os.path.join(os.path.dirname(__file__), "test_media")


class MediaFileModelTests(TestCase):
    """Tests for the legacy MediaFile model (still used by upload paths)."""

    def setUp(self):
        """Set up test data"""
        with open(os.path.join(TEST_MEDIA_DIR, "small_image.jpg"), "rb") as f:
            self.test_image_content = f.read()

    def create_test_image_file(self, filename="test.jpg", content=None):
        """Create a test image file for testing."""
        if content is None:
            content = self.test_image_content
        return SimpleUploadedFile(filename, content, content_type="image/jpeg")

    def test_media_file_creation(self):
        """Test media file creation"""
        uploaded_file = self.create_test_image_file()

        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        self.assertIsNotNone(media_file.id)
        self.assertEqual(media_file.original_filename, "test.jpg")
        self.assertEqual(media_file.file_size, len(self.test_image_content))
        self.assertEqual(media_file.mime_type, "image/jpeg")
        self.assertIsNotNone(media_file.file_hash)
        self.assertTrue(media_file.file.name.endswith(".jpg"))

    def test_media_file_validation(self):
        """Test media file validation"""
        # Test valid image
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        media_file.full_clean()  # Should not raise ValidationError

        # Test invalid extension
        invalid_file = SimpleUploadedFile(
            "test.txt", b"not an image", content_type="text/plain"
        )

        with self.assertRaises(ValidationError):
            MediaFile.objects.create_from_upload(invalid_file)

    def test_media_file_hash_calculation(self):
        """Test media file hash calculation for deduplication"""
        uploaded_file1 = self.create_test_image_file("test1.jpg")
        uploaded_file2 = self.create_test_image_file(
            "test2.jpg"
        )  # Same content, different name

        media_file1 = MediaFile.objects.create_from_upload(uploaded_file1)
        media_file2 = MediaFile.objects.create_from_upload(uploaded_file2)

        # Should be the same file due to deduplication
        self.assertEqual(media_file1.id, media_file2.id)
        self.assertEqual(media_file1.file_hash, media_file2.file_hash)

    def test_media_file_secure_path_generation(self):
        """Test secure path generation for media files"""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # Check that file path contains UUID and year/month structure
        file_path = media_file.file.name
        self.assertIn("photos/", file_path)
        self.assertIn("/originals/", file_path)
        # Should contain year/month pattern
        self.assertTrue(re.search(r"\d{4}/\d{2}", file_path))
        # Original filename must not leak into the stored path
        self.assertNotIn("test.jpg", file_path)

    def test_media_file_string_representation(self):
        """Test MediaFile string representation"""
        uploaded_file = self.create_test_image_file("my_photo.jpg")
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # normalize_filename preserves underscores (lowercase, sanitized)
        self.assertEqual(str(media_file), "my_photo.jpg")

    def test_media_file_display_methods(self):
        """Test MediaFile display methods"""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # Test file size display
        size_display = media_file.get_display_size()
        # Small test files may be in bytes rather than KB
        self.assertTrue("B" in size_display or "KB" in size_display)

        # Test secure URL
        secure_url = media_file.get_secure_url()
        self.assertIn("/mediafiles/serve/", secure_url)
        self.assertIn(str(media_file.id), secure_url)

    def test_media_file_metadata_extraction(self):
        """Test metadata extraction from image files"""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # Should have extracted width and height
        self.assertIsNotNone(media_file.width)
        self.assertIsNotNone(media_file.height)
        self.assertGreater(media_file.width, 0)
        self.assertGreater(media_file.height, 0)


class PhotoModelTests(TestCase):
    """Tests for the FilePond-based Photo model."""

    def setUp(self):
        """Set up test data"""
        self.user = create_user(password_change_required=False, terms_accepted=True)
        self.patient = create_patient(self.user)

    def make_photo(self, **kwargs):
        """Create a Photo using the current FilePond metadata fields."""
        defaults = {
            "file_id": str(uuid.uuid4()),
            "original_filename": "foto.jpg",
            "file_size": 1024,
            "width": 100,
            "height": 100,
            "thumbnail_path": "",
            "description": "Test photo",
            "event_datetime": timezone.now() - timezone.timedelta(hours=1),
            "patient": self.patient,
            "created_by": self.user,
            "updated_by": self.user,
            "caption": "Test caption",
        }
        defaults.update(kwargs)
        return Photo.objects.create(**defaults)

    def test_photo_creation(self):
        """Test photo creation with FilePond metadata fields"""
        photo = self.make_photo()

        self.assertIsNotNone(photo.id)
        self.assertIsNotNone(photo.file_id)
        self.assertEqual(photo.original_filename, "foto.jpg")
        self.assertEqual(photo.file_size, 1024)
        self.assertEqual(photo.caption, "Test caption")
        self.assertEqual(photo.description, "Test photo")
        self.assertEqual(photo.patient, self.patient)
        self.assertEqual(photo.created_by, self.user)

    def test_photo_event_type(self):
        """Test that photo uses correct event type"""
        photo = self.make_photo()

        self.assertEqual(photo.event_type, Event.PHOTO_EVENT)

    def test_photo_model_validation(self):
        """Test Photo model validation (Event base contract)"""
        # A complete photo passes full_clean
        photo = self.make_photo()
        photo.full_clean()  # Should not raise ValidationError

        # A photo missing required Event fields is rejected
        incomplete = Photo(description="No event metadata")
        with self.assertRaises(ValidationError) as ctx:
            incomplete.full_clean()
        self.assertIn("event_datetime", ctx.exception.message_dict)
        self.assertIn("patient", ctx.exception.message_dict)
        self.assertIn("event_type", ctx.exception.message_dict)

    def test_photo_methods(self):
        """Test Photo model methods"""
        photo = self.make_photo(
            thumbnail_path=f"photos/{timezone.now().strftime('%Y/%m')}/thumbnails/x_thumb.jpg"
        )

        # Test get_absolute_url
        absolute_url = photo.get_absolute_url()
        self.assertIn("/mediafiles/photos/", absolute_url)
        self.assertIn(str(photo.id), absolute_url)

        # Test get_edit_url
        edit_url = photo.get_edit_url()
        self.assertIn("/edit/", edit_url)

        # Test get_thumbnail (requires both file_id and thumbnail_path)
        thumbnail_url = photo.get_thumbnail()
        self.assertIsNotNone(thumbnail_url)
        self.assertIn("/mediafiles/thumbnail/", thumbnail_url)
        self.assertIn(photo.file_id, thumbnail_url)

        # Without a thumbnail path the helper returns None (no crash)
        photo_no_thumb = self.make_photo(thumbnail_path="")
        self.assertIsNone(photo_no_thumb.get_thumbnail())

        # Test get_file_info
        file_info = photo.get_file_info()
        self.assertIn("size", file_info)
        self.assertIn("dimensions", file_info)
        self.assertIn("filename", file_info)
        self.assertEqual(file_info["filename"], "foto.jpg")

    def test_photo_secure_url(self):
        """Test secure file URL generation from the FilePond file_id"""
        photo = self.make_photo()

        secure_url = photo.get_secure_url()
        self.assertIn("/mediafiles/serve/", secure_url)
        self.assertIn(photo.file_id, secure_url)

        # Without a file_id there is no URL to build
        photo_no_file = self.make_photo(file_id=None)
        self.assertIsNone(photo_no_file.get_secure_url())

    def test_photo_display_helpers(self):
        """Test display helpers (size and dimensions)"""
        photo = self.make_photo(file_size=2048, width=640, height=480)

        self.assertEqual(photo.get_display_size(), "2.0 KB")
        self.assertEqual(photo.get_dimensions_display(), "640 × 480")

        unknown = self.make_photo(file_size=None, width=None, height=None)
        self.assertEqual(unknown.get_display_size(), "Unknown")
        self.assertEqual(unknown.get_dimensions_display(), "Unknown")

    def test_photo_manager_optimization(self):
        """Test Photo manager query optimization"""
        self.make_photo()

        # Test that queryset includes select_related
        with self.assertNumQueries(1):
            photo = Photo.objects.first()
            # These should not trigger additional queries due to select_related
            _ = photo.patient.name
            _ = photo.created_by.username


class PhotoSeriesFileModelTests(TestCase):
    """Tests for PhotoSeriesFile (FilePond series rows)."""

    def setUp(self):
        """Set up test data"""
        self.user = create_user(password_change_required=False, terms_accepted=True)
        self.patient = create_patient(self.user)
        self.photo_series = PhotoSeries.objects.create(
            description="Test series",
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            caption="Test caption",
        )

    def make_series_file(self, **kwargs):
        """Create a PhotoSeriesFile row using the current FilePond fields."""
        defaults = {
            "photo_series": self.photo_series,
            "file_id": str(uuid.uuid4()),
            "original_filename": "foto.jpg",
            "file_size": 1024,
            "width": 100,
            "height": 100,
            "order": 1,
            "description": "First photo",
        }
        defaults.update(kwargs)
        return PhotoSeriesFile.objects.create(**defaults)

    def test_photo_series_file_creation(self):
        """Test PhotoSeriesFile creation"""
        series_file = self.make_series_file()

        self.assertIsNotNone(series_file.id)
        self.assertEqual(series_file.photo_series, self.photo_series)
        self.assertIsNotNone(series_file.file_id)
        self.assertEqual(series_file.original_filename, "foto.jpg")
        self.assertEqual(series_file.file_size, 1024)
        self.assertEqual(series_file.order, 1)
        self.assertEqual(series_file.description, "First photo")

    def test_photo_series_file_explicit_ordering(self):
        """Test that ordering follows the explicit order values"""
        # Order assignment lives in the form/upload layer: the model simply
        # stores and sorts by the explicit order values.
        self.make_series_file(order=3, file_id=str(uuid.uuid4()))
        self.make_series_file(order=1, file_id=str(uuid.uuid4()))
        self.make_series_file(order=2, file_id=str(uuid.uuid4()))

        files = PhotoSeriesFile.objects.filter(photo_series=self.photo_series)
        self.assertEqual([f.order for f in files], [1, 2, 3])

    def test_photo_series_file_unique_constraint(self):
        """Test unique constraint on (photo_series, order)"""
        self.make_series_file(order=1)

        with self.assertRaises(IntegrityError):
            self.make_series_file(order=1, file_id=str(uuid.uuid4()))

    def test_photo_series_file_display_methods(self):
        """Test PhotoSeriesFile display helpers"""
        series_file = self.make_series_file(
            file_size=2048,
            width=640,
            height=480,
            thumbnail_path=f"photo_series/{timezone.now().strftime('%Y/%m')}/thumbnails/thumb.jpg",
        )

        # Size formatting
        self.assertEqual(series_file.get_display_size(), "2.0 KB")

        # Dimensions use the compact WxH format
        self.assertEqual(series_file.get_dimensions_display(), "640x480")

        # MIME type derived from the extension
        self.assertEqual(series_file.mime_type, "image/jpeg")
        unknown = self.make_series_file(
            original_filename="file.xyz", file_id=str(uuid.uuid4()), order=2
        )
        self.assertEqual(unknown.mime_type, "application/octet-stream")

        # Secure URLs derive from the FilePond file_id
        self.assertIn("/mediafiles/serve/", series_file.get_secure_url())
        self.assertIn(series_file.file_id, series_file.get_secure_url())
        self.assertIn("/mediafiles/thumbnail/", series_file.get_thumbnail_url())

    def test_photo_series_file_ordering(self):
        """Test PhotoSeriesFile ordering"""
        # Create files in random order
        self.make_series_file(order=3, file_id=str(uuid.uuid4()))
        self.make_series_file(order=1, file_id=str(uuid.uuid4()))
        self.make_series_file(order=2, file_id=str(uuid.uuid4()))

        # Should be returned in order
        series_files = PhotoSeriesFile.objects.filter(photo_series=self.photo_series)
        orders = [sf.order for sf in series_files]
        self.assertEqual(orders, [1, 2, 3])


class PhotoSeriesModelTests(TestCase):
    """Tests for PhotoSeries model."""

    def setUp(self):
        """Set up test data"""
        self.user = create_user(password_change_required=False, terms_accepted=True)
        self.patient = create_patient(self.user)

    def make_series(self, **kwargs):
        """Create a PhotoSeries instance."""
        defaults = {
            "description": "Test series",
            "event_datetime": timezone.now() - timezone.timedelta(hours=1),
            "patient": self.patient,
            "created_by": self.user,
            "updated_by": self.user,
            "caption": "Test caption",
        }
        defaults.update(kwargs)
        return PhotoSeries.objects.create(**defaults)

    def add_series_file(self, series, order, description="", **kwargs):
        """Add a PhotoSeriesFile row (current ORM-level API)."""
        defaults = {
            "photo_series": series,
            "file_id": str(uuid.uuid4()),
            "original_filename": "foto.jpg",
            "file_size": 1024,
            "width": 100,
            "height": 100,
            "thumbnail_path": f"photo_series/{timezone.now().strftime('%Y/%m')}/thumbnails/{uuid.uuid4()}_thumb.jpg",
            "order": order,
            "description": description,
        }
        defaults.update(kwargs)
        return PhotoSeriesFile.objects.create(**defaults)

    def test_photo_series_creation(self):
        """Test PhotoSeries creation"""
        photo_series = self.make_series()

        self.assertIsNotNone(photo_series.id)
        self.assertEqual(photo_series.description, "Test series")
        self.assertEqual(photo_series.caption, "Test caption")
        self.assertEqual(photo_series.patient, self.patient)
        self.assertEqual(photo_series.created_by, self.user)

    def test_photo_series_event_type(self):
        """Test that PhotoSeries uses correct event type"""
        photo_series = self.make_series()

        self.assertEqual(photo_series.event_type, Event.PHOTO_SERIES_EVENT)

    def test_photo_series_methods(self):
        """Test PhotoSeries model methods"""
        photo_series = self.make_series()

        for i in range(3):
            self.add_series_file(
                photo_series, order=i + 1, description=f"Photo {i + 1}"
            )

        # Test get_photo_count
        self.assertEqual(photo_series.get_photo_count(), 3)

        # Test get_ordered_photos returns rows ordered by explicit order
        ordered_photos = photo_series.get_ordered_photos()
        self.assertEqual(ordered_photos.count(), 3)
        self.assertEqual([p.order for p in ordered_photos], [1, 2, 3])

        # Test get_primary_thumbnail (first row's thumbnail URL)
        primary_thumbnail = photo_series.get_primary_thumbnail()
        self.assertIsNotNone(primary_thumbnail)
        self.assertEqual(primary_thumbnail, ordered_photos[0].get_thumbnail_url())

        # get_photos is the same ordered list
        self.assertEqual(list(photo_series.get_photos()), list(ordered_photos))

    def test_photo_series_file_addition(self):
        """Test adding series files via the current ORM API"""
        photo_series = self.make_series()

        series_file = self.add_series_file(
            photo_series, order=1, description="Test photo"
        )

        self.assertEqual(photo_series.get_photo_count(), 1)
        saved = PhotoSeriesFile.objects.get(pk=series_file.pk)
        self.assertEqual(saved.order, 1)
        self.assertEqual(saved.description, "Test photo")
        self.assertEqual(saved.photo_series, photo_series)

    def test_photo_series_file_removal(self):
        """Test removing series files (no automatic renumbering)"""
        photo_series = self.make_series()

        files = [self.add_series_file(photo_series, order=i + 1) for i in range(3)]

        # Remove middle photo
        files[1].delete()

        # Should have 2 photos left
        self.assertEqual(photo_series.get_photo_count(), 2)

        # The model does not renumber remaining rows; order values persist
        remaining_files = PhotoSeriesFile.objects.filter(photo_series=photo_series)
        self.assertEqual([sf.order for sf in remaining_files], [1, 3])

    def test_photo_series_reorder_photos(self):
        """Test reordering via explicit order updates (ORM contract)"""
        photo_series = self.make_series()

        files = [self.add_series_file(photo_series, order=i + 1) for i in range(3)]

        # Reorder: reverse the order values directly on the rows. Orders are
        # unique per series, so move rows through temporary values first to
        # avoid transient unique-constraint collisions.
        for index, series_file in enumerate(files):
            series_file.order = 100 + index
            series_file.save()
        for index, series_file in enumerate(files):
            series_file.order = 3 - index
            series_file.save()

        ordered_photos = photo_series.get_ordered_photos()
        self.assertEqual([p.order for p in ordered_photos], [1, 2, 3])
        self.assertEqual(ordered_photos[0].pk, files[2].pk)
        self.assertEqual(ordered_photos[2].pk, files[0].pk)

    def test_photo_series_validation(self):
        """Test PhotoSeries validation"""
        photo_series = self.make_series()

        # Empty series should not raise validation error during creation
        # (the model is deliberately lenient to allow gradual photo addition)
        photo_series.full_clean()  # Should not raise

    def test_photo_series_manager_optimization(self):
        """Test PhotoSeries manager query optimization"""
        photo_series = self.make_series()
        self.add_series_file(photo_series, order=1)

        # One query for the series + joined relations, one for the prefetched
        # series files; get_photo_count() is served from the prefetch cache.
        with self.assertNumQueries(2):
            series = PhotoSeries.objects.first()
            # These should not trigger additional queries due to select_related
            _ = series.patient.name
            _ = series.created_by.username
            # Access photo count (may trigger one more query)
            _ = series.get_photo_count()


class MediaFileSeriesUtilsTests(TestCase):
    """Tests for the photo-series path/validation utilities.

    The MediaFile <-> PhotoSeriesFile relation was removed in the FilePond
    migration (PhotoSeriesFile stores its own file_id metadata), so the
    current series-path and series-validation contracts live in utils.
    """

    def setUp(self):
        """Set up test data"""
        self.user = create_user(password_change_required=False, terms_accepted=True)
        self.patient = create_patient(self.user)

    def test_secure_series_upload_path_generation(self):
        """Test secure series path generation (util contract)"""
        # Generate a path for a series file
        series_path = get_secure_series_upload_path(None, "foto.jpg")

        self.assertIsNotNone(series_path)
        self.assertIn("photo_series/", series_path)
        self.assertIn("/originals/", series_path)
        self.assertIn("series_", series_path)
        # New security function generates a random UUID, not using a model id
        self.assertIn(
            str(uuid.UUID(series_path.split("series_")[1].split(".")[0])), series_path
        )
        self.assertTrue(series_path.endswith(".jpg"))
        # No original filename leaks into the stored path
        self.assertNotIn("foto", series_path.split("/")[-1])

    def test_secure_series_upload_path_extension_validation(self):
        """Test that series paths reject non-image extensions"""
        from django.core.exceptions import ValidationError as DjangoValidationError

        with self.assertRaises(DjangoValidationError):
            get_secure_series_upload_path(None, "file.txt")

    def test_media_file_series_validation(self):
        """Test MediaFile.validate_series_file (image-only contract)"""
        uploaded_file = make_uploaded_image()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # Should not raise for valid image file
        media_file.validate_series_file()

        # Test with non-image file
        media_file.mime_type = "text/plain"
        with self.assertRaises(ValidationError):
            media_file.validate_series_file()

        # Oversized files are rejected for series inclusion
        media_file.mime_type = "image/jpeg"
        media_file.file_size = 10 * 1024 * 1024  # 10MB > 5MB limit
        with self.assertRaises(ValidationError):
            media_file.validate_series_file()

    def test_batch_series_file_addition(self):
        """Test batch addition of series files via the ORM (current contract)"""
        photo_series = PhotoSeries.objects.create(
            description="Test series",
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
        )

        # The form/upload layer creates one PhotoSeriesFile row per image
        created_files = []
        for i in range(3):
            created_files.append(
                PhotoSeriesFile.objects.create(
                    photo_series=photo_series,
                    file_id=str(uuid.uuid4()),
                    original_filename=f"batch_{i}.jpg",
                    file_size=100,
                    order=i + 1,
                )
            )

        self.assertEqual(len(created_files), 3)
        self.assertEqual(photo_series.get_photo_count(), 3)

        # Verify order
        ordered_photos = photo_series.get_ordered_photos()
        self.assertEqual([p.pk for p in ordered_photos], [f.pk for f in created_files])

    def test_series_security_validation(self):
        """Test security validation for photo series files"""
        # Test with valid files
        valid_files = []
        for i in range(2):
            uploaded_file = SimpleUploadedFile(
                f"valid_{i}.jpg",
                load_test_image_bytes() + f"security_test_{i}".encode(),
                content_type="image/jpeg",
            )
            valid_files.append(uploaded_file)

        # Should not raise for valid files
        validate_series_files(valid_files)

        # Test with empty list
        with self.assertRaises(ValidationError):
            validate_series_files([])

        # Test with mixed file types
        mixed_files = [
            SimpleUploadedFile("image.jpg", b"fake image", content_type="image/jpeg"),
            SimpleUploadedFile("doc.txt", b"text content", content_type="text/plain"),
        ]

        with self.assertRaises(ValidationError):
            validate_series_files(mixed_files)


class ModelIntegrationTests(TestCase):
    """Tests for model integration and relationships"""

    def setUp(self):
        """Set up test data"""
        self.user = create_user(password_change_required=False, terms_accepted=True)
        self.patient = create_patient(self.user)

    def make_photo(self, **kwargs):
        """Create a Photo using the current FilePond metadata fields."""
        defaults = {
            "file_id": str(uuid.uuid4()),
            "original_filename": "foto.jpg",
            "file_size": 1024,
            "description": "Test photo",
            "event_datetime": timezone.now() - timezone.timedelta(hours=1),
            "patient": self.patient,
            "created_by": self.user,
            "updated_by": self.user,
        }
        defaults.update(kwargs)
        return Photo.objects.create(**defaults)

    def test_event_model_integration(self):
        """Test integration with Event model"""
        photo = self.make_photo()

        # Test that Photo is an Event
        self.assertIsInstance(photo, Event)

        # Test that it appears in Event queries
        events = Event.objects.filter(patient=self.patient)
        event_ids = [e.id for e in events]
        self.assertIn(photo.id, event_ids)

        # Test event type is correctly set
        self.assertEqual(photo.event_type, Event.PHOTO_EVENT)

    def test_patient_media_relationship(self):
        """Test relationship between patients and photos"""
        photo = self.make_photo()

        # Test patient can access their photos
        patient_photos = Photo.objects.filter(patient=self.patient)
        self.assertIn(photo, patient_photos)

        # Test photo belongs to correct patient
        self.assertEqual(photo.patient, self.patient)

    def test_user_permissions_on_media(self):
        """Test user permissions on media files"""
        photo = self.make_photo()

        # Test creator relationship
        self.assertEqual(photo.created_by, self.user)

        # Test user can access their created photos
        user_photos = Photo.objects.filter(created_by=self.user)
        self.assertIn(photo, user_photos)

        # Test 24-hour edit window
        self.assertTrue(photo.can_be_edited)


class MediaFileSecurityTests(TestCase):
    """Security-focused tests for MediaFile model"""

    def setUp(self):
        """Set up test data"""
        with open(os.path.join(TEST_MEDIA_DIR, "small_image.jpg"), "rb") as f:
            self.test_image_content = f.read()

    def test_file_hash_uniqueness(self):
        """Test that file hash ensures uniqueness"""
        uploaded_file1 = SimpleUploadedFile(
            "test1.jpg", self.test_image_content, content_type="image/jpeg"
        )
        uploaded_file2 = SimpleUploadedFile(
            "test2.jpg",
            self.test_image_content,  # Same content
            content_type="image/jpeg",
        )

        media_file1 = MediaFile.objects.create_from_upload(uploaded_file1)
        media_file2 = MediaFile.objects.create_from_upload(uploaded_file2)

        # Should be the same object due to deduplication
        self.assertEqual(media_file1.id, media_file2.id)

    def test_secure_filename_generation(self):
        """Test that filenames are securely generated"""
        uploaded_file = SimpleUploadedFile(
            "../../../etc/passwd.jpg",  # Malicious filename
            self.test_image_content,
            content_type="image/jpeg",
        )

        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # File path should not contain the malicious parts
        self.assertNotIn("..", media_file.file.name)
        self.assertNotIn("etc", media_file.file.name)
        self.assertNotIn("passwd", media_file.file.name)

        # Should contain UUID pattern
        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        self.assertTrue(re.search(uuid_pattern, media_file.file.name))

    def test_file_extension_validation(self):
        """Test file extension validation"""
        # Test invalid extension
        invalid_file = SimpleUploadedFile(
            "malicious.exe",
            b"fake image content",
            content_type="application/octet-stream",
        )

        with self.assertRaises(ValidationError):
            MediaFile.objects.create_from_upload(invalid_file)

    def test_mime_type_validation(self):
        """Test MIME type validation"""
        # Test invalid MIME type
        invalid_file = SimpleUploadedFile(
            "test.jpg", b"not really an image", content_type="text/plain"
        )

        with self.assertRaises(ValidationError):
            MediaFile.objects.create_from_upload(invalid_file)


class VideoClipModelTests(TestCase):
    """Tests for the FilePond-based VideoClip model."""

    def setUp(self):
        """Set up test data"""
        self.user = create_user(password_change_required=False, terms_accepted=True)
        self.patient = create_patient(self.user)

    def make_video_clip(self, **kwargs):
        """Create a VideoClip using the current FilePond metadata fields."""
        defaults = {
            "file_id": str(uuid.uuid4()),
            "original_filename": "test.mp4",
            "file_size": 2048,
            "duration": 60,
            "width": 1920,
            "height": 1080,
            "video_codec": "h264",
            "description": "Test video",
            "event_datetime": timezone.now() - timezone.timedelta(hours=1),
            "patient": self.patient,
            "created_by": self.user,
            "updated_by": self.user,
            "caption": "Test caption",
        }
        defaults.update(kwargs)
        return VideoClip.objects.create(**defaults)

    def test_video_clip_creation(self):
        """Test VideoClip creation"""
        video_clip = self.make_video_clip()

        self.assertIsNotNone(video_clip.id)
        self.assertIsNotNone(video_clip.file_id)
        self.assertEqual(video_clip.original_filename, "test.mp4")
        self.assertEqual(video_clip.file_size, 2048)
        self.assertEqual(video_clip.duration, 60)
        self.assertEqual(video_clip.description, "Test video")
        self.assertEqual(video_clip.caption, "Test caption")
        self.assertEqual(video_clip.patient, self.patient)
        self.assertEqual(video_clip.created_by, self.user)

    def test_video_clip_event_type_auto_assignment(self):
        """Test that VideoClip automatically sets correct event type"""
        video_clip = self.make_video_clip()

        self.assertEqual(video_clip.event_type, Event.VIDEO_CLIP_EVENT)

    def test_video_clip_duration_validation(self):
        """Test duration validation (≤ 2 minutes)"""
        # Test valid duration (120 seconds = 2 minutes)
        video_clip_valid = VideoClip(
            file_id=str(uuid.uuid4()),
            original_filename="valid.mp4",
            file_size=100,
            duration=120,
            description="Valid video",
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
        )
        video_clip_valid.clean()  # Set event_type first
        video_clip_valid.full_clean()  # Should not raise

        # Test invalid duration (over 2 minutes)
        video_clip_invalid = VideoClip(
            file_id=str(uuid.uuid4()),
            original_filename="invalid.mp4",
            file_size=100,
            duration=180,  # 3 minutes
            description="Invalid video",
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
        )

        with self.assertRaises(ValidationError):
            video_clip_invalid.clean()  # Raises before full_clean

    def test_video_clip_file_relationship(self):
        """Test the FilePond file_id relationship"""
        video_clip = self.make_video_clip()

        # The clip references its stored file through the FilePond file_id
        self.assertIsNotNone(video_clip.file_id)
        self.assertEqual(
            video_clip.file_id, VideoClip.objects.get(pk=video_clip.pk).file_id
        )

    def test_video_clip_metadata_fields_optional(self):
        """Test that upload metadata is optional at the model level"""
        # File metadata fields are nullable: content validation happens in the
        # validators/forms layer, not in the model.
        video_clip = VideoClip(
            file_id=None,
            original_filename=None,
            file_size=None,
            duration=None,
            description="No metadata yet",
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
        )
        video_clip.clean()  # Should not raise
        video_clip.full_clean()  # Should not raise

    def test_video_clip_url_methods(self):
        """Test URL generation methods"""
        video_clip = self.make_video_clip()

        # Test get_absolute_url
        absolute_url = video_clip.get_absolute_url()
        self.assertIn("/mediafiles/videos/", absolute_url)
        self.assertIn(str(video_clip.id), absolute_url)

        # Test get_edit_url
        edit_url = video_clip.get_edit_url()
        self.assertIn("/edit/", edit_url)

        # Test get_video_url (derives from the FilePond file_id)
        video_url = video_clip.get_video_url()
        self.assertIn("/mediafiles/serve/", video_url)
        self.assertIn(video_clip.file_id, video_url)

        # Without a file_id there is no URL to build
        self.assertIsNone(self.make_video_clip(file_id=None).get_video_url())

    def test_video_clip_thumbnail_method(self):
        """Test thumbnail method (documented TODO returning None)"""
        video_clip = self.make_video_clip()

        # Thumbnail generation for FilePond videos is not implemented yet
        self.assertIsNone(video_clip.get_thumbnail())

    def test_video_clip_duration_method(self):
        """Test duration formatting method"""
        video_clip = self.make_video_clip(duration=90)  # 1:30

        duration = video_clip.get_duration()
        self.assertEqual(duration, "1:30")

        self.assertEqual(self.make_video_clip(duration=None).get_duration(), "0:00")

    def test_video_clip_file_info_method(self):
        """Test file info method"""
        video_clip = self.make_video_clip(duration=75)

        file_info = video_clip.get_file_info()
        self.assertIn("size", file_info)
        self.assertIn("dimensions", file_info)
        self.assertIn("duration", file_info)
        self.assertIn("filename", file_info)
        self.assertIn("codec", file_info)
        self.assertEqual(file_info["codec"], "h264")
        self.assertEqual(file_info["filename"], "test.mp4")
        self.assertEqual(file_info["dimensions"], "1920 × 1080")

    def test_video_clip_manager_optimization(self):
        """Test VideoClip manager query optimization"""
        self.make_video_clip()

        # Test that queryset includes select_related
        with self.assertNumQueries(1):
            video_clip = VideoClip.objects.first()
            # These should not trigger additional queries due to select_related
            _ = video_clip.file_id
            _ = video_clip.patient.name
            _ = video_clip.created_by.username

    def test_video_clip_save_validation(self):
        """Test save method validation"""
        video_clip = VideoClip(
            file_id=str(uuid.uuid4()),
            original_filename="long.mp4",
            file_size=100,
            duration=180,  # 3 minutes - too long
            description="Test video",
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
        )

        # Should raise ValidationError during save due to duration validation
        with self.assertRaises(ValidationError):
            video_clip.save()


class MediaFileVideoMethodsTests(TestCase):
    """Tests for MediaFile video-related methods"""

    def setUp(self):
        """Set up test data"""
        self.user = create_user(password_change_required=False, terms_accepted=True)

    def create_test_video_media_file(self, filename="test.mp4", duration=60):
        """Create a test MediaFile with video properties."""
        # Make content unique based on duration to avoid hash conflicts
        fake_video_content = (
            b"\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom"
            + f"fake_video_data_{duration}".encode() * 100
        )
        uploaded_file = SimpleUploadedFile(
            filename, fake_video_content, content_type="video/mp4"
        )

        media_file = MediaFile.objects.create(
            original_filename=filename,
            file_size=len(fake_video_content),
            mime_type="video/mp4",
            file_hash=calculate_file_hash(uploaded_file),
            duration=duration,
            width=1920,
            height=1080,
            video_codec="h264",
            video_bitrate=5000000,
            fps=30.0,
        )

        uploaded_file.seek(0)
        media_file.file.save(uploaded_file.name, uploaded_file, save=False)
        return media_file

    def test_media_file_is_video_method(self):
        """Test is_video() method"""
        # Test video file
        video_file = self.create_test_video_media_file()
        self.assertTrue(video_file.is_video())

        # Test image file
        image_file = MediaFile.objects.create(
            original_filename="test.jpg",
            file_size=1000,
            mime_type="image/jpeg",
            file_hash="dummy_hash",
        )
        self.assertFalse(image_file.is_video())

    def test_media_file_duration_display_method(self):
        """Test get_duration_display() method"""
        # Test various durations
        test_cases = [
            (0, "0:00"),
            (30, "0:30"),
            (60, "1:00"),
            (90, "1:30"),
            (3600, "1:00:00"),  # 1 hour
            (3665, "1:01:05"),  # 1 hour, 1 minute, 5 seconds
        ]

        for duration, expected in test_cases:
            video_file = self.create_test_video_media_file(duration=duration)
            self.assertEqual(video_file.get_duration_display(), expected)

    def test_media_file_video_metadata_extraction(self):
        """Test extract_video_metadata() method"""
        video_file = self.create_test_video_media_file()

        # Mock ffmpeg probe response
        mock_probe_result = {
            "streams": [
                {
                    "codec_type": "video",
                    "duration": "60.0",
                    "width": 1920,
                    "height": 1080,
                    "codec_name": "h264",
                    "codec_long_name": "H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
                    "profile": "High",
                    "level": 40,
                    "pix_fmt": "yuv420p",
                    "bit_rate": "5000000",
                    "r_frame_rate": "30/1",
                }
            ],
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "bit_rate": "5000000"},
        }

        with patch("ffmpeg.probe", return_value=mock_probe_result):
            video_file.extract_video_metadata()

            self.assertEqual(video_file.duration, 60)
            self.assertEqual(video_file.width, 1920)
            self.assertEqual(video_file.height, 1080)
            self.assertEqual(video_file.video_codec, "h264")
            self.assertEqual(video_file.video_bitrate, 5000000)
            self.assertEqual(video_file.fps, 30.0)

    def test_media_file_video_thumbnail_generation(self):
        """Test generate_video_thumbnail() method - basic functionality"""
        video_file = self.create_test_video_media_file()

        # Ensure the video file has no existing thumbnail
        video_file.thumbnail = None

        # Test that the method doesn't crash when called
        # The method records ffmpeg failures in metadata instead of raising,
        # so a successful call is the whole contract.
        video_file.generate_video_thumbnail()

        # Test early return conditions
        # 1. Method should return early if file doesn't exist
        video_file_no_file = MediaFile.objects.create(
            original_filename="test.mp4",
            file_size=1000,
            mime_type="video/mp4",
            file_hash="dummy_hash_no_file",
            duration=60,
        )
        # Should not crash
        video_file_no_file.generate_video_thumbnail()

        # 2. Method should return early if not a video
        image_file = MediaFile.objects.create(
            original_filename="test.jpg",
            file_size=1000,
            mime_type="image/jpeg",
            file_hash="dummy_hash_image",
        )
        # Should not crash
        image_file.generate_video_thumbnail()

        # 3. Method should return early if thumbnail already exists
        video_file.thumbnail = "fake_thumbnail.jpg"
        video_file.generate_video_thumbnail()  # Should return early

    def test_media_file_video_duration_validation(self):
        """Test validate_video_duration() method"""
        # Test valid duration
        valid_video = self.create_test_video_media_file(duration=120)  # 2 minutes
        valid_video.validate_video_duration()  # Should not raise

        # Test invalid duration
        invalid_video = self.create_test_video_media_file(duration=180)  # 3 minutes
        with self.assertRaises(ValidationError):
            invalid_video.validate_video_duration()

    def test_media_file_video_security_validation(self):
        """Test validate_video_security() method"""
        video_file = self.create_test_video_media_file()

        # Test valid video
        video_file.validate_video_security()  # Should not raise

        # Test oversized video: the effective limit is 100MB (the later
        # MEDIA_VIDEO_MAX_SIZE override in config/settings.py wins).
        video_file.file_size = 150 * 1024 * 1024  # 150MB
        with self.assertRaises(ValidationError):
            video_file.validate_video_security()

        # Test invalid video MIME type (still video/* but not allowed)
        video_file.file_size = 1000  # Reset size
        video_file.mime_type = "video/avi"  # Not in allowed types
        with self.assertRaises(ValidationError):
            video_file.validate_video_security()

        # Test invalid codec
        video_file.mime_type = "video/mp4"  # Reset MIME type
        video_file.video_codec = "dangerous_codec"
        with self.assertRaises(ValidationError):
            video_file.validate_video_security()

    def test_media_file_get_secure_video_path(self):
        """Test get_secure_video_path() method"""
        video_file = self.create_test_video_media_file()

        secure_path = video_file.get_secure_video_path()
        self.assertIsNotNone(secure_path)
        self.assertIn("/mediafiles/serve/", secure_path)
        self.assertIn(str(video_file.id), secure_path)

        # Test non-video file
        image_file = MediaFile.objects.create(
            original_filename="test.jpg",
            file_size=1000,
            mime_type="image/jpeg",
            file_hash="dummy_hash",
        )
        self.assertIsNone(image_file.get_secure_video_path())
