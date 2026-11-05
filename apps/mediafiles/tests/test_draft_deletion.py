"""S5 R4: media draft deletion rights and stored-file cleanup (design D7).

Never-finalized media drafts are hard-deleted by their creator or by any
doctor/resident with patient access, and the hard delete removes the stored
artifacts those rows own (photo file + thumbnail; every series member file +
thumbnail; the video file — video thumbnails do not exist). Anything ever
finalized keeps the soft-delete path and keeps its files.

The assertions run against the real FilePond storage layout; the deletion
itself is not mocked.
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

TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="mediafiles_draft_deletion_"))

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
class MediaDraftDeletionTests(TestCase):
    """R4: hard delete for never-finalized media drafts, soft delete otherwise."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("media-del-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "media-del-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("media-del-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Media Deletion Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    # Fixtures -----------------------------------------------------------

    def _event_fields(self, *, author, is_draft, promoted_at=None, promoted_by=None):
        """Shared event fields; a student acting user would force a draft."""
        return {
            "patient": self.patient,
            "description": "Mídia de teste da exclusão.",
            "event_datetime": timezone.now() - timedelta(hours=1),
            "is_draft": is_draft,
            "draft_promoted_at": promoted_at,
            "draft_promoted_by": promoted_by,
            "created_by": author,
            "updated_by": promoted_by or author,
        }

    def _create_photo(self, *, author, is_draft, promoted_at=None, promoted_by=None,
                      with_thumbnail=True):
        photo = Photo.objects.create(
            file_id=str(uuid.uuid4()),
            original_filename="foto_deletada.jpg",
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
        photo_original = write_filepond_file(
            photo_original_dir(photo.created_at),
            photo.file_id,
            ".jpg",
            load_test_image_bytes(),
        )
        thumbnail = None
        if with_thumbnail:
            thumb_dir = f"photos/{photo.created_at.strftime('%Y/%m')}/thumbnails"
            photo.thumbnail_path = f"{thumb_dir}/{photo.file_id}_thumb.jpg"
            photo.save(update_fields=["thumbnail_path"])
            thumbnail = write_filepond_file(
                thumb_dir,
                f"{photo.file_id}_thumb",
                ".jpg",
                load_test_image_bytes(),
            )
        return photo, [path for path in (photo_original, thumbnail) if path]

    def _create_series(self, *, author, is_draft, promoted_at=None, promoted_by=None,
                       member_count=2):
        series = PhotoSeries.objects.create(
            caption="Legenda da série",
            **self._event_fields(
                author=author,
                is_draft=is_draft,
                promoted_at=promoted_at,
                promoted_by=promoted_by,
            ),
        )
        date_path = series.created_at.strftime("%Y/%m")
        artifacts = []
        for order in range(1, member_count + 1):
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
            artifacts.append(
                write_filepond_file(
                    f"photo_series/{date_path}/originals",
                    file_id,
                    ".jpg",
                    load_test_image_bytes(),
                )
            )
            artifacts.append(
                write_filepond_file(
                    thumb_dir,
                    f"{file_id}_thumb",
                    ".jpg",
                    load_test_image_bytes(),
                )
            )
        return series, artifacts

    def _create_video(self, *, author, is_draft, promoted_at=None, promoted_by=None):
        clip = VideoClip.objects.create(
            file_id=str(uuid.uuid4()),
            original_filename="video_deletado.mp4",
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
        artifact = write_filepond_file(
            f"videos/{clip.created_at.strftime('%Y/%m')}/originals",
            clip.file_id,
            ".mp4",
            VIDEO_CONTENT,
        )
        return clip, [artifact]

    def _delete(self, user, url_name, obj):
        self.client.force_login(user)
        return self.client.post(reverse(url_name, kwargs={"pk": obj.pk}))

    def _delete_via_http_delete(self, user, url_name, obj):
        self.client.force_login(user)
        return self.client.delete(reverse(url_name, kwargs={"pk": obj.pk}))

    # R4 photo -----------------------------------------------------------

    def test_creator_hard_deletes_own_photo_draft_with_its_artifacts(self):
        photo, artifacts = self._create_photo(author=self.student, is_draft=True)
        self.assertEqual(len(artifacts), 2)
        self.assertTrue(all(path.exists() for path in artifacts))

        response = self._delete(self.student, "mediafiles:photo_delete", photo)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Photo.all_objects.filter(pk=photo.pk).exists())
        for path in artifacts:
            self.assertFalse(path.exists(), f"{path} should have been removed")

    def test_photo_draft_without_a_thumbnail_deletes_cleanly(self):
        photo, artifacts = self._create_photo(
            author=self.student, is_draft=True, with_thumbnail=False
        )
        self.assertEqual(len(artifacts), 1)
        self.assertFalse(photo.thumbnail_path)

        response = self._delete(self.student, "mediafiles:photo_delete", photo)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Photo.all_objects.filter(pk=photo.pk).exists())
        for path in artifacts:
            self.assertFalse(path.exists())

    def test_physician_clears_a_student_photo_draft(self):
        photo, artifacts = self._create_photo(author=self.student, is_draft=True)

        response = self._delete(self.doctor, "mediafiles:photo_delete", photo)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Photo.all_objects.filter(pk=photo.pk).exists())
        for path in artifacts:
            self.assertFalse(path.exists())

    def test_unrelated_student_cannot_delete_and_keeps_the_files(self):
        photo, artifacts = self._create_photo(author=self.student, is_draft=True)

        response = self._delete(
            self.other_student, "mediafiles:photo_delete", photo
        )

        self.assertEqual(response.status_code, 403)
        stored = Photo.all_objects.get(pk=photo.pk)
        self.assertFalse(stored.is_deleted)
        for path in artifacts:
            self.assertTrue(path.exists())

    # R4 photo series ----------------------------------------------------

    def test_physician_clears_a_series_draft_including_member_files(self):
        series, artifacts = self._create_series(author=self.student, is_draft=True)
        self.assertEqual(PhotoSeriesFile.objects.filter(photo_series=series).count(), 2)
        self.assertEqual(len(artifacts), 4)

        response = self._delete(self.doctor, "mediafiles:photoseries_delete", series)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(PhotoSeries.all_objects.filter(pk=series.pk).exists())
        self.assertEqual(PhotoSeriesFile.objects.filter(photo_series=series).count(), 0)
        for path in artifacts:
            self.assertFalse(path.exists(), f"{path} should have been removed")

    def test_series_creator_hard_deletes_own_draft_with_member_files(self):
        series, artifacts = self._create_series(
            author=self.student, is_draft=True, member_count=1
        )

        response = self._delete(
            self.student, "mediafiles:photoseries_delete", series
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(PhotoSeries.all_objects.filter(pk=series.pk).exists())
        for path in artifacts:
            self.assertFalse(path.exists())

    # R4 video clip ------------------------------------------------------

    def test_video_draft_hard_delete_removes_the_file(self):
        clip, artifacts = self._create_video(author=self.student, is_draft=True)

        response = self._delete(self.student, "mediafiles:videoclip_delete", clip)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(VideoClip.all_objects.filter(pk=clip.pk).exists())
        for path in artifacts:
            self.assertFalse(path.exists())

    # Soft path: finals and reverted finals keep their files ---------------

    def test_definitive_photo_keeps_the_soft_delete_path_and_its_files(self):
        photo, artifacts = self._create_photo(
            author=self.student,
            is_draft=False,
            promoted_at=timezone.now() - timedelta(hours=1),
            promoted_by=self.doctor,
        )

        response = self._delete(self.doctor, "mediafiles:photo_delete", photo)

        self.assertEqual(response.status_code, 302)
        stored = Photo.all_objects.get(pk=photo.pk)
        self.assertTrue(stored.is_deleted)
        self.assertIsNotNone(stored.deleted_at)
        for path in artifacts:
            self.assertTrue(path.exists())

    def test_reverted_series_final_keeps_the_soft_delete_path_and_its_files(self):
        series, artifacts = self._create_series(
            author=self.student,
            is_draft=True,
            promoted_at=timezone.now() - timedelta(days=1),
            promoted_by=self.doctor,
        )

        response = self._delete(self.doctor, "mediafiles:photoseries_delete", series)

        self.assertEqual(response.status_code, 302)
        stored = PhotoSeries.all_objects.get(pk=series.pk)
        self.assertTrue(stored.is_deleted)
        for path in artifacts:
            self.assertTrue(path.exists())

    # HTTP DELETE method path --------------------------------------------
    # ``DeleteView`` dispatches HTTP DELETE to ``DeletionMixin.delete``, not to
    # ``form_valid``, so the method rule must hold on that path too.

    def test_photo_draft_http_delete_hard_deletes_row_and_artifacts(self):
        photo, artifacts = self._create_photo(author=self.student, is_draft=True)
        self.assertEqual(len(artifacts), 2)

        response = self._delete_via_http_delete(
            self.student, "mediafiles:photo_delete", photo
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Photo.all_objects.filter(pk=photo.pk).exists())
        for path in artifacts:
            self.assertFalse(path.exists(), f"{path} should have been removed")

    def test_series_draft_http_delete_hard_deletes_row_and_member_artifacts(self):
        series, artifacts = self._create_series(author=self.student, is_draft=True)
        self.assertEqual(len(artifacts), 4)

        response = self._delete_via_http_delete(
            self.doctor, "mediafiles:photoseries_delete", series
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(PhotoSeries.all_objects.filter(pk=series.pk).exists())
        self.assertEqual(
            PhotoSeriesFile.objects.filter(photo_series=series).count(), 0
        )
        for path in artifacts:
            self.assertFalse(path.exists(), f"{path} should have been removed")

    def test_video_draft_http_delete_hard_deletes_row_and_file(self):
        clip, artifacts = self._create_video(author=self.student, is_draft=True)

        response = self._delete_via_http_delete(
            self.student, "mediafiles:videoclip_delete", clip
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(VideoClip.all_objects.filter(pk=clip.pk).exists())
        for path in artifacts:
            self.assertFalse(path.exists(), f"{path} should have been removed")

    def test_definitive_photo_http_delete_keeps_soft_path_and_files(self):
        photo, artifacts = self._create_photo(
            author=self.student,
            is_draft=False,
            promoted_at=timezone.now() - timedelta(hours=1),
            promoted_by=self.doctor,
        )

        response = self._delete_via_http_delete(
            self.doctor, "mediafiles:photo_delete", photo
        )

        self.assertEqual(response.status_code, 302)
        stored = Photo.all_objects.get(pk=photo.pk)
        self.assertTrue(stored.is_deleted)
        self.assertIsNotNone(stored.deleted_at)
        for path in artifacts:
            self.assertTrue(path.exists())

    def test_definitive_video_keeps_the_soft_delete_path_and_its_file(self):
        clip, artifacts = self._create_video(
            author=self.student,
            is_draft=False,
            promoted_at=timezone.now() - timedelta(hours=1),
            promoted_by=self.doctor,
        )

        response = self._delete(self.doctor, "mediafiles:videoclip_delete", clip)

        self.assertEqual(response.status_code, 302)
        stored = VideoClip.all_objects.get(pk=clip.pk)
        self.assertTrue(stored.is_deleted)
        for path in artifacts:
            self.assertTrue(path.exists())
