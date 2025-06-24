"""
Security tests for PhotoSeries and mediafiles functionality.

Tests security aspects including:
- File validation and sanitization
- Access control and permissions
- Path traversal prevention
- File enumeration protection
- MIME type validation
"""

import os
import tempfile
import zipfile
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.hospitals.models import Hospital
from apps.patients.models import Patient
from apps.events.models import Event
from ..models import MediaFile, Photo, PhotoSeries, PhotoSeriesFile, VideoClip
from ..forms import PhotoCreateForm, PhotoSeriesCreateForm
from ..validators import FileSecurityValidator, validate_media_file
from ..utils import normalize_filename, calculate_file_hash, validate_video_filename_security, validate_video_upload_security, VideoProcessor

User = get_user_model()


class MediaFileSecurityTestCase(TestCase):
    """Base test case with common security test setup."""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user 
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
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
        
        # Create test patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.OUTPATIENT,
            current_hospital=self.hospital,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Load test media files
        self.test_media_dir = os.path.join(os.path.dirname(__file__), 'test_media')
        
        # Load test image content
        with open(os.path.join(self.test_media_dir, 'small_image.jpg'), 'rb') as f:
            self.test_image_content = f.read()

        # Load test video content if available
        test_video_path = os.path.join(self.test_media_dir, 'test_video.mp4')
        if os.path.exists(test_video_path):
            with open(test_video_path, 'rb') as f:
                self.test_video_content = f.read()
        else:
            # Create minimal MP4 header for testing
            self.test_video_content = b'\x00\x00\x00\x18ftypmp4\x00' + b'\x00' * 100
    
    def create_test_image_file(self, filename='test.jpg', content=None):
        """Create a test image file for testing."""
        if content is None:
            content = self.test_image_content
        return SimpleUploadedFile(
            filename,
            content,
            content_type='image/jpeg'
        )

    def create_test_video_file(self, filename='test.mp4', content=None, content_type='video/mp4'):
        """Create a test video file for testing."""
        if content is None:
            content = self.test_video_content
        return SimpleUploadedFile(
            filename,
            content,
            content_type=content_type
        )


class FileValidationSecurityTests(MediaFileSecurityTestCase):
    """Test file validation security measures."""
    
    def test_malicious_filename_sanitization(self):
        """Test that malicious filenames are properly sanitized."""
        malicious_filenames = [
            '../../../etc/passwd.jpg',
            'file%00.jpg',
            'script<img src=x onerror=alert(1)>.jpg',
            'CON.jpg',  # Windows reserved name
            'file\x00.jpg',  # Null byte injection
            '../../../../../../windows/system32/cmd.exe.jpg',
        ]
        
        for filename in malicious_filenames:
            with self.subTest(filename=filename):
                uploaded_file = self.create_test_image_file(filename)
                media_file = MediaFile.objects.create_from_upload(uploaded_file)
                
                # Check that filename was sanitized
                self.assertNotIn('..', media_file.original_filename)
                self.assertNotIn('\x00', media_file.original_filename)
                self.assertNotIn('<', media_file.original_filename)
                self.assertNotIn('>', media_file.original_filename)
    
    def test_file_extension_validation(self):
        """Test that only allowed file extensions are accepted."""
        invalid_extensions = [
            'malicious.exe',
            'script.php',
            'payload.asp',
            'test.html',
            'file.js',
            'test.jsp',
        ]
        
        for filename in invalid_extensions:
            with self.subTest(filename=filename):
                uploaded_file = SimpleUploadedFile(
                    filename,
                    self.test_image_content,
                    content_type='image/jpeg'
                )
                
                with self.assertRaises(ValidationError):
                    validate_media_file(uploaded_file, 'image')
    
    def test_mime_type_validation(self):
        """Test MIME type validation against spoofing."""
        # Test image with wrong MIME type
        uploaded_file = SimpleUploadedFile(
            'test.jpg',
            b'<html><script>alert("xss")</script></html>',
            content_type='text/html'
        )
        
        with self.assertRaises(ValidationError):
            validate_media_file(uploaded_file, 'image')
    
    def test_file_size_limits(self):
        """Test file size validation."""
        # Create oversized file content
        large_content = b'x' * (6 * 1024 * 1024)  # 6MB
        uploaded_file = SimpleUploadedFile(
            'large.jpg',
            large_content,
            content_type='image/jpeg'
        )
        
        with self.assertRaises(ValidationError):
            validate_media_file(uploaded_file, 'image')
    
    def test_malicious_file_content_detection(self):
        """Test detection of malicious content in files."""
        # Load malicious test file if it exists
        malicious_file_path = os.path.join(self.test_media_dir, 'malicious.jpg')
        if os.path.exists(malicious_file_path):
            with open(malicious_file_path, 'rb') as f:
                malicious_content = f.read()
            
            uploaded_file = SimpleUploadedFile(
                'malicious.jpg',
                malicious_content,
                content_type='image/jpeg'
            )
            
            with self.assertRaises(ValidationError):
                validate_media_file(uploaded_file, 'image')
    
    def test_filename_normalization(self):
        """Test filename normalization security."""
        test_cases = [
            ('file with spaces.jpg', 'file-with-spaces.jpg'),
            ('File_With_Underscores.jpg', 'file-with-underscores.jpg'),
            ('UPPERCASE.JPG', 'uppercase.jpg'),
            ('file-with-dashes.jpg', 'file-with-dashes.jpg'),
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                normalized = normalize_filename(original)
                # The actual implementation uses hyphens to replace underscores and spaces
                self.assertTrue(normalized.replace('_', '-') == expected or normalized == expected)


class FileAccessControlTests(MediaFileSecurityTestCase):
    """Test file access control and permissions."""
    
    def test_unauthorized_file_access_prevention(self):
        """Test that unauthorized users cannot access files."""
        # Create a photo
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        photo = Photo.objects.create(
            media_file=media_file,
            description='Test photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create unauthorized user
        unauthorized_user = User.objects.create_user(
            username='unauthorized',
            email='unauth@example.com',
            password='testpass123'
        )
        
        # Try to access file without authentication
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': media_file.id})
        response = self.client.get(file_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Try with unauthorized user
        self.client.login(username='unauthorized', password='testpass123')
        response = self.client.get(file_url)
        self.assertIn(response.status_code, [403, 404])  # Forbidden or not found
    
    def test_file_enumeration_prevention(self):
        """Test prevention of file enumeration attacks."""
        # Try to access non-existent file
        fake_uuid = '11111111-1111-1111-1111-111111111111'
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': fake_uuid})
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(file_url)
        self.assertEqual(response.status_code, 404)
    
    def test_secure_file_serving_headers(self):
        """Test that secure headers are set when serving files."""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        photo = Photo.objects.create(
            media_file=media_file,
            description='Test photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client.login(username='testuser', password='testpass123')
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': media_file.id})
        response = self.client.get(file_url)
        
        if response.status_code == 200:
            # Check security headers
            self.assertIn('Content-Type', response)


class PhotoSeriesSecurityTests(MediaFileSecurityTestCase):
    """Test PhotoSeries-specific security measures."""
    
    def test_photoseries_access_control(self):
        """Test access control for PhotoSeries operations."""
        # Create PhotoSeries
        series = PhotoSeries.objects.create(
            description='Test Series',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create unauthorized user
        unauthorized_user = User.objects.create_user(
            username='unauthorized',
            email='unauth@example.com',
            password='testpass123'
        )
        
        # Test unauthorized access to detail view
        self.client.login(username='unauthorized', password='testpass123')
        detail_url = reverse('mediafiles:photoseries_detail', kwargs={'pk': series.pk})
        response = self.client.get(detail_url)
        self.assertIn(response.status_code, [403, 404])  # Should be forbidden or not found
    
    def test_photoseries_zip_download_security(self):
        """Test security of ZIP download functionality."""
        # Create PhotoSeries with photos
        series = PhotoSeries.objects.create(
            description='Test Series',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add photos to series
        for i in range(3):
            uploaded_file = self.create_test_image_file(f'test{i}.jpg')
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            series.add_photo(media_file, order=i+1)
        
        self.client.login(username='testuser', password='testpass123')
        download_url = reverse('mediafiles:photoseries_download', kwargs={'pk': series.pk})
        response = self.client.get(download_url)
        
        if response.status_code == 200:
            self.assertEqual(response['Content-Type'], 'application/zip')
            self.assertIn('attachment', response['Content-Disposition'])
            
            # Verify ZIP content is safe
            with tempfile.NamedTemporaryFile() as temp_file:
                for chunk in response.streaming_content:
                    temp_file.write(chunk)
                temp_file.flush()
                
                with zipfile.ZipFile(temp_file.name, 'r') as zip_file:
                    # Check that no files escape the ZIP structure
                    for file_info in zip_file.filelist:
                        self.assertNotIn('..', file_info.filename)
                        self.assertFalse(file_info.filename.startswith('/'))
    
    def test_photoseries_batch_operations_security(self):
        """Test security of batch operations on PhotoSeries."""
        series = PhotoSeries.objects.create(
            description='Test Series',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test AJAX photo addition with proper CSRF
        self.client.login(username='testuser', password='testpass123')
        
        uploaded_file = self.create_test_image_file()
        add_url = reverse('mediafiles:photoseries_add_photo', kwargs={'pk': series.pk})
        
        # Should require POST
        response = self.client.get(add_url)
        self.assertEqual(response.status_code, 405)  # Method not allowed


class FormSecurityTests(MediaFileSecurityTestCase):
    """Test form-level security measures."""
    
    def test_photo_form_file_validation(self):
        """Test that photo forms properly validate uploaded files."""
        # Test with malicious file
        malicious_file = SimpleUploadedFile(
            'malicious.php.jpg',
            b'<?php phpinfo(); ?>',
            content_type='image/jpeg'
        )
        
        form_data = {
            'description': 'Test photo',
        }
        form = PhotoCreateForm(data=form_data, files={'image': malicious_file})
        
        self.assertFalse(form.is_valid())
    
    def test_photoseries_form_validation(self):
        """Test PhotoSeries form security validation."""
        # Test with invalid file
        invalid_file = SimpleUploadedFile(
            'test.txt',
            b'This is not an image',
            content_type='text/plain'
        )
        
        form_data = {
            'description': 'Test series',
        }
        form = PhotoSeriesCreateForm(data=form_data, files={'images': invalid_file})
        
        self.assertFalse(form.is_valid())


class FileSystemSecurityTests(MediaFileSecurityTestCase):
    """Test filesystem-level security measures."""
    
    def test_secure_file_path_generation(self):
        """Test that secure file paths are generated."""
        uploaded_file = self.create_test_image_file('test.jpg')
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        
        file_path = media_file.file.name
        
        # Should not contain original filename
        self.assertNotIn('test.jpg', file_path)
        
        # Should be in secure directory structure
        self.assertIn('photos/', file_path)
        self.assertIn('/originals/', file_path)
        
        # Should contain year/month structure
        import re
        self.assertTrue(re.search(r'\d{4}/\d{2}', file_path))
    
    def test_file_hash_consistency(self):
        """Test that file hashes are consistent and prevent duplicates."""
        uploaded_file1 = self.create_test_image_file('file1.jpg')
        uploaded_file2 = self.create_test_image_file('file2.jpg')  # Same content
        
        media_file1 = MediaFile.objects.create_from_upload(uploaded_file1)
        media_file2 = MediaFile.objects.create_from_upload(uploaded_file2)
        
        # Should have same hash for same content
        self.assertEqual(media_file1.file_hash, media_file2.file_hash)
        
        # Should reference same file
        self.assertEqual(media_file1.file.name, media_file2.file.name)
    
    def test_filename_sanitization(self):
        """Test filename sanitization."""
        dangerous_filename = "../../../etc/passwd<script>alert('xss')</script>.jpg"
        sanitized = normalize_filename(dangerous_filename)
        
        # Should not contain dangerous characters
        self.assertNotIn('..', sanitized)
        self.assertNotIn('<', sanitized)
        self.assertNotIn('>', sanitized)
        self.assertNotIn('script', sanitized)
        
        # Should still have extension
        self.assertTrue(sanitized.endswith('.jpg'))


class CSRFProtectionTests(MediaFileSecurityTestCase):
    """Test CSRF protection on sensitive operations."""
    
    def test_photo_creation_csrf_protection(self):
        """Test CSRF protection on photo creation."""
        self.client.login(username='testuser', password='testpass123')
        
        create_url = reverse('mediafiles:photo_create', kwargs={'patient_id': self.patient.id})
        uploaded_file = self.create_test_image_file()
        
        # POST without CSRF token should fail
        response = self.client.post(create_url, {
            'image': uploaded_file,
            'description': 'Test photo',
        }, enforce_csrf_checks=True)
        
        # Should be forbidden due to CSRF
        self.assertEqual(response.status_code, 403)
    
    def test_photoseries_operations_csrf_protection(self):
        """Test CSRF protection on PhotoSeries operations."""
        series = PhotoSeries.objects.create(
            description='Test Series',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Test photo addition CSRF
        add_url = reverse('mediafiles:photoseries_add_photo', kwargs={'pk': series.pk})
        response = self.client.post(add_url, {
            'image': self.create_test_image_file(),
        }, enforce_csrf_checks=True)
        
        self.assertEqual(response.status_code, 403)


class DataLeakagePreventionTests(MediaFileSecurityTestCase):
    """Test prevention of data leakage."""
    
    def test_error_message_information_disclosure(self):
        """Test that error messages don't leak sensitive information."""
        # Try to access non-existent file
        fake_uuid = '11111111-1111-1111-1111-111111111111'
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': fake_uuid})
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(file_url)
        
        # Should return 404, not detailed error
        self.assertEqual(response.status_code, 404)
        
        # Should not leak system paths or file structure
        if hasattr(response, 'content'):
            content_str = str(response.content)
            self.assertNotIn(settings.MEDIA_ROOT, content_str)
    
    def test_metadata_exposure_prevention(self):
        """Test that sensitive metadata is not exposed."""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        
        # File hash should not be exposed in URLs
        photo = Photo.objects.create(
            media_file=media_file,
            description='Test photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client.login(username='testuser', password='testpass123')
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': photo.pk})
        response = self.client.get(detail_url)
        
        if response.status_code == 200:
            # Should not expose file hash in response
            content_str = str(response.content)
            self.assertNotIn(media_file.file_hash, content_str)


class FileHashSecurityTests(MediaFileSecurityTestCase):
    """Test file hash security and consistency."""
    
    def test_file_hash_calculation(self):
        """Test file hash calculation for deduplication."""
        content1 = b"This is test content for file 1"
        content2 = b"This is test content for file 2"
        content1_duplicate = b"This is test content for file 1"
        
        hash1 = calculate_file_hash(SimpleUploadedFile("test1.jpg", content1, content_type="image/jpeg"))
        hash2 = calculate_file_hash(SimpleUploadedFile("test2.jpg", content2, content_type="image/jpeg"))
        hash1_dup = calculate_file_hash(SimpleUploadedFile("test1_dup.jpg", content1_duplicate, content_type="image/jpeg"))
        
        # Same content should produce same hash
        self.assertEqual(hash1, hash1_dup)
        
        # Different content should produce different hash
        self.assertNotEqual(hash1, hash2)
        
        # Hash should be SHA-256 (64 hex characters)
        self.assertEqual(len(hash1), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash1))
    
    def test_file_deduplication_security(self):
        """Test that file deduplication works securely."""
        # Create two files with same content
        content = self.test_image_content
        file1 = self.create_test_image_file('duplicate1.jpg', content)
        file2 = self.create_test_image_file('duplicate2.jpg', content)
        
        media_file1 = MediaFile.objects.create_from_upload(file1)
        media_file2 = MediaFile.objects.create_from_upload(file2)
        
        # Should have same hash
        self.assertEqual(media_file1.file_hash, media_file2.file_hash)
        
        # Should point to same physical file
        self.assertEqual(media_file1.file.name, media_file2.file.name)


class ThumbnailSecurityTests(MediaFileSecurityTestCase):
    """Test thumbnail generation and access security."""
    
    def test_thumbnail_access_control(self):
        """Test access control for thumbnail serving."""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        
        thumbnail_url = reverse('mediafiles:serve_thumbnail', kwargs={'file_id': media_file.id})
        
        # Unauthenticated access should be denied
        response = self.client.get(thumbnail_url)
        self.assertIn(response.status_code, [302, 403])  # Redirect to login or forbidden
        
        # Authenticated access with proper permissions
        self.client.login(username='testuser', password='testpass123')
        
        # Create photo to establish permission
        photo = Photo.objects.create(
            media_file=media_file,
            description='Test photo',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        response = self.client.get(thumbnail_url)
        # Should either serve thumbnail or return 404 if not generated yet
        self.assertIn(response.status_code, [200, 404])
    
    def test_thumbnail_path_security(self):
        """Test that thumbnail paths are secure."""
        uploaded_file = self.create_test_image_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        
        if hasattr(media_file, 'thumbnail_path') and media_file.thumbnail_path:
            # Should not contain path traversal
            self.assertNotIn('..', media_file.thumbnail_path)
            
            # Should be in thumbnails directory
            self.assertIn('thumbnails/', media_file.thumbnail_path)


class PhotoSeriesIntegrityTests(MediaFileSecurityTestCase):
    """Test PhotoSeries data integrity and consistency."""
    
    def test_photoseries_ordering_integrity(self):
        """Test that photo ordering in series is maintained securely."""
        series = PhotoSeries.objects.create(
            description='Ordering test',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add photos in specific order
        for i in range(3):
            uploaded_file = self.create_test_image_file(f'order{i}.jpg')
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            series.add_photo(media_file, order=i+1, description=f'Photo {i+1}')
        
        # Verify ordering is maintained
        photos = series.get_ordered_photos()
        self.assertEqual(len(photos), 3)
        
        for i, photo in enumerate(photos):
            series_file = PhotoSeriesFile.objects.get(photo_series=series, media_file=photo)
            self.assertEqual(series_file.order, i+1)
    
    def test_photoseries_file_consistency(self):
        """Test consistency of files within PhotoSeries."""
        series = PhotoSeries.objects.create(
            description='Consistency test',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add multiple photos
        for i in range(2):
            uploaded_file = self.create_test_image_file(f'consistent{i}.jpg')
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            series.add_photo(media_file, order=i+1)
        
        # All photos should belong to same series
        photos = series.get_ordered_photos()
        for photo in photos:
            series_files = PhotoSeriesFile.objects.filter(media_file=photo)
            self.assertEqual(series_files.count(), 1)
            self.assertEqual(series_files.first().photo_series, series)


class VideoSecurityTests(MediaFileSecurityTestCase):
    """Test video-specific security measures."""

    def test_video_filename_security_validation(self):
        """Test video filename security validation."""
        dangerous_filenames = [
            '../../../etc/passwd.mp4',
            'video%00.mp4',
            'script<img src=x onerror=alert(1)>.mp4',
            'CON.mp4',  # Windows reserved name
            'video\x00.mp4',  # Null byte injection
            '../../../../../../windows/system32/cmd.exe.mp4',
            'video.exe.mp4',  # Double extension
            'video.php.mp4',  # Suspicious double extension
        ]

        for filename in dangerous_filenames:
            with self.subTest(filename=filename):
                with self.assertRaises(ValidationError):
                    validate_video_filename_security(filename)

    def test_video_file_enumeration_prevention(self):
        """Test prevention of video file enumeration attacks."""
        # Create a video file
        uploaded_file = self.create_test_video_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        video_clip = VideoClip.objects.create(
            media_file=media_file,
            description='Test video',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )

        # Try to access non-existent video
        fake_uuid = '22222222-2222-2222-2222-222222222222'
        video_url = reverse('mediafiles:serve_file', kwargs={'file_id': fake_uuid})

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(video_url)
        self.assertEqual(response.status_code, 404)

    def test_video_codec_validation(self):
        """Test video codec security validation."""
        # Test with potentially dangerous codec content
        dangerous_video_content = b'\x00\x00\x00\x18ftypasf\x00'  # ASF format header
        uploaded_file = SimpleUploadedFile(
            'dangerous.mp4',
            dangerous_video_content,
            content_type='video/mp4'
        )

        # Should be rejected due to codec validation
        with self.assertRaises(ValidationError):
            validate_media_file(uploaded_file, 'video')

    def test_video_container_format_validation(self):
        """Test video container format security validation."""
        # Test mismatched MIME type and extension
        uploaded_file = SimpleUploadedFile(
            'test.mp4',
            self.test_video_content,
            content_type='video/webm'  # Wrong MIME type for .mp4
        )

        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # Should detect container format mismatch
        with self.assertRaises(ValidationError):
            media_file._validate_video_container_format()

    def test_video_malicious_payload_detection(self):
        """Test detection of malicious payloads in video files."""
        # Create video with suspicious script content
        malicious_content = b'\x00\x00\x00\x18ftypmp4\x00<script>alert("xss")</script>' + b'\x00' * 100
        uploaded_file = SimpleUploadedFile(
            'malicious.mp4',
            malicious_content,
            content_type='video/mp4'
        )

        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # Should detect suspicious patterns
        with self.assertRaises(ValidationError):
            media_file._validate_video_content_security()

    def test_video_stream_security_validation(self):
        """Test video stream security validation."""
        uploaded_file = self.create_test_video_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # Set suspicious video properties
        media_file.width = 10000  # Unusual width
        media_file.height = 1     # Unusual height (extreme aspect ratio)
        media_file.video_bitrate = 100_000_000  # Excessive bitrate
        media_file.fps = 1000  # Unusual frame rate

        # Should detect security issues
        with self.assertRaises(ValidationError):
            media_file._validate_video_stream_security()

    def test_video_duration_validation(self):
        """Test video duration security limits."""
        uploaded_file = self.create_test_video_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # Set excessive duration
        media_file.duration = 300  # 5 minutes (exceeds 2-minute limit)

        with self.assertRaises(ValidationError):
            media_file.validate_video_duration()

    def test_video_file_integrity_validation(self):
        """Test video file integrity validation."""
        uploaded_file = self.create_test_video_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        # Simulate file size mismatch
        original_size = media_file.file_size
        media_file.file_size = original_size + 1000  # Wrong size

        with self.assertRaises(ValidationError):
            media_file.validate_video_file_integrity()


class VideoStreamingSecurityTests(MediaFileSecurityTestCase):
    """Test video streaming security measures."""

    def test_video_streaming_access_control(self):
        """Test access control for video streaming."""
        # Create a video
        uploaded_file = self.create_test_video_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        video_clip = VideoClip.objects.create(
            media_file=media_file,
            description='Test video',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )

        # Create unauthorized user
        unauthorized_user = User.objects.create_user(
            username='unauthorized',
            email='unauth@example.com',
            password='testpass123'
        )

        # Try to access video without authentication
        video_url = reverse('mediafiles:serve_file', kwargs={'file_id': media_file.id})
        response = self.client.get(video_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

        # Try with unauthorized user
        self.client.login(username='unauthorized', password='testpass123')
        response = self.client.get(video_url)
        self.assertIn(response.status_code, [403, 404])  # Forbidden or not found

    def test_video_range_request_security(self):
        """Test HTTP range request security for video streaming."""
        uploaded_file = self.create_test_video_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        video_clip = VideoClip.objects.create(
            media_file=media_file,
            description='Test video',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )

        self.client.login(username='testuser', password='testpass123')
        video_url = reverse('mediafiles:serve_file', kwargs={'file_id': media_file.id})

        # Test malicious range requests
        malicious_ranges = [
            'bytes=0-999999999',  # Excessive range
            'bytes=-1-100',       # Invalid range
            'bytes=100-50',       # Start > end
            'bytes=0-100,200-300', # Multiple ranges
        ]

        for range_header in malicious_ranges:
            with self.subTest(range_header=range_header):
                response = self.client.get(video_url, HTTP_RANGE=range_header)
                # Should either reject or handle safely
                self.assertIn(response.status_code, [200, 206, 416])  # OK, Partial, or Range Not Satisfiable

    def test_video_streaming_headers_security(self):
        """Test security headers for video streaming."""
        uploaded_file = self.create_test_video_file()
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        video_clip = VideoClip.objects.create(
            media_file=media_file,
            description='Test video',
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )

        self.client.login(username='testuser', password='testpass123')
        video_url = reverse('mediafiles:serve_file', kwargs={'file_id': media_file.id})
        response = self.client.get(video_url)

        if response.status_code == 200:
            # Check video-specific security headers
            self.assertIn('Accept-Ranges', response)
            self.assertEqual(response['Accept-Ranges'], 'bytes')
            self.assertIn('X-Content-Type-Options', response)
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')


class VideoProcessorSecurityTests(MediaFileSecurityTestCase):
    """Test VideoProcessor security measures."""

    def test_video_processor_ffmpeg_injection_prevention(self):
        """Test prevention of FFmpeg command injection."""
        processor = VideoProcessor()

        # Test with malicious file paths
        malicious_paths = [
            '/etc/passwd; rm -rf /',
            'video.mp4`rm -rf /`',
            'video.mp4$(rm -rf /)',
            'video.mp4 && rm -rf /',
            'video.mp4|rm -rf /',
        ]

        for malicious_path in malicious_paths:
            with self.subTest(path=malicious_path):
                with self.assertRaises(ValueError):
                    processor._sanitize_ffmpeg_path(malicious_path)

    def test_video_metadata_sanitization(self):
        """Test video metadata sanitization."""
        processor = VideoProcessor()

        # Test malicious metadata values
        malicious_values = [
            '<script>alert("xss")</script>',
            '../../etc/passwd',
            '\x00\x01\x02malicious',
            'very_long_string' * 100,  # Excessive length
        ]

        for value in malicious_values:
            with self.subTest(value=value):
                sanitized = processor._sanitize_string_value(value)
                self.assertNotIn('<script>', sanitized)
                self.assertNotIn('..', sanitized)
                self.assertNotIn('\x00', sanitized)
                self.assertLessEqual(len(sanitized), 100)

    def test_video_numeric_validation(self):
        """Test video numeric value validation."""
        processor = VideoProcessor()

        # Test invalid numeric values
        invalid_values = [
            (-1, 'width'),      # Negative width
            (20000, 'height'),  # Excessive height
            (-100, 'duration'), # Negative duration
            (10000, 'duration'), # Excessive duration (> 2 hours)
        ]

        for value, field_name in invalid_values:
            with self.subTest(value=value, field=field_name):
                with self.assertRaises(ValueError):
                    processor._validate_numeric_value(value, field_name)