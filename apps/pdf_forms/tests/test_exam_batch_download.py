"""S2: batch 3-up download of an exam-request batch (chequinho).

Covers R1 (pagination ceil(N/3)), R2 (deterministic slots at 100%),
R3 (cut lines only between printed vias), R4 (via identical to single
print), R5 (draft gating + per-submission permissions), R6 (fallback
1-up on unexpected template height). R7 is covered by the untouched
single-download suite (no regression allowed).
"""

import re
import uuid
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from apps.accounts.tests.helpers import create_navigation_user
from apps.pdf_forms.models import PDFFormSubmission
from apps.pdf_forms.services.exam_batch_imposition import (
    CROP_BASE_CM,
    CROP_TOP_CM,
    VIAS_PER_SHEET,
    batch_slot,
    compose_exam_batch,
    cut_line_ys,
)
from apps.pdf_forms.services.pdf_overlay import PDFFormOverlay

from .factories import PatientFactory, PDFFormTemplateFactory

User = get_user_model()

EXAM_FIELD_CONFIG = {
    "requestReason": {
        "type": "text",
        "label": "Motivo",
        "x": 2.0,
        "y": 2.0,
        "width": 17.0,
        "height": 0.7,
        "font_size": 12,
    },
    "examRequested": {
        "type": "text",
        "label": "Exame",
        "x": 2.0,
        "y": 4.0,
        "width": 12.0,
        "height": 0.7,
        "font_size": 12,
    },
    "examCode": {
        "type": "text",
        "label": "Codigo",
        "x": 15.0,
        "y": 4.0,
        "width": 4.0,
        "height": 0.7,
        "font_size": 12,
    },
    "currentDate": {
        "type": "date",
        "label": "Data",
        "x": 2.0,
        "y": 6.0,
        "width": 5.0,
        "height": 0.7,
        "font_size": 12,
    },
    "doctor": {
        "type": "text",
        "label": "Profissional",
        "x": 8.0,
        "y": 6.0,
        "width": 11.0,
        "height": 0.7,
        "font_size": 12,
    },
}


def make_blank_pdf_bytes(width=A4[0], height=A4[1]):
    """Build a blank single-page PDF of the requested size."""
    buffer = BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=(width, height))
    pdf_canvas.showPage()
    pdf_canvas.save()
    buffer.seek(0)
    return buffer.getvalue()


def make_chequinho_template(user, name="Chequinho S2", page_size=A4):
    template = PDFFormTemplateFactory(
        name=name,
        form_fields=dict(EXAM_FIELD_CONFIG),
        created_by=user,
    )
    template.pdf_file.save(
        f"cheq_s2_{uuid.uuid4().hex}.pdf",
        ContentFile(make_blank_pdf_bytes(*page_size)),
        save=True,
    )
    return template


def exam_form_data(n, batch_id):
    """Form data whose overlay text carries no 's'/'S' (stroke counting)."""
    return {
        "requestReason": "Dor no peito",
        "examRequested": f"EXAME-{n:02d} HEMOGRAMA",
        "examCode": f"02020{n:04d}",
        "currentDate": "2026-11-01",
        "doctor": "Dra. Ana",
        "batch_id": batch_id,
    }


def page_texts(pdf_bytes):
    reader = PdfReader(BytesIO(pdf_bytes))
    return [page.extract_text() or "" for page in reader.pages]


def stroke_count(page):
    """Count standalone 'S' (stroke) operators in a page content stream."""
    contents = page.get_contents()
    raw = contents.get_data() if contents is not None else b""
    return len(re.findall(rb"\nS\n", b"\n" + raw + b"\n"))


class BatchSlotMathTests(TestCase):
    """R2 unit: deterministic pagination slot=(N-1)%3 sheet=(N-1)//3."""

    def test_first_via_top_of_first_sheet(self):
        self.assertEqual(batch_slot(1), (0, 0))

    def test_third_via_bottom_of_first_sheet(self):
        self.assertEqual(batch_slot(3), (0, 2))

    def test_fourth_via_top_of_second_sheet(self):
        self.assertEqual(batch_slot(4), (1, 0))

    def test_ninth_via_bottom_of_third_sheet(self):
        self.assertEqual(batch_slot(9), (2, 2))


class CutLineHelperTests(TestCase):
    """R3 unit: dashed cut lines only between printed vias."""

    def test_single_via_has_no_cut_line(self):
        self.assertEqual(cut_line_ys(1), [])

    def test_two_vias_have_one_cut_line(self):
        self.assertEqual(len(cut_line_ys(2)), 1)

    def test_three_vias_have_two_cut_lines(self):
        self.assertEqual(len(cut_line_ys(3)), 2)

    def test_cut_lines_run_top_to_bottom_inside_page(self):
        page_height = A4[1]
        ys = cut_line_ys(3)
        self.assertTrue(all(0 < y < page_height for y in ys))
        self.assertGreater(ys[0], ys[1])


class ComposeEmptyTests(TestCase):
    """Composing zero vias is a programmer error, never a blank PDF."""

    def test_empty_batch_raises(self):
        with self.assertRaises(ValueError):
            compose_exam_batch([])


class ExamBatchDownloadViewTests(TestCase):
    """R1/R2/R3/R4/R5 end to end through the batch download route."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = create_navigation_user(
            username="batch-dl-doctor",
            email="batch-dl-doctor@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
        )
        cls.patient = PatientFactory(created_by=cls.doctor, updated_by=cls.doctor)
        cls.template = make_chequinho_template(cls.doctor)

    def _create_batch(self, count, draft_indices=frozenset(), batch_id=None):
        batch_id = batch_id or str(uuid.uuid4())
        submissions = []
        for n in range(1, count + 1):
            submissions.append(
                PDFFormSubmission.objects.create(
                    form_template=self.template,
                    patient=self.patient,
                    created_by=self.doctor,
                    updated_by=self.doctor,
                    event_datetime=timezone.now(),
                    description=f"Exame {n}",
                    form_data=exam_form_data(n, batch_id),
                    is_draft=(n in draft_indices),
                )
            )
        return batch_id, submissions

    def _download_url(self, batch_id):
        return reverse("pdf_forms:exam_batch_download", kwargs={"batch_id": batch_id})

    def _download(self, batch_id):
        self.client.force_login(self.doctor)
        return self.client.get(self._download_url(batch_id))

    def test_pagination_one_two_three_vias_single_sheet(self):
        """R1: N=1/2/3 finals compose onto exactly one A4 sheet."""
        for count in (1, 2, 3):
            with self.subTest(count=count):
                batch_id, _ = self._create_batch(count)
                response = self._download(batch_id)
                self.assertEqual(response.status_code, 200)
                reader = PdfReader(BytesIO(response.content))
                self.assertEqual(len(reader.pages), 1)
                self.assertEqual(response["Content-Type"], "application/pdf")

    def test_pagination_four_vias_two_sheets(self):
        """R1: N=4 finals compose onto two sheets (3 + 1)."""
        batch_id, _ = self._create_batch(4)
        response = self._download(batch_id)
        self.assertEqual(response.status_code, 200)
        reader = PdfReader(BytesIO(response.content))
        self.assertEqual(len(reader.pages), 2)

    def test_pagination_nine_vias_three_full_sheets(self):
        """R1/R2: N=9 finals compose onto three full sheets."""
        batch_id, _ = self._create_batch(9)
        response = self._download(batch_id)
        self.assertEqual(response.status_code, 200)
        reader = PdfReader(BytesIO(response.content))
        self.assertEqual(len(reader.pages), 3)

    def test_slots_follow_creation_order_top_to_bottom(self):
        """R2: exam N sits at slot (N-1)%3 of sheet (N-1)//3, in order."""
        batch_id, _ = self._create_batch(4)
        response = self._download(batch_id)
        texts = page_texts(response.content)
        self.assertEqual(len(texts), 2)
        for n in (1, 2, 3):
            self.assertIn(f"EXAME-{n:02d}", texts[0])
        self.assertNotIn("EXAME-04", texts[0])
        self.assertIn("EXAME-04", texts[1])
        self.assertNotIn("EXAME-01", texts[1])

    def test_sheets_are_a4_and_stack_without_scaling(self):
        """R2: sheets stay A4; vias merge by pure translation (100%)."""
        batch_id, _ = self._create_batch(3)
        response = self._download(batch_id)
        reader = PdfReader(BytesIO(response.content))
        page = reader.pages[0]
        self.assertAlmostEqual(float(page.mediabox.width), A4[0], places=1)
        self.assertAlmostEqual(float(page.mediabox.height), A4[1], places=1)
        contents = page.get_contents()
        raw = contents.get_data() if contents is not None else b""
        matrices = re.findall(
            rb"([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) cm",
            raw,
        )
        self.assertTrue(matrices)
        for a, b, c, d, _e, _f in matrices:
            self.assertEqual((float(a), float(b), float(c), float(d)), (1.0, 0.0, 0.0, 1.0))

    def test_cut_lines_only_between_printed_vias(self):
        """R3: 3 vias -> 2 lines; a lone via on sheet 2 -> none."""
        batch_id, _ = self._create_batch(4)
        response = self._download(batch_id)
        reader = PdfReader(BytesIO(response.content))
        self.assertEqual(stroke_count(reader.pages[0]), 2)
        self.assertEqual(stroke_count(reader.pages[1]), 0)

    def test_single_via_sheet_has_no_cut_line(self):
        """R3: a lone via never carries a stray cut line."""
        batch_id, _ = self._create_batch(1)
        response = self._download(batch_id)
        reader = PdfReader(BytesIO(response.content))
        self.assertEqual(stroke_count(reader.pages[0]), 0)

    def test_via_identical_to_single_print(self):
        """R4: batch via carries exactly the single-print text content."""
        batch_id, submissions = self._create_batch(2)
        overlay = PDFFormOverlay()
        single_bytes = overlay.render_filled_pdf_bytes(
            submissions[0].form_template.pdf_file.path,
            submissions[0].form_data,
            submissions[0].form_template.form_fields,
        )
        single_text = page_texts(single_bytes)[0]
        response = self._download(batch_id)
        batch_texts = page_texts(response.content)
        # extract_text order is not visual order: compare line by line.
        for line in single_text.strip().splitlines():
            self.assertIn(line.strip(), batch_texts[0])

    def test_drafts_excluded_from_composition(self):
        """R5: drafts never compose; only finals set pagination."""
        batch_id, _ = self._create_batch(3, draft_indices={2})
        response = self._download(batch_id)
        self.assertEqual(response.status_code, 200)
        texts = page_texts(response.content)
        self.assertEqual(len(texts), 1)
        self.assertIn("EXAME-01", texts[0])
        self.assertIn("EXAME-03", texts[0])
        self.assertNotIn("EXAME-02", texts[0])

    def test_draft_only_batch_is_404(self):
        """R5: a batch resolving to drafts only mirrors single-download 404."""
        batch_id, _ = self._create_batch(2, draft_indices={1, 2})
        response = self._download(batch_id)
        self.assertEqual(response.status_code, 404)

    def test_unknown_batch_is_404(self):
        response = self._download(str(uuid.uuid4()))
        self.assertEqual(response.status_code, 404)

    def test_user_without_patient_access_is_denied(self):
        """R5: per-submission download permission is enforced."""
        batch_id, _ = self._create_batch(2)
        with patch(
            "apps.pdf_forms.permissions.can_access_patient", return_value=False
        ):
            response = self._download(batch_id)
        self.assertEqual(response.status_code, 403)

    def test_download_is_attachment_pdf(self):
        batch_id, _ = self._create_batch(2)
        response = self._download(batch_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_vias_per_sheet_constant_is_three(self):
        self.assertEqual(VIAS_PER_SHEET, 3)
        self.assertEqual((CROP_TOP_CM, CROP_BASE_CM), (1.0, 10.0))


class ExamBatchFallbackTests(TestCase):
    """R6: unexpected template height falls back to 1-up without error."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = create_navigation_user(
            username="batch-fb-doctor",
            email="batch-fb-doctor@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
        )
        cls.patient = PatientFactory(created_by=cls.doctor, updated_by=cls.doctor)
        cls.tall_template = make_chequinho_template(
            cls.doctor, name="Chequinho alto", page_size=(A4[0], 1000.0)
        )

    def test_unexpected_height_falls_back_to_one_via_per_page(self):
        batch_id = str(uuid.uuid4())
        for n in (1, 2):
            PDFFormSubmission.objects.create(
                form_template=self.tall_template,
                patient=self.patient,
                created_by=self.doctor,
                updated_by=self.doctor,
                event_datetime=timezone.now(),
                description=f"Exame {n}",
                form_data=exam_form_data(n, batch_id),
            )
        self.client.force_login(self.doctor)
        url = reverse("pdf_forms:exam_batch_download", kwargs={"batch_id": batch_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        reader = PdfReader(BytesIO(response.content))
        self.assertEqual(len(reader.pages), 2)
        texts = [page.extract_text() or "" for page in reader.pages]
        self.assertIn("EXAME-01", texts[0])
        self.assertIn("EXAME-02", texts[1])
