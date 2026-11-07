"""Batch 3-up imposition for exam-request batches (chequinho) — S2.

Pipeline (design "fill → crop → stack", presentation only):

1. Each via is filled by :class:`PDFFormOverlay` exactly like the single
   print (same overlay, same size — R4).
2. Each filled A4 via is cropped to the fixed window
   (top 1.0 cm / base 10.0 cm, i.e. a 9.0 cm tall strip) with no scaling.
3. Up to three cropped vias are stacked top-to-bottom on a blank A4 sheet
   via ``pypdf.Transformation.translate`` (pure translation = 100% — R2).
   ``merge_transformed_page`` clips the source to its cropbox, so only the
   fixed window shows on the sheet.
4. A ReportLab overlay adds one dashed cut line at each boundary *between
   printed vias* (2 vias → 1 line, 1 via → none — R3).

Pagination is deterministic: exam N (1-based, creation order) sits at
``slot=(N-1)%3`` of ``sheet=(N-1)//3``.

Fallback (R6): if any filled via has an unexpected page size (the admin
replaced the template PDF with one of a different height) or is not a
single page, the whole batch falls back to 1 via per page instead of
erroring. A same-size template whose content merely moved is outside
what can be detected automatically; the fixed crop stays the contract.
"""

from io import BytesIO

from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

# Fixed crop window measured from the top edge of the A4 template page.
CROP_TOP_CM = 1.0
CROP_BASE_CM = 10.0
VIA_HEIGHT_CM = CROP_BASE_CM - CROP_TOP_CM

VIAS_PER_SHEET = 3

# A filled via must match A4 within this tolerance or the batch falls
# back to 1-up (R6). Points.
SIZE_TOLERANCE_PT = 1.0

CUT_LINE_MARGIN_CM = 1.0


def batch_slot(position):
    """Return ``(sheet_index, slot_index)`` for 1-based exam ``position``.

    Slot ``(N-1)%3`` of sheet ``(N-1)//3``: exam 4 opens sheet 2, exam 9
    closes sheet 3.
    """
    index = position - 1
    return (index // VIAS_PER_SHEET, index % VIAS_PER_SHEET)


def cut_line_ys(vias_on_sheet, page_height=A4[1]):
    """Return Y coordinates (PDF points, bottom origin) of cut lines.

    One dashed line at each boundary *between printed vias*: ``k`` vias
    yield ``k-1`` lines, ordered top to bottom. A lone via needs none.
    """
    top_margin = CROP_TOP_CM * cm
    slot_height = VIA_HEIGHT_CM * cm
    return [
        page_height - top_margin - index * slot_height
        for index in range(1, vias_on_sheet)
    ]


def compose_exam_batch(via_pdfs):
    """Compose filled single-print PDFs into a 3-up A4 batch PDF.

    Args:
        via_pdfs: list of PDF bytes, one filled A4 via per final
            submission, in composition order.

    Returns:
        bytes: the composed A4 PDF (``ceil(N/3)`` pages, or N pages on
        fallback).

    Raises:
        ValueError: when ``via_pdfs`` is empty.
    """
    if not via_pdfs:
        raise ValueError("Cannot compose a batch with no vias")

    readers = [PdfReader(BytesIO(via_pdf)) for via_pdf in via_pdfs]
    page_width, page_height = A4

    if _needs_one_up_fallback(readers, page_width, page_height):
        return _compose_one_up(readers)

    writer = PdfWriter()
    slot_height = VIA_HEIGHT_CM * cm
    for chunk_start in range(0, len(readers), VIAS_PER_SHEET):
        chunk = readers[chunk_start : chunk_start + VIAS_PER_SHEET]
        sheet = writer.add_blank_page(width=page_width, height=page_height)
        for slot, reader in enumerate(chunk):
            via_page = reader.pages[0]
            via_page.cropbox = RectangleObject(
                [
                    0,
                    page_height - CROP_BASE_CM * cm,
                    page_width,
                    page_height - CROP_TOP_CM * cm,
                ]
            )
            sheet.merge_transformed_page(
                via_page, Transformation().translate(0, -slot * slot_height)
            )
        _draw_cut_lines(writer, sheet, len(chunk), page_width, page_height)

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output.getvalue()


def _needs_one_up_fallback(readers, page_width, page_height):
    """Detect vias that no longer fit the fixed crop window (R6)."""
    for reader in readers:
        if len(reader.pages) != 1:
            return True
        mediabox = reader.pages[0].mediabox
        if (
            abs(float(mediabox.width) - page_width) > SIZE_TOLERANCE_PT
            or abs(float(mediabox.height) - page_height) > SIZE_TOLERANCE_PT
        ):
            return True
    return False


def _compose_one_up(readers):
    """Fallback: one via per page, appended unchanged (R6)."""
    writer = PdfWriter()
    for reader in readers:
        for page in reader.pages:
            writer.add_page(page)
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output.getvalue()


def _draw_cut_lines(writer, sheet, vias_on_sheet, page_width, page_height):
    """Merge a ReportLab dashed-line overlay between printed vias (R3)."""
    ys = cut_line_ys(vias_on_sheet, page_height)
    if not ys:
        return
    overlay = BytesIO()
    overlay_canvas = canvas.Canvas(overlay, pagesize=(page_width, page_height))
    overlay_canvas.setStrokeColorRGB(0.35, 0.35, 0.35)
    overlay_canvas.setLineWidth(0.5)
    overlay_canvas.setDash(3, 3)
    margin = CUT_LINE_MARGIN_CM * cm
    for y in ys:
        overlay_canvas.line(margin, y, page_width - margin, y)
    overlay_canvas.showPage()
    overlay_canvas.save()
    overlay.seek(0)
    sheet.merge_page(PdfReader(overlay).pages[0])
