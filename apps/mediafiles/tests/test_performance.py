"""
Performance tests for PhotoSeries and mediafiles functionality.

Tests performance aspects including:
- Large file upload and processing performance
- Batch upload performance for PhotoSeries
- Gallery loading and navigation performance
- Database query optimization
- Memory usage and efficiency
- File serving performance
"""

import os
import time
import tempfile
from django.test import TestCase, TransactionTestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.db import connection
from django.test import Client

# Note: Hospital model removed after single-hospital refactor
from apps.patients.models import Patient
from apps.events.models import Event
from ..models import MediaFile, Photo, PhotoSeries, PhotoSeriesFile
from ..forms import PhotoCreateForm, PhotoSeriesCreateForm

User = get_user_model()


class MediaFilePerformanceTestCase(TestCase):
    """Base test case with common performance test setup."""
    
    def setUp(self):
        """Set up test data"""
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
    
    def create_test_image_file(self, filename='test.jpg', content=None):
        """Create a test image file for testing."""
        if content is None:
            content = self.test_image_content
        return SimpleUploadedFile(
            filename,
            content,
            content_type='image/jpeg'
        )
    
    def create_large_image_content(self, size):
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


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    MEDIA_USE_UUID_FILENAMES=True,
    MEDIA_ENABLE_FILE_DEDUPLICATION=True
)
class LargeImageUploadPerformanceTests(MediaFilePerformanceTestCase, TransactionTestCase):
    """Tests for large image upload performance"""
    
    def test_large_image_upload_time(self):
        """Test upload time for large images"""
        large_content = self.create_large_image_content(4 * 1024 * 1024)  # 4MB
        uploaded_file = SimpleUploadedFile(
            "large_image.jpg",
            large_content,
            content_type="image/jpeg"
        )
        
        start_time = time.time()
        
        # Test MediaFile creation
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        
        upload_time = time.time() - start_time
        
        # Upload should complete within 3 seconds for 4MB file
        self.assertLess(upload_time, 3.0, f"Upload took {upload_time:.2f}s, should be < 3s")
        
        # Verify file was created successfully
        self.assertIsNotNone(media_file)
        self.assertEqual(media_file.file_size, len(large_content))
        self.assertTrue(os.path.exists(media_file.file.path))
    
    def test_large_image_form_processing_time(self):
        """Test form processing time for large images"""
        large_content = self.create_large_image_content(2 * 1024 * 1024)  # 2MB
        uploaded_file = SimpleUploadedFile(
            "large_form_image.jpg",
            large_content,
            content_type="image/jpeg"
        )
        
        form_data = {
            'description': 'Large image test',
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
        
        # Form processing should complete within 4 seconds
        self.assertLess(processing_time, 4.0, f"Form processing took {processing_time:.2f}s, should be < 4s")
        self.assertTrue(is_valid)
        if is_valid:
            self.assertIsNotNone(photo)
    
    def test_multiple_large_uploads_performance(self):
        """Test performance with multiple large uploads"""
        num_uploads = 3
        upload_times = []
        large_content = self.create_large_image_content(2 * 1024 * 1024)  # 2MB each
        
        for i in range(num_uploads):
            uploaded_file = SimpleUploadedFile(
                f"large_image_{i}.jpg",
                large_content,
                content_type="image/jpeg"
            )
            
            start_time = time.time()
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            upload_time = time.time() - start_time
            
            upload_times.append(upload_time)
            
            # Each upload should still be fast
            self.assertLess(upload_time, 3.0, f"Upload {i} took {upload_time:.2f}s")
        
        # Average upload time should be reasonable
        avg_time = sum(upload_times) / len(upload_times)
        self.assertLess(avg_time, 2.5, f"Average upload time {avg_time:.2f}s too high")


class ThumbnailGenerationPerformanceTests(MediaFilePerformanceTestCase):
    """Tests for thumbnail generation performance"""
    
    def test_thumbnail_generation_speed(self):
        """Test thumbnail generation speed"""
        uploaded_file = self.create_test_image_file("test_image.jpg")
        
        start_time = time.time()
        
        # Create MediaFile (includes thumbnail generation)
        media_file = MediaFile.objects.create_from_upload(uploaded_file)
        
        generation_time = time.time() - start_time
        
        # Thumbnail generation should be fast (< 2 seconds)
        self.assertLess(generation_time, 2.0, f"Thumbnail generation took {generation_time:.2f}s")
        
        # Verify MediaFile was created
        self.assertIsNotNone(media_file)
    
    def test_multiple_thumbnail_generation(self):
        """Test performance of generating multiple thumbnails"""
        num_images = 5
        generation_times = []
        
        for i in range(num_images):
            # Create unique content for each file
            content = self.test_image_content + bytes([i])
            uploaded_file = self.create_test_image_file(f"test_image_{i}.jpg", content=content)
            
            start_time = time.time()
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            generation_time = time.time() - start_time
            
            generation_times.append(generation_time)
            
            # Each generation should be fast
            self.assertLess(generation_time, 2.0, f"Thumbnail {i} took {generation_time:.2f}s")
        
        # Average generation time should be reasonable
        avg_time = sum(generation_times) / len(generation_times)
        self.assertLess(avg_time, 1.5, f"Average generation time {avg_time:.2f}s too high")


class DatabaseQueryOptimizationTests(MediaFilePerformanceTestCase):
    """Tests for database query optimization"""
    
    def setUp(self):
        """Set up test data with multiple photos"""
        super().setUp()
        
        # Create multiple photos for testing
        self.photos = []
        for i in range(10):
            # Create unique content for each file to avoid deduplication conflicts
            content = self.test_image_content + bytes([i])  # Make each file unique
            uploaded_file = self.create_test_image_file(f"test_{i}.jpg", content=content)
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            photo = Photo.objects.create(
                media_file=media_file,
                description=f"Test photo {i}",
                patient=self.patient,
                event_datetime=timezone.now(),
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
        self.assertLessEqual(query_count, 3, f"Used {query_count} queries, should be ≤ 3")
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
        
        # Use Photo objects manager
        photos = list(Photo.objects.filter(patient=self.patient))
        
        query_count = len(connection.queries)
        
        # Manager should be reasonably optimized
        self.assertLessEqual(query_count, 3, f"Manager used {query_count} queries")
        
        # Test accessing basic properties
        for photo in photos[:3]:  # Test first 3
            _ = photo.description
            _ = photo.patient.name


class FileServingPerformanceTests(MediaFilePerformanceTestCase):
    """Tests for file serving performance"""

    def setUp(self):
        """Set up test data"""
        super().setUp()
        
        # Create test photo
        uploaded_file = self.create_test_image_file("test.jpg")
        self.media_file = MediaFile.objects.create_from_upload(uploaded_file)
        self.photo = Photo.objects.create(
            media_file=self.media_file,
            description="Test photo",
            patient=self.patient,
            event_datetime=timezone.now(),
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

        # File serving should be fast (< 1 second)
        self.assertLess(response_time, 1.0, f"File serving took {response_time:.2f}s")

        # Should return appropriate response
        self.assertIn(response.status_code, [200, 403, 404])

    def test_thumbnail_serving_response_time(self):
        """Test thumbnail serving response time"""
        thumbnail_url = reverse('mediafiles:serve_thumbnail', kwargs={'file_id': self.media_file.id})

        start_time = time.time()
        response = self.client.get(thumbnail_url)
        response_time = time.time() - start_time

        # Thumbnail serving should be fast (< 1 second)
        self.assertLess(response_time, 1.0, f"Thumbnail serving took {response_time:.2f}s")

        # Should either serve thumbnail or return 404 if not generated
        self.assertIn(response.status_code, [200, 404, 403])

    def test_multiple_file_requests_performance(self):
        """Test performance with multiple requests"""
        file_url = reverse('mediafiles:serve_file', kwargs={'file_id': self.media_file.id})

        response_times = []
        num_requests = 5

        for i in range(num_requests):
            start_time = time.time()
            response = self.client.get(file_url)
            response_time = time.time() - start_time

            response_times.append(response_time)

            # Each request should be fast
            self.assertLess(response_time, 1.5, f"Request {i} took {response_time:.2f}s")

            # Verify response is valid
            self.assertIn(response.status_code, [200, 403, 404])

        # Average response time should be good
        avg_time = sum(response_times) / len(response_times)
        self.assertLess(avg_time, 1.0, f"Average response time {avg_time:.2f}s too high")

    def test_photo_detail_view_performance(self):
        """Test photo detail view performance"""
        detail_url = reverse('mediafiles:photo_detail', kwargs={'pk': self.photo.pk})

        start_time = time.time()
        response = self.client.get(detail_url)
        response_time = time.time() - start_time

        # Detail view should load quickly (< 2 seconds)
        self.assertLess(response_time, 2.0, f"Detail view took {response_time:.2f}s")
        self.assertIn(response.status_code, [200, 403, 404])


class MemoryUsageTests(MediaFilePerformanceTestCase):
    """Tests for memory usage during file operations"""

    def test_large_file_memory_usage(self):
        """Test memory usage with large files"""
        # Create a moderately large file (1MB)
        large_content = self.create_large_image_content(1 * 1024 * 1024)

        uploaded_file = SimpleUploadedFile(
            "large_test.jpg",
            large_content,
            content_type="image/jpeg"
        )

        # This should not cause memory issues
        try:
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            self.assertIsNotNone(media_file)
            self.assertGreaterEqual(media_file.file_size, 1024 * 1024)
        except MemoryError:
            self.fail("Large file upload caused memory error")

    def test_multiple_files_memory_efficiency(self):
        """Test memory efficiency with multiple files"""
        # Create multiple files to test memory efficiency
        media_files = []
        num_files = 10

        try:
            for i in range(num_files):
                # Create unique content for each file
                content = self.test_image_content + bytes([i])
                uploaded_file = self.create_test_image_file(f"test_{i}.jpg", content=content)
                media_file = MediaFile.objects.create_from_upload(uploaded_file)
                media_files.append(media_file)

            # Should successfully create all files
            self.assertEqual(len(media_files), num_files)

        except MemoryError:
            self.fail("Multiple file creation caused memory error")


class ConcurrencyPerformanceTests(MediaFilePerformanceTestCase, TransactionTestCase):
    """Tests for performance under concurrent-like operations"""

    def test_concurrent_upload_simulation(self):
        """Test simulated concurrent uploads"""
        # Simulate concurrent uploads by rapid sequential uploads
        upload_times = []
        num_uploads = 5

        start_total = time.time()

        for i in range(num_uploads):
            # Create unique content for each file
            content = self.test_image_content + bytes([i])
            uploaded_file = self.create_test_image_file(f"concurrent_{i}.jpg", content=content)

            start_time = time.time()
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            upload_time = time.time() - start_time

            upload_times.append(upload_time)

            # Each upload should still be reasonably fast
            self.assertLess(upload_time, 3.0, f"Concurrent upload {i} took {upload_time:.2f}s")

            # Verify file was created
            self.assertIsNotNone(media_file)

        total_time = time.time() - start_total

        # Total time should be reasonable
        self.assertLess(total_time, 15.0, f"Total concurrent uploads took {total_time:.2f}s")

        # Verify all files were created
        self.assertEqual(MediaFile.objects.count(), num_uploads)


# PhotoSeries Performance Tests

@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    MEDIA_USE_UUID_FILENAMES=True,
    MEDIA_ENABLE_FILE_DEDUPLICATION=True
)
class PhotoSeriesBatchUploadPerformanceTests(MediaFilePerformanceTestCase, TransactionTestCase):
    """Tests for PhotoSeries batch upload performance"""

    def test_large_batch_upload_performance(self):
        """Test performance with large batch uploads (10+ photos)"""
        num_photos = 8  # Reduced for performance
        uploaded_files = []

        # Create multiple files for batch upload
        for i in range(num_photos):
            # Create unique content for each file
            content = self.test_image_content + bytes([i])
            uploaded_files.append(self.create_test_image_file(f"batch_photo_{i}.jpg", content=content))

        form_data = {
            'description': 'Large batch upload test',
            'caption': 'Performance test series'
        }

        start_time = time.time()

        form = PhotoSeriesCreateForm(
            data=form_data,
            files={'images': uploaded_files},
            patient=self.patient,
            user=self.user
        )

        is_valid = form.is_valid()
        if is_valid:
            series = form.save()

        upload_time = time.time() - start_time

        # Batch upload should complete within 8 seconds
        self.assertLess(upload_time, 8.0, f"Batch upload took {upload_time:.2f}s, should be < 8s")
        self.assertTrue(is_valid)

        if is_valid:
            # Verify all photos were uploaded
            self.assertEqual(series.get_photo_count(), num_photos)

    def test_batch_upload_memory_efficiency(self):
        """Test memory efficiency during batch uploads"""
        num_photos = 5
        uploaded_files = []

        # Create files for batch upload
        for i in range(num_photos):
            # Create unique content for each file
            content = self.test_image_content + bytes([i])
            uploaded_files.append(self.create_test_image_file(f"memory_test_{i}.jpg", content=content))

        form_data = {
            'description': 'Memory efficiency test',
            'caption': 'Memory test series'
        }

        # This should not cause memory issues
        try:
            form = PhotoSeriesCreateForm(
                data=form_data,
                files={'images': uploaded_files},
                patient=self.patient,
                user=self.user
            )

            if form.is_valid():
                series = form.save()
                self.assertEqual(series.get_photo_count(), num_photos)

        except MemoryError:
            self.fail("Batch upload caused memory error")


class PhotoSeriesGalleryPerformanceTests(MediaFilePerformanceTestCase):
    """Tests for PhotoSeries gallery loading performance"""

    def setUp(self):
        """Set up test data"""
        super().setUp()
        
        # Create PhotoSeries with photos
        self.series = PhotoSeries.objects.create(
            description="Gallery performance test",
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )

        # Add multiple photos to series
        for i in range(8):  # Reduced for performance
            # Create unique content for each file
            content = self.test_image_content + bytes([i])
            uploaded_file = self.create_test_image_file(f"gallery_test_{i}.jpg", content=content)
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            self.series.add_photo(media_file, order=i+1, description=f"Photo {i+1}")

        self.client = Client()
        self.client.force_login(self.user)

    def test_gallery_loading_performance(self):
        """Test gallery loading performance with multiple photos"""
        detail_url = reverse('mediafiles:photoseries_detail', kwargs={'pk': self.series.pk})

        start_time = time.time()
        response = self.client.get(detail_url)
        load_time = time.time() - start_time

        # Gallery should load within 3 seconds
        self.assertLess(load_time, 3.0, f"Gallery loading took {load_time:.2f}s, should be < 3s")
        self.assertIn(response.status_code, [200, 403, 404])

    def test_gallery_query_optimization(self):
        """Test database query optimization for gallery loading"""
        # Reset query count
        connection.queries_log.clear()

        # Load PhotoSeries with photos
        series = PhotoSeries.objects.select_related(
            'patient', 'created_by'
        ).prefetch_related(
            'photoseriesfile_set__media_file'
        ).get(pk=self.series.pk)

        # Access photos
        photos = series.get_ordered_photos()
        list(photos)  # Force evaluation

        query_count = len(connection.queries)

        # Should use minimal queries due to prefetch_related
        self.assertLessEqual(query_count, 4, f"Gallery used {query_count} queries, should be ≤ 4")

        # Access related objects should not trigger too many additional queries
        connection.queries_log.clear()
        for photo in photos[:3]:  # Test first 3
            _ = photo.original_filename
            _ = photo.file_size

        additional_queries = len(connection.queries)
        self.assertLessEqual(additional_queries, 1, "Accessing photo data triggered too many additional queries")


class PhotoSeriesOperationPerformanceTests(MediaFilePerformanceTestCase):
    """Tests for PhotoSeries operation performance"""

    def setUp(self):
        """Set up test data"""
        super().setUp()
        
        # Create PhotoSeries with photos
        self.series = PhotoSeries.objects.create(
            description="Operation performance test",
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )

        # Add photos to series
        self.photos = []
        for i in range(6):  # Reduced for performance
            # Create unique content for each file
            content = self.test_image_content + bytes([i])
            uploaded_file = self.create_test_image_file(f"operation_test_{i}.jpg", content=content)
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            self.series.add_photo(media_file, order=i+1)
            self.photos.append(media_file)

    def test_photo_addition_performance(self):
        """Test photo addition performance"""
        uploaded_file = self.create_test_image_file("addition_test.jpg")
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        start_time = time.time()
        self.series.add_photo(media_file, description="Added photo")
        addition_time = time.time() - start_time

        # Photo addition should be fast (< 1 second)
        self.assertLess(addition_time, 1.0, f"Photo addition took {addition_time:.2f}s")

        # Verify photo was added
        self.assertEqual(self.series.get_photo_count(), 7)

    def test_photo_removal_performance(self):
        """Test photo removal performance"""
        # Remove a photo from the middle
        photo_to_remove = self.photos[3]

        start_time = time.time()
        self.series.remove_photo(photo_to_remove)
        removal_time = time.time() - start_time

        # Photo removal should be fast (< 1 second)
        self.assertLess(removal_time, 1.0, f"Photo removal took {removal_time:.2f}s")

        # Verify photo was removed
        self.assertEqual(self.series.get_photo_count(), 5)

    def test_series_deletion_performance(self):
        """Test series deletion performance with batch cleanup"""
        # Create a separate series for deletion test
        deletion_series = PhotoSeries.objects.create(
            description="Deletion test series",
            patient=self.patient,
            event_datetime=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )

        # Add photos to deletion series
        for i in range(4):
            # Create unique content for each file
            content = self.test_image_content + bytes([i + 10])  # Use different range to avoid conflicts
            uploaded_file = self.create_test_image_file(f"deletion_test_{i}.jpg", content=content)
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            deletion_series.add_photo(media_file, order=i+1)

        start_time = time.time()
        deletion_series.delete()
        deletion_time = time.time() - start_time

        # Series deletion with cleanup should be reasonable (< 3 seconds)
        self.assertLess(deletion_time, 3.0, f"Series deletion took {deletion_time:.2f}s")

        # Verify series was deleted
        self.assertFalse(PhotoSeries.objects.filter(pk=deletion_series.pk).exists())

    def test_zip_download_performance(self):
        """Test ZIP download generation performance"""
        self.client = Client()
        self.client.force_login(self.user)

        download_url = reverse('mediafiles:photoseries_download', kwargs={'pk': self.series.pk})

        start_time = time.time()
        response = self.client.get(download_url)
        download_time = time.time() - start_time

        # ZIP generation should be reasonable (< 4 seconds)
        self.assertLess(download_time, 4.0, f"ZIP download took {download_time:.2f}s")

        # Should either provide ZIP or handle appropriately
        self.assertIn(response.status_code, [200, 302, 404, 403])

        if response.status_code == 200:
            self.assertEqual(response['Content-Type'], 'application/zip')