"""S4 R6: DailyNote duplicate sources and student duplicate results.

Duplicate sources stay definitive-only (human and bot drafts 404 as sources,
design D14) and a duplicate created by a student persists as a draft through
the model backstop.
"""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import Patient

from ..models import DailyNote

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class DailyNoteDraftDuplicationTests(TestCase):
    """R6: drafts cannot seed duplicates; student copies are drafts."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("dn-dup-student", User.STUDENT)
        cls.doctor = create_profession_user("dn-dup-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Draft Duplication Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def _create_note(self, *, author=None, is_draft=False, draft_created_by_bot=""):
        author = author or self.doctor
        return DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(days=1),
            content="Conteúdo suficiente para a evolução de origem.",
            is_draft=is_draft,
            draft_created_by_bot=draft_created_by_bot,
            created_by=author,
            updated_by=author,
        )

    def _payload(self):
        return {
            "event_datetime": timezone.localtime(
                timezone.now() - timedelta(hours=1)
            ).strftime("%Y-%m-%dT%H:%M"),
            "content": "Conteúdo suficiente para a evolução duplicada.",
        }

    def test_human_draft_cannot_be_duplicated(self):
        draft = self._create_note(author=self.student, is_draft=True)
        self.client.force_login(self.doctor)

        response = self.client.get(
            reverse("dailynotes:dailynote_duplicate", kwargs={"pk": draft.pk})
        )

        self.assertEqual(response.status_code, 404)

    def test_bot_draft_cannot_be_duplicated(self):
        bot_draft = self._create_note(
            author=self.doctor, is_draft=True, draft_created_by_bot="bot-client-1"
        )
        self.client.force_login(self.doctor)

        response = self.client.get(
            reverse("dailynotes:dailynote_duplicate", kwargs={"pk": bot_draft.pk})
        )

        self.assertEqual(response.status_code, 404)

    def test_student_duplicate_result_persists_as_draft(self):
        source = self._create_note(author=self.doctor)
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("dailynotes:dailynote_duplicate", kwargs={"pk": source.pk}),
            data=self._payload(),
        )

        self.assertEqual(response.status_code, 302)
        copy = DailyNote.all_objects.get(
            content="Conteúdo suficiente para a evolução duplicada."
        )
        self.assertTrue(copy.is_draft)
        self.assertEqual(copy.created_by, self.student)
        self.assertIsNone(copy.draft_promoted_at)

    def test_physician_duplicate_result_stays_definitive(self):
        source = self._create_note(author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse("dailynotes:dailynote_duplicate", kwargs={"pk": source.pk}),
            data=self._payload(),
        )

        self.assertEqual(response.status_code, 302)
        copy = DailyNote.objects.get(
            content="Conteúdo suficiente para a evolução duplicada."
        )
        self.assertFalse(copy.is_draft)
