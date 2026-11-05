"""S5 R5: the media review-versus-export endpoint matrix (design D10).

Inline serving stays available to authorized viewers of drafts so a draft can
be reviewed and approved on screen; every file-download endpoint denies drafts
for all users and keeps serving finals exactly as today.
"""

import tempfile
import uuid
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.mediafiles.models import Photo, PhotoSeries, PhotoSeriesFile, VideoClip
from apps.patients.models import Patient

from .factories import (
    load_test_image_bytes,
    photo_original_dir,
    write_filepond_file,
)

User = get_user_model()

TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="mediafiles_draft_output_"))

VIDEO_CONTENT = b"\x00\x00\x00\x18ftypmp42" + b"synthetic video payload"


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class MediaDraftOutputGatingTests(TestCase):
    """R5: inline review stays open on drafts, downloads deny them for all."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("media-out-student", User.STUDENT)
        cls.doctor = create_profession_user("media-out-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Media Output Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    # Fixtures -----------------------------------------------------------

    def _event_fields(self, *, author, is_draft, promoted_at=None, promoted_by=None):
        """Shared event fields; a student acting user would force a draft."""
        return {
            "patient": self.patient,
            "description": "Mídia de teste da matriz de endpoints.",
            "event_datetime": timezone.now() - timedelta(hours=1),
            "is_draft": is_draft,
            "draft_promoted_at": promoted_at,
            "draft_promoted_by": promoted_by,
            "created_by": author,
            "updated_by": promoted_by or author,
        }

    def _create_photo(self, *, author, is_draft, promoted_at=None, promoted_by=None):
        photo = Photo.objects.create(
            file_id=str(uuid.uuid4()),
            original_filename="foto_matriz.jpg",
            file_size=1024,
            width=100,
            height=100,
            caption="",
            **self._event_fields(
                author=author,
                is_draft=is_draft,
                promoted_at=promoted_at,
                promoted_by=promoted_by,
            ),
        )
        write_filepond_file(
            photo_original_dir(photo.created_at),
            photo.file_id,
            ".jpg",
            load_test_image_bytes(),
        )
        thumb_dir = f"photos/{photo.created_at.strftime('%Y/%m')}/thumbnails"
        photo.thumbnail_path = f"{thumb_dir}/{photo.file_id}_thumb.jpg"
        photo.save(update_fields=["thumbnail_path"])
        write_filepond_file(
            thumb_dir, f"{photo.file_id}_thumb", ".jpg", load_test_image_bytes()
        )
        return photo

    def _create_series(self, *, author, is_draft, promoted_at=None, promoted_by=None):
        series = PhotoSeries.objects.create(
            caption="",
            **self._event_fields(
                author=author,
                is_draft=is_draft,
                promoted_at=promoted_at,
                promoted_by=promoted_by,
            ),
        )
        date_path = series.created_at.strftime("%Y/%m")
        for order in (1, 2):
            file_id = str(uuid.uuid4())
            thumb_dir = f"photo_series/{date_path}/thumbnails"
            PhotoSeriesFile.objects.create(
                photo_series=series,
                file_id=file_id,
                original_filename=f"serie_{order}.jpg",
                file_size=1024,
                width=100,
                height=100,
                order=order,
                thumbnail_path=f"{thumb_dir}/{file_id}_thumb.jpg",
            )
            write_filepond_file(
                f"photo_series/{date_path}/originals",
                file_id,
                ".jpg",
                load_test_image_bytes(),
            )
            write_filepond_file(
                thumb_dir, f"{file_id}_thumb", ".jpg", load_test_image_bytes()
            )
        return series

    def _create_video(self, *, author, is_draft, promoted_at=None, promoted_by=None):
        clip = VideoClip.objects.create(
            file_id=str(uuid.uuid4()),
            original_filename="video_matriz.mp4",
            file_size=len(VIDEO_CONTENT),
            duration=30,
            width=320,
            height=240,
            video_codec="h264",
            caption="",
            **self._event_fields(
                author=author,
                is_draft=is_draft,
                promoted_at=promoted_at,
                promoted_by=promoted_by,
            ),
        )
        write_filepond_file(
            f"videos/{clip.created_at.strftime('%Y/%m')}/originals",
            clip.file_id,
            ".mp4",
            VIDEO_CONTENT,
        )
        return clip

    def _get(self, user, url_name, **kwargs):
        self.client.force_login(user)
        return self.client.get(reverse(url_name, kwargs=kwargs))

    # Inline review endpoints: drafts stay viewable on screen ------------

    def test_photo_draft_original_is_served_inline(self):
        photo = self._create_photo(author=self.student, is_draft=True)

        for user in (self.student, self.doctor):
            with self.subTest(user=user.username):
                response = self._get(
                    user, "mediafiles:serve_file", file_id=photo.file_id
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_photo_draft_thumbnail_is_served_inline(self):
        photo = self._create_photo(author=self.student, is_draft=True)

        response = self._get(
            self.doctor, "mediafiles:serve_thumbnail", file_id=photo.file_id
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_series_draft_member_is_served_inline(self):
        series = self._create_series(author=self.student, is_draft=True)
        member = series.photoseriesfile_set.order_by("order").first()

        response = self._get(
            self.doctor, "mediafiles:serve_file", file_id=member.file_id
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_series_draft_member_thumbnail_is_served_inline(self):
        series = self._create_series(author=self.student, is_draft=True)
        member = series.photoseriesfile_set.order_by("order").first()

        response = self._get(
            self.doctor, "mediafiles:serve_thumbnail", file_id=member.file_id
        )

        self.assertEqual(response.status_code, 200)

    def test_video_draft_is_streamed_inline(self):
        clip = self._create_video(author=self.student, is_draft=True)

        response = self._get(
            self.doctor, "mediafiles:videoclip_stream", pk=clip.pk
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "video/mp4")

    def test_video_draft_original_is_served_inline(self):
        clip = self._create_video(author=self.student, is_draft=True)

        response = self._get(
            self.student, "mediafiles:serve_file", file_id=clip.file_id
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "video/mp4")

    # Download endpoints: drafts are denied for every user ----------------

    def test_photo_download_denies_drafts_for_all_users(self):
        photo = self._create_photo(author=self.student, is_draft=True)

        for user in (self.student, self.doctor):
            with self.subTest(user=user.username):
                response = self._get(
                    user, "mediafiles:photo_download", pk=photo.pk
                )
                self.assertEqual(response.status_code, 404)

    def test_series_download_denies_drafts_for_all_users(self):
        series = self._create_series(author=self.student, is_draft=True)

        for user in (self.student, self.doctor):
            with self.subTest(user=user.username):
                response = self._get(
                    user, "mediafiles:photoseries_download", pk=series.pk
                )
                self.assertEqual(response.status_code, 404)

    def test_video_download_denies_drafts_for_all_users(self):
        clip = self._create_video(author=self.student, is_draft=True)

        for user in (self.student, self.doctor):
            with self.subTest(user=user.username):
                response = self._get(
                    user, "mediafiles:videoclip_download", pk=clip.pk
                )
                self.assertEqual(response.status_code, 404)

    # Download endpoints: finals serve as today --------------------------

    def test_photo_download_serves_final_as_today(self):
        photo = self._create_photo(
            author=self.student,
            is_draft=False,
            promoted_at=timezone.now() - timedelta(hours=1),
            promoted_by=self.doctor,
        )

        response = self._get(self.doctor, "mediafiles:photo_download", pk=photo.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/octet-stream")
        self.assertIn('attachment; filename="foto_matriz.jpg"',
                      response["Content-Disposition"])

    def test_series_download_serves_final_as_today(self):
        """Finals keep the pre-existing FilePond ZIP contract (302 redirect)."""
        series = self._create_series(
            author=self.student,
            is_draft=False,
            promoted_at=timezone.now() - timedelta(hours=1),
            promoted_by=self.doctor,
        )

        response = self._get(
            self.doctor, "mediafiles:photoseries_download", pk=series.pk
        )

        self.assertNotEqual(response.status_code, 404)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("mediafiles:photoseries_detail", kwargs={"pk": series.pk}),
        )

    def test_video_download_serves_final_as_today(self):
        clip = self._create_video(
            author=self.student,
            is_draft=False,
            promoted_at=timezone.now() - timedelta(hours=1),
            promoted_by=self.doctor,
        )

        response = self._get(self.doctor, "mediafiles:videoclip_download", pk=clip.pk)

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
