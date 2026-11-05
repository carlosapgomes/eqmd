"""S6 R8: consent form timeline card actions for drafts (design D8).

The card offers the delete link gated on the object predicate alone, a review
link to the edit screen for drafts, and suppresses the export (PDF) and
duplicate actions on drafts. Approval never happens from the card.
"""

from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.events.models import Event
from apps.patients.models import Patient

from ..models import ConsentForm, ConsentTemplate

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class ConsentFormDraftCardActionTests(TestCase):
    """R8: review, delete, export and duplicate actions on the consent card."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("cf-card-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "cf-card-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("cf-card-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Consent Card Patient",
            birthday="1990-01-01",
            current_record_number="RN222",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        cls.template = ConsentTemplate.objects.create(
            name="Template de Cartão",
            markdown_body=(
                "{{ patient_name }} {{ patient_record_number }} "
                "{{ document_date }} {{ procedure_description }}"
            ),
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    def _create_consent(self, *, author=None, is_draft=False, promoted_by=None):
        author = author or self.doctor
        return ConsentForm.objects.create(
            template=self.template,
            patient=self.patient,
            document_date=date(2026, 1, 2),
            procedure_description="Procedimento de teste",
            rendered_markdown="Conteúdo do termo.",
            rendered_at=timezone.now(),
            event_datetime=timezone.now() - timedelta(hours=1),
            description="Termo de Consentimento - Template de Cartão",
            event_type=Event.CONSENT_FORM_EVENT,
            is_draft=is_draft,
            draft_promoted_by=promoted_by,
            created_by=author,
            # The finalizer is the acting user on an approved record (design D5).
            updated_by=promoted_by or author,
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

    def _edit_url(self, consent):
        return reverse("consentforms:consentform_update", kwargs={"pk": consent.pk})

    def _delete_url(self, consent):
        return reverse("consentforms:consentform_delete", kwargs={"pk": consent.pk})

    def _duplicate_url(self, consent):
        return reverse("consentforms:consentform_duplicate", kwargs={"pk": consent.pk})

    def _pdf_url(self, consent):
        return reverse("consentforms:consentform_pdf", kwargs={"pk": consent.pk})

    def test_physician_card_offers_review_and_delete_for_a_draft(self):
        draft = self._create_consent(author=self.student, is_draft=True)

        html = self._timeline_html(self.doctor)

        self.assertIn(self._edit_url(draft), html)
        self.assertIn(self._delete_url(draft), html)
        self.assertIn("Revisar", html)

    def test_student_author_card_offers_review_and_delete_for_own_draft(self):
        draft = self._create_consent(author=self.student, is_draft=True)

        html = self._timeline_html(self.student)

        self.assertIn(self._edit_url(draft), html)
        self.assertIn(self._delete_url(draft), html)

    def test_unrelated_student_card_has_no_review_or_delete_for_the_draft(self):
        draft = self._create_consent(author=self.student, is_draft=True)

        html = self._timeline_html(self.other_student)

        self.assertNotIn(self._edit_url(draft), html)
        self.assertNotIn(self._delete_url(draft), html)

    def test_delete_link_follows_the_object_predicate_alone(self):
        """R8: the card's former Django-perm conjunct is gone."""
        draft = self._create_consent(author=self.student, is_draft=True)
        # A physician keeps the predicate (profession) but loses the Django
        # permission, so only a predicate-gated link can render.
        self.doctor.groups.clear()

        html = self._timeline_html(self.doctor)

        self.assertIn(self._delete_url(draft), html)

    def test_draft_card_suppresses_the_export_and_duplicate_actions(self):
        draft = self._create_consent(author=self.student, is_draft=True)

        html = self._timeline_html(self.doctor)

        self.assertNotIn(self._pdf_url(draft), html)
        self.assertNotIn(self._duplicate_url(draft), html)

    def test_definitive_card_keeps_the_export_and_duplicate_actions(self):
        final = self._create_consent(author=self.doctor)

        html = self._timeline_html(self.doctor)

        self.assertIn(self._pdf_url(final), html)
        self.assertIn(self._duplicate_url(final), html)

    def test_card_never_offers_one_click_approval(self):
        self._create_consent(author=self.student, is_draft=True)

        html = self._timeline_html(self.doctor)

        self.assertNotIn("save_final", html)
        self.assertNotIn("Aprovar", html)
