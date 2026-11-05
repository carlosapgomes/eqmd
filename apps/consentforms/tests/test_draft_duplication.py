"""S6 R10: consent duplication sources stay definitive-only (design D14).

Drafts 404 as duplicate sources through the draft-excluding manager, and a
student-authored duplicate result persists as a draft through the model
backstop.
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


class ConsentFormDraftDuplicationTests(TestCase):
    """R10: draft sources 404, duplicate results follow the author's rules."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("cf-dup-student", User.STUDENT)
        cls.doctor = create_profession_user("cf-dup-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Consent Duplicate Patient",
            birthday="1990-01-01",
            current_record_number="RN321",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        cls.template = ConsentTemplate.objects.create(
            name="Template de Duplicação",
            markdown_body=(
                "{{ patient_name }} {{ patient_record_number }} "
                "{{ document_date }} {{ procedure_description }}"
            ),
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        cache.clear()

    def _create_consent(self, *, author=None, is_draft=False):
        author = author or self.doctor
        return ConsentForm.objects.create(
            template=self.template,
            patient=self.patient,
            document_date=date(2026, 1, 2),
            procedure_description="Procedimento de teste",
            rendered_markdown="Paciente Consent Duplicate Patient - 02/01/2026",
            rendered_at=timezone.now(),
            event_datetime=timezone.now() - timedelta(hours=1),
            description="Termo de Consentimento - Template de Duplicação",
            event_type=Event.CONSENT_FORM_EVENT,
            is_draft=is_draft,
            created_by=author,
            updated_by=author,
        )

    def _duplicate_url(self, consent):
        return reverse("consentforms:consentform_duplicate", kwargs={"pk": consent.pk})

    def _form_data(self, source, **overrides):
        data = {
            "document_date": timezone.localdate().strftime("%Y-%m-%d"),
            "procedure_description": source.procedure_description,
            "markdown": source.rendered_markdown,
        }
        data.update(overrides)
        return data

    def test_draft_source_is_a_404_for_the_author_and_physicians(self):
        draft = self._create_consent(author=self.student, is_draft=True)

        for user in (self.student, self.doctor):
            self.client.force_login(user)
            response = self.client.post(
                self._duplicate_url(draft), self._form_data(draft)
            )
            self.assertEqual(response.status_code, 404)

    def test_student_duplicate_result_persists_as_draft(self):
        source = self._create_consent(author=self.doctor)
        self.client.force_login(self.student)

        response = self.client.post(
            self._duplicate_url(source), self._form_data(source)
        )

        self.assertEqual(response.status_code, 302)
        copy = ConsentForm.all_objects.get(
            created_by=self.student, is_draft=True
        )
        self.assertNotEqual(copy.pk, source.pk)
        self.assertEqual(copy.procedure_description, source.procedure_description)

    def test_physician_duplicate_result_stays_definitive(self):
        source = self._create_consent(author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.post(
            self._duplicate_url(source), self._form_data(source)
        )

        self.assertEqual(response.status_code, 302)
        copy = (
            ConsentForm.all_objects.filter(created_by=self.doctor)
            .exclude(pk=source.pk)
            .get()
        )
        self.assertFalse(copy.is_draft)
