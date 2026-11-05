"""S4 R5: the HistoryAndPhysical print output denies drafts (design D10).

The H&P has no PDF endpoint; its only document output is the print view.
Drafts stay reviewable on screen (detail/update) but never leave the record:
print denies human and bot drafts alike and keeps serving final records.
"""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import Patient

from ..models import HistoryAndPhysical

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class HistoryAndPhysicalDraftPrintGatingTests(TestCase):
    """R5: print denies drafts for all users and serves finals as today."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("hp-print-student", User.STUDENT)
        cls.doctor = create_profession_user("hp-print-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Draft Print Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def _create_note(self, *, author=None, is_draft=False, draft_created_by_bot=""):
        author = author or self.doctor
        return HistoryAndPhysical.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=1),
            content="Conteúdo suficiente para a anamnese em impressão.",
            is_draft=is_draft,
            draft_created_by_bot=draft_created_by_bot,
            created_by=author,
            updated_by=author,
        )

    def _url(self, note):
        return reverse(
            "historyandphysicals:historyandphysical_print", kwargs={"pk": note.pk}
        )

    def test_print_denies_human_draft_for_its_author(self):
        draft = self._create_note(author=self.student, is_draft=True)

        self.client.force_login(self.student)

        self.assertEqual(self.client.get(self._url(draft)).status_code, 404)

    def test_print_denies_human_draft_for_a_physician(self):
        draft = self._create_note(author=self.student, is_draft=True)

        self.client.force_login(self.doctor)

        self.assertEqual(self.client.get(self._url(draft)).status_code, 404)

    def test_print_denies_bot_draft(self):
        bot_draft = self._create_note(
            author=self.doctor, is_draft=True, draft_created_by_bot="bot-client-1"
        )

        self.client.force_login(self.doctor)

        self.assertEqual(self.client.get(self._url(bot_draft)).status_code, 404)

    def test_print_serves_final_note(self):
        note = self._create_note(author=self.doctor, is_draft=False)

        self.client.force_login(self.doctor)
        response = self.client.get(self._url(note))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, note.content)

    def test_no_pdf_endpoint_exists_for_history_and_physical(self):
        note = self._create_note(author=self.doctor, is_draft=False)

        with self.assertRaises(NoReverseMatch):
            reverse(
                "historyandphysicals:historyandphysical_pdf", kwargs={"pk": note.pk}
            )
