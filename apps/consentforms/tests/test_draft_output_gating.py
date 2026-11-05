"""S6 R7/R8: consent document output denies drafts (design D10).

The consent PDF endpoint denies drafts for every user and keeps serving
definitive forms; the attachments ZIP endpoint is verified denied for drafts
by its draft-excluding default-manager lookup (no code change required).
"""

from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.events.models import Event
from apps.patients.models import Patient

from ..models import ConsentAttachment, ConsentForm, ConsentTemplate

User = get_user_model()


def create_profession_user(username, profession_type):
    """Create a lifecycle-ready user; the profession signal assigns the group."""
    return create_navigation_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        profession_type=profession_type,
    )


class ConsentFormDraftOutputGatingTests(TestCase):
    """R7: no document output for draft consent forms."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_groups", stdout=StringIO())
        cls.student = create_profession_user("cf-output-student", User.STUDENT)
        cls.doctor = create_profession_user("cf-output-doctor", User.MEDICAL_DOCTOR)
        cls.patient = Patient.objects.create(
            name="Consent Output Patient",
            birthday="1990-01-01",
            current_record_number="RN111",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        cls.template = ConsentTemplate.objects.create(
            name="Template de Saída",
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
            rendered_markdown="Paciente Consent Output Patient - Conteúdo.",
            rendered_at=timezone.now(),
            event_datetime=timezone.now() - timedelta(hours=1),
            description="Termo de Consentimento - Template de Saída",
            event_type=Event.CONSENT_FORM_EVENT,
            is_draft=is_draft,
            created_by=author,
            updated_by=author,
        )

    def _pdf_url(self, consent):
        return reverse("consentforms:consentform_pdf", kwargs={"pk": consent.pk})

    def _zip_url(self, consent):
        return reverse(
            "consentforms:consentform_attachments_zip", kwargs={"pk": consent.pk}
        )

    def test_pdf_denies_a_human_draft_for_every_user(self):
        draft = self._create_consent(author=self.student, is_draft=True)

        for user in (self.student, self.doctor):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self._pdf_url(draft)).status_code, 404)

    def test_pdf_serves_a_definitive_consent(self):
        final = self._create_consent(author=self.doctor)
        self.client.force_login(self.doctor)

        response = self.client.get(self._pdf_url(final))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_attachments_zip_is_denied_for_a_draft(self):
        """R8: verified denied by construction (default manager excludes drafts)."""
        draft = self._create_consent(author=self.student, is_draft=True)
        self.client.force_login(self.doctor)

        response = self.client.get(self._zip_url(draft))

        self.assertEqual(response.status_code, 404)

    def test_attachments_zip_serves_a_definitive_consent(self):
        final = self._create_consent(author=self.doctor)
        ConsentAttachment.objects.create(
            consent_form=final,
            file=SimpleUploadedFile(
                "page1.jpg",
                b"\xff\xd8\xff\xe0" + b"0" * 200,
                content_type="image/jpeg",
            ),
            original_filename="page1.jpg",
            file_size=204,
            mime_type="image/jpeg",
            file_type=ConsentAttachment.FILE_TYPE_IMAGE,
            order=1,
        )
        self.client.force_login(self.doctor)

        response = self.client.get(self._zip_url(final))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
