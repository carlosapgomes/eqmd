# MediaFiles Integration Tests
# End-to-end integration tests for photo functionality

import os
import tempfile
from django.test import TestCase, TransactionTestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from apps.mediafiles.models import MediaFile, Photo
from apps.mediafiles.forms import PhotoCreateForm
from apps.patients.models import Patient
from apps.events.models import Event

User = get_user_model()


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    MEDIA_USE_UUID_FILENAMES=True,
    MEDIA_ENABLE_FILE_DEDUPLICATION=True
)
class PhotoUploadWorkflowTests(TransactionTestCase):
    """Tests for complete photo upload workflow"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='doctor',
            email='doctor@hospital.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            name="John Doe",
            birth_date="1980-05-15",
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create valid test image
        self.test_image_content = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01'
            b'\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff'
            b'\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        )
    
    def test_complete_photo_upload_workflow(self):
        """Test complete photo upload from form to database"""
        self.client.force_login(self.user)
        
        # Step 1: Access photo upload form
        upload_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(upload_url)
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Submit photo upload form
        uploaded_file = SimpleUploadedFile(
            "test_xray.jpg",
            self.test_image_content,
            content_type="image/jpeg"
        )
        
        form_data = {
            'description': 'Chest X-ray showing clear lungs',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Patient shows good recovery',
            'image': uploaded_file
        }
        
        response = self.client.post(upload_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Step 3: Verify photo was created in database
        photo = Photo.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(photo)
        self.assertEqual(photo.description, 'Chest X-ray showing clear lungs')
        self.assertEqual(photo.caption, 'Patient shows good recovery')
        self.assertEqual(photo.event_type, Event.PHOTO_EVENT)
        self.assertEqual(photo.created_by, self.user)
        
        # Step 4: Verify MediaFile was created
        self.assertIsNotNone(photo.media_file)
        self.assertEqual(photo.media_file.original_filename, 'test_xray.jpg')
        self.assertEqual(photo.media_file.mime_type, 'image/jpeg')
        self.assertGreater(photo.media_file.file_size, 0)
        
        # Step 5: Verify file was saved to disk
        self.assertTrue(photo.media_file.file.name)
        self.assertTrue(os.path.exists(photo.media_file.file.path))
        
        # Step 6: Verify secure filename was used
        filename = os.path.basename(photo.media_file.file.name)
        self.assertNotIn('test_xray', filename)  # Original name not in path
        self.assertTrue(filename.endswith('.jpg'))
        
        # Step 7: Verify thumbnail generation
        if photo.media_file.thumbnail:
            self.assertTrue(os.path.exists(photo.media_file.thumbnail.path))
    
    def test_photo_viewing_workflow(self):
        """Test photo viewing in detail view"""
        # Create photo first
        uploaded_file = SimpleUploadedFile(
            "test.jpg",
            self.test_image_content,
            content_type="image/jpeg"
        )
        
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        photo = Photo.objects.create(
            media_file=media_file,
            description="Test photo for viewing",
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client.force_login(self.user)
        
        # Test photo detail view
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': photo.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        
        # Verify photo information is displayed
        self.assertContains(response, photo.description)
        self.assertContains(response, photo.patient.name)
        
        # Test file serving
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': media_file.id})
        response = self.client.get(file_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
    
    def test_photo_editing_workflow(self):
        """Test photo editing workflow"""
        # Create photo first
        uploaded_file = SimpleUploadedFile(
            "test.jpg",
            self.test_image_content,
            content_type="image/jpeg"
        )
        
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        photo = Photo.objects.create(
            media_file=media_file,
            description="Original description",
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client.force_login(self.user)
        
        # Test edit form access
        edit_url = reverse('mediafiles:photo_update', kwargs={'pk': photo.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)
        
        # Test form submission
        form_data = {
            'description': 'Updated description',
            'event_datetime': photo.event_datetime.strftime('%Y-%m-%dT%H:%M'),
            'caption': 'Updated caption'
        }
        
        response = self.client.post(edit_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify changes were saved
        photo.refresh_from_db()
        self.assertEqual(photo.description, 'Updated description')
        self.assertEqual(photo.caption, 'Updated caption')
        self.assertEqual(photo.updated_by, self.user)
    
    def test_photo_deletion_workflow(self):
        """Test photo deletion workflow with file cleanup"""
        # Create photo first
        uploaded_file = SimpleUploadedFile(
            "test.jpg",
            self.test_image_content,
            content_type="image/jpeg"
        )
        
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        photo = Photo.objects.create(
            media_file=media_file,
            description="Photo to be deleted",
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Store file paths for cleanup verification
        file_path = photo.media_file.file.path
        thumbnail_path = photo.media_file.thumbnail.path if photo.media_file.thumbnail else None
        
        self.client.force_login(self.user)
        
        # Test delete confirmation page
        delete_url = reverse('mediafiles:photo_delete', kwargs={'pk': photo.pk})
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, photo.description)
        
        # Test actual deletion
        response = self.client.post(delete_url, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify photo was deleted from database
        self.assertFalse(Photo.objects.filter(pk=photo.pk).exists())
        self.assertFalse(MediaFile.objects.filter(pk=media_file.pk).exists())
        
        # Verify files were cleaned up from disk
        self.assertFalse(os.path.exists(file_path))
        if thumbnail_path:
            self.assertFalse(os.path.exists(thumbnail_path))


class PermissionIntegrationTests(TestCase):
    """Tests for permission-based access integration"""

    def setUp(self):
        """Set up test data"""
        self.doctor1 = User.objects.create_user(
            username='doctor1',
            email='doctor1@hospital.com',
            password='testpass123'
        )

        self.doctor2 = User.objects.create_user(
            username='doctor2',
            email='doctor2@hospital.com',
            password='testpass123'
        )

        self.patient = Patient.objects.create(
            name="Jane Smith",
            birth_date="1975-03-20",
            created_by=self.doctor1,
            updated_by=self.doctor1
        )

        # Create test photo
        test_image_content = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01'
            b'\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff'
            b'\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        )

        uploaded_file = SimpleUploadedFile(
            "test.jpg",
            test_image_content,
            content_type="image/jpeg"
        )

        self.media_file = MediaFile.objects.create_from_upload(uploaded_file)
        self.photo = Photo.objects.create(
            media_file=self.media_file,
            description="Private patient photo",
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.doctor1,
            updated_by=self.doctor1
        )

    def test_authorized_access_workflow(self):
        """Test that authorized users can access photos"""
        self.client.force_login(self.doctor1)

        # Test photo detail access
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': self.photo.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        # Test file serving access
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': self.media_file.id})
        response = self.client.get(file_url)
        self.assertEqual(response.status_code, 200)

        # Test thumbnail access
        thumbnail_url = reverse('mediafiles:serve_thumbnail', kwargs={'file_id': self.media_file.id})
        response = self.client.get(thumbnail_url)
        # Should either serve thumbnail or return 404 if not generated
        self.assertIn(response.status_code, [200, 404])

    def test_unauthorized_access_prevention(self):
        """Test that unauthorized users cannot access photos"""
        self.client.force_login(self.doctor2)

        # Test photo detail access denial
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': self.photo.pk})
        response = self.client.get(detail_url)
        self.assertIn(response.status_code, [403, 404])

        # Test file serving access denial
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': self.media_file.id})
        response = self.client.get(file_url)
        self.assertIn(response.status_code, [403, 404])

    def test_unauthenticated_access_prevention(self):
        """Test that unauthenticated users cannot access photos"""
        # Test without login
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': self.photo.pk})
        response = self.client.get(detail_url)
        self.assertIn(response.status_code, [302, 401, 403])  # Redirect to login or denied

        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': self.media_file.id})
        response = self.client.get(file_url)
        self.assertIn(response.status_code, [302, 401, 403])

    def test_edit_permission_workflow(self):
        """Test edit permission enforcement"""
        self.client.force_login(self.doctor1)

        # Creator should be able to edit within 24 hours
        edit_url = reverse('mediafiles:photo_update', kwargs={'pk': self.photo.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)

        # Test unauthorized user cannot edit
        self.client.force_login(self.doctor2)
        response = self.client.get(edit_url)
        self.assertIn(response.status_code, [403, 404])

    def test_delete_permission_workflow(self):
        """Test delete permission enforcement"""
        self.client.force_login(self.doctor1)

        # Creator should be able to delete within 24 hours
        delete_url = reverse('mediafiles:photo_delete', kwargs={'pk': self.photo.pk})
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)

        # Test unauthorized user cannot delete
        self.client.force_login(self.doctor2)
        response = self.client.get(delete_url)
        self.assertIn(response.status_code, [403, 404])


class ErrorHandlingIntegrationTests(TestCase):
    """Tests for error handling and user feedback"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.patient = Patient.objects.create(
            name="Test Patient",
            birth_date="1990-01-01",
            created_by=self.user,
            updated_by=self.user
        )

    def test_invalid_file_upload_error_handling(self):
        """Test error handling for invalid file uploads"""
        self.client.force_login(self.user)

        upload_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.pk})

        # Test with invalid file type
        invalid_file = SimpleUploadedFile(
            "document.txt",
            b"This is not an image",
            content_type="text/plain"
        )

        form_data = {
            'description': 'Test photo',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'image': invalid_file
        }

        response = self.client.post(upload_url, form_data)
        self.assertEqual(response.status_code, 200)  # Form redisplayed with errors
        self.assertContains(response, 'error')  # Error message displayed

    def test_missing_file_error_handling(self):
        """Test error handling when no file is uploaded"""
        self.client.force_login(self.user)

        upload_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.pk})

        form_data = {
            'description': 'Test photo',
            'event_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            # No image file
        }

        response = self.client.post(upload_url, form_data)
        self.assertEqual(response.status_code, 200)  # Form redisplayed with errors
        self.assertContains(response, 'required')  # Required field error

    def test_nonexistent_photo_error_handling(self):
        """Test error handling for nonexistent photos"""
        self.client.force_login(self.user)

        # Try to access nonexistent photo
        fake_uuid = '12345678-1234-5678-9012-123456789012'
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': fake_uuid})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 404)

    def test_file_serving_error_handling(self):
        """Test error handling for file serving"""
        self.client.force_login(self.user)

        # Try to access nonexistent file
        fake_uuid = '12345678-1234-5678-9012-123456789012'
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': fake_uuid})
        response = self.client.get(file_url)
        self.assertEqual(response.status_code, 404)


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    MEDIA_ENABLE_FILE_DEDUPLICATION=True
)
class FileDeduplicationIntegrationTests(TestCase):
    """Tests for file deduplication integration"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.patient1 = Patient.objects.create(
            name="Patient One",
            birth_date="1980-01-01",
            created_by=self.user,
            updated_by=self.user
        )

        self.patient2 = Patient.objects.create(
            name="Patient Two",
            birth_date="1985-01-01",
            created_by=self.user,
            updated_by=self.user
        )

        # Same image content for deduplication testing
        self.test_image_content = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01'
            b'\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff'
            b'\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        )

    def test_duplicate_file_deduplication_workflow(self):
        """Test that duplicate files are deduplicated"""
        # Upload same image for two different patients
        uploaded_file1 = SimpleUploadedFile(
            "xray_patient1.jpg",
            self.test_image_content,
            content_type="image/jpeg"
        )

        uploaded_file2 = SimpleUploadedFile(
            "xray_patient2.jpg",
            self.test_image_content,
            content_type="image/jpeg"
        )

        # Create first MediaFile
        media_file1 = MediaFile.objects.create_from_upload(uploaded_file1)
        photo1 = Photo.objects.create(
            media_file=media_file1,
            description="X-ray for patient 1",
            event_datetime=timezone.now(),
            patient=self.patient1,
            created_by=self.user,
            updated_by=self.user
        )

        # Create second MediaFile with same content
        media_file2 = MediaFile.objects.create_from_upload(uploaded_file2)
        photo2 = Photo.objects.create(
            media_file=media_file2,
            description="X-ray for patient 2",
            event_datetime=timezone.now(),
            patient=self.patient2,
            created_by=self.user,
            updated_by=self.user
        )

        # Verify deduplication occurred
        self.assertEqual(media_file1.id, media_file2.id)  # Same MediaFile instance
        self.assertEqual(media_file1.file_hash, media_file2.file_hash)

        # Verify both photos reference the same file
        self.assertEqual(photo1.media_file.file.path, photo2.media_file.file.path)

        # Verify only one file exists on disk
        file_path = media_file1.file.path
        self.assertTrue(os.path.exists(file_path))

        # Count MediaFile instances - should be only 1
        self.assertEqual(MediaFile.objects.count(), 1)

    def test_unique_files_no_deduplication(self):
        """Test that unique files are not deduplicated"""
        # Create two different image contents
        content1 = self.test_image_content
        content2 = self.test_image_content[:-10] + b'\xff\xd9'  # Different ending

        uploaded_file1 = SimpleUploadedFile(
            "image1.jpg",
            content1,
            content_type="image/jpeg"
        )

        uploaded_file2 = SimpleUploadedFile(
            "image2.jpg",
            content2,
            content_type="image/jpeg"
        )

        # Create MediaFiles
        media_file1 = MediaFile.objects.create_from_upload(uploaded_file1)
        media_file2 = MediaFile.objects.create_from_upload(uploaded_file2)

        # Verify no deduplication occurred
        self.assertNotEqual(media_file1.id, media_file2.id)
        self.assertNotEqual(media_file1.file_hash, media_file2.file_hash)

        # Verify separate files exist
        self.assertNotEqual(media_file1.file.path, media_file2.file.path)
        self.assertTrue(os.path.exists(media_file1.file.path))
        self.assertTrue(os.path.exists(media_file2.file.path))

        # Count MediaFile instances - should be 2
        self.assertEqual(MediaFile.objects.count(), 2)

    def test_deduplication_with_deletion_workflow(self):
        """Test deduplication behavior when one photo is deleted"""
        # Create two photos with same content
        uploaded_file1 = SimpleUploadedFile(
            "shared_image.jpg",
            self.test_image_content,
            content_type="image/jpeg"
        )

        uploaded_file2 = SimpleUploadedFile(
            "shared_image_copy.jpg",
            self.test_image_content,
            content_type="image/jpeg"
        )

        media_file1 = MediaFile.objects.create_from_upload(uploaded_file1)
        photo1 = Photo.objects.create(
            media_file=media_file1,
            description="First photo",
            event_datetime=timezone.now(),
            patient=self.patient1,
            created_by=self.user,
            updated_by=self.user
        )

        media_file2 = MediaFile.objects.create_from_upload(uploaded_file2)
        photo2 = Photo.objects.create(
            media_file=media_file2,
            description="Second photo",
            event_datetime=timezone.now(),
            patient=self.patient2,
            created_by=self.user,
            updated_by=self.user
        )

        # Verify deduplication
        self.assertEqual(media_file1.id, media_file2.id)
        file_path = media_file1.file.path

        # Delete first photo
        photo1.delete()

        # Verify file still exists (referenced by second photo)
        self.assertTrue(os.path.exists(file_path))
        self.assertTrue(MediaFile.objects.filter(id=media_file1.id).exists())

        # Delete second photo
        photo2.delete()

        # Now file and MediaFile should be deleted
        self.assertFalse(os.path.exists(file_path))
        self.assertFalse(MediaFile.objects.filter(id=media_file1.id).exists())
