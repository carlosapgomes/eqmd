"""S6 R2/R8: prescription timeline card supervision UI (design D8/D11).

The card labels supervision state distinctly from the clinical status badge,
offers the review (edit) and delete links per the object predicates, and
suppresses the export and duplicate actions on drafts. Approval never happens
on the card.
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

from ..models import OutpatientPrescription, PrescriptionItem

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class PrescriptionDraftCardActionTests(TestCase):
    """R2/R8: supervision badge, review, delete, export and duplicate actions."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("rx-card-student", User.STUDENT)
        cls.other_student = create_profession_user(
            "rx-card-other-student", User.STUDENT
        )
        cls.doctor = create_profession_user("rx-card-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Prescription Card Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    def _create_prescription(self, *, author=None, is_draft=False, status="draft"):
        author = author or self.doctor
        prescription = OutpatientPrescription.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=1),
            prescription_date=timezone.localdate(),
            instructions="Uso oral.",
            status=status,
            is_draft=is_draft,
            description="Receita",
            created_by=author,
            updated_by=author,
        )
        PrescriptionItem.objects.create(
            prescription=prescription,
            drug_name="Paracetamol",
            presentation="500mg comprimidos",
            usage_instructions="Tomar 1 comprimido de 8 em 8 horas.",
            quantity="21 comprimidos",
            order=1,
        )
        return prescription

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

    def _edit_url(self, prescription):
        return reverse(
            "outpatientprescriptions:outpatientprescription_update",
            kwargs={"pk": prescription.pk},
        )

    def _delete_url(self, prescription):
        return reverse(
            "outpatientprescriptions:outpatientprescription_delete",
            kwargs={"pk": prescription.pk},
        )

    def _duplicate_url(self, prescription):
        return reverse(
            "outpatientprescriptions:outpatientprescription_duplicate",
            kwargs={"pk": prescription.pk},
        )

    def _pdf_url(self, prescription):
        return reverse(
            "outpatientprescriptions:outpatientprescription_pdf",
            kwargs={"pk": prescription.pk},
        )

    def test_draft_card_labels_supervision_and_keeps_the_clinical_badge(self):
        draft = self._create_prescription(
            author=self.student, is_draft=True, status="finalized"
        )

        html = self._timeline_html(self.doctor)

        self.assertIn("Aguardando aprovação", html)
        self.assertIn(draft.get_status_display(), html)

    def test_definitive_card_has_no_supervision_badge(self):
        self._create_prescription(author=self.doctor, status="finalized")

        html = self._timeline_html(self.doctor)

        self.assertNotIn("Aguardando aprovação", html)

    def test_physician_card_offers_review_and_delete_for_a_draft(self):
        draft = self._create_prescription(author=self.student, is_draft=True)

        html = self._timeline_html(self.doctor)

        self.assertIn(self._edit_url(draft), html)
        self.assertIn(self._delete_url(draft), html)
        self.assertIn("Revisar", html)

    def test_student_author_card_offers_review_and_delete_for_own_draft(self):
        draft = self._create_prescription(author=self.student, is_draft=True)

        html = self._timeline_html(self.student)

        self.assertIn(self._edit_url(draft), html)
        self.assertIn(self._delete_url(draft), html)

    def test_unrelated_student_card_has_no_review_or_delete_for_the_draft(self):
        draft = self._create_prescription(author=self.student, is_draft=True)

        html = self._timeline_html(self.other_student)

        self.assertNotIn(self._edit_url(draft), html)
        self.assertNotIn(self._delete_url(draft), html)

    def test_delete_link_follows_the_object_predicate_alone(self):
        """R8: no Django-perm conjunct gates the card's delete link."""
        draft = self._create_prescription(author=self.student, is_draft=True)
        # A physician keeps the predicate (profession) but loses the Django
        # permission, so only a predicate-gated link can render.
        self.doctor.groups.clear()

        html = self._timeline_html(self.doctor)

        self.assertIn(self._delete_url(draft), html)

    def test_draft_card_suppresses_the_export_and_duplicate_actions(self):
        draft = self._create_prescription(author=self.student, is_draft=True)

        html = self._timeline_html(self.doctor)

        self.assertNotIn(self._pdf_url(draft), html)
        self.assertNotIn(self._duplicate_url(draft), html)

    def test_definitive_card_keeps_the_export_and_duplicate_actions(self):
        final = self._create_prescription(author=self.doctor)

        html = self._timeline_html(self.doctor)

        self.assertIn(self._pdf_url(final), html)
        self.assertIn(self._duplicate_url(final), html)

    def test_card_never_offers_one_click_approval(self):
        self._create_prescription(author=self.student, is_draft=True)

        html = self._timeline_html(self.doctor)

        self.assertNotIn("save_final", html)
        self.assertNotIn("Aprovar", html)
