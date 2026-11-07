"""Tests for the authenticated PDF template preview surface (design D2).

Storage writes go to a temporary media root so fixtures never touch the real
``MEDIA_ROOT`` (same pattern as ``apps/mediafiles/tests``).
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import resolve, reverse

from apps.pdf_forms.admin import PDFFormTemplateAdmin, TemplatePreviewFileInput
from apps.pdf_forms.models import PDFFormTemplate
from apps.pdf_forms.tests.factories import (
    PDFFormTemplateFactory,
    SuperUserFactory,
    UserFactory,
)
from apps.pdf_forms.views import PDFFormTemplatePreviewView

TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="pdf_forms_template_preview_"))

PDF_BYTES = (
    b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    b"trailer\n<<\n/Root 1 0 R\n>>\n%%EOF\n"
)

CHECK_ACCESS_PATH = "apps.pdf_forms.views.base_views.check_pdf_form_template_access"


def preview_url(template):
    return reverse("pdf_forms:template_preview", kwargs={"pk": template.pk})


def stored_bytes(template):
    with template.pdf_file.open("rb") as file_obj:
        return file_obj.read()


def template_with_filename(filename, created_by):
    """Create a template whose stored file keeps the given upload name."""
    return PDFFormTemplateFactory(
        created_by=created_by,
        pdf_file=SimpleUploadedFile(
            filename, PDF_BYTES, content_type="application/pdf"
        ),
    )


class PDFFormTemplatePreviewRouteTests(SimpleTestCase):
    """R2/AC1: the preview route exists and resolves to the serve view."""

    def test_preview_route_resolves_to_preview_view(self):
        template_id = "f26ce283-8713-4534-9fe1-88cb9c09c45c"

        url = reverse("pdf_forms:template_preview", kwargs={"pk": template_id})

        self.assertEqual(url, f"/pdf-forms/template/{template_id}/preview/")
        self.assertEqual(resolve(url).func.view_class, PDFFormTemplatePreviewView)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PDFFormTemplatePreviewViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)

    def test_authenticated_user_receives_inline_pdf_bytes(self):
        response = self.client.get(preview_url(self.template))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response["Content-Disposition"].startswith("inline;"))
        self.assertNotIn("attachment", response["Content-Disposition"])
        self.assertIn(
            f'filename="{Path(self.template.pdf_file.name).name}"',
            response["Content-Disposition"],
        )
        body = b"".join(response.streaming_content)
        self.assertEqual(body, stored_bytes(self.template))
        self.assertGreater(len(body), 0)

    def test_response_is_privately_cacheable(self):
        response = self.client.get(preview_url(self.template))

        self.assertEqual(response["Cache-Control"], "private")

    def test_gate_uses_existing_template_access_helper(self):
        with patch(CHECK_ACCESS_PATH, return_value=True) as check_access:
            response = self.client.get(preview_url(self.template))

        self.assertEqual(response.status_code, 200)
        check_access.assert_called_once_with(self.user)

    def test_inactive_template_previews(self):
        inactive = PDFFormTemplateFactory(created_by=self.user, is_active=False)

        response = self.client.get(preview_url(inactive))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), stored_bytes(inactive))

    @override_settings(DEBUG=False)
    def test_preview_works_with_debug_disabled(self):
        response = self.client.get(preview_url(self.template))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(b"".join(response.streaming_content), stored_bytes(self.template))

    def test_anonymous_request_redirects_to_login(self):
        self.client.logout()

        response = self.client.get(preview_url(self.template))

        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.LOGIN_URL, response["Location"])

    def test_unknown_template_returns_404(self):
        response = self.client.get(
            reverse("pdf_forms:template_preview", kwargs={"pk": "3f7d1c9a-0000-4000-8000-000000000000"})
        )

        self.assertEqual(response.status_code, 404)

    def test_missing_file_on_disk_returns_404(self):
        template = PDFFormTemplateFactory(created_by=self.user)
        template.pdf_file.name = "pdf_forms/templates/2020/01/missing.pdf"
        template._skip_validation = True
        template.save(update_fields=["pdf_file"])
        self.assertFalse(Path(template.pdf_file.path).exists())

        response = self.client.get(preview_url(template))

        self.assertEqual(response.status_code, 404)

    def store_template_named(self, stored_name):
        """Create a template whose *stored* name is exactly ``stored_name``."""
        template = PDFFormTemplateFactory(created_by=self.user)
        path = Path(settings.MEDIA_ROOT) / stored_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(PDF_BYTES)
        template.pdf_file.name = stored_name
        template._skip_validation = True
        template.save(update_fields=["pdf_file"])
        return template

    def test_quoted_filename_is_served_safely(self):
        # Upload sanitises quotes away, so craft the stored name directly.
        template = self.store_template_named('pdf_forms/templates/laudo "especial".pdf')

        response = self.client.get(preview_url(template))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(b"".join(response.streaming_content), PDF_BYTES)
        disposition = response["Content-Disposition"]
        self.assertTrue(disposition.startswith("inline;"))
        self.assertIn('filename="laudo \\"especial\\".pdf"', disposition)
        self.assertNotIn("\n", disposition)
        self.assertNotIn("\r", disposition)

    def test_unicode_filename_is_served_safely(self):
        template = template_with_filename("formulário-saúde.pdf", self.user)

        response = self.client.get(preview_url(template))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(b"".join(response.streaming_content), PDF_BYTES)
        self.assertIn("filename*=utf-8''", response["Content-Disposition"])


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class PDFFormTemplatePreviewLinkTests(TestCase):
    """Every pdf_forms surface must link the preview route, never raw media."""

    def setUp(self):
        self.client = Client()
        self.user = SuperUserFactory()
        self.client.force_login(self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)

    def test_admin_pdf_preview_links_preview_route(self):
        admin = PDFFormTemplateAdmin(PDFFormTemplate, AdminSite())

        rendered = admin.pdf_preview(self.template)

        self.assertIn(preview_url(self.template), rendered)
        self.assertNotIn(self.template.pdf_file.url, rendered)

    def test_template_list_links_preview_route(self):
        response = self.client.get(reverse("pdf_forms:template_list"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(preview_url(self.template), content)
        self.assertNotIn(self.template.pdf_file.url, content)

    def test_change_form_widget_links_preview_route(self):
        response = self.client.get(
            reverse("admin:pdf_forms_pdfformtemplate_change", args=[self.template.pk])
        )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f'href="{preview_url(self.template)}"', content)
        self.assertIn(Path(self.template.pdf_file.name).name, content)
        self.assertNotIn(self.template.pdf_file.url, content)

    def test_widget_resolves_preview_url_from_value_instance(self):
        other = PDFFormTemplateFactory(created_by=self.user)

        context = TemplatePreviewFileInput().get_context(
            "pdf_file", self.template.pdf_file, {}
        )

        self.assertEqual(context["widget"]["value"].url, preview_url(self.template))
        self.assertEqual(str(context["widget"]["value"]), self.template.pdf_file.name)
        self.assertNotEqual(preview_url(self.template), preview_url(other))

    def test_widget_link_does_not_mutate_stored_field(self):
        stored_name = self.template.pdf_file.name

        response = self.client.get(
            reverse("admin:pdf_forms_pdfformtemplate_change", args=[self.template.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.template.refresh_from_db()
        self.assertEqual(self.template.pdf_file.name, stored_name)
        self.assertTrue(Path(self.template.pdf_file.path).exists())
