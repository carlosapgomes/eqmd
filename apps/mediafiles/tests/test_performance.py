"""
Performance tests for PhotoSeries and mediafiles functionality.

Tests performance aspects including:
- Large file upload and processing performance
- Batch upload performance for PhotoSeries
- Gallery loading and navigation performance
- Database query optimization
- Memory usage and efficiency
- File serving performance

Thresholds are explicit and retained from the original suite; fixtures are
synthetic (real small images from ``tests/test_media`` plus header-valid
padded JPEG bodies for large-file paths). Hospital was removed in the
single-hospital refactor.
"""

import os
import tempfile
import time
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.mediafiles.models import MediaFile, Photo, PhotoSeries, PhotoSeriesFile

from .factories import (
    create_patient,
    create_photo_on_disk,
    create_user,
    load_test_image_bytes,
    write_filepond_file,
)

User = get_user_model()

TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="mediafiles_performance_"))

LOGIN_URL = "/accounts/login/"


def grant_permissions(user, *names):
    """Grant Django model permissions to a user (synthetic test fixture)."""
    from django.contrib.auth.models import Permission

    for name in names:
        app_label, codename = name.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app_label, codename=codename)
        )


def add_thumbnail_on_disk(photo):
    """Write the FilePond thumbnail for a photo and point the row at it."""
    content = load_test_image_bytes()
    thumb_dir = f"photos/{photo.created_at.strftime('%Y/%m')}/thumbnails"
    photo.thumbnail_path = f"{thumb_dir}/{photo.file_id}_thumb.jpg"
    photo.save(update_fields=["thumbnail_path"])
    write_filepond_file(thumb_dir, f"{photo.file_id}_thumb", ".jpg", content)


class MediaFilePerformanceTestCase(TestCase):
    """Base test case with common performance test setup."""

    def setUp(self):
        """Set up test data"""
        self.user = create_user(
            username="testuser", password_change_required=False, terms_accepted=True
        )
        self.patient = create_patient(self.user)
        self.test_image_content = load_test_image_bytes()

    def create_test_image_file(self, filename="test.jpg", content=None):
        """Create a test image file for testing."""
        if content is None:
            content = self.test_image_content
        return SimpleUploadedFile(filename, content, content_type="image/jpeg")

    def create_large_image_content(self, size):
        """Create a header-valid padded JPEG body of the requested size."""
        # JPEG SOI + minimal header (valid magic number for the validator)
        jpeg_header = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
            b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
            b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
            b"\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01"
            b"\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff"
            b"\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00"
        )

        # Fill with padding bytes and a JPEG end marker
        padding_size = size - len(jpeg_header) - 2
        padding = bytes([(i % 256) for i in range(padding_size)])
        jpeg_end = b"\xff\xd9"

        return jpeg_header + padding + jpeg_end


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class LargeImageUploadPerformanceTests(MediaFilePerformanceTestCase):
    """Tests for large image upload performance."""

    def test_large_image_upload_time(self):
        """Test upload time for large images (MediaFile pipeline)"""
        large_content = self.create_large_image_content(4 * 1024 * 1024)  # 4MB
        uploaded_file = SimpleUploadedFile(
            "large_image.jpg", large_content, content_type="image/jpeg"
        )

        start_time = time.time()

        # Test MediaFile creation
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        upload_time = time.time() - start_time

        # Upload should complete within 3 seconds for 4MB file
        self.assertLess(
            upload_time, 3.0, f"Upload took {upload_time:.2f}s, should be < 3s"
        )

        # Verify file was created successfully
        self.assertIsNotNone(media_file)
        self.assertEqual(media_file.file_size, len(large_content))
        self.assertTrue(os.path.exists(media_file.file.path))

    def test_large_image_form_processing_time(self):
        """Test FilePond form processing time for large images"""
        import shortuuid
        from django_drf_filepond.models import TemporaryUpload

        large_content = self.create_large_image_content(2 * 1024 * 1024)  # 2MB
        upload_id = shortuuid.uuid()
        TemporaryUpload.objects.create(
            upload_id=upload_id,
            upload_name="large_form_image.jpg",
            upload_type="F",
            file=SimpleUploadedFile(
                "large_form_image.jpg",
                large_content,
                content_type="image/jpeg",
            ),
        )

        from apps.mediafiles.forms import PhotoCreateFormNew

        past_local = timezone.localtime(timezone.now() - timezone.timedelta(hours=2))
        form_data = {
            "description": "Large image test",
            "caption": "Performance test image",
            "event_datetime": past_local.strftime("%Y-%m-%dT%H:%M"),
            "upload_id": upload_id,
        }

        start_time = time.time()

        form = PhotoCreateFormNew(data=form_data, patient=self.patient, user=self.user)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        photo = form.save()

        processing_time = time.time() - start_time

        # Form processing should complete within 4 seconds
        self.assertLess(
            processing_time,
            4.0,
            f"Form processing took {processing_time:.2f}s, should be < 4s",
        )
        self.assertIsNotNone(photo.id)
        self.assertEqual(photo.patient, self.patient)

    def test_multiple_large_uploads_performance(self):
        """Test performance with multiple large uploads"""
        num_uploads = 3
        upload_times = []
        large_content = self.create_large_image_content(2 * 1024 * 1024)  # 2MB each

        for i in range(num_uploads):
            uploaded_file = SimpleUploadedFile(
                f"large_image_{i}.jpg",
                large_content + bytes([i]),  # unique content per file
                content_type="image/jpeg",
            )

            start_time = time.time()
            MediaFile.objects.create_from_upload(uploaded_file)
            upload_time = time.time() - start_time

            upload_times.append(upload_time)

            # Each upload should still be fast
            self.assertLess(upload_time, 3.0, f"Upload {i} took {upload_time:.2f}s")

        # Average upload time should be reasonable
        avg_time = sum(upload_times) / len(upload_times)
        self.assertLess(avg_time, 2.5, f"Average upload time {avg_time:.2f}s too high")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ThumbnailGenerationPerformanceTests(MediaFilePerformanceTestCase):
    """Tests for thumbnail generation performance."""

    def test_thumbnail_generation_speed(self):
        """Test thumbnail generation speed"""
        uploaded_file = self.create_test_image_file("test_image.jpg")

        start_time = time.time()

        # Create MediaFile (includes thumbnail generation)
        media_file = MediaFile.objects.create_from_upload(uploaded_file)

        generation_time = time.time() - start_time

        # Thumbnail generation should be fast (< 2 seconds)
        self.assertLess(
            generation_time,
            2.0,
            f"Thumbnail generation took {generation_time:.2f}s",
        )

        # Verify MediaFile was created
        self.assertIsNotNone(media_file)

    def test_multiple_thumbnail_generation(self):
        """Test performance of generating multiple thumbnails"""
        num_images = 5
        generation_times = []

        for i in range(num_images):
            # Create unique content for each file
            content = self.test_image_content + bytes([i])
            uploaded_file = self.create_test_image_file(
                f"test_image_{i}.jpg", content=content
            )

            start_time = time.time()
            MediaFile.objects.create_from_upload(uploaded_file)
            generation_time = time.time() - start_time

            generation_times.append(generation_time)

            # Each generation should be fast
            self.assertLess(
                generation_time, 2.0, f"Thumbnail {i} took {generation_time:.2f}s"
            )

        # Average generation time should be reasonable
        avg_time = sum(generation_times) / len(generation_times)
        self.assertLess(
            avg_time, 1.5, f"Average generation time {avg_time:.2f}s too high"
        )


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class DatabaseQueryOptimizationTests(MediaFilePerformanceTestCase):
    """Tests for database query optimization."""

    def setUp(self):
        """Set up test data with multiple photos"""
        super().setUp()

        # Create multiple photos for testing
        self.photos = []
        for i in range(10):
            content = self.test_image_content + bytes([i])  # unique content
            self.photos.append(
                create_photo_on_disk(
                    self.patient,
                    self.user,
                    content=content,
                    filename=f"test_{i}.jpg",
                    description=f"Test photo {i}",
                )
            )

    def test_photo_list_query_optimization(self):
        """Test query optimization for photo lists"""
        # Get photos with related objects in a single query
        with self.assertNumQueries(1):
            photos = list(
                Photo.objects.select_related(
                    "patient", "created_by", "updated_by"
                ).filter(patient=self.patient)
            )

        self.assertEqual(len(photos), 10)

        # Accessing related objects should not trigger additional queries
        connection.queries_log.clear()
        for photo in photos:
            _ = photo.patient.name
            _ = photo.created_by.username
            _ = photo.updated_by.username

        self.assertEqual(
            len(connection.queries),
            0,
            "Accessing related objects triggered additional queries",
        )

    def test_photo_manager_optimization(self):
        """Test Photo manager query optimization"""
        # The Photo manager already select_related('patient', 'created_by')
        with self.assertNumQueries(1):
            photos = list(Photo.objects.filter(patient=self.patient))

        self.assertEqual(len(photos), 10)

        # Test accessing basic properties without extra queries
        connection.queries_log.clear()
        for photo in photos[:3]:  # Test first 3
            _ = photo.description
            _ = photo.patient.name

        self.assertEqual(
            len(connection.queries),
            0,
            "Accessing related objects triggered additional queries",
        )


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class FileServingPerformanceTests(MediaFilePerformanceTestCase):
    """Tests for file serving performance."""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Create test photo with its FilePond original on disk
        self.photo = create_photo_on_disk(self.patient, self.user)

        grant_permissions(self.user, "events.view_event")
        self.client = Client()
        self.client.force_login(self.user)

    def test_file_serving_response_time(self):
        """Test file serving response time"""
        file_url = reverse(
            "mediafiles:serve_file", kwargs={"file_id": self.photo.file_id}
        )

        start_time = time.time()
        response = self.client.get(file_url)
        response_time = time.time() - start_time

        # File serving should be fast (< 1 second)
        self.assertLess(response_time, 1.0, f"File serving took {response_time:.2f}s")

        # Should return the file
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_thumbnail_serving_response_time(self):
        """Test thumbnail serving response time"""
        add_thumbnail_on_disk(self.photo)
        thumbnail_url = reverse(
            "mediafiles:serve_thumbnail",
            kwargs={"file_id": self.photo.file_id},
        )

        start_time = time.time()
        response = self.client.get(thumbnail_url)
        response_time = time.time() - start_time

        # Thumbnail serving should be fast (< 1 second)
        self.assertLess(
            response_time, 1.0, f"Thumbnail serving took {response_time:.2f}s"
        )

        # Should serve the thumbnail
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_multiple_file_requests_performance(self):
        """Test performance with multiple requests"""
        file_url = reverse(
            "mediafiles:serve_file", kwargs={"file_id": self.photo.file_id}
        )

        response_times = []
        num_requests = 5

        for i in range(num_requests):
            start_time = time.time()
            response = self.client.get(file_url)
            response_time = time.time() - start_time

            response_times.append(response_time)

            # Each request should be fast
            self.assertLess(
                response_time, 1.5, f"Request {i} took {response_time:.2f}s"
            )

            # Verify response is valid
            self.assertEqual(response.status_code, 200)

        # Average response time should be good
        avg_time = sum(response_times) / len(response_times)
        self.assertLess(
            avg_time, 1.0, f"Average response time {avg_time:.2f}s too high"
        )

    def test_photo_detail_view_performance(self):
        """Test photo detail view performance"""
        detail_url = reverse("mediafiles:photo_detail", kwargs={"pk": self.photo.pk})

        start_time = time.time()
        response = self.client.get(detail_url)
        response_time = time.time() - start_time

        # Detail view should load quickly (< 2 seconds)
        self.assertLess(response_time, 2.0, f"Detail view took {response_time:.2f}s")
        self.assertEqual(response.status_code, 200)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class MemoryUsageTests(MediaFilePerformanceTestCase):
    """Tests for memory usage during file operations."""

    def test_large_file_memory_usage(self):
        """Test memory usage with large files"""
        # Create a moderately large file (1MB)
        large_content = self.create_large_image_content(1 * 1024 * 1024)

        uploaded_file = SimpleUploadedFile(
            "large_test.jpg", large_content, content_type="image/jpeg"
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
                uploaded_file = self.create_test_image_file(
                    f"test_{i}.jpg", content=content
                )
                media_file = MediaFile.objects.create_from_upload(uploaded_file)
                media_files.append(media_file)

            # Should successfully create all files
            self.assertEqual(len(media_files), num_files)

        except MemoryError:
            self.fail("Multiple file creation caused memory error")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ConcurrencyPerformanceTests(MediaFilePerformanceTestCase):
    """Tests for performance under concurrent-like operations."""

    def test_concurrent_upload_simulation(self):
        """Test simulated concurrent uploads"""
        # Simulate concurrent uploads by rapid sequential uploads
        upload_times = []
        num_uploads = 5

        start_total = time.time()

        for i in range(num_uploads):
            # Create unique content for each file
            content = self.test_image_content + bytes([i])
            uploaded_file = self.create_test_image_file(
                f"concurrent_{i}.jpg", content=content
            )

            start_time = time.time()
            media_file = MediaFile.objects.create_from_upload(uploaded_file)
            upload_time = time.time() - start_time

            upload_times.append(upload_time)

            # Each upload should still be reasonably fast
            self.assertLess(
                upload_time, 3.0, f"Concurrent upload {i} took {upload_time:.2f}s"
            )

            # Verify file was created
            self.assertIsNotNone(media_file)

        total_time = time.time() - start_total

        # Total time should be reasonable
        self.assertLess(
            total_time, 15.0, f"Total concurrent uploads took {total_time:.2f}s"
        )

        # Verify all files were created
        self.assertEqual(MediaFile.objects.count(), num_uploads)


# PhotoSeries Performance Tests


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PhotoSeriesBatchUploadPerformanceTests(MediaFilePerformanceTestCase):
    """Tests for PhotoSeries batch upload performance (FilePond form)."""

    def create_temp_uploads(self, num_uploads, size=0):
        """Create FilePond TemporaryUpload rows and return comma-joined ids."""
        import shortuuid
        from django_drf_filepond.models import TemporaryUpload

        upload_ids = []
        for i in range(num_uploads):
            content = self.test_image_content + bytes([i])
            if size:
                content = self.create_large_image_content(size) + bytes([i])
            upload_id = shortuuid.uuid()
            TemporaryUpload.objects.create(
                upload_id=upload_id,
                upload_name=f"batch_photo_{i}.jpg",
                upload_type="F",
                file=SimpleUploadedFile(
                    f"batch_photo_{i}.jpg",
                    content,
                    content_type="image/jpeg",
                ),
            )
            upload_ids.append(upload_id)
        return ",".join(upload_ids)

    def test_large_batch_upload_performance(self):
        """Test performance with large batch uploads (8 photos)"""
        num_photos = 8
        upload_ids = self.create_temp_uploads(num_photos)

        from apps.mediafiles.forms import PhotoSeriesCreateFormNew

        past_local = timezone.localtime(timezone.now() - timezone.timedelta(hours=2))
        form_data = {
            "description": "Large batch upload test",
            "caption": "Performance test series",
            "event_datetime": past_local.strftime("%Y-%m-%dT%H:%M"),
            "upload_ids": upload_ids,
        }

        start_time = time.time()

        form = PhotoSeriesCreateFormNew(
            data=form_data, patient=self.patient, user=self.user
        )
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        series = form.save()

        upload_time = time.time() - start_time

        # Batch upload should complete within 8 seconds
        self.assertLess(
            upload_time,
            8.0,
            f"Batch upload took {upload_time:.2f}s, should be < 8s",
        )

        # Verify all photos were uploaded
        self.assertEqual(series.get_photo_count(), num_photos)

    def test_batch_upload_memory_efficiency(self):
        """Test memory efficiency during batch uploads"""
        num_photos = 5
        upload_ids = self.create_temp_uploads(num_photos)

        from apps.mediafiles.forms import PhotoSeriesCreateFormNew

        past_local = timezone.localtime(timezone.now() - timezone.timedelta(hours=2))
        form_data = {
            "description": "Memory efficiency test",
            "caption": "Memory test series",
            "event_datetime": past_local.strftime("%Y-%m-%dT%H:%M"),
            "upload_ids": upload_ids,
        }

        # This should not cause memory issues
        try:
            form = PhotoSeriesCreateFormNew(
                data=form_data, patient=self.patient, user=self.user
            )
            if form.is_valid():
                series = form.save()
                self.assertEqual(series.get_photo_count(), num_photos)
        except MemoryError:
            self.fail("Batch upload caused memory error")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PhotoSeriesGalleryPerformanceTests(MediaFilePerformanceTestCase):
    """Tests for PhotoSeries gallery loading performance."""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Create PhotoSeries with photos (current ORM-level API)
        self.series = PhotoSeries.objects.create(
            description="Gallery performance test",
            patient=self.patient,
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            created_by=self.user,
            updated_by=self.user,
        )
        for i in range(8):
            PhotoSeriesFile.objects.create(
                photo_series=self.series,
                file_id=str(uuid.uuid4()),
                original_filename=f"gallery_test_{i}.jpg",
                file_size=100,
                width=100,
                height=100,
                order=i + 1,
            )

        grant_permissions(self.user, "events.view_event")
        self.client = Client()
        self.client.force_login(self.user)

    def test_gallery_loading_performance(self):
        """Test gallery loading performance with multiple photos"""
        detail_url = reverse(
            "mediafiles:photoseries_detail", kwargs={"pk": self.series.pk}
        )

        start_time = time.time()
        response = self.client.get(detail_url)
        load_time = time.time() - start_time

        # Gallery should load within 3 seconds
        self.assertLess(
            load_time, 3.0, f"Gallery loading took {load_time:.2f}s, should be < 3s"
        )
        self.assertEqual(response.status_code, 200)

    def test_gallery_query_optimization(self):
        """Test database query optimization for gallery loading"""
        # The PhotoSeries manager select_related('patient', 'created_by') and
        # prefetches photoseriesfile_set: 2 queries for series + files.
        with self.assertNumQueries(2):
            series = PhotoSeries.objects.get(pk=self.series.pk)
            photos = series.get_ordered_photos()
            _ = series.patient.name
            _ = series.created_by.username

        # Accessing series-file data is served from the prefetch cache
        connection.queries_log.clear()
        for photo in photos[:3]:  # Test first 3
            _ = photo.original_filename
            _ = photo.file_size

        self.assertEqual(
            len(connection.queries),
            0,
            "Accessing photo data triggered additional queries",
        )


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PhotoSeriesOperationPerformanceTests(MediaFilePerformanceTestCase):
    """Tests for PhotoSeries operation performance (current ORM API)."""

    def setUp(self):
        """Set up test data"""
        super().setUp()

        # Create PhotoSeries with photos
        self.series = PhotoSeries.objects.create(
            description="Operation performance test",
            patient=self.patient,
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            created_by=self.user,
            updated_by=self.user,
        )
        self.photos = []
        for i in range(6):
            series_file = PhotoSeriesFile.objects.create(
                photo_series=self.series,
                file_id=str(uuid.uuid4()),
                original_filename=f"operation_test_{i}.jpg",
                file_size=100,
                order=i + 1,
            )
            self.photos.append(series_file)

        grant_permissions(self.user, "events.view_event")
        self.client = Client()
        self.client.force_login(self.user)

    def test_photo_addition_performance(self):
        """Test photo addition performance (PhotoSeriesFile create)"""
        start_time = time.time()
        PhotoSeriesFile.objects.create(
            photo_series=self.series,
            file_id=str(uuid.uuid4()),
            original_filename="addition_test.jpg",
            file_size=100,
            order=7,
        )
        addition_time = time.time() - start_time

        # Photo addition should be fast (< 1 second)
        self.assertLess(addition_time, 1.0, f"Photo addition took {addition_time:.2f}s")

        # Verify photo was added
        self.assertEqual(self.series.get_photo_count(), 7)

    def test_photo_removal_performance(self):
        """Test photo removal performance (row delete, no renumbering)"""
        photo_to_remove = self.photos[3]

        start_time = time.time()
        photo_to_remove.delete()
        removal_time = time.time() - start_time

        # Photo removal should be fast (< 1 second)
        self.assertLess(removal_time, 1.0, f"Photo removal took {removal_time:.2f}s")

        # Verify photo was removed
        self.assertEqual(self.series.get_photo_count(), 5)

    def test_series_deletion_performance(self):
        """Test series deletion performance"""
        # Create a separate series for deletion test
        deletion_series = PhotoSeries.objects.create(
            description="Deletion test series",
            patient=self.patient,
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            created_by=self.user,
            updated_by=self.user,
        )
        for i in range(4):
            PhotoSeriesFile.objects.create(
                photo_series=deletion_series,
                file_id=str(uuid.uuid4()),
                original_filename=f"deletion_test_{i}.jpg",
                file_size=100,
                order=i + 1,
            )

        start_time = time.time()
        deletion_series.delete()
        deletion_time = time.time() - start_time

        # Series deletion should be reasonable (< 3 seconds)
        self.assertLess(
            deletion_time, 3.0, f"Series deletion took {deletion_time:.2f}s"
        )

        # Verify series was soft-deleted
        self.assertTrue(PhotoSeries.objects.get(pk=deletion_series.pk).is_deleted)

    def test_zip_download_performance(self):
        """Test ZIP download request performance (current 302 contract)"""
        download_url = reverse(
            "mediafiles:photoseries_download", kwargs={"pk": self.series.pk}
        )

        start_time = time.time()
        response = self.client.get(download_url)
        download_time = time.time() - start_time

        # The request should be fast (< 4 seconds)
        self.assertLess(download_time, 4.0, f"ZIP download took {download_time:.2f}s")

        # Current FilePond contract: the legacy ZIP path redirects to detail
        # (documented production-gap candidate; see test_integration)
        self.assertEqual(response.status_code, 302)
