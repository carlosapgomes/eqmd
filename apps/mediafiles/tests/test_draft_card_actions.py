"""S5 R3: media timeline card actions for drafts (design D8/D10).

The card offers the delete link gated on the object predicate alone, a review
link to the edit screen for drafts, and suppresses the export actions on
drafts. Approval never happens from the card: it is the ``Salvar definitivo``
submission inside the edit screen.
"""

import tempfile
import uuid
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.mediafiles.models import Photo, PhotoSeries, PhotoSeriesFile, VideoClip
from apps.patients.models import Patient

User = get_user_model()

TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="mediafiles_draft_cards_"))


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class MediaDraftCardActionTests(TestCase):
    """R3: delete, review, and export actions on the media cards."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("media-card-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "media-card-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("media-card-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Media Card Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    # Fixtures -----------------------------------------------------------

    def _event_fields(self, *, author, is_draft, promoted_at=None, promoted_by=None):
        """Shared event fields; a student acting user would force a draft."""
        return {
            "patient": self.patient,
            "description": "Mídia de teste do cartão.",
            "event_datetime": timezone.now() - timedelta(hours=1),
            "is_draft": is_draft,
            "draft_promoted_at": promoted_at,
            "draft_promoted_by": promoted_by,
            "created_by": author,
            "updated_by": promoted_by or author,
        }

    def _create_photo(self, *, author, is_draft, promoted_at=None, promoted_by=None):
        return Photo.objects.create(
            file_id=str(uuid.uuid4()),
            original_filename="foto_cartao.jpg",
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
        PhotoSeriesFile.objects.create(
            photo_series=series,
            file_id=str(uuid.uuid4()),
            original_filename="serie_cartao.jpg",
            file_size=1024,
            width=100,
            height=100,
            order=1,
        )
        return series

    def _create_video(self, *, author, is_draft, promoted_at=None, promoted_by=None):
        return VideoClip.objects.create(
            file_id=str(uuid.uuid4()),
            original_filename="video_cartao.mp4",
            file_size=2048,
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

    def _timeline_html(self, user):
        self.client.force_login(user)
        response = self.client.get(
            reverse(
                "apps.patients:patient_events_timeline",
                kwargs={"patient_id": self.patient.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def _url_for(self, url_name, obj):
        return reverse(url_name, kwargs={"pk": obj.pk})

    # R3 physician and author actions ------------------------------------

    def test_physician_card_offers_review_and_delete_for_media_drafts(self):
        cases = (
            ("photo", self._create_photo, "mediafiles:photo_delete",
             "mediafiles:photo_update"),
            ("photo_series", self._create_series, "mediafiles:photoseries_delete",
             "mediafiles:photoseries_update"),
            ("video_clip", self._create_video, "mediafiles:videoclip_delete",
             "mediafiles:videoclip_update"),
        )
        for kind, create, delete_name, update_name in cases:
            with self.subTest(kind=kind):
                draft = create(author=self.student, is_draft=True)

                html = self._timeline_html(self.doctor)

                self.assertIn(self._url_for(delete_name, draft), html)
                self.assertIn(self._url_for(update_name, draft), html)
                self.assertIn("Revisar", html)

    def test_author_card_offers_review_and_delete_for_own_media_draft(self):
        draft = self._create_photo(author=self.student, is_draft=True)

        html = self._timeline_html(self.student)

        self.assertIn(self._url_for("mediafiles:photo_delete", draft), html)
        self.assertIn(self._url_for("mediafiles:photo_update", draft), html)
        self.assertIn("Revisar", html)

    def test_unrelated_student_card_has_no_review_or_delete_for_the_draft(self):
        draft = self._create_photo(author=self.student, is_draft=True)

        html = self._timeline_html(self.other_student)

        self.assertNotIn(self._url_for("mediafiles:photo_delete", draft), html)
        self.assertNotIn(self._url_for("mediafiles:photo_update", draft), html)

    def test_definitive_card_keeps_delete_without_the_review_action(self):
        photo = self._create_photo(
            author=self.student,
            is_draft=False,
            promoted_at=timezone.now() - timedelta(hours=1),
            promoted_by=self.doctor,
        )

        html = self._timeline_html(self.doctor)

        self.assertIn(self._url_for("mediafiles:photo_delete", photo), html)
        self.assertNotIn("Revisar", html)

    # R3 export suppression on drafts ------------------------------------

    def test_photo_draft_card_suppresses_the_download_action(self):
        self._create_photo(author=self.student, is_draft=True)

        html = self._timeline_html(self.doctor)

        # The page-level photo modal keeps its inline-serve affordance; the
        # card's own download action is what drafts must not offer.
        self.assertNotIn('aria-label="Baixar foto original"', html)

    def test_photo_final_card_keeps_the_download_action(self):
        photo = self._create_photo(
            author=self.doctor, is_draft=False
        )
        self.assertFalse(photo.is_draft)

        html = self._timeline_html(self.doctor)

        self.assertIn('aria-label="Baixar foto original"', html)

    def test_series_draft_card_suppresses_the_zip_download(self):
        draft = self._create_series(author=self.student, is_draft=True)

        html = self._timeline_html(self.doctor)

        self.assertNotIn(
            self._url_for("mediafiles:photoseries_download", draft), html
        )

    def test_series_final_card_keeps_the_zip_download(self):
        series = self._create_series(author=self.doctor, is_draft=False)

        html = self._timeline_html(self.doctor)

        self.assertIn(
            self._url_for("mediafiles:photoseries_download", series), html
        )

    def test_video_draft_card_suppresses_the_download_action(self):
        draft = self._create_video(author=self.student, is_draft=True)

        html = self._timeline_html(self.doctor)

        self.assertNotIn(self._url_for("mediafiles:videoclip_download", draft), html)

    def test_video_final_card_keeps_the_download_action(self):
        clip = self._create_video(author=self.doctor, is_draft=False)

        html = self._timeline_html(self.doctor)

        self.assertIn(self._url_for("mediafiles:videoclip_download", clip), html)

    # R3 no one-click approval -------------------------------------------

    def test_media_cards_never_offer_one_click_approval(self):
        self._create_photo(author=self.student, is_draft=True)
        self._create_series(author=self.student, is_draft=True)
        self._create_video(author=self.student, is_draft=True)

        html = self._timeline_html(self.doctor)

        self.assertNotIn('name="save_final"', html)
        self.assertNotIn("Salvar definitivo", html)
