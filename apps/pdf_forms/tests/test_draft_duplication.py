"""S6 R9: PDF duplication sources stay definitive-only (design D14).

Drafts 404 as duplicate sources, the template opt-in rules are unchanged, and
a student-authored duplicate result persists as a draft through the model
backstop.
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

from ..models import PDFFormSubmission
from .factories import PDFFormTemplateFactory

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class PDFSubmissionDraftDuplicationTests(TestCase):
    """R9: draft sources 404, opt-in preserved, student results are drafts."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("pdf-dup-student", User.STUDENT)
        cls.doctor = create_profession_user("pdf-dup-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="PDF Duplicate Patient",
            birthday="1990-01-01",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        cls.template = PDFFormTemplateFactory(
            name="Formulário Duplicável",
            created_by=cls.doctor,
            allow_duplication=True,
            form_fields={
                "notes": {"type": "textarea", "required": False, "label": "Notas"},
            },
        )
        cls.closed_template = PDFFormTemplateFactory(
            name="Formulário Sem Duplicação",
            created_by=cls.doctor,
            allow_duplication=False,
            form_fields={
                "notes": {"type": "textarea", "required": False, "label": "Notas"},
            },
        )

    def setUp(self):
        cache.clear()

    def _create_submission(self, *, author=None, is_draft=False, template=None):
        author = author or self.doctor
        return PDFFormSubmission.objects.create(
            form_template=template or self.template,
            patient=self.patient,
            created_by=author,
            updated_by=author,
            event_datetime=timezone.now() - timedelta(hours=1),
            description="Formulário PDF de teste",
            form_data={"notes": "Nota original"},
            is_draft=is_draft,
        )

    def _duplicate_url(self, submission):
        return reverse(
            "pdf_forms:submission_duplicate", kwargs={"pk": submission.pk}
        )

    def test_draft_source_is_a_404_for_the_author_and_physicians(self):
        draft = self._create_submission(author=self.student, is_draft=True)

        for user in (self.student, self.doctor):
            self.client.force_login(user)
            response = self.client.get(self._duplicate_url(draft))
            self.assertEqual(response.status_code, 404)

    def test_student_duplicate_result_persists_as_draft(self):
        source = self._create_submission(author=self.doctor)
        self.client.force_login(self.student)

        response = self.client.post(
            self._duplicate_url(source), {"notes": "Nota original"}
        )

        self.assertEqual(response.status_code, 302)
        copy = PDFFormSubmission.all_objects.get(
            created_by=self.student, is_draft=True
        )
        self.assertNotEqual(copy.pk, source.pk)
        self.assertEqual(copy.form_data["notes"], "Nota original")

    def test_physician_duplicate_result_stays_definitive(self):
        source = self._create_submission(author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.post(
            self._duplicate_url(source), {"notes": "Nota original"}
        )

        self.assertEqual(response.status_code, 302)
        copy = (
            PDFFormSubmission.all_objects.filter(created_by=self.doctor)
            .exclude(pk=source.pk)
            .get()
        )
        self.assertFalse(copy.is_draft)

    def test_template_opt_in_rules_are_unchanged(self):
        """R9 regression: a template without the opt-in still denies duplication."""
        source = self._create_submission(template=self.closed_template)
        self.client.force_login(self.doctor)

        response = self.client.get(self._duplicate_url(source))

        self.assertEqual(response.status_code, 403)
