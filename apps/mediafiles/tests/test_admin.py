"""
MediaFiles Admin Tests

Regression tests for the mediafiles admin around the current FilePond models
(``Photo``/``PhotoSeriesFile`` keep ``file_id``/``thumbnail_path``, neither has
a ``media_file`` FK): the Photo and PhotoSeries admin pages must render, and
their previews must point at each object's ``get_thumbnail_url()`` — the
tested ``mediafiles:serve_thumbnail`` route — instead of a raw ``/media/``
URL.

The emitted ``<img src>`` is fetched through the test client so the preview is
proven servable, not just string-compared. Empty references must keep the
existing placeholder texts.
"""

import re
import tempfile
import uuid
from pathlib import Path

from django.test import Client, TestCase, override_settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.mediafiles.models import Photo, PhotoSeries, PhotoSeriesFile

from .factories import (
    create_patient,
    create_photo_on_disk,
    load_test_image_bytes,
    write_filepond_file,
)

# FilePond storage helpers build paths with ``MEDIA_ROOT / "photos/..."``, so
# the override must be a Path (see test_views).
TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="mediafiles_admin_"))

IMG_SRC_RE = re.compile(r'<img src="([^"]+)"')

THUMBNAIL_URL_FRAGMENT = "thumbnail"


def emitted_img_srcs(response):
    """Return every ``<img src>`` value rendered in the response."""
    return IMG_SRC_RE.findall(response.content.decode())


def emitted_thumbnail_srcs(response):
    """Return the ``<img src>`` values that point at a served thumbnail."""
    return [src for src in emitted_img_srcs(response) if THUMBNAIL_URL_FRAGMENT in src]


def past_event_datetime(hours=2):
    """Return a recent past instant for ``Event.event_datetime``."""
    return timezone.now() - timezone.timedelta(hours=hours)


class MediaFilesAdminTestCase(TestCase):
    """Shared staff client and synthetic patient for the admin tests."""

    def setUp(self):
        self.client = Client()
        # Lifecycle-clean staff user (see apps.core.tests.test_lifecycle_guard_rail).
        self.staff = create_navigation_user(
            username="mediafiles-admin-staff",
            email="mediafiles-admin-staff@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.patient = create_patient(self.staff)
        self.client.force_login(self.staff)

    def change_url(self, obj):
        """Return the admin change-page URL for *obj*."""
        opts = obj._meta
        return reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk])

    def create_series(self, file_references):
        """Create a PhotoSeries with one PhotoSeriesFile per reference dict."""
        series = PhotoSeries.objects.create(
            caption="Série de teste",
            description="Série de teste",
            patient=self.patient,
            created_by=self.staff,
            updated_by=self.staff,
            event_datetime=past_event_datetime(),
        )
        series_files = [
            PhotoSeriesFile.objects.create(
                photo_series=series,
                order=order,
                original_filename="serie_foto.jpg",
                file_size=1024,
                width=100,
                height=100,
                **references,
            )
            for order, references in enumerate(file_references, start=1)
        ]
        return series, series_files


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PhotoAdminThumbnailPreviewTests(MediaFilesAdminTestCase):
    """Photo admin previews point at ``Photo.get_thumbnail_url()``."""

    def add_thumbnail_on_disk(self, photo):
        """Write the FilePond thumbnail for a photo and point the row at it."""
        thumb_dir = f"photos/{photo.created_at.strftime('%Y/%m')}/thumbnails"
        photo.thumbnail_path = f"{thumb_dir}/{photo.file_id}_thumb.jpg"
        photo.save(update_fields=["thumbnail_path"])
        write_filepond_file(
            thumb_dir, f"{photo.file_id}_thumb", ".jpg", load_test_image_bytes()
        )
        return photo.thumbnail_path

    def test_changelist_renders_and_preview_is_served(self):
        """The changelist renders and its small preview fetches 200."""
        photo = create_photo_on_disk(self.patient, self.staff)
        self.add_thumbnail_on_disk(photo)
        thumbnail_url = photo.get_thumbnail_url()
        self.assertIsNotNone(thumbnail_url)

        response = self.client.get(reverse("admin:mediafiles_photo_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(thumbnail_url, emitted_thumbnail_srcs(response))

        served = self.client.get(thumbnail_url)
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served["Content-Type"], "image/jpeg")

    def test_change_page_renders_and_large_preview_is_served(self):
        """The change page renders and its large preview fetches 200."""
        photo = create_photo_on_disk(self.patient, self.staff)
        self.add_thumbnail_on_disk(photo)
        thumbnail_url = photo.get_thumbnail_url()
        self.assertIsNotNone(thumbnail_url)

        response = self.client.get(self.change_url(photo))

        self.assertEqual(response.status_code, 200)
        self.assertIn(thumbnail_url, emitted_thumbnail_srcs(response))

        served = self.client.get(thumbnail_url)
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served["Content-Type"], "image/jpeg")

    def test_changelist_search_renders_with_original_filename(self):
        """The repaired search field queries the FilePond filename."""
        wanted = create_photo_on_disk(self.patient, self.staff, filename="busca.jpg")
        other = create_photo_on_disk(self.patient, self.staff, filename="outra.jpg")

        response = self.client.get(
            reverse("admin:mediafiles_photo_changelist"), {"q": "busca.jpg"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(wanted.pk))
        self.assertNotContains(response, str(other.pk))

    def test_change_page_renders_file_information(self):
        """The change page renders its file-information block (R3 display)."""
        photo = create_photo_on_disk(self.patient, self.staff)

        response = self.client.get(self.change_url(photo))

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn(photo.original_filename, body)
        self.assertIn(photo.get_secure_url(), body)

    def test_previews_without_reference_render_placeholders(self):
        """Empty ``file_id``/``thumbnail_path`` each render the placeholder."""
        cases = {
            "no-file-id-no-thumbnail-path": {"file_id": None, "thumbnail_path": ""},
            "file-id-without-thumbnail-path": {
                "file_id": str(uuid.uuid4()),
                "thumbnail_path": "",
            },
            "thumbnail-path-without-file-id": {
                "file_id": None,
                "thumbnail_path": "photos/2026/11/thumbnails/orphan_thumb.jpg",
            },
        }

        for label, references in cases.items():
            with self.subTest(label):
                photo = Photo.objects.create(
                    patient=self.patient,
                    created_by=self.staff,
                    updated_by=self.staff,
                    description=f"Photo {label}",
                    event_datetime=past_event_datetime(),
                    **references,
                )
                self.assertIsNone(photo.get_thumbnail_url())

                changelist = self.client.get(reverse("admin:mediafiles_photo_changelist"))
                self.assertEqual(changelist.status_code, 200)
                self.assertIn("No thumbnail", changelist.content.decode())
                self.assertEqual(emitted_thumbnail_srcs(changelist), [])

                change = self.client.get(self.change_url(photo))
                self.assertEqual(change.status_code, 200)
                self.assertIn("No thumbnail available", change.content.decode())
                self.assertEqual(emitted_thumbnail_srcs(change), [])


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PhotoSeriesAdminInlinePreviewTests(MediaFilesAdminTestCase):
    """PhotoSeries inline previews point at each file's thumbnail URL."""

    def add_thumbnail_on_disk(self, series_file):
        """Write the FilePond thumbnail for a series file and point it at it."""
        created_at = series_file.photo_series.created_at
        thumb_dir = f"photo_series/{created_at.strftime('%Y/%m')}/thumbnails"
        series_file.thumbnail_path = f"{thumb_dir}/{series_file.file_id}_thumb.jpg"
        series_file.save(update_fields=["thumbnail_path"])
        write_filepond_file(
            thumb_dir, f"{series_file.file_id}_thumb", ".jpg", load_test_image_bytes()
        )
        return series_file.thumbnail_path

    def test_change_page_renders_and_inline_preview_is_served(self):
        """The series change page renders and the inline preview fetches 200."""
        series, series_files = self.create_series(
            [{"file_id": str(uuid.uuid4())}, {"file_id": str(uuid.uuid4())}]
        )
        first_file = series_files[0]
        self.add_thumbnail_on_disk(first_file)
        thumbnail_url = first_file.get_thumbnail_url()
        self.assertIsNotNone(thumbnail_url)

        response = self.client.get(self.change_url(series))

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn(thumbnail_url, emitted_thumbnail_srcs(response))
        # The second row has no thumbnail_path yet and keeps the placeholder.
        self.assertIn("No thumbnail", body)

        served = self.client.get(thumbnail_url)
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served["Content-Type"], "image/jpeg")

    def test_inline_previews_without_reference_render_placeholders(self):
        """Empty ``file_id``/``thumbnail_path`` each render the placeholder."""
        cases = {
            "no-file-id-no-thumbnail-path": {"file_id": None, "thumbnail_path": ""},
            "file-id-without-thumbnail-path": {
                "file_id": str(uuid.uuid4()),
                "thumbnail_path": "",
            },
            "thumbnail-path-without-file-id": {
                "file_id": None,
                "thumbnail_path": "photo_series/2026/11/thumbnails/orphan_thumb.jpg",
            },
        }

        for label, references in cases.items():
            with self.subTest(label):
                # The first file stays reference-free too, so only the row
                # under test varies across the sub-cases.
                series, _series_files = self.create_series(
                    [{"file_id": str(uuid.uuid4())}, references]
                )

                response = self.client.get(self.change_url(series))

                self.assertEqual(response.status_code, 200)
                self.assertIn("No thumbnail", response.content.decode())
                self.assertEqual(emitted_thumbnail_srcs(response), [])

    def test_series_model_getter_raises_for_thumbnail_path_without_file_id(self):
        """D4: the series getter is unguarded, hence the admin-side guard."""
        _, series_files = self.create_series(
            [
                {
                    "file_id": None,
                    "thumbnail_path": "photo_series/2026/11/thumbnails/orphan_thumb.jpg",
                }
            ]
        )

        with self.assertRaises(NoReverseMatch):
            series_files[0].get_thumbnail_url()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PhotoSeriesAdminPrimaryThumbnailTests(MediaFilesAdminTestCase):
    """Primary series previews guard a partial reference on the first file."""

    ORPHAN_THUMBNAIL_PATH = "photo_series/2026/11/thumbnails/orphan_thumb.jpg"

    def test_primary_previews_render_placeholder_for_first_file_path_without_file_id(
        self,
    ):
        """A thumbnail path without file ID on the first row keeps both pages 200."""
        series, series_files = self.create_series(
            [{"file_id": None, "thumbnail_path": self.ORPHAN_THUMBNAIL_PATH}]
        )
        self.assertEqual(series.get_photos().first().pk, series_files[0].pk)

        changelist = self.client.get(
            reverse("admin:mediafiles_photoseries_changelist")
        )
        self.assertEqual(changelist.status_code, 200)
        self.assertIn("No photos", changelist.content.decode())
        self.assertEqual(emitted_thumbnail_srcs(changelist), [])

        change = self.client.get(self.change_url(series))
        self.assertEqual(change.status_code, 200)
        self.assertIn("No photos available", change.content.decode())
        self.assertEqual(emitted_thumbnail_srcs(change), [])

    def test_primary_preview_uses_the_first_file_reference(self):
        """Only the first row decides the primary preview, not a later one."""
        series, series_files = self.create_series(
            [
                {"file_id": None, "thumbnail_path": self.ORPHAN_THUMBNAIL_PATH},
                {"file_id": str(uuid.uuid4()), "thumbnail_path": "photo_series/x.jpg"},
            ]
        )
        second_file = series_files[1]

        changelist = self.client.get(
            reverse("admin:mediafiles_photoseries_changelist")
        )
        self.assertEqual(changelist.status_code, 200)
        self.assertIn("No photos", changelist.content.decode())

        change = self.client.get(self.change_url(series))
        self.assertEqual(change.status_code, 200)
        self.assertIn("No photos available", change.content.decode())
        # The reference-free first row shadows the valid second row in the
        # primary preview; the inline still renders the second row's URL.
        self.assertIn(second_file.get_thumbnail_url(), emitted_thumbnail_srcs(change))
