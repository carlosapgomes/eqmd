"""
MediaFiles View Tests

Comprehensive tests for media file views including photo CRUD operations,
permissions, security, and file handling.

All fixtures use the current FilePond-based models: Photo/PhotoSeriesFile/
VideoClip store FilePond ``file_id`` metadata and their originals live under
``<media_type>/YYYY/MM/originals/<file_id>.<ext>`` (see
``apps/mediafiles/tests/factories.py``). Hospital was removed in the
single-hospital refactor and no longer exists anywhere in the codebase.
"""

import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.mediafiles.models import Photo, PhotoSeries, PhotoSeriesFile, VideoClip

from .factories import (
    create_patient,
    create_photo_on_disk,
    create_user,
    create_videoclip_on_disk,
    load_test_image_bytes,
    photo_original_dir,
    write_filepond_file,
)

User = get_user_model()

# PhotoCreateFormNew builds paths with ``MEDIA_ROOT / "photos/..."``, so the
# override must be a Path (the string MEDIA_ROOT in test_settings would fail).
TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="mediafiles_views_"))

LOGIN_URL = "/accounts/login/"


def grant_permissions(user, *names):
    """Grant Django model permissions to a user (synthetic test fixture)."""
    for name in names:
        app_label, codename = name.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app_label, codename=codename)
        )


FULL_EVENT_PERMS = (
    "events.add_event",
    "events.view_event",
    "events.change_event",
    "events.delete_event",
    "patients.view_patient",
)


def past_datetime_str(hours=2):
    """HTML5 ``datetime-local`` value for a recent past instant."""
    return timezone.localtime(
        timezone.now() - timezone.timedelta(hours=hours)
    ).strftime("%Y-%m-%dT%H:%M")


def add_thumbnail_on_disk(photo, content=None):
    """Write the FilePond thumbnail for a photo and point the row at it.

    Returns the written absolute path. The thumbnail lives under
    ``photos/YYYY/MM/thumbnails/<file_id>_thumb.jpg``.
    """
    content = load_test_image_bytes() if content is None else content
    thumb_dir = f"photos/{photo.created_at.strftime('%Y/%m')}/thumbnails"
    photo.thumbnail_path = f"{thumb_dir}/{photo.file_id}_thumb.jpg"
    photo.save(update_fields=["thumbnail_path"])
    return write_filepond_file(thumb_dir, f"{photo.file_id}_thumb", ".jpg", content)


def create_series_with_file_on_disk(patient, user, **kwargs):
    """Create a PhotoSeries whose first PhotoSeriesFile original is on disk."""
    series = PhotoSeries.objects.create(
        caption=kwargs.pop("caption", "Test series"),
        description=kwargs.pop("description", "Test series description"),
        patient=patient,
        created_by=user,
        updated_by=user,
        event_datetime=timezone.now() - timezone.timedelta(hours=1),
        **kwargs,
    )
    content = load_test_image_bytes()
    file_id = str(uuid.uuid4())
    PhotoSeriesFile.objects.create(
        photo_series=series,
        file_id=file_id,
        original_filename="serie_foto.jpg",
        file_size=len(content),
        width=100,
        height=100,
        order=1,
    )
    write_filepond_file(
        f"photo_series/{series.created_at.strftime('%Y/%m')}/originals",
        file_id,
        ".jpg",
        content,
    )
    return series


class MediaFileServingViewTests(TestCase):
    """Tests for the FilePond secure serving endpoints."""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = create_user(username="testuser")
        self.patient = create_patient(self.user)
        self.client.force_login(self.user)

    def test_media_file_serving_ok(self):
        """A Photo with its FilePond original on disk is served securely."""
        photo = create_photo_on_disk(self.patient, self.user, filename="foto.jpg")

        url = reverse("mediafiles:serve_file", kwargs={"file_id": photo.file_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertIn('inline; filename="foto.jpg"', response["Content-Disposition"])
        self.assertEqual(response["Content-Length"], str(photo.file_size))

    def test_media_file_serving_unknown_id_404(self):
        """An unknown FilePond file id is not leaked (404, no 403/500)."""
        url = reverse(
            "mediafiles:serve_file",
            kwargs={"file_id": "11111111-1111-1111-1111-111111111111"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_media_file_serving_missing_on_disk_404(self):
        """A Photo without its original on disk is not served (404)."""
        photo = Photo.objects.create(
            file_id=str(uuid.uuid4()),
            original_filename="missing.jpg",
            file_size=10,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="Missing file",
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
        )

        url = reverse("mediafiles:serve_file", kwargs={"file_id": photo.file_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_media_file_serving_anonymous_redirect(self):
        """Anonymous users are redirected to login before serving."""
        photo = create_photo_on_disk(self.patient, self.user)
        self.client.logout()

        url = reverse("mediafiles:serve_file", kwargs={"file_id": photo.file_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(LOGIN_URL, response.url)

    def test_thumbnail_serving_ok(self):
        """A Photo with its FilePond thumbnail on disk serves image/jpeg."""
        photo = create_photo_on_disk(self.patient, self.user)
        add_thumbnail_on_disk(photo)

        url = reverse("mediafiles:serve_thumbnail", kwargs={"file_id": photo.file_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")

    def test_thumbnail_serving_missing_404(self):
        """A Photo without a stored thumbnail path returns 404 (no fallback)."""
        photo = create_photo_on_disk(self.patient, self.user)

        url = reverse("mediafiles:serve_thumbnail", kwargs={"file_id": photo.file_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_video_serving_ok(self):
        """A VideoClip with its FilePond original on disk is streamed."""
        clip = create_videoclip_on_disk(self.patient, self.user)

        url = reverse("mediafiles:serve_file", kwargs={"file_id": clip.file_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "video/mp4")
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_photoseries_file_serving_ok(self):
        """A PhotoSeriesFile original is served from the series layout."""
        series = create_series_with_file_on_disk(self.patient, self.user)
        series_file = series.photoseriesfile_set.first()

        url = reverse("mediafiles:serve_file", kwargs={"file_id": series_file.file_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PhotoViewTests(TestCase):
    """Comprehensive tests for photo views."""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test user with permissions
        self.user = create_user(username="testuser")
        grant_permissions(self.user, *FULL_EVENT_PERMS)

        self.patient = create_patient(self.user)
        self.client.force_login(self.user)

    def create_temp_upload(self, filename="foto.jpg", content=None):
        """Create a FilePond TemporaryUpload row and return its upload_id."""
        import shortuuid
        from django_drf_filepond.models import TemporaryUpload

        content = load_test_image_bytes() if content is None else content
        upload_id = shortuuid.uuid()
        TemporaryUpload.objects.create(
            upload_id=upload_id,
            upload_name=filename,
            upload_type="F",
            file=SimpleUploadedFile(filename, content, content_type="image/jpeg"),
        )
        return upload_id

    def post_photo_form(self, upload_id, description="Test photo", **extra):
        """POST the FilePond photo-create form with a valid past datetime."""
        data = {
            "description": description,
            "event_datetime": past_datetime_str(),
            "caption": extra.pop("caption", "Test caption"),
            "upload_id": upload_id,
        }
        data.update(extra)
        return self.client.post(
            reverse(
                "mediafiles:photo_create",
                kwargs={"patient_id": self.patient.pk},
            ),
            data,
        )

    def test_photo_create_view_get(self):
        """Test photo create view GET request"""
        url = reverse("mediafiles:photo_create", kwargs={"patient_id": self.patient.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nova Foto")
        self.assertContains(response, self.patient.name)

    def test_photo_create_view_post_valid(self):
        """Test photo create view POST request with a valid FilePond upload"""
        upload_id = self.create_temp_upload("test_image.jpg")
        response = self.post_photo_form(upload_id, description="Test photo description")

        # Redirect to the patient timeline on success
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse(
                "apps.patients:patient_events_timeline",
                kwargs={"patient_id": self.patient.pk},
            ),
        )

        photo = Photo.objects.get(patient=self.patient)
        self.assertEqual(photo.description, "Test photo description")
        self.assertEqual(photo.original_filename, "test_image.jpg")
        self.assertEqual(photo.created_by, self.user)
        self.assertEqual(photo.event_type, 3)  # Event.PHOTO_EVENT

        # Original file is stored under photos/YYYY/MM/originals/<file_id>.jpg
        stored = (
            Path(settings.MEDIA_ROOT)
            / photo_original_dir(photo.created_at)
            / f"{photo.file_id}.jpg"
        )
        self.assertTrue(stored.exists(), f"Original should exist at {stored}")

        # And the stored file is servable
        serve_url = reverse("mediafiles:serve_file", kwargs={"file_id": photo.file_id})
        serve_response = self.client.get(serve_url)
        self.assertEqual(serve_response.status_code, 200)
        self.assertEqual(serve_response["Content-Type"], "image/jpeg")

    def test_photo_create_view_post_invalid_upload(self):
        """An unknown FilePond upload id keeps the form with errors (200)."""
        response = self.post_photo_form("a" * 22, description="Invalid upload test")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertIn("upload_id", response.context["form"].errors)

    def test_photo_create_view_post_missing_upload(self):
        """A missing FilePond upload id keeps the form with errors (200)."""
        url = reverse("mediafiles:photo_create", kwargs={"patient_id": self.patient.pk})
        response = self.client.post(
            url,
            {
                "description": "Missing upload",
                "event_datetime": past_datetime_str(),
                "caption": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertIn("upload_id", response.context["form"].errors)

    def test_photo_create_view_post_non_image(self):
        """A non-image FilePond upload is rejected by the form."""
        upload_id = self.create_temp_upload("malicious.txt")
        response = self.post_photo_form(upload_id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertIn("upload_id", response.context["form"].errors)
        self.assertFalse(Photo.objects.filter(patient=self.patient).exists())

    def test_photo_detail_view(self):
        """Test photo detail view"""
        photo = create_photo_on_disk(
            self.patient, self.user, description="Detail photo"
        )

        url = reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail photo")
        self.assertContains(response, photo.original_filename)
        # Secure rendering: the FilePond serve URL is used for the image
        self.assertContains(
            response,
            reverse("mediafiles:serve_file", kwargs={"file_id": photo.file_id}),
        )

    def test_photo_update_view_get(self):
        """Test photo update view GET request"""
        photo = create_photo_on_disk(self.patient, self.user)

        url = reverse("mediafiles:photo_update", kwargs={"pk": photo.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Editar Foto")

    def test_photo_update_view_post(self):
        """Test photo update view POST request"""
        photo = create_photo_on_disk(
            self.patient, self.user, description="Original description"
        )

        url = reverse("mediafiles:photo_update", kwargs={"pk": photo.pk})
        data = {
            "description": "Updated description",
            "event_datetime": timezone.localtime(photo.event_datetime).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "caption": "Updated caption",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        photo.refresh_from_db()
        self.assertEqual(photo.description, "Updated description")
        self.assertEqual(photo.caption, "Updated caption")
        self.assertEqual(photo.updated_by, self.user)

    def test_photo_delete_view_get(self):
        """Test photo delete view GET request"""
        photo = create_photo_on_disk(self.patient, self.user)

        url = reverse("mediafiles:photo_delete", kwargs={"pk": photo.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirmar Exclusão")
        self.assertContains(response, photo.description)

    def test_photo_delete_view_post(self):
        """Test photo delete view POST request (soft delete)"""
        photo = create_photo_on_disk(self.patient, self.user)
        photo_id = photo.pk

        url = reverse("mediafiles:photo_delete", kwargs={"pk": photo.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        # Soft delete: the row is flagged with is_deleted/deleted_at and
        # stays visible through the custom Photo manager
        deleted = Photo.objects.get(pk=photo_id)
        self.assertTrue(deleted.is_deleted)
        self.assertIsNotNone(deleted.deleted_at)

    def test_photo_download_view(self):
        """Test photo download view"""
        photo = create_photo_on_disk(self.patient, self.user, filename="download.jpg")

        url = reverse("mediafiles:photo_download", kwargs={"pk": photo.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/octet-stream")
        self.assertIn(
            'attachment; filename="download.jpg"', response["Content-Disposition"]
        )

    def test_photo_download_missing_file_404(self):
        """Download of a photo whose original is missing returns 404."""
        photo = Photo.objects.create(
            file_id=str(uuid.uuid4()),
            original_filename="missing.jpg",
            file_size=10,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="Missing file",
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
        )

        url = reverse("mediafiles:photo_download", kwargs={"pk": photo.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_photo_views_require_login(self):
        """Anonymous users are not allowed into photo views.

        Detail/update/delete/download redirect to login (302). The create
        view's ``dispatch`` runs ``can_access_patient`` before the login
        check and raises PermissionDenied, so anonymous create requests are
        rejected with 403 (current production contract, pinned).
        """
        photo = create_photo_on_disk(self.patient, self.user)
        self.client.logout()

        redirect_urls = [
            reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk}),
            reverse("mediafiles:photo_update", kwargs={"pk": photo.pk}),
            reverse("mediafiles:photo_delete", kwargs={"pk": photo.pk}),
            reverse("mediafiles:photo_download", kwargs={"pk": photo.pk}),
        ]
        for url in redirect_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(LOGIN_URL, response.url)

        create_url = reverse(
            "mediafiles:photo_create",
            kwargs={"patient_id": self.patient.pk},
        )
        self.assertEqual(self.client.get(create_url).status_code, 403)

    def test_photo_views_require_permissions(self):
        """Test that photo views return 403 without the events permissions"""
        # Create user without permissions (lifecycle-navigation-ready)
        no_perms_user = create_user(username="noperms")
        self.client.force_login(no_perms_user)

        photo = create_photo_on_disk(self.patient, self.user)

        urls = [
            reverse(
                "mediafiles:photo_create",
                kwargs={"patient_id": self.patient.pk},
            ),
            reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk}),
            reverse("mediafiles:photo_update", kwargs={"pk": photo.pk}),
            reverse("mediafiles:photo_delete", kwargs={"pk": photo.pk}),
            reverse("mediafiles:photo_download", kwargs={"pk": photo.pk}),
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    def test_photo_edit_delete_restricted_to_creator(self):
        """Non-creators with change/delete perms are denied edit/delete."""
        other_user = create_user(username="other")
        grant_permissions(other_user, *FULL_EVENT_PERMS)
        photo = create_photo_on_disk(self.patient, self.user)

        self.client.force_login(other_user)

        update_url = reverse("mediafiles:photo_update", kwargs={"pk": photo.pk})
        self.assertEqual(self.client.get(update_url).status_code, 403)

        delete_url = reverse("mediafiles:photo_delete", kwargs={"pk": photo.pk})
        self.assertEqual(self.client.get(delete_url).status_code, 403)

    def test_photo_detail_cross_user_view_allowed(self):
        """Every authenticated user with view_event may view a photo."""
        other_user = create_user(username="viewer")
        grant_permissions(other_user, "events.view_event")
        photo = create_photo_on_disk(self.patient, self.user)

        self.client.force_login(other_user)
        url = reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # can_edit/can_delete flags are False for the non-creator
        self.assertFalse(response.context["can_edit"])
        self.assertFalse(response.context["can_delete"])

    def test_photo_file_handling(self):
        """Photo originals are stored and servable (FilePond layout)."""
        photo = create_photo_on_disk(self.patient, self.user, filename="foto.jpg")

        self.assertTrue(photo.file_id)
        self.assertEqual(photo.original_filename, "foto.jpg")
        self.assertGreater(photo.file_size, 0)

        stored = (
            Path(settings.MEDIA_ROOT)
            / photo_original_dir(photo.created_at)
            / f"{photo.file_id}.jpg"
        )
        self.assertTrue(stored.exists())
        self.assertGreater(stored.stat().st_size, 0)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PhotoSeriesViewTests(TestCase):
    """Tests for photo series views."""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        self.user = create_user(username="testuser")
        grant_permissions(self.user, *FULL_EVENT_PERMS)

        self.patient = create_patient(self.user)
        self.client.force_login(self.user)

    def create_temp_uploads(self, filenames):
        """Create FilePond TemporaryUpload rows; return comma-joined ids."""
        import shortuuid
        from django_drf_filepond.models import TemporaryUpload

        upload_ids = []
        for index, filename in enumerate(filenames):
            upload_id = shortuuid.uuid()
            TemporaryUpload.objects.create(
                upload_id=upload_id,
                upload_name=filename,
                upload_type="F",
                file=SimpleUploadedFile(
                    filename,
                    load_test_image_bytes(),
                    content_type="image/jpeg",
                ),
            )
            upload_ids.append(upload_id)
        return ",".join(upload_ids)

    def test_photo_series_upload_view_get(self):
        """Test photo series upload view GET request"""
        url = reverse(
            "mediafiles:photoseries_create",
            kwargs={"patient_id": self.patient.pk},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nova Série de Fotos")
        self.assertContains(response, self.patient.name)

    def test_photo_series_upload_view_post(self):
        """Test photo series upload view POST with multiple FilePond files"""
        upload_ids = self.create_temp_uploads(
            ["series_a.jpg", "series_b.jpg", "series_c.jpg"]
        )

        url = reverse(
            "mediafiles:photoseries_create",
            kwargs={"patient_id": self.patient.pk},
        )
        response = self.client.post(
            url,
            {
                "description": "Series upload test",
                "event_datetime": past_datetime_str(),
                "caption": "Series caption",
                "upload_ids": upload_ids,
            },
        )

        self.assertEqual(response.status_code, 302)

        series = PhotoSeries.objects.get(patient=self.patient)
        self.assertEqual(series.description, "Series upload test")
        self.assertEqual(series.get_photo_count(), 3)

        # Explicit order is preserved (1-based)
        ordered = series.get_ordered_photos()
        self.assertEqual([sf.order for sf in ordered], [1, 2, 3])

        # Each series file original is stored and servable
        for series_file in ordered:
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

    def test_photo_series_upload_rejects_unknown_upload(self):
        """An unknown FilePond upload id rejects the whole batch."""
        url = reverse(
            "mediafiles:photoseries_create",
            kwargs={"patient_id": self.patient.pk},
        )
        response = self.client.post(
            url,
            {
                "description": "Invalid series",
                "event_datetime": past_datetime_str(),
                "caption": "",
                "upload_ids": "b" * 22,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertIn("upload_ids", response.context["form"].errors)
        self.assertFalse(PhotoSeries.objects.filter(patient=self.patient).exists())

    def test_photo_series_detail_view(self):
        """Test photo series detail view with ordered photos"""
        series = create_series_with_file_on_disk(
            self.patient, self.user, description="Detail series"
        )

        url = reverse("mediafiles:photoseries_detail", kwargs={"pk": series.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail series")
        self.assertContains(response, "fotos")
        self.assertContains(response, "photo-gallery")

    def test_photo_series_update_view(self):
        """Test photo series update view GET and POST"""
        series = create_series_with_file_on_disk(
            self.patient, self.user, description="Original series"
        )

        url = reverse("mediafiles:photoseries_update", kwargs={"pk": series.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Editar Série de Fotos")

        response = self.client.post(
            url,
            {
                "description": "Updated series",
                "event_datetime": timezone.localtime(series.event_datetime).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "caption": "Updated caption",
            },
        )
        self.assertEqual(response.status_code, 302)
        series.refresh_from_db()
        self.assertEqual(series.description, "Updated series")
        self.assertEqual(series.caption, "Updated caption")

    def test_photo_series_delete_view(self):
        """Test photo series delete view GET and POST"""
        series = create_series_with_file_on_disk(
            self.patient, self.user, description="Delete series"
        )
        series_id = series.pk

        url = reverse("mediafiles:photoseries_delete", kwargs={"pk": series.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirmar Exclusão")

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        # Soft delete: the row is flagged with is_deleted (visible through
        # the custom PhotoSeries manager)
        self.assertTrue(PhotoSeries.objects.get(pk=series_id).is_deleted)

    def test_photo_series_zip_download_current_contract(self):
        """ZIP download follows the current FilePond behavior (302 redirect).

        ``photoseries_download`` still reads the removed
        ``PhotoSeriesFile.media_file`` relation; the exception path redirects
        to the series detail page. Pinned as the current contract; the
        FilePond ZIP implementation is a production-gap candidate for the
        planner (no production edit without approval).
        """
        series = create_series_with_file_on_disk(
            self.patient, self.user, description="Download series"
        )

        url = reverse("mediafiles:photoseries_download", kwargs={"pk": series.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("mediafiles:photoseries_detail", kwargs={"pk": series.pk}),
        )

    def test_photo_series_views_require_login(self):
        """Anonymous users are not allowed into photo series views.

        Detail/update/delete redirect to login (302); the create view's
        ``dispatch`` rejects anonymous requests with 403 (current contract).
        """
        series = create_series_with_file_on_disk(self.patient, self.user)
        self.client.logout()

        redirect_urls = [
            reverse("mediafiles:photoseries_detail", kwargs={"pk": series.pk}),
            reverse("mediafiles:photoseries_update", kwargs={"pk": series.pk}),
            reverse("mediafiles:photoseries_delete", kwargs={"pk": series.pk}),
        ]
        for url in redirect_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(LOGIN_URL, response.url)

        create_url = reverse(
            "mediafiles:photoseries_create",
            kwargs={"patient_id": self.patient.pk},
        )
        self.assertEqual(self.client.get(create_url).status_code, 403)

    def test_photo_series_views_require_permissions(self):
        """Photo series views return 403 without the events permissions"""
        no_perms_user = create_user(username="noperms")
        self.client.force_login(no_perms_user)

        series = create_series_with_file_on_disk(self.patient, self.user)

        urls = [
            reverse(
                "mediafiles:photoseries_create",
                kwargs={"patient_id": self.patient.pk},
            ),
            reverse("mediafiles:photoseries_detail", kwargs={"pk": series.pk}),
            reverse("mediafiles:photoseries_update", kwargs={"pk": series.pk}),
            reverse("mediafiles:photoseries_delete", kwargs={"pk": series.pk}),
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class VideoClipViewTests(TestCase):
    """Tests for video clip views."""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        self.user = create_user(username="testuser")
        grant_permissions(self.user, *FULL_EVENT_PERMS)

        self.patient = create_patient(self.user)
        self.client.force_login(self.user)

    def test_video_upload_view_get(self):
        """Test video upload view GET request"""
        url = reverse(
            "mediafiles:videoclip_create", kwargs={"patient_id": self.patient.pk}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Novo Vídeo")

    def test_video_detail_view(self):
        """Test video detail view"""
        clip = create_videoclip_on_disk(
            self.patient, self.user, description="Detail video"
        )

        url = reverse("mediafiles:videoclip_detail", kwargs={"pk": clip.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail video")
        self.assertContains(response, "video-player")
        self.assertContains(response, "fullscreenModal")

    def test_video_update_view(self):
        """Test video update view GET and POST (metadata only)"""
        clip = create_videoclip_on_disk(
            self.patient, self.user, description="Original video"
        )

        url = reverse("mediafiles:videoclip_update", kwargs={"pk": clip.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Editar Vídeo")

        response = self.client.post(
            url,
            {
                "description": "Updated video",
                "event_datetime": timezone.localtime(clip.event_datetime).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "caption": "Updated caption",
            },
        )
        self.assertEqual(response.status_code, 302)
        clip.refresh_from_db()
        self.assertEqual(clip.description, "Updated video")

    def test_video_delete_view(self):
        """Test video delete view GET and POST"""
        clip = create_videoclip_on_disk(
            self.patient, self.user, description="Delete video"
        )
        clip_id = clip.pk

        url = reverse("mediafiles:videoclip_delete", kwargs={"pk": clip.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirmar Exclusão")

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        # Soft delete: the row is flagged with is_deleted (visible through
        # the custom VideoClip manager)
        self.assertTrue(VideoClip.objects.get(pk=clip_id).is_deleted)

    def test_video_stream_view(self):
        """Test video stream view serves the FilePond original"""
        clip = create_videoclip_on_disk(self.patient, self.user)

        url = reverse("mediafiles:videoclip_stream", kwargs={"pk": clip.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "video/mp4")
        self.assertEqual(response["Accept-Ranges"], "bytes")

    def test_video_stream_missing_file_404(self):
        """Streaming a video whose original is missing returns 404."""
        clip = VideoClip.objects.create(
            file_id=str(uuid.uuid4()),
            original_filename="missing.mp4",
            file_size=10,
            duration=30,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            description="Missing video",
            event_datetime=timezone.now() - timezone.timedelta(hours=1),
        )

        url = reverse("mediafiles:videoclip_stream", kwargs={"pk": clip.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_video_download_view(self):
        """Test video download view"""
        clip = create_videoclip_on_disk(
            self.patient, self.user, filename="download.mp4"
        )

        url = reverse("mediafiles:videoclip_download", kwargs={"pk": clip.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/octet-stream")
        self.assertIn(
            'attachment; filename="download.mp4"', response["Content-Disposition"]
        )

    def test_video_views_require_login(self):
        """Anonymous users are not allowed into video views.

        Detail/update/delete/stream/download redirect to login (302); the
        create view's ``dispatch`` rejects anonymous requests with 403
        (current contract).
        """
        clip = create_videoclip_on_disk(self.patient, self.user)
        self.client.logout()

        redirect_urls = [
            reverse("mediafiles:videoclip_detail", kwargs={"pk": clip.pk}),
            reverse("mediafiles:videoclip_update", kwargs={"pk": clip.pk}),
            reverse("mediafiles:videoclip_delete", kwargs={"pk": clip.pk}),
            reverse("mediafiles:videoclip_stream", kwargs={"pk": clip.pk}),
            reverse("mediafiles:videoclip_download", kwargs={"pk": clip.pk}),
        ]
        for url in redirect_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(LOGIN_URL, response.url)

        create_url = reverse(
            "mediafiles:videoclip_create",
            kwargs={"patient_id": self.patient.pk},
        )
        self.assertEqual(self.client.get(create_url).status_code, 403)

    def test_video_views_require_permissions(self):
        """Video views return 403 without the events permissions"""
        no_perms_user = create_user(username="noperms")
        self.client.force_login(no_perms_user)

        clip = create_videoclip_on_disk(self.patient, self.user)

        urls = [
            reverse(
                "mediafiles:videoclip_create",
                kwargs={"patient_id": self.patient.pk},
            ),
            reverse("mediafiles:videoclip_detail", kwargs={"pk": clip.pk}),
            reverse("mediafiles:videoclip_update", kwargs={"pk": clip.pk}),
            reverse("mediafiles:videoclip_delete", kwargs={"pk": clip.pk}),
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)


class SecurityViewTests(TestCase):
    """Tests for view security and access control."""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test users (lifecycle-navigation-ready)
        self.user1 = create_user(username="user1")
        self.user2 = create_user(username="user2")

        self.patient1 = create_patient(self.user1, name="Patient 1")
        self.patient2 = create_patient(self.user2, name="Patient 2")

    def test_cross_user_media_access_denied_without_permission(self):
        """A user without view_event cannot open another user's photo."""
        photo = create_photo_on_disk(self.patient1, self.user1)

        self.client.force_login(self.user2)
        url = reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_cross_user_media_access_with_permission(self):
        """Every authenticated user with view_event may access a photo.

        ``can_access_patient`` returns True for every authenticated user
        (documented current permission contract), so the Django
        ``events.view_event`` permission is the enforcing gate.
        """
        grant_permissions(self.user2, "events.view_event")
        photo = create_photo_on_disk(self.patient1, self.user1)

        self.client.force_login(self.user2)
        url = reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_access_denied(self):
        """Anonymous users are redirected to login for photo views."""
        photo = create_photo_on_disk(self.patient1, self.user1)

        url = reverse("mediafiles:photo_detail", kwargs={"pk": photo.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(LOGIN_URL, response.url)

    def test_file_serving_security(self):
        """Serving endpoints keep secure headers and hide missing files."""
        photo = create_photo_on_disk(self.patient1, self.user1)
        self.client.force_login(self.user1)

        serve_url = reverse("mediafiles:serve_file", kwargs={"file_id": photo.file_id})
        response = self.client.get(serve_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertIn("Cache-Control", response)

        # Enumeration attempt on a missing file id is a plain 404
        unknown_url = reverse(
            "mediafiles:serve_file",
            kwargs={"file_id": "11111111-1111-1111-1111-111111111111"},
        )
        response = self.client.get(unknown_url)
        self.assertEqual(response.status_code, 404)


class PhotoEventCardTemplateTests(TestCase):
    """Tests for photo-related template rendering (event card + modal)."""

    def setUp(self):
        """Set up test data"""
        self.user = create_user(username="testuser")
        self.patient = create_patient(self.user)

    def test_photo_event_card_template_renders(self):
        """Test that photo event card template renders without errors"""
        photo = create_photo_on_disk(
            self.patient,
            self.user,
            description="Test photo description",
        )
        photo.caption = "Test photo caption"
        photo.save(update_fields=["caption"])

        event_data = {
            "event": photo,
            "can_edit": True,
            "can_delete": True,
            "excerpt": photo.description[:100],
        }

        template_content = render_to_string(
            "events/partials/event_card_photo.html",
            {
                "event": photo,
                "event_data": event_data,
                "user": self.user,
            },
        )

        # Check that key elements are present
        self.assertIn("photo-event-content", template_content)
        self.assertIn("photo-thumbnail-container", template_content)
        self.assertIn("Test photo description", template_content)
        self.assertIn("Test photo caption", template_content)
        self.assertIn("photo-modal-trigger", template_content)
        self.assertIn('data-bs-target="#photoModal"', template_content)
        # The card renders the secure serving URL for the FilePond file
        self.assertIn(
            reverse("mediafiles:serve_file", kwargs={"file_id": photo.file_id}),
            template_content,
        )

    def test_photo_modal_template_renders(self):
        """Test that photo modal template renders without errors"""
        template_content = render_to_string("mediafiles/partials/photo_modal.html")

        # Check that key modal elements are present
        self.assertIn('id="photoModal"', template_content)
        self.assertIn("photoModalImage", template_content)
        self.assertIn("photoZoomIn", template_content)
        self.assertIn("photoZoomOut", template_content)
        self.assertIn("photoZoomReset", template_content)
        self.assertIn("photoDownloadBtn", template_content)
        self.assertIn("photoModalContainer", template_content)
        self.assertIn("photoModalLoading", template_content)

    def test_photo_event_card_template_with_missing_thumbnail(self):
        """Photo card falls back to the placeholder without a thumbnail."""
        photo = create_photo_on_disk(self.patient, self.user)

        event_data = {
            "event": photo,
            "can_edit": True,
            "can_delete": True,
            "excerpt": photo.description[:100],
        }

        template_content = render_to_string(
            "events/partials/event_card_photo.html",
            {
                "event": photo,
                "event_data": event_data,
                "user": self.user,
            },
        )

        # No thumbnail_path -> placeholder icon instead of the image wrapper
        self.assertIn("photo-placeholder", template_content)
        self.assertIn("bi bi-image", template_content)
        self.assertNotIn("photo-thumbnail-wrapper", template_content)

    def test_photo_event_card_template_with_thumbnail(self):
        """Photo card renders the thumbnail wrapper when a thumbnail exists."""
        photo = create_photo_on_disk(self.patient, self.user)
        photo.thumbnail_path = (
            f"photos/{photo.created_at.strftime('%Y/%m')}/thumbnails/"
            f"{photo.file_id}_thumb.jpg"
        )
        photo.save(update_fields=["thumbnail_path"])

        event_data = {
            "event": photo,
            "can_edit": True,
            "can_delete": True,
            "excerpt": photo.description[:100],
        }

        template_content = render_to_string(
            "events/partials/event_card_photo.html",
            {
                "event": photo,
                "event_data": event_data,
                "user": self.user,
            },
        )

        self.assertIn("photo-thumbnail-wrapper", template_content)
        self.assertIn("photo-overlay", template_content)
        self.assertIn("bi bi-camera", template_content)

    def test_photo_event_card_template_permissions(self):
        """Photo event card hides edit actions without can_edit."""
        photo = create_photo_on_disk(self.patient, self.user)

        event_data = {
            "event": photo,
            "can_edit": False,
            "can_delete": False,
            "excerpt": photo.description[:100],
        }

        template_content = render_to_string(
            "events/partials/event_card_photo.html",
            {
                "event": photo,
                "event_data": event_data,
                "user": self.user,
            },
        )

        # Edit button should not be present
        self.assertNotIn("btn-outline-warning", template_content)

        # View and download buttons should still be present
        self.assertIn("photo-modal-trigger", template_content)
        self.assertIn("btn-outline-secondary", template_content)
