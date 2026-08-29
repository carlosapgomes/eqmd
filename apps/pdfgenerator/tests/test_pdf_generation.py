"""
Tests for PDF generation functionality.
"""

import io
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.patients.models import Patient
from apps.pdfgenerator.services.markdown_parser import MarkdownToPDFParser
from apps.pdfgenerator.services.pdf_generator import HospitalLetterheadGenerator

User = get_user_model()


class PDFGeneratorTestCase(TestCase):
    """Test case for PDF generation functionality"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username="testdoctor",
            email="test@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
        )

        # Create test patient
        from datetime import date

        self.patient = Patient.objects.create(
            name="Test Patient",
            birthday=date(1990, 1, 1),
            fiscal_number="123.456.789-00",
            healthcard_number="123456789012345",
            created_by=self.user,
            updated_by=self.user,
        )

        # Initialize PDF generator
        self.pdf_generator = HospitalLetterheadGenerator()
        self.markdown_parser = MarkdownToPDFParser(self.pdf_generator.styles)

    def test_pdf_generator_initialization(self):
        """Test that PDF generator initializes correctly"""
        self.assertIsNotNone(self.pdf_generator)
        self.assertIsNotNone(self.pdf_generator.styles)
        self.assertIsNotNone(self.pdf_generator.hospital_config)
        self.assertIsNotNone(self.pdf_generator.pdf_config)

    def test_markdown_parser_initialization(self):
        """Test that markdown parser initializes correctly"""
        self.assertIsNotNone(self.markdown_parser)
        self.assertIsNotNone(self.markdown_parser.styles)
        self.assertIsNotNone(self.markdown_parser.md)

    def test_markdown_parsing_basic(self):
        """Test basic markdown parsing functionality"""
        markdown_text = """
        # Test Header
        
        This is a **bold** text and this is *italic*.
        
        - Item 1
        - Item 2
        - Item 3
        """

        flowables = self.markdown_parser.parse(markdown_text)
        self.assertIsInstance(flowables, list)
        self.assertGreater(len(flowables), 0)

    def test_patient_identification_rendered_in_header(self):
        """Test that patient identification renders in the repeated page header.

        Current contract (outpatient-prescription layout refactor, 9d1bd14): the
        base generator draws the patient name in the page header on every page
        (``NumberedCanvas.draw_header``), so the body table was removed and
        ``_create_patient_info_table`` intentionally yields no flowables. See
        ``openspec/changes/daily-note-pdf/design.md`` section 2, which relies on
        the base implementation returning an empty list.
        """
        from apps.pdfgenerator.services.pdf_generator import NumberedCanvas

        patient_data = {
            "name": "Test Patient",
            "fiscal_number": "123.456.789-00",
            "birth_date": "01/01/1990",
            "health_card_number": "123456789012345",
        }

        # No body table: patient identification moved to the page header.
        table_elements = self.pdf_generator._create_patient_info_table(patient_data)
        self.assertEqual(table_elements, [])

        # Patient name is drawn in the header on every page.
        buffer = io.BytesIO()
        canvas = NumberedCanvas(
            buffer,
            pagesize=self.pdf_generator.page_size,
            hospital_config=self.pdf_generator.hospital_config,
            patient_data=patient_data,
            doctor_info={},
        )
        with patch.object(canvas, "drawString") as mock_str:
            canvas.draw_header()
        drawn_texts = [call.args[2] for call in mock_str.call_args_list]
        self.assertIn("Paciente: Test Patient", drawn_texts)

        # Without patient data, no patient line is drawn.
        buffer_no_patient = io.BytesIO()
        canvas_no_patient = NumberedCanvas(
            buffer_no_patient,
            pagesize=self.pdf_generator.page_size,
            hospital_config=self.pdf_generator.hospital_config,
            patient_data={},
            doctor_info={},
        )
        with patch.object(canvas_no_patient, "drawString") as mock_str_no_patient:
            canvas_no_patient.draw_header()
        drawn_no_patient = [call.args[2] for call in mock_str_no_patient.call_args_list]
        self.assertNotIn("Paciente:", drawn_no_patient)

    def test_signature_section_creation(self):
        """Test medical signature section creation"""
        doctor_info = {"name": "Dr. Test Doctor", "profession": "Médico"}

        signature_elements = self.pdf_generator._create_signature_section(doctor_info)
        self.assertIsInstance(signature_elements, list)
        self.assertGreater(len(signature_elements), 0)

    def test_basic_pdf_generation(self):
        """Test basic PDF generation with simple content"""
        # Prepare test data
        patient_data = {
            "name": self.patient.name,
            "fiscal_number": self.patient.fiscal_number,
            "birth_date": "01/01/1990",
            "health_card_number": self.patient.healthcard_number,
        }

        doctor_info = {"name": self.user.username, "profession": "Médico"}

        # Simple content
        content_elements = self.markdown_parser.parse(
            "## Test Document\n\nThis is a test document."
        )

        # Generate PDF
        pdf_buffer = self.pdf_generator.generate_pdf(
            content_elements=content_elements,
            document_title="Test Document",
            patient_data=patient_data,
            doctor_info=doctor_info,
        )

        # Verify PDF was generated
        self.assertIsInstance(pdf_buffer, io.BytesIO)
        pdf_content = pdf_buffer.read()
        self.assertGreater(len(pdf_content), 0)

        # Basic PDF validation - should start with PDF header
        pdf_buffer.seek(0)
        first_bytes = pdf_buffer.read(4)
        self.assertEqual(first_bytes, b"%PDF")

    def test_prescription_pdf_generation(self):
        """Test prescription-specific PDF generation"""
        # Prepare test data
        patient_data = {
            "name": self.patient.name,
            "fiscal_number": self.patient.fiscal_number,
            "birth_date": "01/01/1990",
            "health_card_number": self.patient.healthcard_number,
        }

        doctor_info = {"name": self.user.username, "profession": "Médico"}

        prescription_data = {
            "prescription_date": "22/07/2025",
            "instructions": "Tomar conforme orientação médica.",
            "status": "Ativa",
        }

        items = [
            {
                "drug_name": "Paracetamol",
                "presentation": "500mg comprimido",
                "usage_instructions": "Tomar 1 comprimido a cada 8 horas",
                "quantity": "30 comprimidos",
            },
            {
                "drug_name": "Ibuprofeno",
                "presentation": "400mg comprimido",
                "usage_instructions": "Tomar 1 comprimido a cada 12 horas",
                "quantity": "20 comprimidos",
            },
        ]

        # Generate prescription PDF
        pdf_buffer = self.pdf_generator.create_prescription_pdf(
            prescription_data=prescription_data,
            items=items,
            patient_data=patient_data,
            doctor_info=doctor_info,
        )

        # Verify PDF was generated
        self.assertIsInstance(pdf_buffer, io.BytesIO)
        pdf_content = pdf_buffer.read()
        self.assertGreater(len(pdf_content), 0)

        # Basic PDF validation
        pdf_buffer.seek(0)
        first_bytes = pdf_buffer.read(4)
        self.assertEqual(first_bytes, b"%PDF")

    def test_empty_content_handling(self):
        """Test handling of empty or None content"""
        # Test empty markdown
        flowables_empty = self.markdown_parser.parse("")
        self.assertEqual(len(flowables_empty), 0)

        # Test None markdown
        flowables_none = self.markdown_parser.parse(None)
        self.assertEqual(len(flowables_none), 0)

        # Test whitespace-only markdown
        flowables_whitespace = self.markdown_parser.parse("   \n\n   ")
        self.assertEqual(len(flowables_whitespace), 0)

    def test_html_escaping(self):
        """Test that HTML characters are properly escaped"""
        test_text = "Test <script>alert('xss')</script> & other > chars"
        escaped = self.markdown_parser._escape_html(test_text)

        self.assertNotIn("<script>", escaped)
        self.assertNotIn("<", escaped)
        self.assertNotIn(">", escaped)
        # Current contract escapes the full HTML special set (quotes included),
        # which is stricter than the legacy &, <, > set.
        self.assertIn("&amp;", escaped)
        self.assertIn("&lt;", escaped)
        self.assertIn("&gt;", escaped)
        self.assertIn("&#39;", escaped)
        # Every remaining ampersand is the start of an entity, never raw input.
        stripped = (
            escaped.replace("&amp;", "")
            .replace("&lt;", "")
            .replace("&gt;", "")
            .replace("&#39;", "")
            .replace("&quot;", "")
        )
        self.assertNotIn("&", stripped)
        # Double quotes are escaped as well.
        escaped_quotes = self.markdown_parser._escape_html('say "hello"')
        self.assertIn("&quot;", escaped_quotes)


class MarkdownParsingTestCase(TestCase):
    """Detailed tests for markdown parsing functionality"""

    def setUp(self):
        """Set up markdown parser"""
        pdf_generator = HospitalLetterheadGenerator()
        self.parser = MarkdownToPDFParser(pdf_generator.styles)

    def test_bold_text_parsing(self):
        """Test bold text parsing"""
        markdown = "This is **bold text** and this is normal."
        flowables = self.parser.parse(markdown)

        # Should contain at least one paragraph
        self.assertGreater(len(flowables), 0)

    def test_italic_text_parsing(self):
        """Test italic text parsing"""
        markdown = "This is *italic text* and this is normal."
        flowables = self.parser.parse(markdown)

        self.assertGreater(len(flowables), 0)

    def test_list_parsing(self):
        """Test list parsing"""
        markdown = """
        - Item 1
        - Item 2
        - Item 3
        """
        flowables = self.parser.parse(markdown)

        self.assertGreater(len(flowables), 0)

    def test_ordered_list_parsing(self):
        """Test ordered list parsing"""
        markdown = """
        1. First item
        2. Second item
        3. Third item
        """
        flowables = self.parser.parse(markdown)

        self.assertGreater(len(flowables), 0)

    def test_headers_parsing(self):
        """Test header parsing"""
        markdown = """
        # Header 1
        ## Header 2
        ### Header 3
        """
        flowables = self.parser.parse(markdown)

        self.assertGreater(len(flowables), 0)

    def test_medical_content_parsing(self):
        """Test parsing of medical content"""
        medical_content = """
        ## Prescrição Médica
        
        **Medicamento:** Paracetamol 500mg
        
        **Posologia:** 
        - Tomar 1 comprimido
        - A cada 8 horas
        - Por 7 dias
        
        **Observações:**
        Tomar preferencialmente após as refeições.
        """

        flowables = self.parser.parse_medical_content(medical_content, "Receita Médica")

        self.assertGreater(len(flowables), 0)

    def test_prescription_instructions_parsing(self):
        """Test prescription instructions parsing"""
        instructions = """
        **Instruções gerais:**
        
        1. Tomar os medicamentos nos horários indicados
        2. Não interromper o tratamento sem orientação médica
        3. Em caso de dúvidas, procurar o médico
        """

        flowables = self.parser.parse_prescription_instructions(instructions)

        self.assertGreater(len(flowables), 0)
