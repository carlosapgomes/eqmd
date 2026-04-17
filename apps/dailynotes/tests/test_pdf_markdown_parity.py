"""
Tests for PDF markdown parity — Slice 05.

Verifies that the Daily Note PDF uses the shared markdown pipeline
renderer and preserves semantic fidelity for nested lists, inline
formatting, tables, blockquotes, code blocks, and task lists.
"""

import io
from datetime import date

import pypdf
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.dailynotes.models import DailyNote
from apps.dailynotes.services.pdf_generator import DailyNotePDFGenerator
from apps.patients.models import Patient

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_pdf_text(pdf_buffer: io.BytesIO) -> str:
    """Extract and return full text from a PDF buffer."""
    pdf_buffer.seek(0)
    reader = pypdf.PdfReader(pdf_buffer)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _make_dailynote(user, patient, content="Simple content."):
    """Create a DailyNote for testing."""
    return DailyNote.objects.create(
        patient=patient,
        event_datetime=timezone.now(),
        description="Test note",
        content=content,
        created_by=user,
        updated_by=user,
    )


# ---------------------------------------------------------------------------
# Test Case
# ---------------------------------------------------------------------------


class PDFMarkdownParityTestCase(TestCase):
    """Base case with shared fixtures."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="drparity",
            email="drparity@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            first_name="Ana",
            last_name="Costa",
            professional_registration_number="98765",
        )
        self.patient = Patient.objects.create(
            name="Carlos Mendes",
            birthday=date(1970, 5, 20),
            fiscal_number="11122233344",
            healthcard_number="555666777888999",
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        self.generator = DailyNotePDFGenerator()


# ===================================================================
# Mandatory tests
# ===================================================================


class TestPDFPreservesNestedUnorderedListHierarchy(PDFMarkdownParityTestCase):
    """test_pdf_preserves_nested_unordered_list_hierarchy"""

    def test_nested_unordered_list_hierarchy(self):
        """Nested unordered lists must preserve parent→child order in PDF."""
        markdown = (
            "## Medicamentos\n\n"
            "- Amoxicilina\n"
            "  - 500mg\n"
            "  - 8/8h\n"
            "- Dipirona\n"
            "  - 1g\n"
            "  - 6/6h\n"
        )
        note = _make_dailynote(self.user, self.patient, content=markdown)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        text = _extract_pdf_text(pdf_buffer)

        # Parent items must appear
        self.assertIn("Amoxicilina", text)
        self.assertIn("Dipirona", text)
        # Nested items must appear
        self.assertIn("500mg", text)
        self.assertIn("8/8h", text)
        self.assertIn("1g", text)
        self.assertIn("6/6h", text)
        # Semantic order: parent before child
        self.assertLess(
            text.index("Amoxicilina"),
            text.index("500mg"),
            "Amoxicilina must precede its nested items",
        )
        self.assertLess(
            text.index("Dipirona"),
            text.index("1g"),
            "Dipirona must precede its nested items",
        )


class TestPDFPreservesNestedOrderedListHierarchy(PDFMarkdownParityTestCase):
    """test_pdf_preserves_nested_ordered_list_hierarchy"""

    def test_nested_ordered_list_hierarchy(self):
        """Nested ordered lists must preserve parent→child order in PDF."""
        markdown = (
            "## Plano Terapêutico\n\n"
            "1. Manter medicação\n"
            "   1. Medicamento A 500mg\n"
            "   2. Medicamento B 250mg\n"
            "2. Solicitar exames\n"
            "   1. Hemograma\n"
            "   2. Painel metabólico\n"
        )
        note = _make_dailynote(self.user, self.patient, content=markdown)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        text = _extract_pdf_text(pdf_buffer)

        # Parent items
        self.assertIn("Manter medicação", text)
        self.assertIn("Solicitar exames", text)
        # Nested items
        self.assertIn("Medicamento A 500mg", text)
        self.assertIn("Medicamento B 250mg", text)
        self.assertIn("Hemograma", text)
        self.assertIn("Painel metabólico", text)
        # Order
        self.assertLess(
            text.index("Manter medicação"),
            text.index("Medicamento A 500mg"),
        )
        self.assertLess(
            text.index("Solicitar exames"),
            text.index("Hemograma"),
        )


class TestPDFPreservesInlineSemanticsForSupportedConstructs(PDFMarkdownParityTestCase):
    """test_pdf_preserves_inline_semantics_for_supported_constructs"""

    def test_inline_semantics_preserved(self):
        """Bold, italic, strikethrough, inline code, and link text must appear."""
        markdown = (
            "## Nota Clínica\n\n"
            "Paciente **João Silva** em *observação*.\n\n"
            "Texto ~~riscado~~ e `código inline`.\n\n"
            "Ver [protocolo](https://example.com/protocolo).\n"
        )
        note = _make_dailynote(self.user, self.patient, content=markdown)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        text = _extract_pdf_text(pdf_buffer)

        # Inline text content must be preserved
        self.assertIn("João Silva", text)
        self.assertIn("observação", text)
        self.assertIn("riscado", text)
        self.assertIn("código inline", text)
        self.assertIn("protocolo", text)


class TestPDFHandlesTablesBlockquotesAndCodeWithDefinedFallbacks(PDFMarkdownParityTestCase):
    """test_pdf_handles_tables_blockquotes_and_code_with_defined_fallbacks"""

    def test_table_fallback_preserves_cell_content(self):
        """Tables must render with cell content preserved in the PDF."""
        markdown = (
            "## Critérios\n\n"
            "| Critério | Status |\n"
            "| -------- | ------ |\n"
            "| Dor | Controlada |\n"
            "| Deambulação | Sim |\n"
        )
        note = _make_dailynote(self.user, self.patient, content=markdown)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        text = _extract_pdf_text(pdf_buffer)

        self.assertIn("Critério", text)
        self.assertIn("Controlada", text)
        self.assertIn("Deambulação", text)

    def test_blockquote_fallback_preserves_quoted_content(self):
        """Blockquotes must render with content preserved."""
        markdown = (
            "## Avaliação\n\n"
            "> Paciente em melhora.\n"
            "> Continuar plano atual.\n"
        )
        note = _make_dailynote(self.user, self.patient, content=markdown)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        text = _extract_pdf_text(pdf_buffer)

        self.assertIn("Paciente em melhora", text)
        self.assertIn("Continuar plano atual", text)

    def test_code_block_fallback_preserves_code_content(self):
        """Code blocks must render with content preserved."""
        markdown = (
            "## Observações\n\n"
            "```text\n"
            "Linha 1 do código\n"
            "Linha 2 do código\n"
            "```\n"
        )
        note = _make_dailynote(self.user, self.patient, content=markdown)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        text = _extract_pdf_text(pdf_buffer)

        self.assertIn("Linha 1 do código", text)
        self.assertIn("Linha 2 do código", text)


# ===================================================================
# Hardening tests
# ===================================================================


class TestSemanticBlockOrderInPDF(PDFMarkdownParityTestCase):
    """Guarantee semantic order of blocks in the extracted PDF text."""

    def test_blocks_appear_in_source_order(self):
        """Headings, paragraphs, and lists must appear in source order."""
        markdown = (
            "## Seção Alpha\n\n"
            "Parágrafo alpha.\n\n"
            "## Seção Beta\n\n"
            "- Item B1\n"
            "- Item B2\n\n"
            "## Seção Gamma\n\n"
            "Parágrafo gamma.\n"
        )
        note = _make_dailynote(self.user, self.patient, content=markdown)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        text = _extract_pdf_text(pdf_buffer)

        self.assertLess(text.index("Seção Alpha"), text.index("Seção Beta"))
        self.assertLess(text.index("Seção Beta"), text.index("Seção Gamma"))
        self.assertLess(text.index("Parágrafo alpha"), text.index("Item B1"))


class TestTaskListDeterministicRepresentation(PDFMarkdownParityTestCase):
    """Validate task lists (checked/unchecked) with deterministic representation."""

    def test_task_list_items_appear_with_status(self):
        """Checked and unchecked task items must be present in PDF text."""
        markdown = (
            "## Checklists\n\n"
            "- [x] Hemograma\n"
            "- [ ] ECG\n"
            "- [ ] Raio-X\n"
            "- [x] Urina\n"
        )
        note = _make_dailynote(self.user, self.patient, content=markdown)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        text = _extract_pdf_text(pdf_buffer)

        # All task items must appear
        self.assertIn("Hemograma", text)
        self.assertIn("ECG", text)
        self.assertIn("Raio-X", text)
        self.assertIn("Urina", text)

    def test_checked_and_unchecked_have_deterministic_markers(self):
        """Checked items use [x], unchecked use [ ] (deterministic markers)."""
        markdown = "- [x] Done\n- [ ] Todo\n"
        note = _make_dailynote(self.user, self.patient, content=markdown)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        text = _extract_pdf_text(pdf_buffer)

        self.assertIn("Done", text)
        self.assertIn("Todo", text)
        # Deterministic markers (font-compatible)
        self.assertIn("[x]", text)
        self.assertIn("[ ]", text)


class TestHeadingMarkdownNotLiteralInPDF(PDFMarkdownParityTestCase):
    """Heading markdown must not appear with # literal in the PDF."""

    def test_no_hash_literals(self):
        """## Heading should not render as literal ## in PDF."""
        markdown = "## Exame Físico\n\nConteúdo do exame.\n"
        note = _make_dailynote(self.user, self.patient, content=markdown)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        text = _extract_pdf_text(pdf_buffer)

        self.assertIn("Exame Físico", text)
        self.assertNotIn("## ", text)


class TestEmptyContentNoRegression(PDFMarkdownParityTestCase):
    """Confirm that empty content continues to generate a valid PDF."""

    def test_empty_content_produces_valid_pdf(self):
        """An empty or whitespace-only note must still generate a valid PDF."""
        note = _make_dailynote(self.user, self.patient, content="")
        pdf_buffer = self.generator.generate_from_dailynote(note)
        pdf_buffer.seek(0)
        self.assertEqual(pdf_buffer.read(4), b"%PDF")

    def test_whitespace_only_content_produces_valid_pdf(self):
        note = _make_dailynote(self.user, self.patient, content="   \n\n  ")
        pdf_buffer = self.generator.generate_from_dailynote(note)
        pdf_buffer.seek(0)
        self.assertEqual(pdf_buffer.read(4), b"%PDF")


class TestSharedPipelineIntegration(PDFMarkdownParityTestCase):
    """Verify DailyNotePDFGenerator uses the shared pipeline for content."""

    def test_generator_uses_shared_pipeline(self):
        """The _build_note_content method must delegate to the shared PDF renderer."""
        markdown = "## Test\n\nParagraph.\n- Item 1\n"
        note = _make_dailynote(self.user, self.patient, content=markdown)

        from unittest.mock import patch
        with patch(
            "apps.dailynotes.services.pdf_generator.render_markdown_pdf_flowables"
        ) as mock_render:
            mock_render.return_value = []
            self.generator.generate_from_dailynote(note)
            mock_render.assert_called_once()
