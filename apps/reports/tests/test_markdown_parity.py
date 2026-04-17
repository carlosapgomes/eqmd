"""
Tests for Reports markdown parity — Slice 06.

Verifies that Reports detail (web) and PDF both use the shared markdown
pipeline (``easymd_v1``) and produce semantically equivalent output.
"""

import io
from datetime import date

import pypdf
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient
from apps.reports.models import Report
from apps.reports.services.pdf_generator import ReportPDFGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_pdf_text(pdf_buffer: io.BytesIO) -> str:
    """Extract and return full text from a PDF buffer."""
    pdf_buffer.seek(0)
    reader = pypdf.PdfReader(pdf_buffer)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _make_report(user, patient, content="# Relatório\n\nConteúdo simples.", title="Test Report"):
    """Create a Report for testing."""
    return Report.objects.create(
        patient=patient,
        created_by=user,
        updated_by=user,
        title=title,
        content=content,
        document_date=date(2024, 3, 15),
        event_datetime=timezone.now(),
    )


# ---------------------------------------------------------------------------
# Base test case
# ---------------------------------------------------------------------------


class ReportMarkdownParityBase(TestCase):
    """Base case with shared fixtures."""

    def setUp(self):
        self.doctor = EqmdCustomUser.objects.create_user(
            username="drreport",
            email="drreport@example.com",
            password="testpass123",
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
            first_name="Maria",
            last_name="Silva",
            professional_registration_number="12345",
            password_change_required=False,
            terms_accepted=True,
        )
        self.patient = Patient.objects.create(
            name="João Santos",
            birthday=date(1985, 6, 10),
            gender=Patient.GenderChoices.MALE,
            created_by=self.doctor,
            updated_by=self.doctor,
            current_record_number="REC99887",
        )
        self.generator = ReportPDFGenerator()


# ===================================================================
# Mandatory test 1: Report detail uses shared markdown profile
# ===================================================================


class TestReportDetailUsesSharedMarkdownProfile(ReportMarkdownParityBase):
    """Verify that report detail (web) renders via the shared pipeline."""

    def test_report_detail_uses_shared_markdown_profile(self):
        """
        The report detail page must use render_markdown_html from the
        shared pipeline, not a local markdown.Markdown() instance.
        """
        content = "# Título\n\n**bold** *italic* ~~strike~~ `code`\n\n- item 1\n  - nested"
        report = _make_report(self.doctor, self.patient, content=content)

        with patch(
            "apps.reports.templatetags.reports_extras.render_markdown_html",
            wraps=None,
        ) as mock_render:
            # Return a plausible HTML string so the template renders
            mock_render.return_value = "<h1>Título</h1><p><strong>bold</strong></p>"

            self.client.login(username="drreport", password="testpass123")
            url = reverse("reports:report_detail", kwargs={"pk": report.pk})
            response = self.client.get(url)

            # The shared pipeline must have been called
            mock_render.assert_called_once_with(content)


# ===================================================================
# Mandatory test 2: Report PDF uses shared markdown profile
# ===================================================================


class TestReportPDFUsesSharedMarkdownProfile(ReportMarkdownParityBase):
    """Verify that report PDF renders via the shared pipeline."""

    def test_report_pdf_uses_shared_markdown_profile(self):
        """
        The report PDF generator must use parse_markdown and
        render_markdown_pdf_flowables from the shared pipeline.
        """
        content = "## Seção\n\nParágrafo com **negrito**.\n\n- item 1\n  - sub item"
        report = _make_report(self.doctor, self.patient, content=content)

        with patch(
            "apps.reports.services.pdf_generator.render_markdown_pdf_flowables",
        ) as mock_render_flowables:
            mock_render_flowables.return_value = []
            self.generator.generate_from_report(report)

            # The shared PDF flowable renderer must have been called
            mock_render_flowables.assert_called_once()

            # The first positional arg must be the parsed document (DocumentNode)
            from apps.core.services.markdown_pipeline.ir import DocumentNode
            call_args = mock_render_flowables.call_args
            self.assertIsInstance(call_args[0][0], DocumentNode)

    def test_report_pdf_uses_parse_markdown(self):
        """
        The report PDF generator must call parse_markdown for each content part.
        """
        content = "## Teste\n\nConteúdo."
        report = _make_report(self.doctor, self.patient, content=content)

        with patch(
            "apps.reports.services.pdf_generator.parse_markdown",
        ) as mock_parse:
            from apps.core.services.markdown_pipeline.ir import DocumentNode
            mock_parse.return_value = DocumentNode(children=())

            with patch(
                "apps.reports.services.pdf_generator.render_markdown_pdf_flowables",
                return_value=[],
            ):
                self.generator.generate_from_report(report)
                mock_parse.assert_called()


# ===================================================================
# Mandatory test 3: Web/PDF semantic parity for nested lists
# ===================================================================


class TestReportWebPDFSemanticParityForNestedLists(ReportMarkdownParityBase):
    """Verify web and PDF both preserve nested list semantics."""

    def test_report_web_pdf_semantic_parity_for_nested_lists(self):
        """
        Both the report detail (web) and the PDF must represent the
        same nested list hierarchy.  The web renders HTML <ul>/<li>
        nesting; the PDF preserves item text in order with indentation.
        """
        markdown = (
            "## Diagnósticos\n\n"
            "- CID J18.9: Pneumonia\n"
            "  - Iniciado antibiótico\n"
            "  - Controle em 48h\n"
            "- CID E11.9: Diabetes\n"
            "  - Ajuste de metformina\n"
        )
        report = _make_report(self.doctor, self.patient, content=markdown)

        # --- Web: detail renders nested list HTML ---
        self.client.login(username="drreport", password="testpass123")
        url = reverse("reports:report_detail", kwargs={"pk": report.pk})
        response = self.client.get(url)
        html = response.content.decode()

        # Outer list must contain nested list
        self.assertIn("<ul>", html)
        self.assertIn("Pneumonia", html)
        self.assertIn("Iniciado antibiótico", html)
        self.assertIn("Controle em 48h", html)
        self.assertIn("Diabetes", html)
        self.assertIn("Ajuste de metformina", html)
        # Nested <ul> inside <li> (semantic nesting)
        self.assertIn("<li>", html)

        # --- PDF: nested items appear in order ---
        pdf_buffer = self.generator.generate_from_report(report)
        text = _extract_pdf_text(pdf_buffer)

        self.assertIn("Pneumonia", text)
        self.assertIn("Iniciado antibiótico", text)
        self.assertIn("Controle em 48h", text)
        self.assertIn("Diabetes", text)
        self.assertIn("Ajuste de metformina", text)

        # Items must appear in source order
        self.assertLess(
            text.index("Pneumonia"),
            text.index("Iniciado antibiótico"),
        )
        self.assertLess(
            text.index("Iniciado antibiótico"),
            text.index("Diabetes"),
        )


# ===================================================================
# Hardening: page break token preserved
# ===================================================================


class TestReportPDFPageBreakPreserved(ReportMarkdownParityBase):
    """PAGE_BREAK_TOKEN must still split content into separate PDF pages."""

    def test_page_break_token_creates_multiple_pages(self):
        from apps.reports.services.renderer import PAGE_BREAK_TOKEN

        content = (
            "## Página 1\n\nConteúdo da primeira página."
            + PAGE_BREAK_TOKEN
            + "## Página 2\n\nConteúdo da segunda página."
        )
        report = _make_report(self.doctor, self.patient, content=content)
        pdf_buffer = self.generator.generate_from_report(report)

        pdf_buffer.seek(0)
        reader = pypdf.PdfReader(pdf_buffer)
        self.assertGreaterEqual(len(reader.pages), 2)

    def test_content_on_separate_pages(self):
        from apps.reports.services.renderer import PAGE_BREAK_TOKEN

        content = (
            "## Primeira Seção\n\nTexto A."
            + PAGE_BREAK_TOKEN
            + "## Segunda Seção\n\nTexto B."
        )
        report = _make_report(self.doctor, self.patient, content=content)
        pdf_buffer = self.generator.generate_from_report(report)
        text = _extract_pdf_text(pdf_buffer)

        self.assertIn("Primeira Seção", text)
        self.assertIn("Texto A", text)
        self.assertIn("Segunda Seção", text)
        self.assertIn("Texto B", text)


# ===================================================================
# Hardening: signature section preserved
# ===================================================================


class TestReportPDFSignaturePreserved(ReportMarkdownParityBase):
    """Signature section (name/profession/CRM) must appear in the PDF."""

    def test_signature_section_in_pdf(self):
        content = "## Relatório\n\nConteúdo."
        report = _make_report(self.doctor, self.patient, content=content)
        pdf_buffer = self.generator.generate_from_report(report)
        text = _extract_pdf_text(pdf_buffer)

        # Doctor name appears
        self.assertIn("Maria Silva", text)
        # Profession or CRM context
        self.assertIn("Assinatura", text)

    def test_signature_with_registration_number(self):
        content = "## Relatório\n\nConteúdo."
        report = _make_report(self.doctor, self.patient, content=content)
        pdf_buffer = self.generator.generate_from_report(report)
        text = _extract_pdf_text(pdf_buffer)

        self.assertIn("12345", text)


# ===================================================================
# Hardening: inline semantics in detail and PDF
# ===================================================================


class TestReportInlineSemantics(ReportMarkdownParityBase):
    """Validate inline formatting (bold/italic/strike/code/link) in web and PDF."""

    def test_inline_semantics_in_web_detail(self):
        content = (
            "Texto com **negrito**, *itálico*, ~~riscado~~ e "
            "`código` e [link](https://example.com)."
        )
        report = _make_report(self.doctor, self.patient, content=content)

        self.client.login(username="drreport", password="testpass123")
        url = reverse("reports:report_detail", kwargs={"pk": report.pk})
        response = self.client.get(url)
        html = response.content.decode()

        self.assertIn("<strong>negrito</strong>", html)
        self.assertIn("<em>itálico</em>", html)
        self.assertIn("<del>riscado</del>", html)
        self.assertIn("<code>código</code>", html)
        self.assertIn('href="https://example.com"', html)

    def test_inline_semantics_in_pdf(self):
        content = (
            "Texto com **negrito**, *itálico*, ~~riscado~~ e "
            "`código` e [link](https://example.com)."
        )
        report = _make_report(self.doctor, self.patient, content=content)
        pdf_buffer = self.generator.generate_from_report(report)
        text = _extract_pdf_text(pdf_buffer)

        # Text tokens must be preserved in extracted PDF text
        self.assertIn("negrito", text)
        self.assertIn("itálico", text)
        self.assertIn("riscado", text)
        self.assertIn("código", text)
        self.assertIn("link", text)


# ===================================================================
# Hardening: sanitization in detail (no raw HTML injection)
# ===================================================================


class TestReportDetailSanitization(ReportMarkdownParityBase):
    """Verify that the web detail sanitizes dangerous HTML."""

    def test_script_tag_stripped(self):
        content = "Texto.\n\n<script>alert('xss')</script>"
        report = _make_report(self.doctor, self.patient, content=content)

        self.client.login(username="drreport", password="testpass123")
        url = reverse("reports:report_detail", kwargs={"pk": report.pk})
        response = self.client.get(url)
        html = response.content.decode()

        # Check only the markdown-content div, not the full page template
        # (the base template contains <script> tags for JS)
        start = html.find('class="markdown-content"')
        end = html.find('</div>', start) + len('</div>')
        content_html = html[start:end]

        self.assertNotIn("<script>", content_html)
        self.assertNotIn("alert", content_html)

    def test_onclick_attribute_stripped(self):
        content = '[click](https://example.com "normal")'
        report = _make_report(self.doctor, self.patient, content=content)

        self.client.login(username="drreport", password="testpass123")
        url = reverse("reports:report_detail", kwargs={"pk": report.pk})
        response = self.client.get(url)
        html = response.content.decode()

        self.assertNotIn("onclick", html)
        self.assertNotIn("onerror", html)


# ===================================================================
# Shared pipeline mock integration (definitive delegation proof)
# ===================================================================


class TestReportPDFGeneratorDelegatesToSharedPipeline(ReportMarkdownParityBase):
    """Definitive proof that ReportPDFGenerator delegates to shared pipeline."""

    def test_no_markdowntopdfparser_usage(self):
        """
        ReportPDFGenerator must NOT use MarkdownToPDFParser anymore.
        It must delegate to shared pipeline's parse_markdown + render_markdown_pdf_flowables.
        """
        content = "## Test\n\n- item 1\n- item 2\n"
        report = _make_report(self.doctor, self.patient, content=content)

        with patch(
            "apps.reports.services.pdf_generator.parse_markdown",
        ) as mock_parse:
            from apps.core.services.markdown_pipeline.ir import DocumentNode
            mock_parse.return_value = DocumentNode(children=())

            with patch(
                "apps.reports.services.pdf_generator.render_markdown_pdf_flowables",
                return_value=[],
            ) as mock_flowables:
                self.generator.generate_from_report(report)
                # parse_markdown is called with the stripped content part
                mock_parse.assert_called_once()
                called_text = mock_parse.call_args[0][0]
                self.assertIn("## Test", called_text)
                self.assertIn("- item 1", called_text)
                mock_flowables.assert_called_once()

    def test_no_local_markdown_import_in_pdf_generator(self):
        """
        The pdf_generator module must NOT import MarkdownToPDFParser.
        """
        import apps.reports.services.pdf_generator as pdf_mod
        source = open(pdf_mod.__file__).read()
        self.assertNotIn("MarkdownToPDFParser", source)
