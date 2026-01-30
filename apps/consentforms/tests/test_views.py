from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.patients.models import Patient
from apps.consentforms.models import ConsentTemplate, ConsentForm, ConsentAttachment
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


class ConsentFormViewTests(TestCase):
    def setUp(self):
        self.user = create_user("admin", is_staff=True, is_superuser=True)
        self.client.force_login(self.user)
        self.patient = Patient.objects.create(
            name="Paciente Teste",
            birthday=date(1980, 1, 1),
            gender=Patient.GenderChoices.MALE,
            current_record_number="RN123",
            created_by=self.user,
            updated_by=self.user,
        )
        self.template = ConsentTemplate.objects.create(
            name="Template",
            markdown_body=(
                "{{ patient_name }} {{ patient_record_number }} {{ document_date }}\n"
                "{{ procedure_description }}"
            ),
            created_by=self.user,
            updated_by=self.user,
        )

    def test_create_consent_form(self):
        url = reverse("consentforms:consentform_create", kwargs={"patient_pk": self.patient.pk})
        response = self.client.post(
            url,
            {
                "template": str(self.template.pk),
                "document_date": "2026-01-01",
                "procedure_description": "Procedimento teste",
            },
        )
        self.assertEqual(response.status_code, 302)
        consent = ConsentForm.objects.get(patient=self.patient)
        self.assertIn("Paciente Teste", consent.rendered_markdown)
        self.assertIn("RN123", consent.rendered_markdown)

    def test_pdf_view_returns_pdf(self):
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
        url = reverse("consentforms:consentform_pdf", kwargs={"pk": consent.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_attachment_upload_images(self):
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
        url = reverse("consentforms:consentform_update", kwargs={"pk": consent.pk})
        image1 = SimpleUploadedFile(
            "page1.jpg", b"\xff\xd8\xff\xe0" + b"0" * 200, content_type="image/jpeg"
        )
        image2 = SimpleUploadedFile(
            "page2.jpg", b"\xff\xd8\xff\xe0" + b"1" * 200, content_type="image/jpeg"
        )
        data = {"attachments": [image1, image2]}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ConsentAttachment.objects.filter(consent_form=consent).count(), 2)

    def test_attachment_upload_too_many_images(self):
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
        url = reverse("consentforms:consentform_update", kwargs={"pk": consent.pk})
        images = [
            SimpleUploadedFile(
                f"page{i}.jpg", b"\xff\xd8\xff\xe0" + bytes([i]) * 200, content_type="image/jpeg"
            )
            for i in range(4)
        ]
        data = {"attachments": images}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ConsentAttachment.objects.filter(consent_form=consent).count(), 0)

    def test_non_creator_cannot_edit_attachments(self):
        creator = create_user("creator")
        consent = ConsentForm.objects.create(
            template=self.template,
            patient=self.patient,
            document_date=date(2026, 1, 1),
            procedure_description="Procedimento",
            rendered_markdown="Conteúdo",
            rendered_at=timezone.now(),
            created_by=creator,
            updated_by=creator,
            event_datetime=timezone.now(),
            description="Termo de Consentimento - Template",
            event_type=Event.CONSENT_FORM_EVENT,
        )
        other_user = create_user("other")
        self.client.force_login(other_user)
        url = reverse("consentforms:consentform_update", kwargs={"pk": consent.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
