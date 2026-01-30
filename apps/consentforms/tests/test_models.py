from datetime import date
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.patients.models import Patient
from apps.consentforms.models import ConsentTemplate, ConsentForm
from apps.events.models import Event


def create_user(username="user", is_staff=False, is_superuser=False):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        is_staff=is_staff,
        is_superuser=is_superuser,
    )
    user.terms_accepted = True
    user.password_change_required = False
    user.save(update_fields=["terms_accepted", "password_change_required"])
    return user


class ConsentTemplateModelTests(TestCase):
    def setUp(self):
        self.user = create_user()

    def test_template_requires_placeholders(self):
        template = ConsentTemplate(
            name="Template inválido",
            markdown_body="Consentimento {{ patient_name }}",
            created_by=self.user,
            updated_by=self.user,
        )
        with self.assertRaises(ValidationError):
            template.save()

    def test_template_accepts_valid_placeholders(self):
        template = ConsentTemplate(
            name="Template válido",
            markdown_body="{{ patient_name }} {{ patient_record_number }} {{ document_date }}",
            created_by=self.user,
            updated_by=self.user,
        )
        template.save()
        self.assertTrue(ConsentTemplate.objects.filter(pk=template.pk).exists())


class ConsentFormImmutabilityTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.patient = Patient.objects.create(
            name="Paciente Teste",
            birthday=date(1980, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.user,
            updated_by=self.user,
        )
        self.template = ConsentTemplate.objects.create(
            name="Template",
            markdown_body="{{ patient_name }} {{ patient_record_number }} {{ document_date }}",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_rendered_markdown_is_immutable(self):
        consent = ConsentForm.objects.create(
            template=self.template,
            patient=self.patient,
            document_date=date(2026, 1, 1),
            procedure_description="Procedimento",
            rendered_markdown="Conteúdo",
            rendered_at=timezone.now(),
            created_by=self.user,
            updated_by=self.user,
            event_datetime=timezone.now(),
            description="Termo de Consentimento - Template",
            event_type=Event.CONSENT_FORM_EVENT,
        )

        consent.rendered_markdown = "Conteúdo alterado"
        with self.assertRaises(ValidationError):
            consent.save()
