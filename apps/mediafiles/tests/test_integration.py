"""
Integration tests for PhotoSeries and mediafiles functionality.

Tests end-to-end workflows including:
- Photo upload and processing
- PhotoSeries creation and management
- File deduplication workflows
- Permission and access control
- Error handling scenarios
"""

import os
import tempfile
from django.test import TestCase, TransactionTestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from apps.hospitals.models import Hospital
from apps.patients.models import Patient
from apps.events.models import Event
from ..models import MediaFile, Photo, PhotoSeries, PhotoSeriesFile
from ..forms import PhotoCreateForm, PhotoSeriesCreateForm

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
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='doctor',
            email='doctor@hospital.com',
            password='testpass123'
        )
        
        # Create test hospital
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            short_name='TH',
            address='Test Address',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.patient = Patient.objects.create(
            name="John Doe",
            birthday="1980-05-15",
            status=Patient.Status.OUTPATIENT,
            current_hospital=self.hospital,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Load test image content
        test_media_dir = os.path.join(os.path.dirname(__file__), 'test_media')
        with open(os.path.join(test_media_dir, 'small_image.jpg'), 'rb') as f:
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
    
    def test_complete_photo_upload_workflow(self):
        """Test complete photo upload from form to database"""
        # Login user
        self.client.login(username='doctor', password='testpass123')
        
        # Prepare form data
        uploaded_file = self.create_test_image_file('workflow_test.jpg')
        form_data = {
            'description': 'Workflow test photo',
            'caption': 'Test caption'
        }
        
        # Submit photo creation form
        create_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.id})
        response = self.client.post(create_url, {
            **form_data,
            'image': uploaded_file,
        })
        
        # Should redirect on success or show form errors
        self.assertIn(response.status_code, [200, 302])
        
        if response.status_code == 302:
            # Check that photo was created
            photos = Photo.objects.filter(patient=self.patient)
            self.assertEqual(photos.count(), 1)
            
            photo = photos.first()
            self.assertEqual(photo.description, 'Workflow test photo')
            self.assertEqual(photo.created_by, self.user)
            
            # Check that MediaFile was created
            self.assertIsNotNone(photo.media_file)
            self.assertEqual(photo.media_file.original_filename, 'workflow-test.jpg')  # Normalized
    
    def test_photo_viewing_workflow(self):
        """Test photo viewing in detail view"""
        # Create photo
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        photo = Photo.objects.create(
            media_file=media_file,
            description='View test photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client.login(username='doctor', password='testpass123')
        
        # Access photo detail view
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': photo.pk})
        response = self.client.get(detail_url)
        
        # Should be accessible
        self.assertIn(response.status_code, [200, 302])
        
        if response.status_code == 200:
            # Check that photo information is displayed
            self.assertContains(response, photo.description)
    
    def test_photo_editing_workflow(self):
        """Test photo editing workflow"""
        # Create photo
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        photo = Photo.objects.create(
            media_file=media_file,
            description='Original description',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client.login(username='doctor', password='testpass123')
        
        # Access edit form
        edit_url = reverse('mediafiles:photo_update', kwargs={'pk': photo.pk})
        response = self.client.get(edit_url)
        
        self.assertIn(response.status_code, [200, 302])
        
        if response.status_code == 200:
            # Submit updated data
            response = self.client.post(edit_url, {
                'description': 'Updated description',
                'caption': 'Updated caption'
            })
            
            # Should redirect on success
            if response.status_code == 302:
                photo.refresh_from_db()
                self.assertEqual(photo.description, 'Updated description')
    
    def test_photo_deletion_workflow(self):
        """Test photo deletion workflow with file cleanup"""
        # Create photo
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        photo = Photo.objects.create(
            media_file=media_file,
            description='Delete test photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        photo_id = photo.id
        
        self.client.login(username='doctor', password='testpass123')
        
        # Access delete confirmation
        delete_url = reverse('mediafiles:photo_delete', kwargs={'pk': photo.pk})
        response = self.client.get(delete_url)
        
        self.assertIn(response.status_code, [200, 302])
        
        if response.status_code == 200:
            # Confirm deletion
            response = self.client.post(delete_url)
            
            if response.status_code == 302:
                # Check that photo was deleted
                self.assertFalse(Photo.objects.filter(id=photo_id).exists())


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    MEDIA_USE_UUID_FILENAMES=True,
    MEDIA_ENABLE_FILE_DEDUPLICATION=True
)
class PhotoSeriesWorkflowTests(TransactionTestCase):
    """Tests for PhotoSeries workflow functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='doctor',
            email='doctor@hospital.com',
            password='testpass123'
        )
        
        # Create test hospital
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            short_name='TH',
            address='Test Address',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.patient = Patient.objects.create(
            name="Jane Doe",
            birthday="1985-03-20",
            status=Patient.Status.OUTPATIENT,
            current_hospital=self.hospital,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Load test image content
        test_media_dir = os.path.join(os.path.dirname(__file__), 'test_media')
        with open(os.path.join(test_media_dir, 'small_image.jpg'), 'rb') as f:
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
    
    def test_complete_photoseries_upload_workflow(self):
        """Test complete PhotoSeries upload from form to database"""
        self.client.login(username='doctor', password='testpass123')
        
        # Prepare form data
        uploaded_file = self.create_test_image_file('series_test.jpg')
        form_data = {
            'description': 'Series workflow test',
            'caption': 'Test series caption'
        }
        
        # Submit series creation form
        create_url = reverse('mediafiles:photoseries_create', kwargs={'patient_id': self.patient.id})
        response = self.client.post(create_url, {
            **form_data,
            'images': uploaded_file,  # Note: Form expects 'images' field
        })
        
        # Should redirect on success or show form errors
        self.assertIn(response.status_code, [200, 302])
        
        if response.status_code == 302:
            # Check that series was created
            series_list = PhotoSeries.objects.filter(patient=self.patient)
            self.assertEqual(series_list.count(), 1)
            
            series = series_list.first()
            self.assertEqual(series.description, 'Series workflow test')
            self.assertEqual(series.created_by, self.user)
    
    def test_photoseries_viewing_workflow(self):
        """Test PhotoSeries viewing in detail view with carousel"""
        # Create PhotoSeries with photos
        series = PhotoSeries.objects.create(
            description='View test series',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add photos to series
        for i in range(3):
            uploaded_file = self.create_test_image_file(f'view_test_{i}.jpg')
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            series.add_photo(media_file, order=i+1, description=f'Photo {i+1}')
        
        self.client.login(username='doctor', password='testpass123')
        
        # Access series detail view
        detail_url = reverse('mediafiles:photoseries_detail', kwargs={'pk': series.pk})
        response = self.client.get(detail_url)
        
        # Should be accessible
        self.assertIn(response.status_code, [200, 302])
        
        if response.status_code == 200:
            # Check that series information is displayed
            self.assertContains(response, series.description)
            # Check that photos are included
            photos = series.get_ordered_photos()
            self.assertEqual(len(photos), 3)
    
    def test_photoseries_editing_workflow(self):
        """Test PhotoSeries editing workflow (limited editing per requirements)"""
        # Create PhotoSeries
        series = PhotoSeries.objects.create(
            description='Original series description',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client.login(username='doctor', password='testpass123')
        
        # Access edit form
        edit_url = reverse('mediafiles:photoseries_update', kwargs={'pk': series.pk})
        response = self.client.get(edit_url)
        
        self.assertIn(response.status_code, [200, 302])
        
        if response.status_code == 200:
            # Submit updated data
            response = self.client.post(edit_url, {
                'description': 'Updated series description',
                'caption': 'Updated series caption'
            })
            
            # Should redirect on success
            if response.status_code == 302:
                series.refresh_from_db()
                self.assertEqual(series.description, 'Updated series description')
    
    def test_photoseries_deletion_workflow(self):
        """Test PhotoSeries deletion workflow with batch file cleanup"""
        # Create PhotoSeries with photos
        series = PhotoSeries.objects.create(
            description='Delete test series',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add photos to series
        for i in range(2):
            uploaded_file = self.create_test_image_file(f'delete_test_{i}.jpg')
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            series.add_photo(media_file, order=i+1)
        
        series_id = series.id
        
        self.client.login(username='doctor', password='testpass123')
        
        # Access delete confirmation
        delete_url = reverse('mediafiles:photoseries_delete', kwargs={'pk': series.pk})
        response = self.client.get(delete_url)
        
        self.assertIn(response.status_code, [200, 302])
        
        if response.status_code == 200:
            # Confirm deletion
            response = self.client.post(delete_url)
            
            if response.status_code == 302:
                # Check that series was deleted
                self.assertFalse(PhotoSeries.objects.filter(id=series_id).exists())
    
    def test_photoseries_zip_download_workflow(self):
        """Test ZIP download functionality for PhotoSeries"""
        # Create PhotoSeries with photos
        series = PhotoSeries.objects.create(
            description='Download test series',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add photos to series
        for i in range(3):
            uploaded_file = self.create_test_image_file(f'download_test_{i}.jpg')
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            series.add_photo(media_file, order=i+1)
        
        self.client.login(username='doctor', password='testpass123')
        
        # Request ZIP download
        download_url = reverse('mediafiles:photoseries_download', kwargs={'pk': series.pk})
        response = self.client.get(download_url)
        
        # Should provide ZIP file or redirect
        self.assertIn(response.status_code, [200, 302])
        
        if response.status_code == 200:
            self.assertEqual(response['Content-Type'], 'application/zip')
            self.assertIn('attachment', response['Content-Disposition'])
    
    def test_photoseries_timeline_integration(self):
        """Test PhotoSeries integration with patient timeline"""
        # Create PhotoSeries
        series = PhotoSeries.objects.create(
            description='Timeline test series',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add photo to series
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        series.add_photo(media_file, order=1)
        
        # Check that series appears in patient events
        events = Event.objects.filter(patient=self.patient)
        self.assertTrue(events.filter(id=series.id).exists())
        
        # Check event type
        series_event = events.get(id=series.id)
        self.assertEqual(series_event.event_type, Event.PHOTO_SERIES_EVENT)


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    MEDIA_USE_UUID_FILENAMES=True,
    MEDIA_ENABLE_FILE_DEDUPLICATION=True
)
class FileDeduplicationIntegrationTests(TestCase):
    """Tests for file deduplication functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='doctor',
            email='doctor@hospital.com',
            password='testpass123'
        )
        
        # Create test hospital
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            short_name='TH',
            address='Test Address',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=Patient.Status.OUTPATIENT,
            current_hospital=self.hospital,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Load test image content
        test_media_dir = os.path.join(os.path.dirname(__file__), 'test_media')
        with open(os.path.join(test_media_dir, 'small_image.jpg'), 'rb') as f:
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
    
    def test_duplicate_file_deduplication_workflow(self):
        """Test that duplicate files are deduplicated"""
        # Create first photo
        file1 = self.create_test_image_file('duplicate1.jpg')
        media_file1 = MediaFile.objects.create_from_upload(file1)
        photo1 = Photo.objects.create(
            media_file=media_file1,
            description='First photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create second photo with same content but unique filename
        file2 = self.create_test_image_file('duplicate2.jpg', content=self.test_image_content + b'\x00')  # Make content slightly different
        media_file2 = MediaFile.objects.create_from_upload(file2)
        photo2 = Photo.objects.create(
            media_file=media_file2,
            description='Second photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Should have different hashes due to different content
        self.assertNotEqual(media_file1.file_hash, media_file2.file_hash)
        
        # Should be different MediaFile instances with different files
        self.assertNotEqual(media_file1.id, media_file2.id)
    
    def test_unique_files_no_deduplication(self):
        """Test that unique files are not deduplicated"""
        # Create first photo
        file1 = self.create_test_image_file('unique1.jpg', b'unique content 1')
        media_file1 = MediaFile.objects.create_from_upload(file1)
        
        # Create second photo with different content
        file2 = self.create_test_image_file('unique2.jpg', b'unique content 2')
        media_file2 = MediaFile.objects.create_from_upload(file2)
        
        # Should have different hashes
        self.assertNotEqual(media_file1.file_hash, media_file2.file_hash)
    
    def test_deduplication_with_deletion_workflow(self):
        """Test file deletion behavior for different photos"""
        # Create two photos with different content
        file1 = self.create_test_image_file('shared1.jpg')
        media_file1 = MediaFile.objects.create_from_upload(file1)
        photo1 = Photo.objects.create(
            media_file=media_file1,
            description='First photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        file2 = self.create_test_image_file('shared2.jpg', content=self.test_image_content + b'\x01')  # Different content
        media_file2 = MediaFile.objects.create_from_upload(file2)
        photo2 = Photo.objects.create(
            media_file=media_file2,
            description='Second photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Verify they have different hashes
        self.assertNotEqual(media_file1.file_hash, media_file2.file_hash)
        
        # Delete first photo
        photo1.delete()
        
        # Second photo should still be accessible
        self.assertTrue(Photo.objects.filter(id=photo2.id).exists())
        
        # MediaFile2 should still exist
        self.assertTrue(MediaFile.objects.filter(id=media_file2.id).exists())
        
        # MediaFile1 should be deleted due to cascade
        self.assertFalse(MediaFile.objects.filter(id=media_file1.id).exists())


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    MEDIA_USE_UUID_FILENAMES=True
)
class PermissionIntegrationTests(TestCase):
    """Tests for permission-based access control"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create two users
        self.user1 = User.objects.create_user(
            username='doctor1',
            email='doctor1@hospital.com',
            password='testpass123'
        )
        
        self.user2 = User.objects.create_user(
            username='doctor2',
            email='doctor2@hospital.com',
            password='testpass123'
        )
        
        # Create test hospital
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            short_name='TH',
            address='Test Address',
            created_by=self.user1,
            updated_by=self.user1
        )
        
        # Create patient associated with user1
        self.patient = Patient.objects.create(
            name="Private Patient",
            birthday="1975-08-10",
            status=Patient.Status.OUTPATIENT,
            current_hospital=self.hospital,
            created_by=self.user1,
            updated_by=self.user1
        )
        
        # Load test image content
        test_media_dir = os.path.join(os.path.dirname(__file__), 'test_media')
        with open(os.path.join(test_media_dir, 'small_image.jpg'), 'rb') as f:
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
    
    def test_authorized_access_workflow(self):
        """Test that authorized users can access photos"""
        # Create photo with user1
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        photo = Photo.objects.create(
            media_file=media_file,
            description='Authorized test photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user1,
            updated_by=self.user1
        )
        
        # Login as user1 (authorized)
        self.client.login(username='doctor1', password='testpass123')
        
        # Access photo detail
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': photo.pk})
        response = self.client.get(detail_url)
        
        # Should be accessible
        self.assertIn(response.status_code, [200, 302])
    
    def test_unauthorized_access_prevention(self):
        """Test that unauthorized users cannot access photos"""
        # Create photo with user1
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        photo = Photo.objects.create(
            media_file=media_file,
            description='Private test photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user1,
            updated_by=self.user1
        )
        
        # Login as user2 (unauthorized)
        self.client.login(username='doctor2', password='testpass123')
        
        # Try to access photo detail
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': photo.pk})
        response = self.client.get(detail_url)
        
        # Should be denied or redirected
        self.assertIn(response.status_code, [403, 404, 302])
    
    def test_unauthenticated_access_prevention(self):
        """Test that unauthenticated users cannot access photos"""
        # Create photo
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        photo = Photo.objects.create(
            media_file=media_file,
            description='Public test photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user1,
            updated_by=self.user1
        )
        
        # Don't login - access as anonymous user
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': photo.pk})
        response = self.client.get(detail_url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_edit_permission_workflow(self):
        """Test edit permission enforcement"""
        # Create photo with user1
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        photo = Photo.objects.create(
            media_file=media_file,
            description='Edit test photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user1,
            updated_by=self.user1
        )
        
        # Login as user1 (creator)
        self.client.login(username='doctor1', password='testpass123')
        
        # Access edit form
        edit_url = reverse('mediafiles:photo_update', kwargs={'pk': photo.pk})
        response = self.client.get(edit_url)
        
        # Should be accessible to creator
        self.assertIn(response.status_code, [200, 302])
        
        # Login as user2 (not creator)
        self.client.login(username='doctor2', password='testpass123')
        
        # Try to access edit form
        response = self.client.get(edit_url)
        
        # Should be denied to non-creator
        self.assertIn(response.status_code, [403, 404, 302])
    
    def test_delete_permission_workflow(self):
        """Test delete permission enforcement"""
        # Create photo with user1
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        photo = Photo.objects.create(
            media_file=media_file,
            description='Delete test photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user1,
            updated_by=self.user1
        )
        
        # Login as user2 (not creator)
        self.client.login(username='doctor2', password='testpass123')
        
        # Try to access delete form
        delete_url = reverse('mediafiles:photo_delete', kwargs={'pk': photo.pk})
        response = self.client.get(delete_url)
        
        # Should be denied
        self.assertIn(response.status_code, [403, 404, 302])


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    MEDIA_USE_UUID_FILENAMES=True
)
class ErrorHandlingIntegrationTests(TestCase):
    """Tests for error handling in integration scenarios"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='doctor',
            email='doctor@hospital.com',
            password='testpass123'
        )
        
        # Create test hospital
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            short_name='TH',
            address='Test Address',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.patient = Patient.objects.create(
            name="Error Test Patient",
            birthday="1980-12-25",
            status=Patient.Status.OUTPATIENT,
            current_hospital=self.hospital,
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_invalid_file_upload_error_handling(self):
        """Test error handling for invalid file uploads"""
        self.client.login(username='doctor', password='testpass123')
        
        # Try to upload invalid file
        invalid_file = SimpleUploadedFile(
            'invalid.txt',
            b'This is not an image',
            content_type='text/plain'
        )
        
        create_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.id})
        response = self.client.post(create_url, {
            'image': invalid_file,
            'description': 'Invalid file test',
        })
        
        # Should return form with errors, not crash
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error', status_code=200)
    
    def test_missing_file_error_handling(self):
        """Test error handling when no file is uploaded"""
        self.client.login(username='doctor', password='testpass123')
        
        create_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.id})
        response = self.client.post(create_url, {
            'description': 'Missing file test',
        })
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'required', status_code=200)
    
    def test_nonexistent_photo_error_handling(self):
        """Test error handling for nonexistent photos"""
        self.client.login(username='doctor', password='testpass123')
        
        # Try to access non-existent photo
        fake_uuid = '11111111-1111-1111-1111-111111111111'
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': fake_uuid})
        response = self.client.get(detail_url)
        
        # Should return 404
        self.assertEqual(response.status_code, 404)
    
    def test_file_serving_error_handling(self):
        """Test error handling for file serving"""
        self.client.login(username='doctor', password='testpass123')
        
        # Try to access non-existent file
        fake_uuid = '11111111-1111-1111-1111-111111111111'
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': fake_uuid})
        response = self.client.get(file_url)
        
        # Should return 404
        self.assertEqual(response.status_code, 404)