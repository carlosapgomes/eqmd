"""S3 R2/R3/R4/R5: the SimpleNote student-draft lifecycle.

Covers creation persisting as a draft through the model backstop, draft
resolution in the detail/update/delete views with the bot-draft guard, the
draft versus finalize update actions with the server-side physician gate, the
post-final owner window, and the per-role update template.
"""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import Patient

from ..models import SimpleNote

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class SimpleNoteDraftLifecycleTests(TestCase):
    """R2/R3/R4/R5: creation, draft resolution, finalize gate, owner window."""

    @classmethod
    def setUpTestData(cls):
        # The real grant under test: profession groups receive the permissions
        # the views enforce.
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("lifecycle-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "lifecycle-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("lifecycle-doctor", User.MEDICAL_DOCTOR)
        cls.other_doctor = create_profession_user(
            "lifecycle-other-doctor", User.MEDICAL_DOCTOR
        )
        cls.patient = Patient.objects.create(
            name="Draft Lifecycle Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    def _create_note(
        self,
        *,
        author,
        is_draft=False,
        draft_created_by_bot="",
        content="Conteúdo suficiente para a nota de teste.",
        promoted_at=None,
        promoted_by=None,
    ):
        note = SimpleNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=1),
            content=content,
            is_draft=is_draft,
            draft_created_by_bot=draft_created_by_bot,
            draft_promoted_at=promoted_at,
            draft_promoted_by=promoted_by,
            created_by=author,
            # A student acting user would force draft state (design D1), so a
            # fixture that must stay definitive records the physician as the
            # acting user.
            updated_by=promoted_by or author,
        )
        return note

    def _payload(self, *, content="Conteúdo atualizado da nota de teste.", action=None):
        payload = {
            "event_datetime": timezone.localtime(
                timezone.now() - timedelta(hours=1)
            ).strftime("%Y-%m-%dT%H:%M"),
            "content": content,
        }
        if action == "save_draft":
            payload["save_draft"] = "1"
        elif action == "save_final":
            payload["save_final"] = "1"
        return payload

    def _url(self, name, note):
        return reverse(f"simplenotes:{name}", kwargs={"pk": note.pk})

    def _status(self, name, note):
        return self.client.get(self._url(name, note)).status_code

    # R2 -----------------------------------------------------------------

    def test_student_creation_persists_as_draft(self):
        self.client.force_login(self.student)

        response = self.client.post(
            reverse(
                "simplenotes:patient_simplenote_create",
                kwargs={"patient_pk": self.patient.pk},
            ),
            data=self._payload(),
        )

        self.assertEqual(response.status_code, 302)
        note = SimpleNote.all_objects.get(patient=self.patient)
        self.assertTrue(note.is_draft)
        self.assertEqual(note.created_by, self.student)
        self.assertEqual(note.updated_by, self.student)
        self.assertIsNone(note.draft_promoted_at)

    # R3 -----------------------------------------------------------------

    def test_detail_resolves_human_draft_for_doctor_and_author(self):
        draft = self._create_note(author=self.student, is_draft=True)

        self.client.force_login(self.doctor)
        self.assertEqual(self._status("simplenote_detail", draft), 200)

        self.client.force_login(self.student)
        self.assertEqual(self._status("simplenote_detail", draft), 200)

    def test_update_and_delete_resolve_human_draft(self):
        draft = self._create_note(author=self.student, is_draft=True)

        self.client.force_login(self.doctor)
        self.assertEqual(self._status("simplenote_update", draft), 200)
        self.assertEqual(self._status("simplenote_delete", draft), 200)

        self.client.force_login(self.student)
        self.assertEqual(self._status("simplenote_update", draft), 200)
        self.assertEqual(self._status("simplenote_delete", draft), 200)

    def test_bot_drafts_stay_unreachable_through_normal_views(self):
        bot_draft = self._create_note(
            author=self.doctor, is_draft=True, draft_created_by_bot="bot-client-1"
        )

        self.client.force_login(self.doctor)

        for name in ("simplenote_detail", "simplenote_update", "simplenote_delete"):
            with self.subTest(view=name):
                self.assertEqual(
                    self.client.get(self._url(name, bot_draft)).status_code, 404
                )

    # R4 -----------------------------------------------------------------

    def test_physician_finalize_flips_state_and_records_approver(self):
        draft = self._create_note(author=self.student, is_draft=True)
        self.client.force_login(self.doctor)

        response = self.client.post(
            self._url("simplenote_update", draft),
            data=self._payload(action="save_final"),
        )

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertFalse(draft.is_draft)
        self.assertEqual(draft.draft_promoted_by, self.doctor)
        self.assertIsNotNone(draft.draft_promoted_at)
        self.assertEqual(draft.created_by, self.student)

    def test_resaving_a_draft_keeps_it_a_draft(self):
        draft = self._create_note(author=self.student, is_draft=True)
        self.client.force_login(self.student)

        response = self.client.post(
            self._url("simplenote_update", draft),
            data=self._payload(action="save_draft"),
        )

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertTrue(draft.is_draft)
        self.assertIsNone(draft.draft_promoted_at)

    def test_doctor_saving_as_draft_keeps_the_draft_state(self):
        draft = self._create_note(author=self.student, is_draft=True)
        self.client.force_login(self.doctor)

        response = self.client.post(
            self._url("simplenote_update", draft),
            data=self._payload(action="save_draft"),
        )

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertTrue(draft.is_draft)
        self.assertIsNone(draft.draft_promoted_by)

    def test_student_finalize_attempt_is_denied(self):
        draft = self._create_note(author=self.student, is_draft=True)
        self.client.force_login(self.student)

        response = self.client.post(
            self._url("simplenote_update", draft),
            data=self._payload(action="save_final"),
        )

        self.assertEqual(response.status_code, 403)
        draft.refresh_from_db()
        self.assertTrue(draft.is_draft)
        self.assertIsNone(draft.draft_promoted_at)
        self.assertIsNone(draft.draft_promoted_by)

    def test_student_cannot_flip_own_draft_with_a_crafted_field(self):
        draft = self._create_note(author=self.student, is_draft=True)
        self.client.force_login(self.student)

        payload = self._payload(action="save_draft")
        payload["is_draft"] = ""

        response = self.client.post(self._url("simplenote_update", draft), data=payload)

        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertTrue(draft.is_draft)

    def test_definitive_update_by_finalizer_keeps_it_definitive(self):
        note = self._create_note(
            author=self.student,
            is_draft=False,
            promoted_at=timezone.now() - timedelta(hours=1),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.doctor)

        response = self.client.post(
            self._url("simplenote_update", note), data=self._payload()
        )

        self.assertEqual(response.status_code, 302)
        note.refresh_from_db()
        self.assertFalse(note.is_draft)

    # R4 post-final owner window ----------------------------------------

    def test_student_author_is_locked_out_after_approval(self):
        note = self._create_note(
            author=self.student,
            is_draft=False,
            promoted_at=timezone.now(),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.student)

        self.assertEqual(self._status("simplenote_update", note), 403)
        self.assertEqual(
            self.client.post(
                self._url("simplenote_update", note), data=self._payload()
            ).status_code,
            403,
        )
        self.assertEqual(self._status("simplenote_delete", note), 403)

    def test_non_finalizer_physician_is_locked_out_after_approval(self):
        note = self._create_note(
            author=self.student,
            is_draft=False,
            promoted_at=timezone.now(),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.other_doctor)

        self.assertEqual(self._status("simplenote_update", note), 403)

    def test_finalizer_window_expires_after_24_hours(self):
        note = self._create_note(
            author=self.student,
            is_draft=False,
            promoted_at=timezone.now(),
            promoted_by=self.doctor,
        )
        SimpleNote.objects.filter(pk=note.pk).update(
            draft_promoted_at=timezone.now() - timedelta(hours=25)
        )
        self.client.force_login(self.doctor)

        self.assertEqual(self._status("simplenote_update", note), 403)

    # R5 -----------------------------------------------------------------

    def test_update_template_offers_both_actions_to_physicians(self):
        draft = self._create_note(author=self.student, is_draft=True)
        self.client.force_login(self.doctor)

        html = self.client.get(self._url("simplenote_update", draft)).content.decode()

        self.assertIn("Salvar rascunho", html)
        self.assertIn("Salvar definitivo", html)
        self.assertIn('name="save_draft"', html)
        self.assertIn('name="save_final"', html)
        self.assertIn("data-draft-supervision-banner", html)
        self.assertIn("Rascunho aguardando aprovação", html)

    def test_update_template_offers_only_the_draft_action_to_students(self):
        draft = self._create_note(author=self.student, is_draft=True)
        self.client.force_login(self.student)

        html = self.client.get(self._url("simplenote_update", draft)).content.decode()

        self.assertIn("Salvar rascunho", html)
        self.assertIn('name="save_draft"', html)
        self.assertNotIn('name="save_final"', html)
        self.assertIn("data-draft-supervision-banner", html)

    def test_definitive_update_template_has_no_draft_actions(self):
        note = self._create_note(
            author=self.student,
            is_draft=False,
            promoted_at=timezone.now(),
            promoted_by=self.doctor,
        )
        self.client.force_login(self.doctor)

        html = self.client.get(self._url("simplenote_update", note)).content.decode()

        self.assertIn("Atualizar Nota", html)
        self.assertNotIn("Salvar rascunho", html)
        self.assertNotIn("Salvar definitivo", html)
        self.assertNotIn("data-draft-supervision-banner", html)

    def test_student_draft_lifecycle_end_to_end(self):
        """Walk the full lifecycle the way the three actors experience it."""
        # 1. The student writes a note: it persists as a draft.
        self.client.force_login(self.student)
        self.client.post(
            reverse(
                "simplenotes:patient_simplenote_create",
                kwargs={"patient_pk": self.patient.pk},
            ),
            data=self._payload(),
        )
        note = SimpleNote.all_objects.get(patient=self.patient)
        self.assertTrue(note.is_draft)

        # 2. The timeline shows the draft with its badge and review action.
        timeline_url = reverse(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )
        self.client.force_login(self.doctor)
        self.assertContains(self.client.get(timeline_url), "draft-badge")
        self.assertContains(self.client.get(timeline_url), "Revisar")

        # 3. The physician approves it from the edit screen.
        response = self.client.post(
            self._url("simplenote_update", note),
            data=self._payload(action="save_final"),
        )
        self.assertEqual(response.status_code, 302)
        note.refresh_from_db()
        self.assertFalse(note.is_draft)
        self.assertEqual(note.draft_promoted_by, self.doctor)
        self.assertEqual(note.created_by, self.student)

        # 4. The card loses the draft badge; the student loses edit access and
        #    the finalizer keeps it inside the 24h window. The timeline caches
        #    for 60s and the test session store shares the cache, so reset both
        #    before reading the approved card.
        cache.clear()
        self.client.force_login(self.doctor)
        self.assertNotContains(self.client.get(timeline_url), "draft-badge")
        self.client.force_login(self.student)
        self.assertEqual(self._status("simplenote_update", note), 403)
        self.client.force_login(self.doctor)
        self.assertEqual(self._status("simplenote_update", note), 200)
