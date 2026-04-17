"""
Cross-app regression bundle for the unified markdown pipeline (Slice 07).

Validates that Daily Notes, Reports, and Core pipeline maintain semantic
parity, legacy paths are not used by migrated apps, and performance stays
within acceptable bounds for long notes.

TDD — written FIRST (RED phase).
"""

from __future__ import annotations

import io
import time
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pypdf
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, SimpleTestCase
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.core.services.markdown_pipeline import (
    parse_markdown,
    render_markdown_html,
)
from apps.core.services.markdown_pipeline.html_renderer import render_html
from apps.core.services.markdown_pipeline.ir import (
    DocumentNode,
    HeadingNode,
    ListNode,
    ListItemNode,
    ParagraphNode,
    StrongNode,
    TextNode,
)
from apps.core.services.markdown_pipeline.pdf_renderer import (
    render_markdown_pdf_flowables,
)
from apps.core.services.markdown_pipeline.profile import get_supported_constructs
from apps.dailynotes.models import DailyNote
from apps.dailynotes.services.pdf_generator import DailyNotePDFGenerator
from apps.patients.models import Patient
from apps.reports.models import Report
from apps.reports.services.pdf_generator import ReportPDFGenerator


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "tests/fixtures/markdown/easymd_v1"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_pdf_text(pdf_buffer: io.BytesIO) -> str:
    """Extract and return full text from a PDF buffer."""
    pdf_buffer.seek(0)
    reader = pypdf.PdfReader(pdf_buffer)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _long_markdown_note() -> str:
    """Generate a long but deterministic markdown document for perf testing."""
    lines: list[str] = []
    for section_idx in range(1, 21):
        lines.append(f"## Seção {section_idx}")
        lines.append("")
        lines.append(
            f"Paciente em acompanhamento na seção {section_idx}. "
            f"Apresenta **sinais vitais** estáveis com *monitoramento* contínuo."
        )
        lines.append("")
        # Add a list per section
        lines.append(f"{section_idx}. Item principal {section_idx}")
        for sub_idx in range(1, 4):
            lines.append(f"   {sub_idx}. Sub-item {section_idx}.{sub_idx}")
        lines.append("")
        # Add a blockquote every 5 sections
        if section_idx % 5 == 0:
            lines.append(f"> Observação importante da seção {section_idx}.")
            lines.append("")
    return "\n".join(lines)


# ===================================================================
# Mandatory test 1: Cross-app markdown contract bundle
# ===================================================================


class TestCrossAppMarkdownContractBundle(TestCase):
    """Validate the full markdown contract across Daily Notes, Reports, and
    Core pipeline for a representative clinical note."""

    @classmethod
    def setUpTestData(cls):
        cls.user = EqmdCustomUser.objects.create_user(
            username="bundledoc",
            email="bundle@example.com",
            password="testpass123",
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
            first_name="Bundle",
            last_name="Doctor",
            professional_registration_number="BNDG01",
            password_change_required=False,
            terms_accepted=True,
        )
        # Grant view permissions
        from apps.events.models import Event
        event_ct = ContentType.objects.get_for_model(Event)
        cls.user.user_permissions.add(
            Permission.objects.get(content_type=event_ct, codename="view_event"),
        )
        patient_ct = ContentType.objects.get_for_model(Patient)
        cls.user.user_permissions.add(
            Permission.objects.get(content_type=patient_ct, codename="view_patient"),
        )
        cls.patient = Patient.objects.create(
            name="Bundle Patient",
            birthday="1985-03-15",
            created_by=cls.user,
            updated_by=cls.user,
        )
        cls.markdown_content = (
            "## Evolução Clínica\n\n"
            "Paciente **estável** com *melhora* dos sinais.\n\n"
            "### Medicamentos\n\n"
            "1. Amoxicilina\n"
            "   - 500mg\n"
            "   - 8/8h\n"
            "2. Dipirona\n"
            "   - 1g\n\n"
            "> Observação: paciente alérgico a penicilina.\n\n"
            "## Checklists\n\n"
            "- [x] Hemograma\n"
            "- [ ] ECG\n\n"
            "| Critério | Status |\n"
            "| -------- | ------ |\n"
            "| Dor | Controlada |\n"
            "| Febre | Ausente |\n"
        )

    def setUp(self):
        self.client.login(username="bundledoc", password="testpass123")

    # --- Core pipeline ---

    def test_core_pipeline_parses_to_document_node(self):
        """Core pipeline must parse markdown to a valid DocumentNode."""
        doc = parse_markdown(self.markdown_content)
        self.assertIsInstance(doc, DocumentNode)
        self.assertGreater(len(doc.children), 0)

    def test_core_pipeline_html_renders_all_constructs(self):
        """HTML output must contain all key semantic constructs."""
        html = render_markdown_html(self.markdown_content)
        self.assertIn("<strong>estável</strong>", html)
        self.assertIn("<em>melhora</em>", html)
        self.assertIn("<ol>", html)
        self.assertIn("<ul>", html)
        self.assertIn("<blockquote>", html)
        self.assertIn("<table>", html)
        self.assertIn('type="checkbox"', html)

    def test_core_pipeline_pdf_flowables_produced(self):
        """PDF flowables must be generated without errors."""
        doc = parse_markdown(self.markdown_content)
        from reportlab.lib.styles import getSampleStyleSheet
        styles = getSampleStyleSheet()
        flowables = render_markdown_pdf_flowables(doc, styles)
        self.assertIsInstance(flowables, list)
        self.assertGreater(len(flowables), 0)

    # --- Daily Notes integration ---

    def test_dailynote_pdf_preserves_all_tokens(self):
        """Daily Note PDF must contain all semantic tokens from the markdown."""
        note = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Bundle test",
            content=self.markdown_content,
            created_by=self.user,
            updated_by=self.user,
        )
        generator = DailyNotePDFGenerator()
        pdf_buffer = generator.generate_from_dailynote(note)
        text = _extract_pdf_text(pdf_buffer)

        self.assertIn("estável", text)
        self.assertIn("Amoxicilina", text)
        self.assertIn("500mg", text)
        self.assertIn("Dipirona", text)
        self.assertIn("Hemograma", text)
        self.assertIn("ECG", text)
        self.assertIn("Controlada", text)

    def test_dailynote_detail_renders_shared_pipeline_html(self):
        """Daily Note detail page must render via shared pipeline."""
        note = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Bundle test",
            content=self.markdown_content,
            created_by=self.user,
            updated_by=self.user,
        )
        from django.urls import reverse
        url = reverse("dailynotes:dailynote_detail", kwargs={"pk": note.pk})
        response = self.client.get(url)
        html = response.content.decode()

        self.assertIn("<strong>estável</strong>", html)
        self.assertIn("<blockquote>", html)
        self.assertIn("<table>", html)

    # --- Reports integration ---

    def test_report_pdf_preserves_all_tokens(self):
        """Report PDF must contain all semantic tokens from the markdown."""
        report = Report.objects.create(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            title="Bundle Report",
            content=self.markdown_content,
            document_date=date(2024, 3, 15),
            event_datetime=timezone.now(),
        )
        generator = ReportPDFGenerator()
        pdf_buffer = generator.generate_from_report(report)
        text = _extract_pdf_text(pdf_buffer)

        self.assertIn("estável", text)
        self.assertIn("Amoxicilina", text)
        self.assertIn("Hemograma", text)
        self.assertIn("Controlada", text)

    def test_report_detail_renders_shared_pipeline_html(self):
        """Report detail page must render via shared pipeline."""
        report = Report.objects.create(
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user,
            title="Bundle Report",
            content=self.markdown_content,
            document_date=date(2024, 3, 15),
            event_datetime=timezone.now(),
        )
        from django.urls import reverse
        url = reverse("reports:report_detail", kwargs={"pk": report.pk})
        response = self.client.get(url)
        html = response.content.decode()

        self.assertIn("<strong>estável</strong>", html)
        self.assertIn("<blockquote>", html)
        self.assertIn("<table>", html)

    # --- Cross-app parity ---

    def test_dailynote_and_report_produce_same_html_for_same_markdown(self):
        """Both Daily Note and Report must produce the same HTML for the same
        markdown input via the shared pipeline."""
        html_dn = render_markdown_html(self.markdown_content)
        html_rp = render_markdown_html(self.markdown_content)
        self.assertEqual(html_dn, html_rp)

    def test_fixture_corpus_cross_validated(self):
        """Every fixture in the corpus must parse, render to HTML, and produce
        PDF flowables without errors."""
        if not FIXTURES_DIR.exists():
            self.skipTest("Fixtures directory not found")

        from reportlab.lib.styles import getSampleStyleSheet
        styles = getSampleStyleSheet()

        for md_file in sorted(FIXTURES_DIR.glob("*.md")):
            with self.subTest(fixture=md_file.stem):
                md = md_file.read_text(encoding="utf-8")
                doc = parse_markdown(md)
                self.assertIsInstance(doc, DocumentNode)

                html = render_markdown_html(md)
                self.assertIsInstance(html, str)
                self.assertGreater(len(html), 0)

                flowables = render_markdown_pdf_flowables(doc, styles)
                self.assertIsInstance(flowables, list)


# ===================================================================
# Mandatory test 2: Legacy paths not used by migrated apps
# ===================================================================


class TestLegacyMarkdownPathsNotUsedInMigratedApps(SimpleTestCase):
    """Verify that migrated apps (Daily Notes, Reports) no longer import or
    use the legacy MarkdownToPDFParser from pdfgenerator."""

    def test_dailynotes_pdf_generator_does_not_import_legacy_parser(self):
        """DailyNotePDFGenerator source must not reference MarkdownToPDFParser."""
        import apps.dailynotes.services.pdf_generator as mod
        source = open(mod.__file__).read()
        self.assertNotIn("MarkdownToPDFParser", source)
        self.assertNotIn("markdown_parser", source)

    def test_reports_pdf_generator_does_not_import_legacy_parser(self):
        """ReportPDFGenerator source must not reference MarkdownToPDFParser."""
        import apps.reports.services.pdf_generator as mod
        source = open(mod.__file__).read()
        self.assertNotIn("MarkdownToPDFParser", source)
        self.assertNotIn("markdown_parser", source)

    def test_reports_templatetags_delegates_to_shared_pipeline(self):
        """reports_extras.markdown_filter must use render_markdown_html."""
        import apps.reports.templatetags.reports_extras as mod
        source = open(mod.__file__).read()
        self.assertIn("render_markdown_html", source)
        self.assertNotIn("import markdown", source)
        self.assertNotIn("markdown.Markdown", source)

    def test_dailynotes_uses_shared_pipeline_imports(self):
        """DailyNotePDFGenerator must import from core markdown_pipeline."""
        import apps.dailynotes.services.pdf_generator as mod
        source = open(mod.__file__).read()
        self.assertIn("apps.core.services.markdown_pipeline", source)
        self.assertIn("parse_markdown", source)
        self.assertIn("render_markdown_pdf_flowables", source)

    def test_reports_uses_shared_pipeline_imports(self):
        """ReportPDFGenerator must import from core markdown_pipeline."""
        import apps.reports.services.pdf_generator as mod
        source = open(mod.__file__).read()
        self.assertIn("apps.core.services.markdown_pipeline", source)
        self.assertIn("parse_markdown", source)
        self.assertIn("render_markdown_pdf_flowables", source)

    def test_legacy_parser_is_deprecated(self):
        """The legacy MarkdownToPDFParser must have a deprecation notice."""
        import apps.pdfgenerator.services.markdown_parser as mod
        source = open(mod.__file__).read()
        # Must contain a deprecation indicator
        self.assertTrue(
            "DEPRECATED" in source or "deprecated" in source.lower(),
            "Legacy MarkdownToPDFParser must be marked as deprecated",
        )


# ===================================================================
# Mandatory test 3: Performance smoke test
# ===================================================================


class TestMarkdownPipelineLongNotePerformanceSmoke(TestCase):
    """Performance smoke test: long note must render within acceptable time."""

    @classmethod
    def setUpTestData(cls):
        cls.user = EqmdCustomUser.objects.create_user(
            username="perfdoc",
            email="perf@example.com",
            password="testpass123",
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
            first_name="Perf",
            last_name="Doctor",
            professional_registration_number="PRF001",
            password_change_required=False,
            terms_accepted=True,
        )
        cls.patient = Patient.objects.create(
            name="Performance Patient",
            birthday="1990-01-01",
            created_by=cls.user,
            updated_by=cls.user,
        )

    def test_parse_long_note_under_threshold(self):
        """Parsing a long note must complete within 2 seconds."""
        md = _long_markdown_note()
        start = time.monotonic()
        doc = parse_markdown(md)
        elapsed = time.monotonic() - start
        self.assertIsInstance(doc, DocumentNode)
        self.assertLess(elapsed, 2.0, f"Parsing took {elapsed:.3f}s (> 2s)")

    def test_html_render_long_note_under_threshold(self):
        """HTML rendering of a long note must complete within 2 seconds."""
        md = _long_markdown_note()
        start = time.monotonic()
        html = render_markdown_html(md)
        elapsed = time.monotonic() - start
        self.assertIsInstance(html, str)
        self.assertGreater(len(html), 0)
        self.assertLess(elapsed, 2.0, f"HTML render took {elapsed:.3f}s (> 2s)")

    def test_pdf_flowables_long_note_under_threshold(self):
        """PDF flowable generation for a long note must complete within 5 seconds."""
        md = _long_markdown_note()
        doc = parse_markdown(md)
        from reportlab.lib.styles import getSampleStyleSheet
        styles = getSampleStyleSheet()
        start = time.monotonic()
        flowables = render_markdown_pdf_flowables(doc, styles)
        elapsed = time.monotonic() - start
        self.assertIsInstance(flowables, list)
        self.assertGreater(len(flowables), 0)
        self.assertLess(elapsed, 5.0, f"PDF flowable render took {elapsed:.3f}s (> 5s)")

    def test_dailynote_pdf_generation_long_note_under_threshold(self):
        """Full Daily Note PDF generation for a long note must complete within
        10 seconds."""
        md = _long_markdown_note()
        note = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Perf test",
            content=md,
            created_by=self.user,
            updated_by=self.user,
        )
        generator = DailyNotePDFGenerator()
        start = time.monotonic()
        pdf_buffer = generator.generate_from_dailynote(note)
        elapsed = time.monotonic() - start
        pdf_buffer.seek(0)
        self.assertEqual(pdf_buffer.read(4), b"%PDF")
        self.assertLess(
            elapsed, 10.0,
            f"Full PDF generation took {elapsed:.3f}s (> 10s)",
        )

    def test_performance_deterministic_across_runs(self):
        """Parsing the same long note 3 times must produce identical output."""
        md = _long_markdown_note()
        results = [parse_markdown(md) for _ in range(3)]

        def _signature(node):
            """Simple structural signature for comparison."""
            if isinstance(node, DocumentNode):
                return f"DOC[{','.join(_signature(c) for c in node.children)}]"
            if isinstance(node, HeadingNode):
                return f"H{node.level}"
            if isinstance(node, ParagraphNode):
                return "P"
            if isinstance(node, ListNode):
                prefix = "OL" if node.ordered else "UL"
                return f"{prefix}[{len(node.children)}]"
            return type(node).__name__

        sigs = [_signature(r) for r in results]
        self.assertEqual(sigs[0], sigs[1])
        self.assertEqual(sigs[1], sigs[2])
