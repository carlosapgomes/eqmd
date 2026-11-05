"""S5 R1/R2: the media student-draft lifecycle (photo, series, video clip).

Covers the explicit draft-aware querysets of the detail/update/delete views
(media managers subclass plain ``models.Manager``, so nothing is excluded for
them), the bot-draft guard, draft editing without a time limit, the draft
versus finalize update actions with the server-side physician gate, the
post-final owner window, the creation backstop, and the per-role update
template.
"""

import tempfile
import uuid
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.mediafiles.models import Photo, PhotoSeries, PhotoSeriesFile, VideoClip
from apps.patients.models import Patient

from .factories import load_test_image_bytes, photo_original_dir

User = get_user_model()

# The FilePond photo-create form builds paths with ``MEDIA_ROOT / "photos/..."``,
# so the override must be a Path (the string MEDIA_ROOT in test_settings would
# fail), shared by the whole module.
TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="mediafiles_draft_lifecycle_"))

KINDS = ("photo", "photo_series", "video_clip")

URL_NAMES = {
    "photo": {
        "detail": "mediafiles:photo_detail",
        "update": "mediafiles:photo_update",
        "delete": "mediafiles:photo_delete",
    },
    "photo_series": {
        "detail": "mediafiles:photoseries_detail",
        "update": "mediafiles:photoseries_update",
        "delete": "mediafiles:photoseries_delete",
    },
    "video_clip": {
        "detail": "mediafiles:videoclip_detail",
        "update": "mediafiles:videoclip_update",
        "delete": "mediafiles:videoclip_delete",
    },
}


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class MediaDraftLifecycleTests(TestCase):
    """R1/R2: draft resolution, finalize gate, owner window, template."""

    @classmethod
    def setUpTestData(cls):
        # The real grant under test: profession groups receive the permissions
        # the views enforce.
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("media-life-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "media-life-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("media-life-doctor", User.MEDICAL_DOCTOR)
        cls.other_doctor = create_profession_user(
            "media-life-other-doctor", User.MEDICAL_DOCTOR
        )
        cls.patient = Patient.objects.create(
            name="Draft Media Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    # Fixtures -----------------------------------------------------------

    def _event_fields(self, *, author, is_draft, draft_created_by_bot, promoted_at,
                      promoted_by):
        """Return the shared event fields for one media row.

        A student acting user would force draft state (design D1), so a fixture
        that must stay definitive records the physician as the acting user.
        """
        return {
            "patient": self.patient,
            "description": "Mídia de teste do fluxo de rascunho.",
            "event_datetime": timezone.now() - timedelta(hours=1),
            "is_draft": is_draft,
            "draft_created_by_bot": draft_created_by_bot,
            "draft_promoted_at": promoted_at,
            "draft_promoted_by": promoted_by,
            "created_by": author,
            "updated_by": promoted_by or author,
        }

    def _create(self, kind, *, author, is_draft=False, draft_created_by_bot="",
                promoted_at=None, promoted_by=None):
        fields = self._event_fields(
            author=author,
            is_draft=is_draft,
            draft_created_by_bot=draft_created_by_bot,
            promoted_at=promoted_at,
            promoted_by=promoted_by,
        )
        if kind == "photo":
            return Photo.objects.create(
                file_id=str(uuid.uuid4()),
                original_filename="foto_teste.jpg",
                file_size=1024,
                width=100,
                height=100,
                caption="Legenda de teste",
                **fields,
            )
        if kind == "photo_series":
            series = PhotoSeries.objects.create(caption="Legenda da série", **fields)
            PhotoSeriesFile.objects.create(
                photo_series=series,
                file_id=str(uuid.uuid4()),
                original_filename="serie_foto.jpg",
                file_size=1024,
                width=100,
                height=100,
                order=1,
            )
            return series
        if kind == "video_clip":
            return VideoClip.objects.create(
                file_id=str(uuid.uuid4()),
                original_filename="video_teste.mp4",
                file_size=2048,
                duration=30,
                width=320,
                height=240,
                video_codec="h264",
                caption="Legenda do vídeo",
                **fields,
            )
        raise AssertionError(f"Unknown media kind: {kind}")

    def _url(self, kind, action, obj):
        return reverse(URL_NAMES[kind][action], kwargs={"pk": obj.pk})

    def _status(self, kind, action, obj):
        return self.client.get(self._url(kind, action, obj)).status_code

    def _payload(self, obj, *, action=None, description="Mídia atualizada."):
        payload = {
            "description": description,
            "event_datetime": timezone.localtime(obj.event_datetime).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "caption": "Legenda atualizada",
        }
        if action == "save_draft":
            payload["save_draft"] = "1"
        elif action == "save_final":
            payload["save_final"] = "1"
        return payload

    def _create_temp_upload(self, filename="foto_teste.jpg"):
        """Create a FilePond TemporaryUpload row and return its upload_id."""
        import shortuuid
        from django_drf_filepond.models import TemporaryUpload

        upload_id = shortuuid.uuid()
        TemporaryUpload.objects.create(
            upload_id=upload_id,
            upload_name=filename,
            upload_type="F",
            file=SimpleUploadedFile(
                filename, load_test_image_bytes(), content_type="image/jpeg"
            ),
        )
        return upload_id

    # R1 creation backstop (regression: already passing via S1) ----------

    def test_student_media_creation_persists_as_draft(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                row = self._create(kind, author=self.student, is_draft=False)

                self.assertTrue(row.is_draft)
                self.assertIsNone(row.draft_promoted_at)

    def test_student_photo_creation_view_persists_as_draft(self):
        self.client.force_login(self.student)
        upload_id = self._create_temp_upload()

        response = self.client.post(
            reverse(
                "mediafiles:photo_create", kwargs={"patient_id": self.patient.pk}
            ),
            data={
                "description": "Foto enviada por estudante.",
                "event_datetime": timezone.localtime(
                    timezone.now() - timedelta(hours=1)
                ).strftime("%Y-%m-%dT%H:%M"),
                "caption": "",
                "upload_id": upload_id,
            },
        )

        self.assertEqual(response.status_code, 302)
        photo = Photo.objects.get(file_id__isnull=False, created_by=self.student)
        self.assertTrue(photo.is_draft)
        self.assertEqual(photo.updated_by, self.student)

    # R1 draft resolution with explicit querysets ------------------------

    def test_human_drafts_resolve_in_detail_update_and_delete(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                draft = self._create(kind, author=self.student, is_draft=True)

                self.client.force_login(self.doctor)
                for action in ("detail", "update", "delete"):
                    self.assertEqual(self._status(kind, action, draft), 200)

                self.client.force_login(self.student)
                for action in ("detail", "update", "delete"):
                    self.assertEqual(self._status(kind, action, draft), 200)

    def test_bot_drafts_stay_unreachable_through_normal_views(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                bot_draft = self._create(
                    kind,
                    author=self.doctor,
                    is_draft=True,
                    draft_created_by_bot="bot-client-1",
                )

                self.client.force_login(self.doctor)
                for action in ("detail", "update", "delete"):
                    self.assertEqual(self._status(kind, action, bot_draft), 404)

    def test_definitive_media_still_resolves(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                row = self._create(
                    kind,
                    author=self.student,
                    is_draft=False,
                    promoted_at=timezone.now() - timedelta(hours=1),
                    promoted_by=self.doctor,
                )

                self.client.force_login(self.doctor)
                for action in ("detail", "update", "delete"):
                    self.assertEqual(self._status(kind, action, row), 200)

    # R1 draft edit rights (no time limit) -------------------------------

    def test_creator_edits_an_old_draft(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                draft = self._create(kind, author=self.student, is_draft=True)
                type(draft).objects.filter(pk=draft.pk).update(
                    created_at=timezone.now() - timedelta(days=3)
                )

                self.client.force_login(self.student)
                self.assertEqual(self._status(kind, "update", draft), 200)

    def test_physician_edits_a_student_draft(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                draft = self._create(kind, author=self.student, is_draft=True)

                self.client.force_login(self.doctor)
                self.assertEqual(self._status(kind, "update", draft), 200)

    def test_unrelated_student_is_denied(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                draft = self._create(kind, author=self.student, is_draft=True)

                self.client.force_login(self.other_student)
                self.assertEqual(self._status(kind, "update", draft), 403)

    # R1 finalize --------------------------------------------------------

    def test_physician_finalize_flips_state_and_records_approver(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                draft = self._create(kind, author=self.student, is_draft=True)
                self.client.force_login(self.doctor)

                response = self.client.post(
                    self._url(kind, "update", draft),
                    data=self._payload(draft, action="save_final"),
                )

                self.assertEqual(response.status_code, 302)
                draft.refresh_from_db()
                self.assertFalse(draft.is_draft)
                self.assertEqual(draft.draft_promoted_by, self.doctor)
                self.assertIsNotNone(draft.draft_promoted_at)
                self.assertEqual(draft.created_by, self.student)
                self.assertEqual(draft.updated_by, self.doctor)

    def test_resaving_a_draft_keeps_it_a_draft(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                draft = self._create(kind, author=self.student, is_draft=True)
                self.client.force_login(self.student)

                response = self.client.post(
                    self._url(kind, "update", draft),
                    data=self._payload(draft, action="save_draft"),
                )

                self.assertEqual(response.status_code, 302)
                draft.refresh_from_db()
                self.assertTrue(draft.is_draft)
                self.assertIsNone(draft.draft_promoted_at)
                self.assertIsNone(draft.draft_promoted_by)

    def test_student_finalize_attempt_is_denied(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                draft = self._create(kind, author=self.student, is_draft=True)
                self.client.force_login(self.student)

                response = self.client.post(
                    self._url(kind, "update", draft),
                    data=self._payload(draft, action="save_final"),
                )

                self.assertEqual(response.status_code, 403)
                draft.refresh_from_db()
                self.assertTrue(draft.is_draft)
                self.assertIsNone(draft.draft_promoted_at)
                self.assertIsNone(draft.draft_promoted_by)

    def test_non_finalizing_student_save_keeps_the_draft(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                draft = self._create(kind, author=self.student, is_draft=True)
                self.client.force_login(self.student)

                payload = self._payload(draft, action="save_draft")
                payload["is_draft"] = ""

                response = self.client.post(
                    self._url(kind, "update", draft), data=payload
                )

                self.assertEqual(response.status_code, 302)
                draft.refresh_from_db()
                self.assertTrue(draft.is_draft)

    # R1 post-final owner window ----------------------------------------

    def test_student_author_is_locked_out_after_approval(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                row = self._create(
                    kind,
                    author=self.student,
                    is_draft=False,
                    promoted_at=timezone.now(),
                    promoted_by=self.doctor,
                )
                self.client.force_login(self.student)

                self.assertEqual(self._status(kind, "update", row), 403)
                self.assertEqual(self._status(kind, "delete", row), 403)

    def test_finalizer_keeps_the_window(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                row = self._create(
                    kind,
                    author=self.student,
                    is_draft=False,
                    promoted_at=timezone.now(),
                    promoted_by=self.doctor,
                )
                self.client.force_login(self.doctor)

                self.assertEqual(self._status(kind, "update", row), 200)

    def test_non_finalizer_physician_is_locked_out_after_approval(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                row = self._create(
                    kind,
                    author=self.student,
                    is_draft=False,
                    promoted_at=timezone.now(),
                    promoted_by=self.doctor,
                )
                self.client.force_login(self.other_doctor)

                self.assertEqual(self._status(kind, "update", row), 403)

    def test_finalizer_window_expires_after_24_hours(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                row = self._create(
                    kind,
                    author=self.student,
                    is_draft=False,
                    promoted_at=timezone.now(),
                    promoted_by=self.doctor,
                )
                type(row).objects.filter(pk=row.pk).update(
                    draft_promoted_at=timezone.now() - timedelta(hours=25)
                )
                self.client.force_login(self.doctor)

                self.assertEqual(self._status(kind, "update", row), 403)

    # R2 update template -------------------------------------------------

    def test_update_template_offers_both_actions_to_physicians(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                draft = self._create(kind, author=self.student, is_draft=True)
                self.client.force_login(self.doctor)

                html = self.client.get(
                    self._url(kind, "update", draft)
                ).content.decode()

                self.assertIn("Salvar rascunho", html)
                self.assertIn("Salvar definitivo", html)
                self.assertIn('name="save_draft"', html)
                self.assertIn('name="save_final"', html)
                self.assertIn("data-draft-supervision-banner", html)
                self.assertIn("Rascunho aguardando aprovação", html)

    def test_update_template_offers_only_the_draft_action_to_students(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                draft = self._create(kind, author=self.student, is_draft=True)
                self.client.force_login(self.student)

                html = self.client.get(
                    self._url(kind, "update", draft)
                ).content.decode()

                self.assertIn("Salvar rascunho", html)
                self.assertIn('name="save_draft"', html)
                self.assertNotIn('name="save_final"', html)
                self.assertIn("data-draft-supervision-banner", html)

    def test_definitive_update_template_has_no_draft_actions(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                row = self._create(
                    kind,
                    author=self.student,
                    is_draft=False,
                    promoted_at=timezone.now(),
                    promoted_by=self.doctor,
                )
                self.client.force_login(self.doctor)

                html = self.client.get(
                    self._url(kind, "update", row)
                ).content.decode()

                self.assertNotIn("Salvar rascunho", html)
                self.assertNotIn("Salvar definitivo", html)
                self.assertNotIn("data-draft-supervision-banner", html)

    def test_student_draft_lifecycle_end_to_end(self):
        """Walk one photo draft through the actors' whole flow."""
        self.client.force_login(self.student)
        upload_id = self._create_temp_upload()
        self.client.post(
            reverse(
                "mediafiles:photo_create", kwargs={"patient_id": self.patient.pk}
            ),
            data={
                "description": "Foto do fluxo completo.",
                "event_datetime": timezone.localtime(
                    timezone.now() - timedelta(hours=1)
                ).strftime("%Y-%m-%dT%H:%M"),
                "caption": "",
                "upload_id": upload_id,
            },
        )
        photo = Photo.objects.get(created_by=self.student)
        self.assertTrue(photo.is_draft)

        # The physician approves it from the edit screen.
        self.client.force_login(self.doctor)
        response = self.client.post(
            self._url("photo", "update", photo),
            data=self._payload(photo, action="save_final"),
        )
        self.assertEqual(response.status_code, 302)
        photo.refresh_from_db()
        self.assertFalse(photo.is_draft)
        self.assertEqual(photo.draft_promoted_by, self.doctor)
        self.assertEqual(photo.created_by, self.student)

        # The student loses access; the finalizer keeps it inside the window.
        self.client.force_login(self.student)
        self.assertEqual(self._status("photo", "update", photo), 403)
        self.client.force_login(self.doctor)
        self.assertEqual(self._status("photo", "update", photo), 200)

    def test_photo_file_stays_on_disk_after_draft_edits(self):
        """Draft edits cover metadata only: the stored image is untouched."""
        photo = self._create("photo", author=self.student, is_draft=True)
        stored = (
            settings.MEDIA_ROOT
            / photo_original_dir(photo.created_at)
            / f"{photo.file_id}.jpg"
        )
        stored.parent.mkdir(parents=True, exist_ok=True)
        stored.write_bytes(load_test_image_bytes())

        self.client.force_login(self.doctor)
        response = self.client.post(
            self._url("photo", "update", photo),
            data=self._payload(photo, action="save_draft"),
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(stored.exists())
        photo.refresh_from_db()
        self.assertEqual(photo.description, "Mídia atualizada.")
