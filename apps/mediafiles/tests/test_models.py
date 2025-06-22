# MediaFiles Model Tests
# Tests for media file models

import os
import tempfile
import hashlib
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.events.models import Event
from apps.patients.models import Patient
from apps.hospitals.models import Hospital
from apps.mediafiles.models import MediaFile, Photo
from apps.mediafiles.utils import calculate_file_hash

User = get_user_model()


class MediaFileModelTests(TestCase):
    """Tests for MediaFile model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            short_name='TH',
            created_by=self.user,
            updated_by=self.user
        )

        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

        # Load test image
        test_image_path = os.path.join(
            os.path.dirname(__file__),
            'test_media',
            'small_image.jpg'
        )
        with open(test_image_path, 'rb') as f:
            self.test_image_content = f.read()

    def create_test_image_file(self, filename='test.jpg', content=None):
        """Create a test image file for testing."""
        if content is None:
            content = self.test_image_content
        return SimpleUploadedFile(
            filename,
            content,
            content_type='image/jpeg'
        )

    def test_media_file_creation(self):
        """Test media file creation"""
        uploaded_file = self.create_test_image_file()

        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        self.assertIsNotNone(media_file.id)
        self.assertEqual(media_file.original_filename, 'test.jpg')
        self.assertEqual(media_file.file_size, len(self.test_image_content))
        self.assertEqual(media_file.mime_type, 'image/jpeg')
        self.assertIsNotNone(media_file.file_hash)
        self.assertTrue(media_file.file.name.endswith('.jpg'))

    def test_media_file_validation(self):
        """Test media file validation"""
        # Test valid image
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        media_file.full_clean()  # Should not raise ValidationError

        # Test invalid extension
        invalid_file = SimpleUploadedFile(
            'test.txt',
            b'not an image',
            content_type='text/plain'
        )

        with self.assertRaises(ValidationError):
            MediaFile.objects.create_from_upload(invalid_file)

    def test_media_file_hash_calculation(self):
        """Test media file hash calculation for deduplication"""
        uploaded_file1 = self.create_test_image_file('test1.jpg')
        uploaded_file2 = self.create_test_image_file('test2.jpg')  # Same content, different name

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
        self.assertIn('photos/', file_path)
        self.assertIn('/originals/', file_path)
        # Should contain year/month pattern
        import re
        self.assertTrue(re.search(r'\d{4}/\d{2}', file_path))

    def test_media_file_string_representation(self):
        """Test MediaFile string representation"""
        uploaded_file = self.create_test_image_file('my_photo.jpg')
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        self.assertEqual(str(media_file), 'my_photo.jpg')

    def test_media_file_display_methods(self):
        """Test MediaFile display methods"""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # Test file size display
        size_display = media_file.get_display_size()
        self.assertIn('KB', size_display)

        # Test secure URL
        secure_url = media_file.get_secure_url()
        self.assertIn('/mediafiles/serve/', secure_url)
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
    """Tests for Photo model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            short_name='TH',
            created_by=self.user,
            updated_by=self.user
        )

        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

    def create_test_image_file(self, filename='test.jpg'):
        """Create a test image file for testing."""
        test_image_path = os.path.join(
            os.path.dirname(__file__),
            'test_media',
            'small_image.jpg'
        )
        with open(test_image_path, 'rb') as f:
            content = f.read()

        return SimpleUploadedFile(
            filename,
            content,
            content_type='image/jpeg'
        )

    def test_photo_creation(self):
        """Test photo creation"""
        # Create MediaFile first
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # Create Photo
        photo = Photo.objects.create(
            media_file=media_file,
            description='Test photo',
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            caption='Test caption'
        )

        self.assertIsNotNone(photo.id)
        self.assertEqual(photo.media_file, media_file)
        self.assertEqual(photo.description, 'Test photo')
        self.assertEqual(photo.caption, 'Test caption')
        self.assertEqual(photo.patient, self.patient)
        self.assertEqual(photo.created_by, self.user)

    def test_photo_event_type(self):
        """Test that photo uses correct event type"""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        photo = Photo.objects.create(
            media_file=media_file,
            description='Test photo',
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(photo.event_type, Event.PHOTO_EVENT)

    def test_photo_file_validation(self):
        """Test photo file validation"""
        # Create a non-image MediaFile (this would normally be prevented by MediaFile validation)
        media_file = MediaFile(
            original_filename='test.txt',
            file_size=100,
            mime_type='text/plain',
            file_hash='dummy_hash_123'
        )

        photo = Photo(
            media_file=media_file,
            description='Test photo',
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        with self.assertRaises(ValidationError):
            photo.full_clean()

    def test_photo_methods(self):
        """Test Photo model methods"""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        photo = Photo.objects.create(
            media_file=media_file,
            description='Test photo',
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        # Test get_absolute_url
        absolute_url = photo.get_absolute_url()
        self.assertIn('/mediafiles/photos/', absolute_url)
        self.assertIn(str(photo.id), absolute_url)

        # Test get_edit_url
        edit_url = photo.get_edit_url()
        self.assertIn('/edit/', edit_url)

        # Test get_thumbnail
        thumbnail_url = photo.get_thumbnail()
        self.assertIsNotNone(thumbnail_url)

        # Test get_file_info
        file_info = photo.get_file_info()
        self.assertIn('size', file_info)
        self.assertIn('dimensions', file_info)
        self.assertIn('filename', file_info)

    def test_photo_manager_optimization(self):
        """Test Photo manager query optimization"""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        Photo.objects.create(
            media_file=media_file,
            description='Test photo',
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        # Test that queryset includes select_related
        with self.assertNumQueries(1):
            photo = Photo.objects.first()
            # These should not trigger additional queries due to select_related
            _ = photo.media_file.original_filename
            _ = photo.patient.name
            _ = photo.created_by.username


# PhotoSeries and VideoClip tests will be implemented in future phases


class ModelIntegrationTests(TestCase):
    """Tests for model integration and relationships"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            short_name='TH',
            created_by=self.user,
            updated_by=self.user
        )

        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

    def create_test_image_file(self, filename='test.jpg'):
        """Create a test image file for testing."""
        test_image_path = os.path.join(
            os.path.dirname(__file__),
            'test_media',
            'small_image.jpg'
        )
        with open(test_image_path, 'rb') as f:
            content = f.read()

        return SimpleUploadedFile(
            filename,
            content,
            content_type='image/jpeg'
        )

    def test_event_model_integration(self):
        """Test integration with Event model"""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        photo = Photo.objects.create(
            media_file=media_file,
            description='Test photo',
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        # Test that Photo is an Event
        self.assertIsInstance(photo, Event)

        # Test that it appears in Event queries
        events = Event.objects.filter(patient=self.patient)
        self.assertIn(photo, events)

        # Test event type is correctly set
        self.assertEqual(photo.event_type, Event.PHOTO_EVENT)

    def test_patient_media_relationship(self):
        """Test relationship between patients and media files"""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        photo = Photo.objects.create(
            media_file=media_file,
            description='Test photo',
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        # Test patient can access their photos
        patient_photos = Photo.objects.filter(patient=self.patient)
        self.assertIn(photo, patient_photos)

        # Test photo belongs to correct patient
        self.assertEqual(photo.patient, self.patient)

    def test_user_permissions_on_media(self):
        """Test user permissions on media files"""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        photo = Photo.objects.create(
            media_file=media_file,
            description='Test photo',
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

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
        test_image_path = os.path.join(
            os.path.dirname(__file__),
            'test_media',
            'small_image.jpg'
        )
        with open(test_image_path, 'rb') as f:
            self.test_image_content = f.read()

    def test_file_hash_uniqueness(self):
        """Test that file hash ensures uniqueness"""
        uploaded_file1 = SimpleUploadedFile(
            'test1.jpg',
            self.test_image_content,
            content_type='image/jpeg'
        )
        uploaded_file2 = SimpleUploadedFile(
            'test2.jpg',
            self.test_image_content,  # Same content
            content_type='image/jpeg'
        )

        media_file1 = MediaFile.objects.create_from_upload(uploaded_file1)
        media_file2 = MediaFile.objects.create_from_upload(uploaded_file2)

        # Should be the same object due to deduplication
        self.assertEqual(media_file1.id, media_file2.id)

    def test_secure_filename_generation(self):
        """Test that filenames are securely generated"""
        uploaded_file = SimpleUploadedFile(
            '../../../etc/passwd.jpg',  # Malicious filename
            self.test_image_content,
            content_type='image/jpeg'
        )

        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # File path should not contain the malicious parts
        self.assertNotIn('..', media_file.file.name)
        self.assertNotIn('etc', media_file.file.name)
        self.assertNotIn('passwd', media_file.file.name)

        # Should contain UUID pattern
        import re
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        self.assertTrue(re.search(uuid_pattern, media_file.file.name))

    def test_file_extension_validation(self):
        """Test file extension validation"""
        # Test invalid extension
        invalid_file = SimpleUploadedFile(
            'malicious.exe',
            b'fake image content',
            content_type='application/octet-stream'
        )

        with self.assertRaises(ValidationError):
            MediaFile.objects.create_from_upload(invalid_file)

    def test_mime_type_validation(self):
        """Test MIME type validation"""
        # Test invalid MIME type
        invalid_file = SimpleUploadedFile(
            'test.jpg',
            b'not really an image',
            content_type='text/plain'
        )

        with self.assertRaises(ValidationError):
            MediaFile.objects.create_from_upload(invalid_file)
