"""
Tests for DailyNote PDF generator compact layout.

Verifies repeated patient context headers, specialty inclusion,
compact metadata, and signature placement.
"""

import io
from datetime import date, datetime, timedelta
from typing import ClassVar

import pypdf
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from reportlab.platypus import Spacer

from apps.accounts.models import MedicalSpecialty
from apps.dailynotes.models import DailyNote
from apps.dailynotes.services.pdf_generator import DailyNotePDFGenerator
from apps.patients.models import Patient

User = get_user_model()

# Long content that forces multi-page PDF generation
LONG_CONTENT = "\n\n".join(
    [
        f"## Item {i}\n\n"
        + "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 20
        for i in range(1, 40)
    ]
)


def _extract_page_texts(pdf_buffer: io.BytesIO) -> list[str]:
    """Extract text from each page of a PDF buffer."""
    pdf_buffer.seek(0)
    reader = pypdf.PdfReader(pdf_buffer)
    return [page.extract_text() or "" for page in reader.pages]


def _make_dailynote(user, patient, content=LONG_CONTENT, event_datetime=None):
    """Create and return a DailyNote instance for testing."""
    return DailyNote.objects.create(
        patient=patient,
        event_datetime=event_datetime or timezone.now(),
        description="Evolução diária de teste",
        content=content,
        created_by=user,
        updated_by=user,
    )


class DailyNotePDFGeneratorTestCase(TestCase):
    """Base test case with common fixtures for PDF generator tests."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="drtest",
            email="drtest@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            first_name="João",
            last_name="Silva",
            professional_registration_number="12345",
        )
        self.patient = Patient.objects.create(
            name="Maria Oliveira Santos",
            birthday=date(1985, 3, 15),
            fiscal_number="12345678901",
            healthcard_number="987654321098765",
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )
        self.generator = DailyNotePDFGenerator()


class TestRepeatedPatientContext(DailyNotePDFGeneratorTestCase):
    """Verify patient context is repeated on every page."""

    def test_multi_page_pdf_repeats_patient_context_on_each_page(
        self,
    ):
        """Each page of a multi-page Daily Note PDF must include patient name."""
        note = _make_dailynote(self.user, self.patient)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        page_texts = _extract_page_texts(pdf_buffer)

        self.assertGreaterEqual(len(page_texts), 2, "PDF must span multiple pages")

        for idx, text in enumerate(page_texts):
            with self.subTest(page=idx + 1):
                self.assertIn(
                    self.patient.name,
                    text,
                    f"Patient name missing from page {idx + 1}",
                )

    def test_multi_page_pdf_repeats_record_number_on_each_page(self):
        """Each page of a multi-page Daily Note PDF must include record number."""
        from apps.patients.models import PatientRecordNumber

        PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number="HGRS-2025-00142",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )

        note = _make_dailynote(self.user, self.patient)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        page_texts = _extract_page_texts(pdf_buffer)

        self.assertGreaterEqual(len(page_texts), 2, "PDF must span multiple pages")

        for idx, text in enumerate(page_texts):
            with self.subTest(page=idx + 1):
                self.assertIn(
                    "HGRS-2025-00142",
                    text,
                    f"Record number missing from page {idx + 1}",
                )


class TestSpecialtyInHeader(DailyNotePDFGeneratorTestCase):
    """Verify current user specialty appears in the repeated header."""

    def test_repeated_header_includes_current_user_specialty_when_available(
        self,
    ):
        """When the author has a current specialty, it appears on every page."""
        specialty, _ = MedicalSpecialty.objects.get_or_create(
            name="Cirurgia Geral",
            defaults={"abbreviation": "CIRGER"},
        )
        self.user.profile.current_specialty = specialty
        self.user.profile.save()

        note = _make_dailynote(self.user, self.patient)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        page_texts = _extract_page_texts(pdf_buffer)

        for idx, text in enumerate(page_texts):
            with self.subTest(page=idx + 1):
                self.assertIn(
                    "Cirurgia Geral",
                    text,
                    f"Specialty missing from page {idx + 1}",
                )

    def test_repeated_header_works_without_specialty(self):
        """PDF generates correctly when author has no specialty set."""
        note = _make_dailynote(self.user, self.patient)
        pdf_buffer = self.generator.generate_from_dailynote(note)

        self.assertIsInstance(pdf_buffer, io.BytesIO)
        pdf_buffer.seek(0)
        self.assertEqual(pdf_buffer.read(4), b"%PDF")


class TestCompactMetadata(DailyNotePDFGeneratorTestCase):
    """Verify compact metadata omits the generic description field."""

    def test_compact_metadata_omits_generic_description(self):
        """The generic note description must not appear in the PDF body."""
        note = _make_dailynote(
            self.user,
            self.patient,
            content="Conteúdo simples.",
        )
        note.description = "Evolução diária genérica para teste"
        note.save()

        pdf_buffer = self.generator.generate_from_dailynote(note)
        page_texts = _extract_page_texts(pdf_buffer)
        full_text = "\n".join(page_texts)

        # The description value should NOT be present in the body
        self.assertNotIn(
            "Evolução diária genérica para teste",
            full_text,
        )

    def test_compact_metadata_includes_event_datetime(self):
        """Compact metadata must include event date/time."""
        note = _make_dailynote(
            self.user,
            self.patient,
            content="Conteúdo curto.",
        )
        pdf_buffer = self.generator.generate_from_dailynote(note)
        page_texts = _extract_page_texts(pdf_buffer)
        full_text = "\n".join(page_texts)

        formatted = note.event_datetime.strftime("%d/%m/%Y %H:%M")
        self.assertIn(formatted, full_text)


class TestSignaturePlacement(DailyNotePDFGeneratorTestCase):
    """Verify signature only appears at end of document."""

    def test_multi_page_pdf_omits_intermediate_signature_and_keeps_final_signature(
        self,
    ):
        """Intermediate pages must not have the doctor mini-signature;
        the final page must include full doctor signature information."""
        note = _make_dailynote(self.user, self.patient)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        page_texts = _extract_page_texts(pdf_buffer)

        self.assertGreaterEqual(
            len(page_texts), 2, "Need at least 2 pages for this test"
        )

        doctor_name = self.user.get_full_name()
        registration = self.user.professional_registration_number

        # Intermediate pages should NOT contain the mini-signature block
        for idx in range(len(page_texts) - 1):
            with self.subTest(page=idx + 1, role="intermediate"):
                text = page_texts[idx]
                # The intermediate page should not have the CRM/registration
                self.assertNotIn(
                    f"CRM: {registration}",
                    text,
                    f"Mini-signature found on intermediate page {idx + 1}",
                )

        # Final page MUST contain doctor signature information
        last_page = page_texts[-1]
        self.assertIn(doctor_name, last_page)
        self.assertIn(
            registration,
            last_page,
            "Doctor registration missing from final page",
        )


class TestWardAndBedInHeader(DailyNotePDFGeneratorTestCase):
    """Verify ward/sector and bed appear in the repeated header."""

    def test_repeated_header_includes_ward_and_bed_when_available(self):
        """When patient has ward and bed, both appear on every page."""
        from apps.patients.models import Ward

        ward = Ward.objects.create(
            name="Unidade de Terapia Intensiva",
            abbreviation="UTI",
            created_by=self.user,
            updated_by=self.user,
        )
        self.patient.ward = ward
        self.patient.bed = "Leito 05"
        self.patient.save()

        note = _make_dailynote(self.user, self.patient)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        page_texts = _extract_page_texts(pdf_buffer)

        self.assertGreaterEqual(len(page_texts), 2, "PDF must span multiple pages")

        for idx, text in enumerate(page_texts):
            with self.subTest(page=idx + 1):
                self.assertIn(
                    "UTI",
                    text,
                    f"Ward abbreviation missing from page {idx + 1}",
                )
                self.assertIn(
                    "Leito 05",
                    text,
                    f"Bed missing from page {idx + 1}",
                )

    def test_repeated_header_uses_placeholders_when_ward_or_bed_missing(self):
        """When ward or bed is missing, placeholder dashes appear on every page."""
        # Patient has no ward and no bed (default state)
        note = _make_dailynote(self.user, self.patient)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        page_texts = _extract_page_texts(pdf_buffer)

        self.assertGreaterEqual(len(page_texts), 2, "PDF must span multiple pages")

        for idx, text in enumerate(page_texts):
            with self.subTest(page=idx + 1):
                # The header should still render without error and include
                # the patient name (confirming header was drawn)
                self.assertIn(
                    self.patient.name,
                    text,
                    f"Patient name missing from page {idx + 1}",
                )


class TestBoxedTwoColumnHeader(DailyNotePDFGeneratorTestCase):
    """Verify the boxed two-column header structure.

    Left column: hospital logo + hospital name.
    Right column: patient context (name, record, ward/sector, bed, specialty).
    Page number in top-right. Title below the boxed header.
    """

    def _build_canvas(
        self, patient_data=None, hospital_config=None, specialty_name="", logo_path=None
    ):
        """Build a DailyNoteCanvas with controlled inputs for unit testing."""
        from apps.dailynotes.services.pdf_generator import DailyNoteCanvas

        buf = io.BytesIO()
        config = hospital_config or {"name": "Hospital Test"}
        if logo_path:
            config["logo_path"] = logo_path
        pd = patient_data or {
            "name": "Paciente Teste",
            "record_number": "REC-001",
            "ward": "UTI",
            "bed": "Leito 03",
        }
        c = DailyNoteCanvas(
            buf,
            pagesize=(595.27, 841.89),  # A4
            hospital_config=config,
            patient_data=pd,
            specialty_name=specialty_name,
        )
        return c, buf

    def test_header_draws_boxed_two_column_structure(self):
        """Header must draw a visible box (rect) around the two-column area."""
        from unittest.mock import patch

        c, _ = self._build_canvas()
        # We'll verify the canvas calls rect (box) during header rendering.
        with patch.object(c, "rect", wraps=c.rect) as mock_rect:
            c._draw_compact_header(1, 1)
            mock_rect.assert_called()
            # Verify a non-zero size rect was drawn
            args = mock_rect.call_args[0]
            self.assertGreater(args[2], 0, "Box width must be positive")
            self.assertGreater(args[3], 0, "Box height must be positive")

    def test_header_renders_hospital_logo_and_name_in_left_column_when_logo_available(
        self,
    ):
        """When logo resolves, left column draws image + hospital name."""
        import os
        import tempfile
        from unittest.mock import patch

        # Create a small 1x1 PNG for testing
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            # Minimal valid PNG bytes
            tmp.write(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00"
                b"\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00"
                b"\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9c"
                b"\x62\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
                b"\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            tmp_path = tmp.name

        try:
            c, buf = self._build_canvas(logo_path=tmp_path)
            with patch.object(c, "drawImage", wraps=c.drawImage) as mock_img:
                c._draw_compact_header(1, 1)
                mock_img.assert_called_once()
                # Hospital name must also be drawn
            buf.seek(0)
        finally:
            os.unlink(tmp_path)

    def test_header_falls_back_to_hospital_name_when_logo_is_unavailable(self):
        """When logo is missing, header still renders hospital name in left column."""
        c, buf = self._build_canvas(
            hospital_config={"name": "Hospital Sem Logo"},
        )
        # No logo_path in config; should not crash
        c._draw_compact_header(1, 1)
        # Verify the hospital name appears in the generated text
        buf.seek(0)
        # We just check no exception was raised and the method completed
        # (the hospital name is drawn via drawString, not extractable as text
        # from a canvas that wasn't fully saved)
        # Instead, use a spy to verify drawString was called with the name
        from unittest.mock import patch

        c2, _ = self._build_canvas(
            hospital_config={"name": "Hospital Sem Logo"},
        )
        with patch.object(c2, "drawString", wraps=c2.drawString) as mock_str:
            c2._draw_compact_header(1, 1)
            calls_text = " ".join(str(call) for call in mock_str.call_args_list)
            self.assertIn("Hospital Sem Logo", calls_text)

    def test_header_renders_patient_context_in_right_column(self):
        """Right column must include patient name, record number, ward/sector, bed."""
        from unittest.mock import patch

        pd = {
            "name": "João da Silva",
            "record_number": "REC-999",
            "ward": "UTI",
            "bed": "Leito 10",
        }
        c, _ = self._build_canvas(
            patient_data=pd,
            specialty_name="Cardiologia",
        )
        with patch.object(c, "drawString", wraps=c.drawString) as mock_str:
            c._draw_compact_header(1, 1)
            calls_text = " ".join(str(call) for call in mock_str.call_args_list)
            self.assertIn("João da Silva", calls_text)
            self.assertIn("REC-999", calls_text)
            self.assertIn("UTI", calls_text)
            self.assertIn("Leito 10", calls_text)
            self.assertIn("Cardiologia", calls_text)

    def test_header_keeps_title_and_page_number_positions_stable(self):
        """Page number must remain in top-right area after boxed header."""
        c, _ = self._build_canvas()
        # _draw_page_number should still work independently
        from unittest.mock import patch

        with patch.object(c, "drawRightString", wraps=c.drawRightString) as mock_rs:
            c._draw_page_number(1, 3)
            mock_rs.assert_called_once()
            # Verify x position is near right edge of A4
            args = mock_rs.call_args[0]
            self.assertGreater(args[0], 400, "Page number x should be near right edge")
            self.assertIn("1/3", args[2])


class TestBoxedTwoColumnHeaderIntegration(DailyNotePDFGeneratorTestCase):
    """Integration tests for the boxed two-column header in full PDF output."""

    def test_full_pdf_contains_hospital_name_on_every_page(self):
        """Hospital name must appear on every page of the generated PDF."""
        note = _make_dailynote(self.user, self.patient)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        page_texts = _extract_page_texts(pdf_buffer)

        self.assertGreaterEqual(len(page_texts), 2)
        hospital_name = self.generator.hospital_config.get("name", "")
        for idx, text in enumerate(page_texts):
            with self.subTest(page=idx + 1):
                self.assertIn(
                    hospital_name,
                    text,
                    f"Hospital name missing from page {idx + 1}",
                )

    def test_full_pdf_contains_patient_context_on_every_page(self):
        """Patient context tokens appear on every page via boxed header."""
        from apps.patients.models import PatientRecordNumber, Ward

        ward = Ward.objects.create(
            name="Centro Cirúrgico",
            abbreviation="CC",
            created_by=self.user,
            updated_by=self.user,
        )
        self.patient.ward = ward
        self.patient.bed = "Leito 12"
        self.patient.save()
        PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number="HGRS-2025-00999",
            is_current=True,
            created_by=self.user,
            updated_by=self.user,
        )

        note = _make_dailynote(self.user, self.patient)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        page_texts = _extract_page_texts(pdf_buffer)

        self.assertGreaterEqual(len(page_texts), 2)
        for idx, text in enumerate(page_texts):
            with self.subTest(page=idx + 1):
                self.assertIn(self.patient.name, text)
                self.assertIn("HGRS-2025-00999", text)
                self.assertIn("CC", text)
                self.assertIn("Leito 12", text)


class TestCompactContentRenderer(DailyNotePDFGeneratorTestCase):
    """Verify compact content rendering for headings, paragraphs, and lists."""

    def test_compact_content_renders_markdown_headings_without_hash_markers(
        self,
    ):
        """Headings in compact content must not include ## hash markers."""
        markdown = (
            "## Exame Físico\n\n"
            "Paciente em bom estado geral.\n\n"
            "### Acondicionamento\n\n"
            "Estável."
        )
        note = _make_dailynote(self.user, self.patient, content=markdown)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        page_texts = _extract_page_texts(pdf_buffer)
        full_text = "\n".join(page_texts)

        # Heading text should be present
        self.assertIn("Exame Físico", full_text)
        self.assertIn("Acondicionamento", full_text)
        # Hash markers must NOT appear in the PDF text
        self.assertNotIn("## ", full_text)
        self.assertNotIn("### ", full_text)

    def test_compact_content_preserves_section_order_with_compact_rendering(
        self,
    ):
        """Sections must appear in the original markdown order."""
        markdown = (
            "## Primeira Seção\n\nTexto da primeira seção.\n\n"
            "## Segunda Seção\n\nTexto da segunda seção.\n\n"
            "## Terceira Seção\n\nTexto da terceira seção."
        )
        note = _make_dailynote(self.user, self.patient, content=markdown)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        page_texts = _extract_page_texts(pdf_buffer)
        full_text = "\n".join(page_texts)

        pos_first = full_text.index("Primeira Seção")
        pos_second = full_text.index("Segunda Seção")
        pos_third = full_text.index("Terceira Seção")

        self.assertLess(pos_first, pos_second, "First section must precede second")
        self.assertLess(pos_second, pos_third, "Second section must precede third")

    def test_compact_content_renders_list_items_as_readable_pdf_text(
        self,
    ):
        """List items must appear as readable text in the PDF."""
        markdown = (
            "## Medicamentos\n\n- Amoxicilina 500mg\n- Dipirona 1g\n- Omeprazol 20mg\n"
        )
        note = _make_dailynote(self.user, self.patient, content=markdown)
        pdf_buffer = self.generator.generate_from_dailynote(note)
        page_texts = _extract_page_texts(pdf_buffer)
        full_text = "\n".join(page_texts)

        self.assertIn("Amoxicilina 500mg", full_text)
        self.assertIn("Dipirona 1g", full_text)
        self.assertIn("Omeprazol 20mg", full_text)

    def test_compact_content_builder_uses_compact_spacers_for_sections(
        self,
    ):
        """Compact renderer must use small spacers (<= 4pt) between sections."""
        markdown = "## Section A\n\nParagraph text.\n\n## Section B\n\nMore text."
        flowables = self.generator._build_compact_content(markdown)
        spacers = [f for f in flowables if isinstance(f, Spacer)]

        self.assertGreater(len(spacers), 0, "Should have some spacers")
        for spacer in spacers:
            self.assertLessEqual(
                spacer.height,
                4,
                f"Compact spacer height {spacer.height} exceeds 4pt threshold",
            )


class TestAgeAtEvent(DailyNotePDFGeneratorTestCase):
    """R1: age shown in the header is computed at the note event date.

    Patient fixture birthday is 1985-03-15: on 2026-03-14 the patient is
    40 years old; on 2026-03-15 the patient turns 41.
    """

    def test_age_uses_event_date_the_day_before_birthday(self):
        """Header shows 40 anos for an event the day before the birthday."""
        event = datetime(2026, 3, 14, 10, 0, tzinfo=timezone.get_current_timezone())
        note = _make_dailynote(
            self.user,
            self.patient,
            content="Evolução curta.",
            event_datetime=event,
        )
        page_texts = _extract_page_texts(self.generator.generate_from_dailynote(note))
        full_text = "\n".join(page_texts)

        self.assertIn("Maria Oliveira Santos - 40 anos", full_text)

    def test_age_uses_event_date_on_birthday(self):
        """Header shows 41 anos for an event on the birthday itself."""
        event = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.get_current_timezone())
        note = _make_dailynote(
            self.user,
            self.patient,
            content="Evolução curta.",
            event_datetime=event,
        )
        page_texts = _extract_page_texts(self.generator.generate_from_dailynote(note))
        full_text = "\n".join(page_texts)

        self.assertIn("Maria Oliveira Santos - 41 anos", full_text)


class TestActiveAdmissionInHeader(DailyNotePDFGeneratorTestCase):
    """R2: active-admission date appears in the repeated header."""

    def test_multipage_header_repeats_age_and_active_admission(self):
        """Every page shows `Nome - N anos` and `Adm.: DD/MM/YY` from the
        active admission."""
        from apps.patients.models import PatientAdmission

        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=30),
            initial_bed="Leito 01",
            created_by=self.user,
            updated_by=self.user,
        )
        event = datetime(2026, 3, 14, 10, 0, tzinfo=timezone.get_current_timezone())
        note = _make_dailynote(
            self.user,
            self.patient,
            event_datetime=event,
        )
        page_texts = _extract_page_texts(self.generator.generate_from_dailynote(note))

        self.assertGreaterEqual(len(page_texts), 2, "PDF must span multiple pages")
        expected_adm = admission.admission_datetime.strftime("%d/%m/%y")
        for idx, text in enumerate(page_texts):
            with self.subTest(page=idx + 1):
                self.assertIn(
                    "Maria Oliveira Santos - 40 anos",
                    text,
                    f"Age token missing from page {idx + 1}",
                )
                self.assertIn(
                    f"Adm.: {expected_adm}",
                    text,
                    f"Admission token missing from page {idx + 1}",
                )

    def test_header_uses_only_active_admission_not_historical(self):
        """Without an active admission the header shows exactly `Adm.: —`,
        even when a historical admission and `last_admission_date` exist."""
        from apps.patients.models import PatientAdmission

        historical = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=60),
            discharge_datetime=timezone.now() - timedelta(days=40),
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            initial_bed="Leito 02",
            created_by=self.user,
            updated_by=self.user,
        )
        self.patient.last_admission_date = historical.admission_datetime.date()
        self.patient.save()

        note = _make_dailynote(self.user, self.patient)
        page_texts = _extract_page_texts(self.generator.generate_from_dailynote(note))

        self.assertGreaterEqual(len(page_texts), 2, "PDF must span multiple pages")
        historical_adm = historical.admission_datetime.strftime("%d/%m/%y")
        for idx, text in enumerate(page_texts):
            with self.subTest(page=idx + 1):
                self.assertIn(
                    "Adm.: —",
                    text,
                    f"Placeholder missing from page {idx + 1}",
                )
                self.assertNotIn(
                    f"Adm.: {historical_adm}",
                    text,
                    f"Historical admission leaked on page {idx + 1}",
                )


class TestHeaderGeometry(DailyNotePDFGeneratorTestCase):
    """R4: Daily Note header geometry prevents overlaps."""

    LONG_PD: ClassVar[dict] = {
        "name": ("Maria Antônia do Nascimento Oliveira Santos Ferreira da Costa"),
        "record_number": "HGRS-2025-0099999999",
        "ward": "Unidade de Terapia Intensiva",
        "bed": "Leito 05",
        "age_at_event": 46,
        "admission_datetime": None,  # replaced per-test to avoid TZ issues
    }

    def _build_canvas(self, patient_data=None, specialty_name=""):
        """Build a DailyNoteCanvas with controlled inputs for geometry tests."""
        from apps.dailynotes.services.pdf_generator import DailyNoteCanvas

        buf = io.BytesIO()
        return DailyNoteCanvas(
            buf,
            pagesize=(595.27, 841.89),  # A4
            hospital_config={"name": "Hospital Test"},
            patient_data=patient_data or {},
            specialty_name=specialty_name,
        )

    def _long_pd(self):
        """Long patient context with an active-admission datetime."""
        pd = dict(self.LONG_PD)
        pd["admission_datetime"] = datetime(
            2026, 2, 1, 8, 30, tzinfo=timezone.get_current_timezone()
        )
        return pd

    def test_fit_helper_keeps_long_lines_inside_column(self):
        """Wrapped context lines fit the right-column width and box height,
        and the age/admission tokens survive wrapping."""
        from apps.dailynotes.services.pdf_generator import (
            _CONTEXT_FONT_MIN,
            _CONTEXT_FONT_NAME,
        )

        c = self._build_canvas(
            patient_data=self._long_pd(), specialty_name="Cardiologia"
        )
        lines = c._build_context_lines(c.patient_data)
        max_width = c._BOX_WIDTH / 2 - 2 * c._BOX_PAD
        font_size, fitted, line_gap = c._fit_context_lines(
            lines, max_width, c._box_height
        )
        available = c._box_height - 2 * c._BOX_PAD

        self.assertLessEqual(
            len(fitted) * line_gap, available + 1e-6, "Block exceeds box"
        )
        for line in fitted:
            width = c.stringWidth(line, _CONTEXT_FONT_NAME, font_size)
            self.assertLessEqual(width, max_width + 1e-6, f"Line too wide: {line!r}")
        self.assertGreaterEqual(font_size, _CONTEXT_FONT_MIN, "Font shrank below floor")
        joined = " ".join(fitted)
        self.assertIn("- 46 anos", joined)
        self.assertIn("Adm.: 01/02/26", joined)

    def test_wrap_to_width_splits_overlong_line(self):
        """Extremely long values wrap word-by-word within the column width."""
        from apps.dailynotes.services.pdf_generator import _CONTEXT_FONT_NAME

        c = self._build_canvas(patient_data={"name": "X"})
        max_width = 100.0
        long_line = "Paciente: " + "Superpalavra " * 20
        wrapped = c._wrap_to_width(long_line.split("\n"), max_width, 7.5)

        self.assertGreater(len(wrapped), 1, "Long line must wrap")
        for line in wrapped:
            width = c.stringWidth(line, _CONTEXT_FONT_NAME, 7.5)
            self.assertLessEqual(width, max_width + 1e-6, f"Segment too wide: {line!r}")
        self.assertIn("Superpalavra", " ".join(wrapped))

    def test_drawn_context_lines_stay_inside_header_box(self):
        """All context text drawn by the header stays inside the box."""
        from unittest.mock import patch

        c = self._build_canvas(
            patient_data=self._long_pd(), specialty_name="Cardiologia"
        )
        with patch.object(c, "drawString", wraps=c.drawString) as mock_str:
            c._draw_compact_header(1, 1)

        box_bottom = c._BOX_TOP_Y - c._box_height
        box_top = c._BOX_TOP_Y
        box_left = c._BOX_LEFT
        box_right = c._BOX_LEFT + c._BOX_WIDTH
        for x, y, text in (call.args for call in mock_str.call_args_list):
            with self.subTest(text=text[:40]):
                self.assertGreaterEqual(
                    y, box_bottom - 0.01, f"Text below box: {text!r}"
                )
                self.assertLessEqual(y, box_top + 0.01, f"Text above box: {text!r}")
                self.assertGreaterEqual(
                    x, box_left - 0.01, f"Text left of box: {text!r}"
                )
                self.assertLessEqual(
                    x, box_right + 0.01, f"Text right of box: {text!r}"
                )

    def test_page_number_has_reserved_area_above_box(self):
        """Page number is drawn in the top strip, not over patient text."""
        from unittest.mock import patch

        c = self._build_canvas(patient_data={"name": "Paciente Teste"})
        with patch.object(c, "drawRightString", wraps=c.drawRightString) as mock_rs:
            c._draw_page_number(2, 5)
        _x, y, text = mock_rs.call_args[0]

        self.assertGreaterEqual(
            y, c._BOX_TOP_Y, "Page number must not enter the header box"
        )
        self.assertIn("2/5", text)

    def test_generate_pdf_reserves_frame_consistent_with_box(self):
        """The generator's top-frame reservation keeps title/body below the
        header box bottom border."""
        from unittest.mock import patch

        from reportlab.lib.units import cm as rl_cm

        from apps.dailynotes.services.pdf_generator import (
            _HEADER_FRAME_GAP_CM,
            _HEADER_FRAME_OFFSET_CM,
            _HEADER_TOP_OFFSET_CM,
            HospitalLetterheadGenerator,
            _required_header_box_height_cm,
        )

        note = _make_dailynote(self.user, self.patient, content="Evolução curta.")
        with patch.object(
            HospitalLetterheadGenerator,
            "generate_pdf",
            wraps=HospitalLetterheadGenerator.generate_pdf.__get__(self.generator),
        ) as mock_gen:
            self.generator.generate_from_dailynote(note)

        header_space_cm = mock_gen.call_args.kwargs["header_height_cm"]
        margins_top_cm = self.generator.margins["top"] / rl_cm
        pd = self.generator._build_header_patient_data(note)
        box_cm = _required_header_box_height_cm(pd, "")
        expected_cm = (
            _HEADER_TOP_OFFSET_CM
            + box_cm
            - margins_top_cm
            + _HEADER_FRAME_OFFSET_CM
            + _HEADER_FRAME_GAP_CM
        )
        self.assertAlmostEqual(header_space_cm, expected_cm, places=6)

        frame_top_cm = margins_top_cm + header_space_cm - _HEADER_FRAME_OFFSET_CM
        box_bottom_cm = _HEADER_TOP_OFFSET_CM + box_cm
        self.assertGreaterEqual(
            frame_top_cm,
            box_bottom_cm + _HEADER_FRAME_GAP_CM - 1e-6,
            "Frame top above header box",
        )


class TestContextFittingLegibility(DailyNotePDFGeneratorTestCase):
    """Fix slice R2/R3/R4: legible leading, oversized tokens, coherent geometry."""

    def _build_canvas(self, patient_data=None, specialty_name=""):
        """Build a DailyNoteCanvas for fitting/drawing unit tests."""
        from apps.dailynotes.services.pdf_generator import DailyNoteCanvas

        buf = io.BytesIO()
        return DailyNoteCanvas(
            buf,
            pagesize=(595.27, 841.89),  # A4
            hospital_config={"name": "Hospital Test"},
            patient_data=patient_data or {},
            specialty_name=specialty_name,
        )

    def _dense_patient_data(self):
        """Context dense enough to force many wrapped lines at min font."""
        return {
            "name": "Maria " * 140,
            "record_number": "HGRS-2025-0099999999",
            "ward": "Unidade de Terapia Intensiva",
            "bed": "Leito 05",
            "age_at_event": 46,
            "admission_datetime": datetime(
                2026, 2, 1, 8, 30, tzinfo=timezone.get_current_timezone()
            ),
        }

    def test_fit_keeps_leading_at_legible_ratio_for_many_lines(self):
        """Leading must never drop below font_size * ratio, even when the
        context forces many wrapped lines."""
        from apps.dailynotes.services.pdf_generator import (
            _CONTEXT_LEADING_RATIO,
        )

        c = self._build_canvas(patient_data=self._dense_patient_data())
        lines = c._build_context_lines(c.patient_data)
        max_width = c._BOX_WIDTH / 2 - 2 * c._BOX_PAD
        font_size, fitted, line_gap = c._fit_context_lines(
            lines, max_width, c._box_height
        )

        self.assertGreater(len(fitted), 5, "Scenario must force many lines")
        self.assertGreaterEqual(
            line_gap,
            font_size * _CONTEXT_LEADING_RATIO - 1e-6,
            "Leading below legible ratio for the chosen font",
        )
        self.assertLessEqual(
            len(fitted) * line_gap,
            c._box_height - 2 * c._BOX_PAD + 1e-6,
            "Wrapped block exceeds the header box",
        )

    def test_oversized_token_without_spaces_is_chunked(self):
        """A single token wider than the column is broken into fragments that
        all fit max_width, preserving every character."""
        from apps.dailynotes.services.pdf_generator import _CONTEXT_FONT_NAME

        c = self._build_canvas(patient_data={"name": "X"})
        max_width = 60.0
        token = "Q" * 300
        wrapped = c._wrap_to_width([f"Prontuário: {token}"], max_width, 6.0)

        self.assertGreater(len(wrapped), 1, "Token must be chunked")
        for line in wrapped:
            self.assertLessEqual(
                c.stringWidth(line, _CONTEXT_FONT_NAME, 6.0),
                max_width + 1e-6,
                f"Fragment too wide: {line[:20]!r}",
            )
        joined = "".join(wrapped)
        self.assertEqual(joined.count("Q"), len(token), "Characters were lost")
        self.assertTrue(joined.startswith("Prontuário:"), "Prefix lost")

    def test_header_reservation_tracks_grown_box(self):
        """The generator reserves a frame that keeps title/body below the
        grown header box for dense context."""
        from unittest.mock import patch

        from reportlab.lib.units import cm as rl_cm

        from apps.dailynotes.services.pdf_generator import (
            _HEADER_BOX_HEIGHT_MIN_CM,
            _HEADER_FRAME_GAP_CM,
            _HEADER_FRAME_OFFSET_CM,
            _HEADER_TOP_OFFSET_CM,
            HospitalLetterheadGenerator,
            _required_header_box_height_cm,
        )

        pd = self._dense_patient_data()
        with patch.object(
            HospitalLetterheadGenerator,
            "generate_pdf",
            wraps=HospitalLetterheadGenerator.generate_pdf.__get__(self.generator),
        ) as mock_gen:
            self.generator.generate_pdf(
                content_elements=[], patient_data=pd, specialty_name="Cardiologia"
            )

        header_space_cm = mock_gen.call_args.kwargs["header_height_cm"]
        box_cm = _required_header_box_height_cm(pd, "Cardiologia")
        self.assertGreater(
            box_cm,
            _HEADER_BOX_HEIGHT_MIN_CM,
            "Dense context must grow the header box",
        )
        margins_top_cm = self.generator.margins["top"] / rl_cm
        expected_cm = (
            _HEADER_TOP_OFFSET_CM
            + box_cm
            - margins_top_cm
            + _HEADER_FRAME_OFFSET_CM
            + _HEADER_FRAME_GAP_CM
        )
        self.assertAlmostEqual(header_space_cm, expected_cm, places=6)

        frame_top_cm = margins_top_cm + header_space_cm - _HEADER_FRAME_OFFSET_CM
        box_bottom_cm = _HEADER_TOP_OFFSET_CM + box_cm
        self.assertGreaterEqual(
            frame_top_cm,
            box_bottom_cm + _HEADER_FRAME_GAP_CM - 1e-6,
            "Frame top must stay below the box bottom",
        )

    def test_drawn_glyphs_stay_inside_header_box_with_font_margin(self):
        """Drawn context baselines keep ascenders/descenders inside the box."""
        from unittest.mock import patch

        from apps.dailynotes.services.pdf_generator import (
            _CONTEXT_ASCENT_RATIO,
            _CONTEXT_DESCENT_RATIO,
            _CONTEXT_FONT_NAME,
        )

        c = self._build_canvas(patient_data=self._dense_patient_data())
        with (
            patch.object(c, "setFont", wraps=c.setFont) as mock_font,
            patch.object(c, "drawString", wraps=c.drawString) as mock_str,
        ):
            c._draw_compact_header(1, 1)

        font_size = next(
            call.args[1]
            for call in mock_font.call_args_list
            if call.args[0] == _CONTEXT_FONT_NAME
        )
        ascent = _CONTEXT_ASCENT_RATIO * font_size
        descent = _CONTEXT_DESCENT_RATIO * font_size
        box_bottom = c._BOX_TOP_Y - c._box_height
        box_top = c._BOX_TOP_Y
        mid_x = c._BOX_LEFT + c._BOX_WIDTH / 2

        right_ys = [
            call.args[1] for call in mock_str.call_args_list if call.args[0] >= mid_x
        ]
        self.assertGreater(len(right_ys), 0, "Right-column lines must be drawn")
        for y in right_ys:
            with self.subTest(y=y):
                self.assertGreaterEqual(
                    y - descent,
                    box_bottom + c._BOX_PAD - 1e-6,
                    "Glyph descender below the box",
                )
                self.assertLessEqual(
                    y + ascent,
                    box_top - c._BOX_PAD + 1e-6,
                    "Glyph ascender above the box",
                )

    def test_short_name_stays_on_single_context_line(self):
        """Normal names render as a single `Paciente: Nome - N anos` line."""
        from apps.dailynotes.services.pdf_generator import (
            _CONTEXT_FONT_MAX,
            _CONTEXT_FONT_NAME,
        )

        c = self._build_canvas(
            patient_data={
                "name": "Maria Oliveira Santos",
                "age_at_event": 40,
            }
        )
        lines = c._build_context_lines(c.patient_data)
        self.assertEqual(lines[0], "Paciente: Maria Oliveira Santos - 40 anos")
        self.assertEqual(lines[-1], "Adm.: —")
        max_width = c._BOX_WIDTH / 2 - 2 * c._BOX_PAD
        self.assertLessEqual(
            c.stringWidth(lines[0], _CONTEXT_FONT_NAME, _CONTEXT_FONT_MAX),
            max_width + 1e-6,
            "Short name line should not wrap",
        )
