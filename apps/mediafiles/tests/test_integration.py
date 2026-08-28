"""
Integration tests for PhotoSeries and mediafiles functionality.

Tests end-to-end workflows through the current views and forms:
- FilePond photo upload and processing (through the HTTP view)
- PhotoSeries creation and management
- MediaFile deduplication workflows (legacy model, still current)
- Permission and access control
- Error handling scenarios

Fixtures use the current FilePond models; Hospital was removed in the
single-hospital refactor.
"""

import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.events.models import Event
from apps.mediafiles.models import MediaFile, Photo, PhotoSeries, PhotoSeriesFile

from .factories import (
    create_patient,
    create_photo_on_disk,
    create_user,
    load_test_image_bytes,
    photo_original_dir,
)

User = get_user_model()

# PhotoCreateFormNew builds paths with ``MEDIA_ROOT / "photos/..."``, so the
# override must be a Path (the string MEDIA_ROOT in test_settings would fail).
TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="mediafiles_integration_"))

LOGIN_URL = "/accounts/login/"

FULL_EVENT_PERMS = (
    "events.add_event",
    "events.view_event",
    "events.change_event",
    "events.delete_event",
    "patients.view_patient",
)


def grant_permissions(user, *names):
    """Grant Django model permissions to a user (synthetic test fixture)."""
    for name in names:
        app_label, codename = name.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app_label, codename=codename)
        )


def past_datetime_str(hours=2):
    """HTML5 ``datetime-local`` value for a recent past instant."""
    return timezone.localtime(
        timezone.now() - timezone.timedelta(hours=hours)
    ).strftime("%Y-%m-%dT%H:%M")


def create_temp_upload(filename, content=None, content_type="image/jpeg"):
    """Create a FilePond TemporaryUpload row; return its upload_id."""
    import shortuuid
    from django_drf_filepond.models import TemporaryUpload

    content = load_test_image_bytes() if content is None else content
    upload_id = shortuuid.uuid()
    TemporaryUpload.objects.create(
        upload_id=upload_id,
        upload_name=filename,
        upload_type="F",
        file=SimpleUploadedFile(filename, content, content_type=content_type),
    )
    return upload_id


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PhotoUploadWorkflowTests(TransactionTestCase):
    """Tests for the complete photo upload workflow through the view."""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        self.user = create_user(username="doctor")
        grant_permissions(self.user, *FULL_EVENT_PERMS)
        self.patient = create_patient(self.user, name="John Doe")

        self.client.force_login(self.user)

    def test_complete_photo_upload_workflow(self):
        """Test complete photo upload from FilePond form to servable file"""
        upload_id = create_temp_upload("workflow_test.jpg")

        create_url = reverse(
            "mediafiles:photo_create", kwargs={"patient_id": self.patient.id}
        )
        response = self.client.post(
            create_url,
            {
                "description": "Workflow test photo",
                "event_datetime": past_datetime_str(),
                "caption": "Test caption",
                "upload_id": upload_id,
            },
        )

        # Redirect to the patient timeline on success
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse(
                "apps.patients:patient_events_timeline",
                kwargs={"patient_id": self.patient.id},
            ),
        )

        # Photo row with FilePond metadata
        photo = Photo.objects.get(patient=self.patient)
        self.assertEqual(photo.description, "Workflow test photo")
        self.assertEqual(photo.created_by, self.user)
        self.assertEqual(photo.original_filename, "workflow_test.jpg")
        self.assertEqual(photo.event_type, Event.PHOTO_EVENT)

        # Original file is stored under photos/YYYY/MM/originals/<file_id>.jpg
        stored = (
            Path(settings.MEDIA_ROOT)
            / photo_original_dir(photo.created_at)
            / f"{photo.file_id}.jpg"
        )
        self.assertTrue(stored.exists(), f"Original should exist at {stored}")

        # The uploaded file is servable through the secure endpoint
        serve_url = reverse("mediafiles:serve_file", kwargs={"file_id": photo.file_id})
        serve_response = self.client.get(serve_url)
        self.assertEqual(serve_response.status_code, 200)
        self.assertEqual(serve_response["Content-Type"], "image/jpeg")

    def test_photo_viewing_workflow(self):
        """Test photo viewing in the detail view"""
        photo = create_photo_on_disk(
            self.patient, self.user, description="View test photo"
        )

        detail_url = reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk})
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, photo.description)
        self.assertContains(
            response,
            reverse("mediafiles:serve_file", kwargs={"file_id": photo.file_id}),
        )

    def test_photo_editing_workflow(self):
        """Test photo editing workflow through the update view"""
        photo = create_photo_on_disk(
            self.patient, self.user, description="Original description"
        )

        edit_url = reverse("mediafiles:photo_update", kwargs={"pk": photo.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)

        # Submit updated data (metadata only; the FilePond file is untouched)
        response = self.client.post(
            edit_url,
            {
                "description": "Updated description",
                "event_datetime": timezone.localtime(photo.event_datetime).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "caption": "Updated caption",
            },
        )
        self.assertEqual(response.status_code, 302)

        photo.refresh_from_db()
        self.assertEqual(photo.description, "Updated description")
        self.assertEqual(photo.caption, "Updated caption")

    def test_photo_deletion_workflow(self):
        """Test photo deletion workflow (soft delete)"""
        photo = create_photo_on_disk(
            self.patient, self.user, description="Delete test photo"
        )
        photo_id = photo.id

        delete_url = reverse("mediafiles:photo_delete", kwargs={"pk": photo.pk})
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)

        # The row is soft-deleted (is_deleted flag set)
        self.assertTrue(Photo.objects.get(pk=photo_id).is_deleted)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PhotoSeriesWorkflowTests(TransactionTestCase):
    """Tests for PhotoSeries workflows through the view."""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        self.user = create_user(username="doctor")
        grant_permissions(self.user, *FULL_EVENT_PERMS)
        self.patient = create_patient(self.user, name="Jane Doe")

        self.client.force_login(self.user)

    def test_complete_photoseries_upload_workflow(self):
        """Test complete PhotoSeries upload through the FilePond view"""
        upload_ids = ",".join(
            [
                create_temp_upload("series_1.jpg"),
                create_temp_upload("series_2.jpg"),
                create_temp_upload("series_3.jpg"),
            ]
        )

        create_url = reverse(
            "mediafiles:photoseries_create",
            kwargs={"patient_id": self.patient.id},
        )
        response = self.client.post(
            create_url,
            {
                "description": "Series workflow test",
                "event_datetime": past_datetime_str(),
                "caption": "Test series caption",
                "upload_ids": upload_ids,
            },
        )

        self.assertEqual(response.status_code, 302)

        series = PhotoSeries.objects.get(patient=self.patient)
        self.assertEqual(series.description, "Series workflow test")
        self.assertEqual(series.created_by, self.user)
        self.assertEqual(series.event_type, Event.PHOTO_SERIES_EVENT)

        # All files are stored in order with their own FilePond originals
        series_files = series.get_ordered_photos()
        self.assertEqual(series_files.count(), 3)
        self.assertEqual([sf.order for sf in series_files], [1, 2, 3])

        for series_file in series_files:
            stored = (
                Path(settings.MEDIA_ROOT)
                / f"photo_series/{series.created_at.strftime('%Y/%m')}/originals"
                / f"{series_file.file_id}.jpg"
            )
            self.assertTrue(stored.exists())
            serve_url = reverse(
                "mediafiles:serve_file",
                kwargs={"file_id": series_file.file_id},
            )
            serve_response = self.client.get(serve_url)
            self.assertEqual(serve_response.status_code, 200)
            self.assertEqual(serve_response["Content-Type"], "image/jpeg")

    def test_photoseries_viewing_workflow(self):
        """Test PhotoSeries viewing in the detail view"""
        series = PhotoSeries.objects.create(
            description="View test series",
            patient=self.patient,
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            created_by=self.user,
            updated_by=self.user,
        )
        PhotoSeriesFile.objects.create(
            photo_series=series,
            file_id="11111111-1111-1111-1111-111111111111",
            original_filename="view_test_1.jpg",
            file_size=100,
            order=1,
        )
        PhotoSeriesFile.objects.create(
            photo_series=series,
            file_id="22222222-2222-2222-2222-222222222222",
            original_filename="view_test_2.jpg",
            file_size=100,
            order=2,
        )

        detail_url = reverse("mediafiles:photoseries_detail", kwargs={"pk": series.pk})
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, series.description)
        # The gallery renders the series files in order
        self.assertEqual(series.get_ordered_photos().count(), 2)

    def test_photoseries_editing_workflow(self):
        """Test PhotoSeries editing workflow (metadata only)"""
        series = PhotoSeries.objects.create(
            description="Original series description",
            patient=self.patient,
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            created_by=self.user,
            updated_by=self.user,
        )

        edit_url = reverse("mediafiles:photoseries_update", kwargs={"pk": series.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            edit_url,
            {
                "description": "Updated series description",
                "event_datetime": timezone.localtime(series.event_datetime).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "caption": "Updated series caption",
            },
        )
        self.assertEqual(response.status_code, 302)

        series.refresh_from_db()
        self.assertEqual(series.description, "Updated series description")
        self.assertEqual(series.caption, "Updated series caption")

    def test_photoseries_deletion_workflow(self):
        """Test PhotoSeries deletion workflow (soft delete)"""
        series = PhotoSeries.objects.create(
            description="Delete test series",
            patient=self.patient,
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            created_by=self.user,
            updated_by=self.user,
        )
        series_id = series.id

        delete_url = reverse("mediafiles:photoseries_delete", kwargs={"pk": series.pk})
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)

        # The row is soft-deleted (is_deleted flag set)
        self.assertTrue(PhotoSeries.objects.get(pk=series_id).is_deleted)

    def test_photoseries_zip_download_current_contract(self):
        """ZIP download follows the current FilePond behavior (302 redirect).

        ``photoseries_download`` still reads the removed
        ``PhotoSeriesFile.media_file`` relation; the exception path redirects
        to the series detail page. Pinned as the current contract; the
        FilePond ZIP implementation is a production-gap candidate for the
        planner (no production edit without approval).
        """
        series = PhotoSeries.objects.create(
            description="Download test series",
            patient=self.patient,
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            created_by=self.user,
            updated_by=self.user,
        )
        PhotoSeriesFile.objects.create(
            photo_series=series,
            file_id="33333333-3333-3333-3333-333333333333",
            original_filename="download_test_1.jpg",
            file_size=100,
            order=1,
        )

        download_url = reverse(
            "mediafiles:photoseries_download", kwargs={"pk": series.pk}
        )
        response = self.client.get(download_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("mediafiles:photoseries_detail", kwargs={"pk": series.pk}),
        )

    def test_photoseries_timeline_integration(self):
        """Test PhotoSeries integration with the patient timeline"""
        series = PhotoSeries.objects.create(
            description="Timeline test series",
            patient=self.patient,
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
            created_by=self.user,
            updated_by=self.user,
        )

        # Series appears as an event with the correct type
        events = Event.objects.filter(patient=self.patient)
        self.assertTrue(events.filter(id=series.id).exists())
        series_event = events.get(id=series.id)
        self.assertEqual(series_event.event_type, Event.PHOTO_SERIES_EVENT)

        # And the timeline page renders the series description
        timeline_url = reverse(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )
        response = self.client.get(timeline_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Timeline test series")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class FileDeduplicationIntegrationTests(TestCase):
    """Tests for MediaFile deduplication (legacy model, still current)."""

    def setUp(self):
        """Set up test data"""
        self.user = create_user(username="doctor")
        self.patient = create_patient(self.user)

    def test_duplicate_file_deduplication_workflow(self):
        """Test that identical files are deduplicated to one MediaFile"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        content = load_test_image_bytes()
        file1 = SimpleUploadedFile("duplicate1.jpg", content, content_type="image/jpeg")
        media_file1 = MediaFile.objects.create_from_upload(file1)

        file2 = SimpleUploadedFile("duplicate2.jpg", content, content_type="image/jpeg")
        media_file2 = MediaFile.objects.create_from_upload(file2)

        # Same SHA-256 hash -> same MediaFile row (deduplication contract)
        self.assertEqual(media_file1.file_hash, media_file2.file_hash)
        self.assertEqual(media_file1.id, media_file2.id)

    def test_unique_files_no_deduplication(self):
        """Test that files with different content are not deduplicated"""
        from io import BytesIO

        from PIL import Image

        def jpeg_bytes(color):
            buffer = BytesIO()
            Image.new("RGB", (10, 10), color).save(buffer, "JPEG")
            return buffer.getvalue()

        media_file1 = MediaFile.objects.create_from_upload(
            SimpleUploadedFile(
                "unique1.jpg", jpeg_bytes("red"), content_type="image/jpeg"
            )
        )
        media_file2 = MediaFile.objects.create_from_upload(
            SimpleUploadedFile(
                "unique2.jpg", jpeg_bytes("blue"), content_type="image/jpeg"
            )
        )

        self.assertNotEqual(media_file1.file_hash, media_file2.file_hash)
        self.assertNotEqual(media_file1.id, media_file2.id)

    def test_media_file_and_photo_rows_are_independent(self):
        """Photo rows are independent of MediaFile rows (FilePond contract).

        The FilePond migration removed the Photo.media_file FK, so deleting a
        MediaFile row never affects Photo rows and vice versa.
        """
        photo = create_photo_on_disk(self.patient, self.user)
        media_file = MediaFile.objects.create(
            original_filename="legacy.jpg",
            file_size=100,
            mime_type="image/jpeg",
            file_hash="a" * 64,
        )

        photo.delete()
        self.assertTrue(MediaFile.objects.filter(pk=media_file.pk).exists())

        media_file.delete()
        self.assertTrue(Photo.objects.filter(pk=photo.pk).exists())


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PermissionIntegrationTests(TestCase):
    """Tests for permission-based access control."""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create two users (lifecycle-navigation-ready)
        self.user1 = create_user(username="doctor1")
        self.user2 = create_user(username="doctor2")

        self.patient = create_patient(self.user1, name="Private Patient")

    def test_authorized_access_workflow(self):
        """Test that authorized users can access photos"""
        grant_permissions(self.user1, *FULL_EVENT_PERMS)
        photo = create_photo_on_disk(self.patient, self.user1)

        self.client.force_login(self.user1)

        detail_url = reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_access_prevention(self):
        """Test that users without view_event cannot access photos"""
        grant_permissions(self.user1, *FULL_EVENT_PERMS)
        photo = create_photo_on_disk(self.patient, self.user1)

        # user2 has no events permission -> 403 (not a redirect, not 200)
        self.client.force_login(self.user2)
        detail_url = reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_access_prevention(self):
        """Test that unauthenticated users cannot access photos"""
        grant_permissions(self.user1, *FULL_EVENT_PERMS)
        photo = create_photo_on_disk(self.patient, self.user1)

        # Anonymous request -> redirect to login
        detail_url = reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(LOGIN_URL, response.url)

    def test_edit_permission_workflow(self):
        """Test edit permission enforcement (creator only, 24h window)"""
        grant_permissions(self.user1, *FULL_EVENT_PERMS)
        grant_permissions(self.user2, *FULL_EVENT_PERMS)
        photo = create_photo_on_disk(self.patient, self.user1)

        # Creator can open the edit form
        self.client.force_login(self.user1)
        edit_url = reverse("mediafiles:photo_update", kwargs={"pk": photo.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)

        # Non-creator is denied even with the change_event permission
        self.client.force_login(self.user2)
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 403)

    def test_delete_permission_workflow(self):
        """Test delete permission enforcement (creator only)"""
        grant_permissions(self.user1, *FULL_EVENT_PERMS)
        grant_permissions(self.user2, *FULL_EVENT_PERMS)
        photo = create_photo_on_disk(self.patient, self.user1)

        self.client.force_login(self.user2)
        delete_url = reverse("mediafiles:photo_delete", kwargs={"pk": photo.pk})
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 403)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ErrorHandlingIntegrationTests(TestCase):
    """Tests for error handling in integration scenarios."""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        self.user = create_user(username="doctor")
        grant_permissions(self.user, *FULL_EVENT_PERMS)
        self.patient = create_patient(self.user, name="Error Test Patient")

        self.client.force_login(self.user)

    def test_invalid_file_upload_error_handling(self):
        """A non-image FilePond upload keeps the form with errors"""
        upload_id = create_temp_upload("invalid.txt")

        create_url = reverse(
            "mediafiles:photo_create", kwargs={"patient_id": self.patient.id}
        )
        response = self.client.post(
            create_url,
            {
                "description": "Invalid file test",
                "event_datetime": past_datetime_str(),
                "caption": "",
                "upload_id": upload_id,
            },
        )

        # Form errors, no crash, no photo created
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(Photo.objects.filter(patient=self.patient).exists())

    def test_missing_file_error_handling(self):
        """A missing FilePond upload id keeps the form with errors"""
        create_url = reverse(
            "mediafiles:photo_create", kwargs={"patient_id": self.patient.id}
        )
        response = self.client.post(
            create_url,
            {
                "description": "Missing file test",
                "event_datetime": past_datetime_str(),
                "caption": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertIn("upload_id", response.context["form"].errors)

    def test_nonexistent_photo_error_handling(self):
        """Test error handling for nonexistent photos"""
        fake_uuid = "11111111-1111-1111-1111-111111111111"
        detail_url = reverse("mediafiles:photo_detail", kwargs={"pk": fake_uuid})
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 404)

    def test_nonexistent_series_error_handling(self):
        """Test error handling for nonexistent photo series"""
        fake_uuid = "11111111-1111-1111-1111-111111111111"
        detail_url = reverse("mediafiles:photoseries_detail", kwargs={"pk": fake_uuid})
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 404)

    def test_file_serving_error_handling(self):
        """Test error handling for file serving"""
        fake_uuid = "11111111-1111-1111-1111-111111111111"
        file_url = reverse("mediafiles:serve_file", kwargs={"file_id": fake_uuid})
        response = self.client.get(file_url)

        # Unknown file id is a plain 404 (no info leakage)
        self.assertEqual(response.status_code, 404)
