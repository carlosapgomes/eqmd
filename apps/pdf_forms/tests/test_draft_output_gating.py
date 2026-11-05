"""S2 R2: PDF submission drafts are readable, never exportable (design D10).

The submission detail screen resolves human drafts for review (bot drafts keep
404) while the download endpoint denies drafts for every user and keeps serving
final submissions as before.
"""

from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from apps.pdf_forms.tests.factories import (
    PatientFactory,
    PDFFormSubmissionFactory,
    PDFFormTemplateFactory,
    UserFactory,
)


class PDFFormSubmissionDraftVisibilityTests(TestCase):
    """R2: detail resolves human drafts, bot drafts stay 404."""

    def setUp(self):
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)
        self.client.force_login(self.user)

    def _create_submission(self, *, is_draft, draft_created_by_bot=""):
        return PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            is_draft=is_draft,
            draft_created_by_bot=draft_created_by_bot,
        )

    def _detail_url(self, submission):
        return reverse("pdf_forms:submission_detail", kwargs={"pk": submission.pk})

    def test_detail_resolves_human_draft(self):
        draft = self._create_submission(is_draft=True)

        response = self.client.get(self._detail_url(draft))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["submission"], draft)
        self.assertContains(response, self.template.name)

    def test_detail_keeps_bot_drafts_hidden(self):
        bot_draft = self._create_submission(
            is_draft=True, draft_created_by_bot="bot-client-1"
        )

        response = self.client.get(self._detail_url(bot_draft))

        self.assertEqual(response.status_code, 404)

    def test_detail_keeps_serving_final_submission(self):
        final = self._create_submission(is_draft=False)

        response = self.client.get(self._detail_url(final))

        self.assertEqual(response.status_code, 200)


class PDFFormDownloadDraftGatingTests(TestCase):
    """R2: download denies drafts for all users and serves finals."""

    def setUp(self):
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)
        self.client.force_login(self.user)

    def _create_submission(self, *, is_draft, draft_created_by_bot=""):
        return PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            is_draft=is_draft,
            draft_created_by_bot=draft_created_by_bot,
        )

    def _download_url(self, submission):
        return reverse("pdf_forms:pdf_download", kwargs={"submission_id": submission.pk})

    def test_download_denies_human_draft(self):
        draft = self._create_submission(is_draft=True)

        response = self.client.get(self._download_url(draft))

        self.assertEqual(response.status_code, 404)

    def test_download_denies_bot_draft(self):
        bot_draft = self._create_submission(
            is_draft=True, draft_created_by_bot="bot-client-1"
        )

        response = self.client.get(self._download_url(bot_draft))

        self.assertEqual(response.status_code, 404)

    @patch("apps.pdf_forms.services.pdf_overlay.PDFFormOverlay.generate_pdf_response")
    def test_download_serves_final_submission(self, mock_generate_pdf):
        final = self._create_submission(is_draft=False)
        mock_generate_pdf.return_value = HttpResponse(
            b"pdf", content_type="application/pdf"
        )

        response = self.client.get(self._download_url(final))

        self.assertEqual(response.status_code, 200)
        mock_generate_pdf.assert_called_once()

    def test_duplicate_keeps_drafts_out_as_sources(self):
        draft = self._create_submission(is_draft=True)

        response = self.client.get(
            reverse("pdf_forms:submission_duplicate", kwargs={"pk": draft.pk})
        )

        self.assertEqual(response.status_code, 404)
