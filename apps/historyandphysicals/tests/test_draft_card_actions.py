"""S4 R4: HistoryAndPhysical timeline card actions for drafts (design D8).

The card offers the delete link gated on the object predicate alone, a review
link to the edit screen for drafts, and suppresses the duplicate action on
drafts (the H&P card carries no export action). Approval never happens from
the card: it is the ``Salvar definitivo`` submission inside the edit screen.
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


class HistoryAndPhysicalDraftCardActionTests(TestCase):
    """R4: delete, review, and duplicate actions on the H&P card."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("hp-card-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "hp-card-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("hp-card-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Draft Card Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    def _create_note(self, *, author=None, is_draft=False, promoted_by=None):
        author = author or self.doctor
        return HistoryAndPhysical.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=1),
            content="Conteúdo suficiente para a anamnese e exame físico de teste.",
            is_draft=is_draft,
            draft_promoted_by=promoted_by,
            created_by=author,
            updated_by=author,
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

    def _delete_url(self, note):
        return reverse(
            "historyandphysicals:historyandphysical_delete", kwargs={"pk": note.pk}
        )

    def _edit_url(self, note):
        return reverse(
            "historyandphysicals:historyandphysical_update", kwargs={"pk": note.pk}
        )

    def _duplicate_url(self, note):
        return reverse(
            "historyandphysicals:historyandphysical_duplicate", kwargs={"pk": note.pk}
        )

    def _print_url(self, note):
        return reverse(
            "historyandphysicals:historyandphysical_print", kwargs={"pk": note.pk}
        )

    def test_physician_card_offers_review_and_delete_for_a_draft(self):
        draft = self._create_note(author=self.student, is_draft=True)

        html = self._timeline_html(self.doctor)

        self.assertIn(self._delete_url(draft), html)
        self.assertIn(self._edit_url(draft), html)
        self.assertIn("Revisar", html)

    def test_student_author_card_offers_review_and_delete_for_own_draft(self):
        draft = self._create_note(author=self.student, is_draft=True)

        html = self._timeline_html(self.student)

        self.assertIn(self._delete_url(draft), html)
        self.assertIn("Revisar", html)

    def test_unrelated_student_card_has_no_review_or_delete_for_the_draft(self):
        draft = self._create_note(author=self.student, is_draft=True)

        html = self._timeline_html(self.other_student)

        self.assertNotIn(self._delete_url(draft), html)
        self.assertNotIn(self._edit_url(draft), html)

    def test_draft_card_suppresses_the_duplicate_action(self):
        draft = self._create_note(author=self.student, is_draft=True)

        html = self._timeline_html(self.doctor)

        self.assertNotIn(self._duplicate_url(draft), html)

    def test_definitive_card_keeps_the_duplicate_action(self):
        note = self._create_note(
            author=self.doctor, is_draft=False, promoted_by=self.doctor
        )

        html = self._timeline_html(self.doctor)

        self.assertIn(self._duplicate_url(note), html)
        self.assertIn(self._delete_url(note), html)
        self.assertNotIn("Revisar", html)

    def test_draft_card_offers_no_delete_to_a_user_without_the_right(self):
        draft = self._create_note(author=self.doctor, is_draft=True)

        html = self._timeline_html(self.student)

        self.assertNotIn(self._delete_url(draft), html)
        self.assertNotIn(self._edit_url(draft), html)

    def test_card_never_offers_one_click_approval(self):
        self._create_note(author=self.student, is_draft=True)

        html = self._timeline_html(self.doctor)

        self.assertNotIn('name="save_final"', html)
        self.assertNotIn("Salvar definitivo", html)
