"""
Test file upload fix to ensure original files are saved correctly.

This test verifies that the critical fix for file saving works properly.
"""

import os
import tempfile
from pathlib import Path
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from PIL import Image

from apps.mediafiles.models import MediaFile, Photo
from apps.patients.models import Patient
# Note: Hospital model removed after single-hospital refactor
from apps.accounts.models import EqmdCustomUser


class FileUploadFixTestCase(TestCase):
    """Test case for file upload fix."""

    def setUp(self):
        """Set up test data."""
        # Create test hospital
        self.hospital = Hospital.objects.create(
            name="Test Hospital",
            address="123 Test St",
            phone="555-0123"
        )
        
        # Create test user
        self.user = EqmdCustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        # Create test patient
        from datetime import date
        self.patient = Patient.objects.create(
            name="Test Patient",
            birthday=date(1990, 1, 1),
            current_hospital=self.hospital,
            created_by=self.user,
            updated_by=self.user
        )

    def create_test_image(self, filename="test_image.jpg", size=(100, 100)):
        """Create a test image file."""
        # Create a simple test image
        image = Image.new('RGB', size, color='red')
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        image.save(temp_file.name, 'JPEG')
        
        # Read file content
        with open(temp_file.name, 'rb') as f:
            content = f.read()
        
        # Clean up temp file
        os.unlink(temp_file.name)
        
        return SimpleUploadedFile(
            filename,
            content,
            content_type='image/jpeg'
        )

    def test_media_file_creation_saves_original_file(self):
        """Test that MediaFile.create_from_upload saves the original file to disk."""
        # Create test image
        uploaded_file = self.create_test_image("test_upload.jpg")
        
        # Create MediaFile using the fixed method
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        
        # Verify MediaFile was created
        self.assertIsNotNone(media_file.id)
        self.assertEqual(media_file.original_filename, "test-upload.jpg")  # Normalized filename
        self.assertEqual(media_file.mime_type, "image/jpeg")
        self.assertGreater(media_file.file_size, 0)
        
        # CRITICAL TEST: Verify original file exists on disk
        file_path = Path(settings.MEDIA_ROOT) / media_file.file.name
        self.assertTrue(file_path.exists(), f"Original file should exist at {file_path}")
        self.assertTrue(file_path.is_file(), "Original file should be a regular file")
        
        # Verify file has content
        self.assertGreater(file_path.stat().st_size, 0, "Original file should not be empty")
        
        # Verify metadata was extracted
        self.assertIsNotNone(media_file.width)
        self.assertIsNotNone(media_file.height)
        self.assertEqual(media_file.width, 100)
        self.assertEqual(media_file.height, 100)
        
        # Verify thumbnail was generated
        if media_file.thumbnail:
            thumbnail_path = Path(settings.MEDIA_ROOT) / media_file.thumbnail.name
            self.assertTrue(thumbnail_path.exists(), "Thumbnail should exist on disk")

    def test_photo_creation_with_media_file(self):
        """Test that Photo creation works with the fixed MediaFile process."""
        from apps.mediafiles.forms import PhotoCreateForm
        from apps.events.models import Event
        
        # Create test image
        uploaded_file = self.create_test_image("photo_test.jpg")
        
        # Simulate form data
        form_data = {
            'description': 'Test photo upload',
            'event_datetime': '2024-01-01T12:00',
            'caption': 'Test caption'
        }
        
        form_files = {
            'image': uploaded_file
        }
        
        # Create form and validate
        form = PhotoCreateForm(
            data=form_data,
            files=form_files,
            user=self.user,
            patient=self.patient
        )
        
        self.assertTrue(form.is_valid(), f"Form should be valid. Errors: {form.errors}")
        
        # Save the photo
        photo = form.save()
        
        # Verify Photo was created
        self.assertIsNotNone(photo.id)
        self.assertEqual(photo.event_type, Event.PHOTO_EVENT)
        self.assertEqual(photo.patient, self.patient)
        self.assertEqual(photo.created_by, self.user)
        
        # Verify MediaFile was created and linked
        self.assertIsNotNone(photo.media_file)
        media_file = photo.media_file
        
        # CRITICAL TEST: Verify original file exists on disk
        file_path = Path(settings.MEDIA_ROOT) / media_file.file.name
        self.assertTrue(file_path.exists(), f"Original file should exist at {file_path}")
        
        # Verify file can be opened and read
        with open(file_path, 'rb') as f:
            content = f.read()
            self.assertGreater(len(content), 0, "File should have content")

    def test_secure_url_generation(self):
        """Test that secure URLs are generated correctly."""
        # Create test image and MediaFile
        uploaded_file = self.create_test_image("url_test.jpg")
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        
        # Test secure URL generation
        secure_url = media_file.get_secure_url()
        self.assertIn('/mediafiles/serve/', secure_url)
        self.assertIn(str(media_file.id), secure_url)

    def test_file_serving_view_access(self):
        """Test that file serving views can access the saved files."""
        from django.test import Client
        from django.urls import reverse
        
        # Create test image and Photo
        uploaded_file = self.create_test_image("serve_test.jpg")
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        
        photo = Photo.objects.create(
            media_file=media_file,
            patient=self.patient,
            created_by=self.user,
            description="Test photo for serving"
        )
        
        # Login user
        client = Client()
        client.force_login(self.user)
        
        # Test file serving URL
        serve_url = reverse('mediafiles:serve_file', kwargs={'file_id': media_file.id})
        
        # Make request (this should not return 404 anymore)
        response = client.get(serve_url)
        
        # Should not be 404 (the original problem)
        self.assertNotEqual(response.status_code, 404, 
                          "File serving should not return 404 when file exists")
        
        # Should be either 200 (success) or 403 (permission denied, but file exists)
        self.assertIn(response.status_code, [200, 403], 
                     f"Expected 200 or 403, got {response.status_code}")

    def tearDown(self):
        """Clean up test files."""
        # Clean up any created media files
        for media_file in MediaFile.objects.all():
            if media_file.file:
                try:
                    file_path = Path(settings.MEDIA_ROOT) / media_file.file.name
                    if file_path.exists():
                        file_path.unlink()
                except:
                    pass
            if media_file.thumbnail:
                try:
                    thumbnail_path = Path(settings.MEDIA_ROOT) / media_file.thumbnail.name
                    if thumbnail_path.exists():
                        thumbnail_path.unlink()
                except:
                    pass
