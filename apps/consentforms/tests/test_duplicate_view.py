"""Tests for the consent form duplicate flow.

Slice 001 of change ``duplicate-consent-form``: the duplicate form exposes the
source's rendered markdown as an editable field with a one-shot date
replacement at prefill (design D6), a new independent document is frozen at
submission (D1/D2), the source is never mutated, attachments are never copied,
and the timeline card exposes the action only to users holding
``events.add_event`` (D5).
"""

from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.consentforms.forms import ConsentFormCreateForm, ConsentFormDuplicateForm
from apps.consentforms.models import ConsentAttachment, ConsentForm, ConsentTemplate
from apps.events.models import Event
from apps.patients.models import Patient

User = get_user_model()

SOURCE_DOCUMENT_DATE = date(2024, 1, 15)
SOURCE_RENDERED_MARKDOWN = (
    "Paciente: Paciente Duplicado - Prontuário RN123\n"
    "Data: 15/01/2024\n"
    "Procedimento: Procedimento de origem."
)


def today_text():
    """Return today's date in the rendering format used by render_template."""
    return timezone.localdate().strftime("%d/%m/%Y")


def expected_prefilled_markdown():
    """Return the source markdown with its baked-in date replaced by today."""
    return SOURCE_RENDERED_MARKDOWN.replace(
        SOURCE_DOCUMENT_DATE.strftime("%d/%m/%Y"),
        today_text(),
    )


class ConsentFormDuplicateViewTests(TestCase):
    """Duplicate route, prefill, copy semantics, permissions and card gating."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = User.objects.create_user(
            username="dup_doctor",
            email="dup_doctor@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        cls.doctor.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="events", codename="add_event"
            )
        )
        cls.reader = User.objects.create_user(
            username="dup_reader",
            email="dup_reader@example.com",
            password="testpass123",
            profession_type=User.NURSE,
            password_change_required=False,
            terms_accepted=True,
        )

        cls.patient = Patient.objects.create(
            name="Paciente Duplicado",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            current_record_number="RN123",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        cls.template = ConsentTemplate.objects.create(
            name="Template de Origem",
            markdown_body=(
                "{{ patient_name }} {{ patient_record_number }} "
                "{{ document_date }} {{ procedure_description }}"
            ),
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        cls.source = ConsentForm.objects.create(
            template=cls.template,
            patient=cls.patient,
            document_date=SOURCE_DOCUMENT_DATE,
            procedure_description="Procedimento de origem.",
            rendered_markdown=SOURCE_RENDERED_MARKDOWN,
            rendered_at=timezone.now() - timedelta(days=10),
            event_datetime=timezone.now() - timedelta(days=10),
            description="Termo de Consentimento - Template de Origem",
            event_type=Event.CONSENT_FORM_EVENT,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        self.client = Client()
        self.client.login(username="dup_doctor", password="testpass123")

    def _duplicate_url(self, pk=None):
        return reverse(
            "consentforms:consentform_duplicate",
            kwargs={"pk": pk or self.source.pk},
        )

    def _timeline_url(self):
        return reverse(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )

    def _copies(self):
        return ConsentForm.objects.filter(patient=self.patient).exclude(
            pk=self.source.pk
        )

    def _form_data(self, **overrides):
        data = {
            "document_date": timezone.localdate().strftime("%Y-%m-%d"),
            "procedure_description": self.source.procedure_description,
            "markdown": expected_prefilled_markdown(),
        }
        data.update(overrides)
        return data

    # R1 — route

    def test_duplicate_route_reverses_to_documented_path(self):
        self.assertEqual(
            self._duplicate_url(),
            f"/consentforms/{self.source.pk}/duplicate/",
        )

    # R2/D6 — prefill

    def test_duplicate_get_prefills_editable_markdown_with_today_date(self):
        response = self.client.get(self._duplicate_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "consentforms/consentform_duplicate_form.html"
        )
        form = response.context["form"]
        self.assertIsInstance(form, ConsentFormDuplicateForm)
        self.assertEqual(
            form.fields["markdown"].initial,
            expected_prefilled_markdown(),
        )
        self.assertIn(today_text(), form.fields["markdown"].initial)
        self.assertNotIn(
            SOURCE_DOCUMENT_DATE.strftime("%d/%m/%Y"),
            form.fields["markdown"].initial,
        )

    def test_duplicate_get_prefills_dates_and_description_from_source(self):
        response = self.client.get(self._duplicate_url())

        form = response.context["form"]
        self.assertEqual(
            form.fields["document_date"].initial,
            timezone.localdate().strftime("%Y-%m-%d"),
        )
        self.assertEqual(
            form.fields["procedure_description"].initial,
            self.source.procedure_description,
        )

    def test_duplicate_get_shows_template_read_only(self):
        response = self.client.get(self._duplicate_url())

        form = response.context["form"]
        self.assertNotIn("template", form.fields)

        content = response.content.decode()
        self.assertNotIn('id="id_template"', content)
        self.assertIn(self.template.name, content)
        self.assertIn("Duplicar Termo de Consentimento", content)

    def test_duplicate_get_context_exposes_patient_source_and_record_number(self):
        response = self.client.get(self._duplicate_url())

        self.assertEqual(response.context["patient"], self.patient)
        self.assertEqual(response.context["source"], self.source)
        self.assertEqual(response.context["patient_record_number"], "RN123")

    def test_duplicate_get_keeps_text_when_source_date_is_absent(self):
        undated_source = ConsentForm.objects.create(
            template=self.template,
            patient=self.patient,
            document_date=SOURCE_DOCUMENT_DATE,
            procedure_description="Procedimento sem data no texto.",
            rendered_markdown="Texto sem data por extenso para o paciente.",
            rendered_at=timezone.now(),
            event_datetime=timezone.now(),
            created_by=self.doctor,
            updated_by=self.doctor,
        )

        response = self.client.get(self._duplicate_url(pk=undated_source.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].fields["markdown"].initial,
            "Texto sem data por extenso para o paciente.",
        )

    def test_duplicate_date_replacement_is_one_shot_at_prefill(self):
        prefilled = self.client.get(
            self._duplicate_url()
        ).context["form"].fields["markdown"].initial
        yesterday = timezone.localdate() - timedelta(days=1)

        response = self.client.post(
            self._duplicate_url(),
            self._form_data(
                document_date=yesterday.strftime("%Y-%m-%d"),
                markdown=prefilled,
            ),
        )

        self.assertEqual(response.status_code, 302)
        copy = self._copies().get()
        self.assertEqual(copy.document_date, yesterday)
        self.assertEqual(copy.rendered_markdown, prefilled)
        self.assertIn(today_text(), copy.rendered_markdown)

    # R2/R3 — POST creates an independent document

    def test_duplicate_post_creates_independent_consent_form(self):
        started_at = timezone.now()
        edited_markdown = expected_prefilled_markdown().replace(
            "Procedimento de origem.",
            "Procedimento de origem corrigido.",
        )

        response = self.client.post(
            self._duplicate_url(),
            self._form_data(
                procedure_description="  Procedimento corrigido.  ",
                markdown=edited_markdown,
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, self._timeline_url(), fetch_redirect_response=False
        )

        copy = self._copies().get()
        self.assertEqual(copy.patient, self.patient)
        self.assertEqual(copy.template, self.template)
        self.assertEqual(copy.rendered_markdown, edited_markdown)
        self.assertEqual(copy.document_date, timezone.localdate())
        self.assertEqual(copy.procedure_description, "Procedimento corrigido.")
        self.assertEqual(copy.event_type, Event.CONSENT_FORM_EVENT)
        self.assertEqual(
            copy.description,
            "Termo de Consentimento - Template de Origem",
        )
        self.assertEqual(copy.created_by, self.doctor)
        self.assertEqual(copy.updated_by, self.doctor)
        self.assertGreater(copy.rendered_at, self.source.rendered_at)
        self.assertGreaterEqual(copy.rendered_at, started_at)
        self.assertGreaterEqual(copy.event_datetime, started_at)

        success_messages = [
            str(message) for message in get_messages(response.wsgi_request)
        ]
        self.assertTrue(
            any("duplicado" in message for message in success_messages),
            success_messages,
        )

    def test_duplicate_post_rejects_future_document_date(self):
        tomorrow = timezone.localdate() + timedelta(days=1)

        response = self.client.post(
            self._duplicate_url(),
            self._form_data(document_date=tomorrow.strftime("%Y-%m-%d")),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "document_date",
            "A data do documento não pode ser no futuro.",
        )
        self.assertEqual(self._copies().count(), 0)

    def test_duplicate_post_rejects_short_procedure_description(self):
        response = self.client.post(
            self._duplicate_url(),
            self._form_data(procedure_description="abc"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "procedure_description",
            "A descrição do procedimento é obrigatória.",
        )
        self.assertEqual(self._copies().count(), 0)

    def test_duplicate_post_rejects_blank_markdown(self):
        response = self.client.post(
            self._duplicate_url(),
            self._form_data(markdown=""),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["markdown"])
        self.assertEqual(self._copies().count(), 0)

    # R2/D2 — source integrity

    def test_duplicate_leaves_source_unchanged(self):
        snapshot = {
            "rendered_markdown": self.source.rendered_markdown,
            "rendered_at": self.source.rendered_at,
            "document_date": self.source.document_date,
            "procedure_description": self.source.procedure_description,
            "template_id": self.source.template_id,
            "description": self.source.description,
            "event_datetime": self.source.event_datetime,
            "created_by_id": self.source.created_by_id,
            "updated_by_id": self.source.updated_by_id,
        }

        self.client.get(self._duplicate_url())
        self.client.post(
            self._duplicate_url(),
            self._form_data(markdown="Texto duplicado e corrigido."),
        )

        self.source.refresh_from_db()
        for field, value in snapshot.items():
            self.assertEqual(getattr(self.source, field), value, field)

    def test_duplicate_of_source_with_attachments_starts_without_attachments(self):
        attachment = SimpleUploadedFile(
            "page1.jpg",
            b"\xff\xd8\xff\xe0" + b"0" * 200,
            content_type="image/jpeg",
        )
        ConsentAttachment.objects.create(
            consent_form=self.source,
            file=attachment,
            original_filename="page1.jpg",
            file_size=attachment.size,
            mime_type="image/jpeg",
            file_type=ConsentAttachment.FILE_TYPE_IMAGE,
            order=1,
        )

        response = self.client.post(
            self._duplicate_url(),
            self._form_data(markdown="Texto duplicado."),
        )

        self.assertEqual(response.status_code, 302)
        copy = self._copies().get()
        self.assertEqual(copy.attachments.count(), 0)
        self.assertEqual(self.source.attachments.count(), 1)

    def test_duplicate_of_deactivated_template_succeeds(self):
        ConsentTemplate.objects.filter(pk=self.template.pk).update(is_active=False)

        response = self.client.get(self._duplicate_url())
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            self._duplicate_url(),
            self._form_data(markdown="Texto duplicado com template inativo."),
        )

        self.assertEqual(response.status_code, 302)
        copy = self._copies().get()
        self.assertEqual(copy.template, self.template)
        self.assertFalse(copy.template.is_active)
        self.assertEqual(
            copy.description,
            "Termo de Consentimento - Template de Origem",
        )

    # R3/D3 — permissions

    def test_duplicate_get_requires_add_event_permission(self):
        self.client.logout()
        self.client.login(username="dup_reader", password="testpass123")

        response = self.client.get(self._duplicate_url())

        self.assertEqual(response.status_code, 403)

    def test_duplicate_post_requires_add_event_permission(self):
        self.client.logout()
        self.client.login(username="dup_reader", password="testpass123")

        response = self.client.post(
            self._duplicate_url(),
            self._form_data(markdown="Texto negado."),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._copies().count(), 0)

    def test_duplicate_get_denied_without_patient_access(self):
        with patch(
            "apps.consentforms.views.can_access_patient", return_value=False
        ):
            response = self.client.get(self._duplicate_url())

        self.assertEqual(response.status_code, 403)

    def test_duplicate_post_denied_without_patient_access(self):
        with patch(
            "apps.consentforms.views.can_access_patient", return_value=False
        ):
            response = self.client.post(
                self._duplicate_url(),
                self._form_data(markdown="Texto negado."),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._copies().count(), 0)

    def test_duplicate_unknown_consent_form_returns_404(self):
        response = self.client.get(
            self._duplicate_url(pk="00000000-0000-0000-0000-000000000000")
        )

        self.assertEqual(response.status_code, 404)

    def test_duplicate_get_requires_login(self):
        self.client.logout()

        response = self.client.get(self._duplicate_url())

        self.assertEqual(response.status_code, 403)

    # R5/D5 — timeline card gating

    def test_timeline_card_shows_duplicate_action_with_add_event(self):
        response = self.client.get(self._timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self._duplicate_url())
        self.assertContains(response, "bi-files")
        self.assertContains(response, "btn-outline-info")
        self.assertContains(response, 'aria-label="Duplicar termo de consentimento"')

    def test_timeline_card_hides_duplicate_action_without_add_event(self):
        self.client.logout()
        self.client.login(username="dup_reader", password="testpass123")

        response = self.client.get(self._timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Gerar PDF do consentimento"')
        self.assertNotContains(response, self._duplicate_url())
        self.assertNotContains(
            response, 'aria-label="Duplicar termo de consentimento"'
        )


class ConsentFormDuplicateFormTests(TestCase):
    """The duplicate form is standalone: no create-form inheritance, no re-render."""

    def test_duplicate_form_is_not_a_create_form_subclass(self):
        self.assertFalse(
            issubclass(ConsentFormDuplicateForm, ConsentFormCreateForm)
        )

    def test_duplicate_form_does_not_expose_template_field(self):
        self.assertNotIn("template", ConsentFormDuplicateForm.base_fields)
