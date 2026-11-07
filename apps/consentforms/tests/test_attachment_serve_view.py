"""Tests for the authenticated consent attachment serve surface (design D3).

Storage writes go to a temporary media root so fixtures never touch the real
``MEDIA_ROOT`` (same pattern as ``apps/pdf_forms/tests``).
"""

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import resolve, reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.events.models import Event
from apps.events.services.event_deletion import delete_event_record
from apps.patients.models import Patient

from ..admin import ConsentAttachmentServeFileInput
from ..models import ConsentAttachment, ConsentForm, ConsentTemplate
from ..views import ConsentAttachmentServeView

TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="consentforms_attachment_serve_"))

IMAGE_BYTES = b"\xff\xd8\xff\xe0" + b"0" * 200
PDF_BYTES = (
    b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    b"trailer\n<<\n/Root 1 0 R\n>>\n%%EOF\n"
)

CHECK_ACCESS_PATH = "apps.consentforms.views.can_access_patient"
OPEN_PATH = "django.db.models.fields.files.FieldFile.open"


def serve_url(attachment):
    return reverse(
        "consentforms:consentattachment_serve", kwargs={"pk": attachment.pk}
    )


def stored_bytes(attachment):
    with attachment.file.open("rb") as file_obj:
        return file_obj.read()


class ConsentAttachmentServeRouteTests(SimpleTestCase):
    """R2/AC1: the serve route exists and resolves to the serve view."""

    def test_serve_route_resolves_to_serve_view(self):
        attachment_id = "8a0d5b7e-4123-4db2-9f1a-0d2c3b4a5e6f"

        url = reverse(
            "consentforms:consentattachment_serve", kwargs={"pk": attachment_id}
        )

        self.assertEqual(url, f"/consentforms/attachments/{attachment_id}/serve/")
        self.assertEqual(resolve(url).func.view_class, ConsentAttachmentServeView)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ConsentAttachmentServeViewTests(TestCase):
    """R1/R5: bytes, headers, permission gates and parent visibility."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_navigation_user(
            username="serve-owner",
            email="serve-owner@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        cls.patient = Patient.objects.create(
            name="Paciente Anexo",
            birthday=date(1980, 1, 1),
            gender=Patient.GenderChoices.MALE,
            current_record_number="RN555",
            created_by=cls.user,
            updated_by=cls.user,
        )
        cls.template = ConsentTemplate.objects.create(
            name="Template Anexo",
            markdown_body=(
                "{{ patient_name }} {{ patient_record_number }} {{ document_date }}\n"
                "{{ procedure_description }}"
            ),
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def create_consent(self, *, is_draft=False, draft_created_by_bot=""):
        return ConsentForm.objects.create(
            template=self.template,
            patient=self.patient,
            document_date=date(2026, 1, 2),
            procedure_description="Procedimento de teste",
            rendered_markdown="Paciente Anexo - Conteúdo.",
            rendered_at=timezone.now(),
            event_datetime=timezone.now(),
            description="Termo de Consentimento - Template Anexo",
            event_type=Event.CONSENT_FORM_EVENT,
            is_draft=is_draft,
            draft_created_by_bot=draft_created_by_bot,
            created_by=self.user,
            updated_by=self.user,
        )

    def create_attachment(
        self,
        consent_form=None,
        *,
        filename="page1.jpg",
        content_type="image/jpeg",
        mime_type="image/jpeg",
        payload=IMAGE_BYTES,
        file_type=ConsentAttachment.FILE_TYPE_IMAGE,
        original_filename=None,
    ):
        consent_form = consent_form or self.create_consent()
        return ConsentAttachment.objects.create(
            consent_form=consent_form,
            file=SimpleUploadedFile(filename, payload, content_type=content_type),
            original_filename=original_filename or filename,
            file_size=len(payload),
            mime_type=mime_type,
            file_type=file_type,
            order=1,
        )

    def test_authorized_user_receives_inline_bytes(self):
        attachment = self.create_attachment()

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertTrue(response["Content-Disposition"].startswith("inline;"))
        self.assertNotIn("attachment;", response["Content-Disposition"])
        self.assertIn('filename="page1.jpg"', response["Content-Disposition"])
        body = b"".join(response.streaming_content)
        self.assertEqual(body, stored_bytes(attachment))
        self.assertGreater(len(body), 0)

    def test_pdf_attachment_is_served_inline(self):
        attachment = self.create_attachment(
            filename="laudo.pdf",
            content_type="application/pdf",
            mime_type="application/pdf",
            payload=PDF_BYTES,
            file_type=ConsentAttachment.FILE_TYPE_PDF,
        )

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response["Content-Disposition"].startswith("inline;"))
        self.assertEqual(b"".join(response.streaming_content), PDF_BYTES)

    def test_response_is_privately_cacheable(self):
        attachment = self.create_attachment()

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response["Cache-Control"], "private")

    @override_settings(DEBUG=False)
    def test_serve_works_with_debug_disabled(self):
        attachment = self.create_attachment()

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(b"".join(response.streaming_content), IMAGE_BYTES)

    def test_patient_denial_returns_403(self):
        attachment = self.create_attachment()

        with patch(CHECK_ACCESS_PATH, return_value=False):
            response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 403)

    def test_access_check_receives_request_user_and_patient(self):
        attachment = self.create_attachment()

        with patch(CHECK_ACCESS_PATH, return_value=True) as check_access:
            response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 200)
        check_access.assert_called_once_with(self.user, self.patient)

    def test_patient_denial_happens_before_the_file_is_opened(self):
        attachment = self.create_attachment()

        with patch(CHECK_ACCESS_PATH, return_value=False), patch(OPEN_PATH) as open_file:
            response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 403)
        open_file.assert_not_called()

    def test_anonymous_request_redirects_to_login(self):
        attachment = self.create_attachment()
        self.client.logout()

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_missing_view_event_permission_is_denied(self):
        attachment = self.create_attachment()
        plain_user = create_navigation_user(
            username="serve-no-perm",
            email="serve-no-perm@example.com",
            password="testpass123",
        )
        self.client.force_login(plain_user)

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 403)

    def test_mime_fallback_guesses_from_extension(self):
        attachment = self.create_attachment(
            filename="scan.png", content_type="", mime_type=""
        )
        self.assertEqual(attachment.mime_type, "")

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

    def test_mime_fallback_defaults_to_octet_stream(self):
        # Upload rejects unknown extensions, so craft the stored name directly.
        attachment = self.create_attachment()
        stored_name = "consent_forms/2020/01/attachments/scan.qqq"
        path = Path(TEST_MEDIA_ROOT) / stored_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(IMAGE_BYTES)
        attachment.file.name = stored_name
        attachment.mime_type = ""
        attachment.save(update_fields=["file", "mime_type"])

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/octet-stream")

    def test_human_draft_attachment_serves(self):
        draft = self.create_consent(is_draft=True)
        attachment = self.create_attachment(draft)

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), IMAGE_BYTES)

    def test_bot_draft_parent_returns_404(self):
        bot_draft = self.create_consent(
            is_draft=True, draft_created_by_bot="bot-client-1"
        )
        attachment = self.create_attachment(bot_draft)

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 404)

    def test_soft_deleted_parent_returns_404(self):
        consent = self.create_consent()
        attachment = self.create_attachment(consent)
        delete_event_record(consent, deleted_by=self.user)

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 404)

    def test_unknown_attachment_returns_404(self):
        response = self.client.get(
            reverse(
                "consentforms:consentattachment_serve",
                kwargs={"pk": "3f7d1c9a-0000-4000-8000-000000000000"},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_missing_file_on_disk_returns_404(self):
        attachment = self.create_attachment()
        attachment.file.name = "consent_forms/2020/01/missing.jpg"
        attachment.save(update_fields=["file"])
        self.assertFalse(Path(attachment.file.path).exists())

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 404)

    def test_quoted_filename_is_served_safely(self):
        attachment = self.create_attachment()
        ConsentAttachment.objects.filter(pk=attachment.pk).update(
            original_filename='laudo "especial".jpg'
        )

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 200)
        disposition = response["Content-Disposition"]
        self.assertTrue(disposition.startswith("inline;"))
        self.assertIn('filename="laudo \\"especial\\".jpg"', disposition)
        self.assertNotIn("\n", disposition)
        self.assertNotIn("\r", disposition)

    def test_unicode_filename_is_served_safely(self):
        attachment = self.create_attachment(original_filename="formulário-saúde.jpg")

        response = self.client.get(serve_url(attachment))

        self.assertEqual(response.status_code, 200)
        self.assertIn("filename*=utf-8''", response["Content-Disposition"])


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ConsentAttachmentLinkTests(TestCase):
    """R3/R4/AC5: every consent surface links the serve route, never raw media."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_navigation_user(
            username="serve-links",
            email="serve-links@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        cls.patient = Patient.objects.create(
            name="Paciente Links",
            birthday=date(1985, 5, 5),
            gender=Patient.GenderChoices.MALE,
            current_record_number="RN777",
            created_by=cls.user,
            updated_by=cls.user,
        )
        cls.template = ConsentTemplate.objects.create(
            name="Template Links",
            markdown_body=(
                "{{ patient_name }} {{ patient_record_number }} {{ document_date }}\n"
                "{{ procedure_description }}"
            ),
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def create_consent(self):
        return ConsentForm.objects.create(
            template=self.template,
            patient=self.patient,
            document_date=date(2026, 1, 3),
            procedure_description="Procedimento de links",
            rendered_markdown="Paciente Links - Conteúdo.",
            rendered_at=timezone.now(),
            event_datetime=timezone.now(),
            description="Termo de Consentimento - Template Links",
            event_type=Event.CONSENT_FORM_EVENT,
            created_by=self.user,
            updated_by=self.user,
        )

    def create_attachment(self):
        consent_form = self.create_consent()
        image = SimpleUploadedFile("page1.jpg", IMAGE_BYTES, content_type="image/jpeg")
        return ConsentAttachment.objects.create(
            consent_form=consent_form,
            file=image,
            original_filename="page1.jpg",
            file_size=image.size,
            mime_type="image/jpeg",
            file_type=ConsentAttachment.FILE_TYPE_IMAGE,
            order=1,
        )

    def test_detail_page_links_serve_route(self):
        attachment = self.create_attachment()

        response = self.client.get(
            reverse(
                "consentforms:consentform_detail",
                kwargs={"pk": attachment.consent_form.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f'href="{serve_url(attachment)}"', content)
        self.assertNotIn(attachment.file.url, content)

    def test_update_page_links_serve_route_for_links_and_images(self):
        attachment = self.create_attachment()

        response = self.client.get(
            reverse(
                "consentforms:consentform_update",
                kwargs={"pk": attachment.consent_form.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f'href="{serve_url(attachment)}"', content)
        self.assertIn(f'src="{serve_url(attachment)}"', content)
        self.assertNotIn(attachment.file.url, content)

    def test_attachment_admin_change_form_links_serve_route(self):
        attachment = self.create_attachment()

        response = self.client.get(
            reverse("admin:consentforms_consentattachment_change", args=[attachment.pk])
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f'href="{serve_url(attachment)}"', content)
        self.assertNotIn(attachment.file.url, content)

    def test_consent_admin_inline_links_serve_route(self):
        attachment = self.create_attachment()

        response = self.client.get(
            reverse("admin:consentforms_consentform_change", args=[attachment.consent_form.pk])
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f'href="{serve_url(attachment)}"', content)
        self.assertNotIn(attachment.file.url, content)

    def test_widget_resolves_serve_url_from_value_instance(self):
        attachment = self.create_attachment()

        context = ConsentAttachmentServeFileInput().get_context(
            "file", attachment.file, {}
        )

        self.assertEqual(context["widget"]["value"].url, serve_url(attachment))
        self.assertEqual(str(context["widget"]["value"]), attachment.file.name)

    def test_admin_file_widget_does_not_mutate_stored_field(self):
        attachment = self.create_attachment()
        stored_name = attachment.file.name

        response = self.client.get(
            reverse("admin:consentforms_consentattachment_change", args=[attachment.pk])
        )

        self.assertEqual(response.status_code, 200)
        attachment.refresh_from_db()
        self.assertEqual(attachment.file.name, stored_name)
        self.assertTrue(Path(attachment.file.path).exists())
