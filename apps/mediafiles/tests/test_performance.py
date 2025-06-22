# MediaFiles Performance Tests
# Performance tests for photo handling and file operations

import os
import time
import tempfile
from django.test import TestCase, TransactionTestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.test.utils import override_settings
from django.db import connection
from django.test import Client

from apps.mediafiles.models import MediaFile, Photo
from apps.mediafiles.forms import PhotoCreateForm
from apps.patients.models import Patient

User = get_user_model()


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    MEDIA_USE_UUID_FILENAMES=True,
    MEDIA_ENABLE_FILE_DEDUPLICATION=True
)
class LargeImageUploadPerformanceTests(TransactionTestCase):
    """Tests for large image upload performance"""
    
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
        
        # Create a large test image (simulated JPEG header + large content)
        self.large_image_content = self._create_large_image_content(4 * 1024 * 1024)  # 4MB
    
    def _create_large_image_content(self, size):
        """Create large image content for testing"""
        # JPEG header
        jpeg_header = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01'
            b'\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff'
            b'\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00'
        )
        
        # Fill with random-like data and JPEG end marker
        padding_size = size - len(jpeg_header) - 2
        padding = bytes([(i % 256) for i in range(padding_size)])
        jpeg_end = b'\xff\xd9'
        
        return jpeg_header + padding + jpeg_end
    
    def test_large_image_upload_time(self):
        """Test upload time for large images"""
        uploaded_file = SimpleUploadedFile(
            "large_image.jpg",
            self.large_image_content,
            content_type="image/jpeg"
        )
        
        start_time = time.time()
        
        # Test MediaFile creation
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        
        upload_time = time.time() - start_time
        
        # Upload should complete within 2 seconds for 4MB file
        self.assertLess(upload_time, 2.0, f"Upload took {upload_time:.2f}s, should be < 2s")
        
        # Verify file was created successfully
        self.assertIsNotNone(media_file)
        self.assertEqual(media_file.file_size, len(self.large_image_content))
        self.assertTrue(os.path.exists(media_file.file.path))
    
    def test_large_image_form_processing_time(self):
        """Test form processing time for large images"""
        uploaded_file = SimpleUploadedFile(
            "large_form_image.jpg",
            self.large_image_content,
            content_type="image/jpeg"
        )
        
        form_data = {
            'description': 'Large image test',
            'event_datetime': timezone.now(),
            'caption': 'Performance test image'
        }
        
        start_time = time.time()
        
        form = PhotoCreateForm(
            data=form_data,
            files={'image': uploaded_file},
            patient=self.patient,
            user=self.user
        )
        
        is_valid = form.is_valid()
        if is_valid:
            photo = form.save()
        
        processing_time = time.time() - start_time
        
        # Form processing should complete within 3 seconds
        self.assertLess(processing_time, 3.0, f"Form processing took {processing_time:.2f}s, should be < 3s")
        self.assertTrue(is_valid)
        if is_valid:
            self.assertIsNotNone(photo)
    
    def test_multiple_large_uploads_performance(self):
        """Test performance with multiple large uploads"""
        num_uploads = 3
        upload_times = []
        
        for i in range(num_uploads):
            uploaded_file = SimpleUploadedFile(
                f"large_image_{i}.jpg",
                self.large_image_content,
                content_type="image/jpeg"
            )
            
            start_time = time.time()
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            upload_time = time.time() - start_time
            
            upload_times.append(upload_time)
            
            # Each upload should still be fast
            self.assertLess(upload_time, 2.5, f"Upload {i} took {upload_time:.2f}s")
        
        # Average upload time should be reasonable
        avg_time = sum(upload_times) / len(upload_times)
        self.assertLess(avg_time, 2.0, f"Average upload time {avg_time:.2f}s too high")


class ThumbnailGenerationPerformanceTests(TestCase):
    """Tests for thumbnail generation performance"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test image content
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
    
    def test_thumbnail_generation_speed(self):
        """Test thumbnail generation speed"""
        uploaded_file = SimpleUploadedFile(
            "test_image.jpg",
            self.test_image_content,
            content_type="image/jpeg"
        )
        
        start_time = time.time()
        
        # Create MediaFile (includes thumbnail generation)
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        
        generation_time = time.time() - start_time
        
        # Thumbnail generation should be fast (< 1 second)
        self.assertLess(generation_time, 1.0, f"Thumbnail generation took {generation_time:.2f}s")
        
        # Verify thumbnail was created
        if media_file.thumbnail:
            self.assertTrue(os.path.exists(media_file.thumbnail.path))
    
    def test_multiple_thumbnail_generation(self):
        """Test performance of generating multiple thumbnails"""
        num_images = 5
        generation_times = []
        
        for i in range(num_images):
            uploaded_file = SimpleUploadedFile(
                f"test_image_{i}.jpg",
                self.test_image_content,
                content_type="image/jpeg"
            )
            
            start_time = time.time()
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            generation_time = time.time() - start_time
            
            generation_times.append(generation_time)
            
            # Each generation should be fast
            self.assertLess(generation_time, 1.5, f"Thumbnail {i} took {generation_time:.2f}s")
        
        # Average generation time should be reasonable
        avg_time = sum(generation_times) / len(generation_times)
        self.assertLess(avg_time, 1.0, f"Average generation time {avg_time:.2f}s too high")


class DatabaseQueryOptimizationTests(TestCase):
    """Tests for database query optimization"""
    
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
        
        # Create multiple photos for testing
        self.photos = []
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
        
        for i in range(10):
            uploaded_file = SimpleUploadedFile(
                f"test_{i}.jpg",
                test_image_content,
                content_type="image/jpeg"
            )
            
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            photo = Photo.objects.create(
                media_file=media_file,
                description=f"Test photo {i}",
                event_datetime=timezone.now(),
                patient=self.patient,
                created_by=self.user,
                updated_by=self.user
            )
            self.photos.append(photo)
    
    def test_photo_list_query_optimization(self):
        """Test query optimization for photo lists"""
        # Reset query count
        connection.queries_log.clear()
        
        # Get photos with related objects
        photos = list(Photo.objects.select_related(
            'patient', 'created_by', 'updated_by', 'media_file'
        ).filter(patient=self.patient))
        
        query_count = len(connection.queries)
        
        # Should use minimal queries due to select_related
        self.assertLessEqual(query_count, 2, f"Used {query_count} queries, should be ≤ 2")
        self.assertEqual(len(photos), 10)
        
        # Access related objects should not trigger additional queries
        connection.queries_log.clear()
        for photo in photos:
            _ = photo.patient.name
            _ = photo.created_by.username
            _ = photo.media_file.original_filename
        
        additional_queries = len(connection.queries)
        self.assertEqual(additional_queries, 0, "Accessing related objects triggered additional queries")
    
    def test_photo_manager_optimization(self):
        """Test Photo manager query optimization"""
        connection.queries_log.clear()
        
        # Use Photo manager which should include select_related
        photos = list(Photo.objects.filter(patient=self.patient))
        
        query_count = len(connection.queries)
        
        # Manager should optimize queries
        self.assertLessEqual(query_count, 2, f"Manager used {query_count} queries")
        
        # Test accessing related objects
        connection.queries_log.clear()
        for photo in photos[:3]:  # Test first 3
            _ = photo.media_file.file_size
            _ = photo.patient.name
            _ = photo.created_by.email
        
        additional_queries = len(connection.queries)
        self.assertEqual(additional_queries, 0, "Manager optimization failed")


class FileServingPerformanceTests(TestCase):
    """Tests for file serving performance"""

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

        # Create test image
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
            description="Test photo",
            event_datetime=timezone.now(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        self.client = Client()
        self.client.force_login(self.user)

    def test_file_serving_response_time(self):
        """Test file serving response time"""
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': self.media_file.id})

        start_time = time.time()
        response = self.client.get(file_url)
        response_time = time.time() - start_time

        # File serving should be fast (< 0.5 seconds)
        self.assertLess(response_time, 0.5, f"File serving took {response_time:.2f}s")

        if response.status_code == 200:
            self.assertEqual(response['Content-Type'], 'image/jpeg')

    def test_thumbnail_serving_response_time(self):
        """Test thumbnail serving response time"""
        thumbnail_url = reverse('mediafiles:serve_thumbnail', kwargs={'file_id': self.media_file.id})

        start_time = time.time()
        response = self.client.get(thumbnail_url)
        response_time = time.time() - start_time

        # Thumbnail serving should be very fast (< 0.3 seconds)
        self.assertLess(response_time, 0.3, f"Thumbnail serving took {response_time:.2f}s")

        # Should either serve thumbnail or return 404 if not generated
        self.assertIn(response.status_code, [200, 404])

    def test_multiple_file_requests_performance(self):
        """Test performance with multiple concurrent-like requests"""
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': self.media_file.id})

        response_times = []
        num_requests = 10

        for i in range(num_requests):
            start_time = time.time()
            response = self.client.get(file_url)
            response_time = time.time() - start_time

            response_times.append(response_time)

            # Each request should be fast
            self.assertLess(response_time, 1.0, f"Request {i} took {response_time:.2f}s")

            # Verify response is valid
            self.assertIn(response.status_code, [200, 403, 404])

        # Average response time should be good
        avg_time = sum(response_times) / len(response_times)
        self.assertLess(avg_time, 0.5, f"Average response time {avg_time:.2f}s too high")

    def test_photo_detail_view_performance(self):
        """Test photo detail view performance"""
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': self.photo.pk})

        start_time = time.time()
        response = self.client.get(detail_url)
        response_time = time.time() - start_time

        # Detail view should load quickly (< 1 second)
        self.assertLess(response_time, 1.0, f"Detail view took {response_time:.2f}s")
        self.assertEqual(response.status_code, 200)


class MemoryUsageTests(TestCase):
    """Tests for memory usage during file operations"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_large_file_memory_usage(self):
        """Test memory usage with large files"""
        # Create a moderately large file (2MB)
        large_content = b"x" * (2 * 1024 * 1024)

        # Add JPEG headers to make it a valid image
        jpeg_header = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
        )
        jpeg_end = b'\xff\xd9'

        large_image = jpeg_header + large_content + jpeg_end

        uploaded_file = SimpleUploadedFile(
            "large_test.jpg",
            large_image,
            content_type="image/jpeg"
        )

        # This should not cause memory issues
        try:
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            self.assertIsNotNone(media_file)
            self.assertGreater(media_file.file_size, 2 * 1024 * 1024)
        except MemoryError:
            self.fail("Large file upload caused memory error")

    def test_multiple_files_memory_efficiency(self):
        """Test memory efficiency with multiple files"""
        test_content = (
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

        # Create multiple files to test memory efficiency
        media_files = []
        num_files = 20

        try:
            for i in range(num_files):
                uploaded_file = SimpleUploadedFile(
                    f"test_{i}.jpg",
                    test_content,
                    content_type="image/jpeg"
                )

                media_file = MediaFile.objects.create_from_upload(uploaded_file)
                media_files.append(media_file)

            # Should successfully create all files
            self.assertEqual(len(media_files), num_files)

        except MemoryError:
            self.fail("Multiple file creation caused memory error")


class ConcurrencyPerformanceTests(TransactionTestCase):
    """Tests for performance under concurrent operations"""

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

    def test_concurrent_upload_simulation(self):
        """Test simulated concurrent uploads"""
        # Simulate concurrent uploads by rapid sequential uploads
        upload_times = []
        num_uploads = 5

        start_total = time.time()

        for i in range(num_uploads):
            uploaded_file = SimpleUploadedFile(
                f"concurrent_{i}.jpg",
                self.test_image_content,
                content_type="image/jpeg"
            )

            start_time = time.time()
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            upload_time = time.time() - start_time

            upload_times.append(upload_time)

            # Each upload should still be reasonably fast
            self.assertLess(upload_time, 2.0, f"Concurrent upload {i} took {upload_time:.2f}s")

            # Verify file was created
            self.assertIsNotNone(media_file)

        total_time = time.time() - start_total

        # Total time should be reasonable
        self.assertLess(total_time, 10.0, f"Total concurrent uploads took {total_time:.2f}s")

        # Verify all files were created
        self.assertEqual(MediaFile.objects.count(), num_uploads)
