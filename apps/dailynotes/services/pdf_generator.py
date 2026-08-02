"""
PDF generator for daily notes.

Produces a compact clinical-print PDF with a repeated patient-context
header on every page, compact note metadata, markdown-rendered content,
and a signature section reserved for the end of the document.
"""

import os
from html import escape

from django.contrib.staticfiles import finders
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.colors import black, grey
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from apps.core.services.markdown_pipeline import parse_markdown
from apps.core.services.markdown_pipeline.pdf_renderer import (
    render_markdown_pdf_flowables,
)
from apps.pdfgenerator.services.pdf_generator import (
    HospitalLetterheadGenerator,
    NumberedCanvas,
)

# ---------------------------------------------------------------------------
# Daily Note header geometry (cm) — single source of truth
# ---------------------------------------------------------------------------

# These values feed both the canvas box and the generator's top-frame
# reservation so the header geometry cannot diverge between the two.
_HEADER_TOP_OFFSET_CM = 1.0  # page top → box top border
_HEADER_BOX_HEIGHT_MIN_CM = 2.0  # minimum boxed header height
_HEADER_FRAME_GAP_CM = 0.1  # box bottom → content frame top gap
# Shared frame math: frame top from page top = margins.top + header_space - 1cm
_HEADER_FRAME_OFFSET_CM = 1.0

# Context typography (points) — single source for wrap/fit math
_CONTEXT_FONT_NAME = "Times-Roman"
_CONTEXT_FONT_MAX = 7.5
_CONTEXT_FONT_MIN = 5.5
_CONTEXT_LEADING_RATIO = 1.2  # line gap / font size minimum for legibility
_CONTEXT_ASCENT_RATIO = 0.75  # conservative ascender bound (Times-Roman ~0.68)
_CONTEXT_DESCENT_RATIO = 0.25  # conservative descender bound (Times-Roman ~0.22)

# Box geometry (points) — single source for wrap/fit math
_BOX_LEFT_PT = 2 * cm
_BOX_WIDTH_PT = A4[0] - 4 * cm  # page width minus both margins
_BOX_PAD_PT = 0.25 * cm
_CONTEXT_MAX_WIDTH_PT = _BOX_WIDTH_PT / 2 - 2 * _BOX_PAD_PT


# ---------------------------------------------------------------------------
# Pure header context + wrap/fit helpers (shared by canvas and generator)
# ---------------------------------------------------------------------------


def _name_age_token(pd: dict) -> str:
    """Patient name followed by the age at the event date when available."""
    age = pd.get("age_at_event")
    if age is None:
        return pd["name"]
    return f"{pd['name']} - {age} anos"


def _admission_token(pd: dict) -> str:
    """Active-admission date token, or the exact placeholder."""
    admission = pd.get("admission_datetime")
    if not admission:
        return "Adm.: —"
    return f"Adm.: {admission.strftime('%d/%m/%y')}"


def _build_context_lines(pd: dict, specialty_name: str) -> list[str]:
    """Assemble the compact context lines (single formatting source)."""
    lines = []
    if pd.get("name"):
        lines.append(f"Paciente: {_name_age_token(pd)}")
    if pd.get("record_number"):
        lines.append(f"Prontuário: {pd['record_number']}")
    ward = pd.get("ward", "")
    bed = pd.get("bed", "")
    if ward or bed:
        parts = [
            f"Setor: {ward}" if ward else "Setor: —",
            f"Leito: {bed}" if bed else "Leito: —",
        ]
        lines.append(" | ".join(parts))
    if specialty_name:
        lines.append(specialty_name)
    lines.append(_admission_token(pd))
    return lines


def _chunk_oversized_token(
    token: str, max_width: float, font_name: str, font_size: float
) -> list[str]:
    """Break a single unbreakable token into fragments that fit max_width.

    Every character is preserved; a fragment may exceed the width only in the
    pathological case where a single glyph is wider than the column.
    """
    chunks: list[str] = []
    current = ""
    for char in token:
        candidate = current + char
        if current and stringWidth(candidate, font_name, font_size) > max_width:
            chunks.append(current)
            current = char
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _wrap_line_to_width(
    line: str, max_width: float, font_name: str, font_size: float
) -> list[str]:
    """Split one line into segments that fit within max_width."""
    if stringWidth(line, font_name, font_size) <= max_width:
        return [line]
    segments: list[str] = []
    current = ""
    for word in line.split():
        if stringWidth(word, font_name, font_size) > max_width:
            if current:
                segments.append(current)
                current = ""
            segments.extend(
                _chunk_oversized_token(word, max_width, font_name, font_size)
            )
            continue
        candidate = f"{current} {word}".strip()
        if stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            if current:
                segments.append(current)
            current = word
    if current:
        segments.append(current)
    return segments


def _wrap_lines_to_width(
    lines: list[str], max_width: float, font_name: str, font_size: float
) -> list[str]:
    """Word-wrap lines that exceed the column width."""
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(_wrap_line_to_width(line, max_width, font_name, font_size))
    return wrapped


def _fit_context_block(
    lines: list[str], max_width: float, available: float
) -> tuple[float, list[str], float]:
    """Pick font size and line gap so the block fits with legible leading.

    Leading never drops below ``_CONTEXT_LEADING_RATIO`` times the font size,
    so glyphs cannot overlap.  Returns ``(font_size, wrapped_lines, line_gap)``.
    """
    font_size = _CONTEXT_FONT_MAX
    wrapped = _wrap_lines_to_width(lines, max_width, _CONTEXT_FONT_NAME, font_size)
    while (
        font_size > _CONTEXT_FONT_MIN
        and len(wrapped) * font_size * _CONTEXT_LEADING_RATIO > available
    ):
        font_size -= 0.5
        wrapped = _wrap_lines_to_width(lines, max_width, _CONTEXT_FONT_NAME, font_size)
    return font_size, wrapped, font_size * _CONTEXT_LEADING_RATIO


def _required_header_box_height_cm(pd: dict, specialty_name: str) -> float:
    """Minimum header box height that fits the wrapped context with legible
    leading at the minimum font size."""
    lines = _build_context_lines(pd, specialty_name)
    wrapped = _wrap_lines_to_width(
        lines, _CONTEXT_MAX_WIDTH_PT, _CONTEXT_FONT_NAME, _CONTEXT_FONT_MIN
    )
    needed_pt = (
        len(wrapped) * _CONTEXT_FONT_MIN * _CONTEXT_LEADING_RATIO + 2 * _BOX_PAD_PT
    )
    return max(_HEADER_BOX_HEIGHT_MIN_CM, needed_pt / cm)


# ---------------------------------------------------------------------------
# Daily Note – specific canvas
# ---------------------------------------------------------------------------


class DailyNoteCanvas(NumberedCanvas):
    """Compact canvas for Daily Note PDFs.

    Draws a boxed two-column repeated header on every page:
    left column  – hospital logo + hospital name
    right column – patient context (name, record, ward/sector, bed, specialty)

    Page numbering stays in the top-right area.  Title is placed below the
    boxed header.  Skips the intermediate-page mini-signature used by the
    generic ``NumberedCanvas``.
    """

    # Box geometry constants
    _BOX_LEFT = _BOX_LEFT_PT
    _BOX_TOP_Y = A4[1] - _HEADER_TOP_OFFSET_CM * cm
    _BOX_WIDTH = _BOX_WIDTH_PT
    _BOX_PAD = _BOX_PAD_PT
    _BOX_LINE_WIDTH = 0.6

    def __init__(self, *args, **kwargs):
        self.specialty_name = kwargs.pop("specialty_name", "")
        self.hospital_config = kwargs.pop("hospital_config", {})
        self.patient_data = kwargs.pop("patient_data", {})
        self.doctor_info = kwargs.pop("doctor_info", {})
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self.page_count = 0
        self._box_height = self._required_box_height()

    # ------------------------------------------------------------------
    # Page lifecycle
    # ------------------------------------------------------------------

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for page_num, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            current_page = page_num + 1

            self._draw_compact_header(current_page, num_pages)
            self._draw_page_number(current_page, num_pages)
            self._draw_light_footer()

            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    # ------------------------------------------------------------------
    # Logo helper
    # ------------------------------------------------------------------

    def _get_logo_path(self):
        """Resolve the hospital logo path from config."""
        logo_path = self.hospital_config.get("logo_path", "")
        if not logo_path:
            return None
        # Try as absolute / direct filesystem path first
        if os.path.isabs(logo_path) and os.path.exists(logo_path):
            return logo_path
        # Then try Django staticfiles finder
        relative = logo_path.replace("static/", "")
        static_path = finders.find(relative)
        if static_path and os.path.exists(static_path):
            return static_path
        # Last resort: try the path as-is
        if os.path.exists(logo_path):
            return logo_path
        return None

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_compact_header(self, page_num, num_pages):
        """Draw a boxed two-column header on every page."""
        bx = self._BOX_LEFT
        by = self._BOX_TOP_Y - self._box_height
        bw = self._BOX_WIDTH
        bh = self._box_height
        pad = self._BOX_PAD

        # Draw outer box border
        self.setStrokeColor(black)
        self.setLineWidth(self._BOX_LINE_WIDTH)
        self.rect(bx, by, bw, bh, stroke=1, fill=0)

        # Vertical divider at midpoint
        mid_x = bx + bw / 2
        self.setLineWidth(0.3)
        self.line(mid_x, by + pad * 0.3, mid_x, by + bh - pad * 0.3)

        # --- Left column ---
        self._draw_left_column(bx, by, bh)

        # --- Right column ---
        self._draw_right_column(mid_x, by, bh)

    def _draw_left_column(self, col_x, col_y, col_height):
        """Render hospital logo and name in the left column of the header."""
        pad = self._BOX_PAD
        text_x = col_x + pad
        hospital_name = self.hospital_config.get("name", "")

        logo_path = self._get_logo_path()
        if logo_path:
            text_x = self._try_draw_logo(col_x, col_y, col_height, logo_path, text_x)

        # Hospital name
        name_y = col_y + col_height / 2 - 0.15 * cm
        self.setFont("Times-Bold", 14)
        self.setFillColor(black)
        self.drawString(text_x, name_y, hospital_name)

    def _try_draw_logo(
        self,
        col_x: float,
        col_y: float,
        col_height: float,
        logo_path: str,
        fallback_x: float,
    ) -> float:
        """Draw the logo, or fall back to the default text position on image
        errors without hiding unrelated failures."""
        try:
            logo_h = col_height - 2 * self._BOX_PAD
            logo_w = logo_h  # square aspect
            logo_x = col_x + self._BOX_PAD
            logo_y = col_y + self._BOX_PAD
            self.drawImage(
                logo_path,
                logo_x,
                logo_y,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                anchor="sw",
            )
        except (OSError, ValueError, TypeError):
            return fallback_x
        return logo_x + logo_w + self._BOX_PAD

    def _draw_right_column(self, col_x, col_y, col_height):
        """Render patient context inside the right column, fitted to the box."""
        pd = self.patient_data or {}
        lines = self._build_context_lines(pd)
        if not lines:
            return
        max_width = self._BOX_WIDTH / 2 - 2 * self._BOX_PAD
        font_size, lines, line_gap = self._fit_context_lines(
            lines, max_width, col_height
        )
        start_y = self._context_start_y(
            col_y, col_height, len(lines), line_gap, font_size
        )

        text_x = col_x + self._BOX_PAD
        self.setFont(_CONTEXT_FONT_NAME, font_size)
        self.setFillColor(black)
        for i, line in enumerate(lines):
            self.drawString(text_x, start_y - i * line_gap, line)

    def _build_context_lines(self, pd: dict) -> list[str]:
        """Assemble the compact context lines (single formatting source)."""
        return _build_context_lines(pd, self.specialty_name)

    def _required_box_height(self) -> float:
        """Box height (points) that fits the wrapped context with legible
        leading, at least the configured minimum."""
        return (
            _required_header_box_height_cm(self.patient_data or {}, self.specialty_name)
            * cm
        )

    def _context_start_y(
        self,
        col_y: float,
        col_height: float,
        line_count: int,
        line_gap: float,
        font_size: float,
    ) -> float:
        """First baseline so glyphs (ascender/descender) stay inside the box."""
        block_height = (line_count - 1) * line_gap
        ascent = _CONTEXT_ASCENT_RATIO * font_size
        descent = _CONTEXT_DESCENT_RATIO * font_size
        centered = col_y + col_height / 2 + block_height / 2 - ascent
        top_limit = col_y + col_height - self._BOX_PAD - ascent
        bottom_limit = col_y + self._BOX_PAD + block_height + descent
        return min(max(centered, bottom_limit), top_limit)

    def _fit_context_lines(
        self, lines: list[str], max_width: float, col_height: float
    ) -> tuple[float, list[str], float]:
        """Pick font size and line gap so the block always fits the box."""
        available = col_height - 2 * self._BOX_PAD
        return _fit_context_block(lines, max_width, available)

    def _wrap_to_width(
        self, lines: list[str], max_width: float, font_size: float
    ) -> list[str]:
        """Word-wrap lines that exceed the column width."""
        return _wrap_lines_to_width(lines, max_width, _CONTEXT_FONT_NAME, font_size)

    def _wrap_line(self, line: str, max_width: float, font_size: float) -> list[str]:
        """Split one line into segments that fit within max_width."""
        return _wrap_line_to_width(line, max_width, _CONTEXT_FONT_NAME, font_size)

    def _draw_page_number(self, page_num, num_pages):
        """Draw page number in the reserved strip above the boxed header."""
        page_x = self._BOX_LEFT + self._BOX_WIDTH  # right edge of the box
        page_y = A4[1] - 0.45 * cm
        self.setFont("Times-Roman", 8)
        self.setFillColor(grey)
        self.drawRightString(
            page_x,
            page_y,
            f"Página {page_num}/{num_pages}",
        )

    def _draw_light_footer(self):
        footer_text = self.hospital_config.get("name", "")
        if self.hospital_config.get("address"):
            footer_text += f" - {self.hospital_config['address']}"

        self.setFont("Times-Roman", 7)
        self.setFillColor(grey)
        self.drawCentredString(A4[0] / 2, 1.0 * cm, footer_text)


# ---------------------------------------------------------------------------
# Compact layout constants
# ---------------------------------------------------------------------------

COMPACT_BODY_SIZE = 10
COMPACT_LEADING = 12
COMPACT_SECTION_SPACER = 4
COMPACT_PARA_SPACER = 2
COMPACT_LIST_INDENT = 12

# ---------------------------------------------------------------------------
# Helper: specialty lookup
# ---------------------------------------------------------------------------


def _get_user_specialty_name(user) -> str:
    """Return the user's current specialty display name, or empty string."""
    try:
        profile = user.profile
    except ObjectDoesNotExist:
        return ""
    display = profile.current_specialty_display
    return display if display else ""


# ---------------------------------------------------------------------------
# Daily Note PDF Generator
# ---------------------------------------------------------------------------


class DailyNotePDFGenerator(HospitalLetterheadGenerator):
    """Daily note PDF generator with compact clinical-print layout."""

    def __init__(self):
        super().__init__()
        self._add_compact_styles()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def generate_from_dailynote(self, dailynote):
        """Generate a compact PDF buffer for the given daily note."""
        specialty = _get_user_specialty_name(dailynote.created_by)
        patient_data = self._build_header_patient_data(dailynote)
        content_elements = self._build_compact_metadata(dailynote)
        content_elements.extend(self._build_note_content(dailynote))

        return self.generate_pdf(
            content_elements=content_elements,
            document_title="EVOLUÇÃO DIÁRIA",
            patient_data=patient_data,
            doctor_info=self._doctor_info(dailynote),
            specialty_name=specialty,
        )

    # ------------------------------------------------------------------
    # Header context (patient tokens for the repeated header)
    # ------------------------------------------------------------------

    def _build_header_patient_data(self, dailynote):
        """Build minimal patient data dict for the repeated header."""
        patient = dailynote.patient
        record_number = patient.get_current_record_number() or ""
        ward_display = patient.get_ward_display() if patient.ward else ""
        admission = patient.get_current_admission()
        return {
            "name": patient.name,
            "record_number": record_number,
            "ward": ward_display,
            "bed": patient.bed or "",
            "age_at_event": self._age_at_event(patient, dailynote),
            "admission_datetime": (admission.admission_datetime if admission else None),
        }

    @staticmethod
    def _age_at_event(patient, dailynote):
        """Full years of age on the note's local event date, not today."""
        birthday = patient.birthday
        if not birthday:
            return None
        reference = timezone.localdate(dailynote.event_datetime)
        years = reference.year - birthday.year
        if (reference.month, reference.day) < (birthday.month, birthday.day):
            years -= 1
        return years

    # ------------------------------------------------------------------
    # Compact metadata (replaces old patient-info + metadata blocks)
    # ------------------------------------------------------------------

    def _build_compact_metadata(self, dailynote):
        """Build compact metadata: event date/time and author only.

        Omits the generic description field.
        """
        author = dailynote.created_by.get_full_name() or dailynote.created_by.username
        fields = [
            ("Data/Hora do Evento", self._format_datetime(dailynote.event_datetime)),
            ("Autor", author),
        ]
        table = self._two_column_table(fields)
        return [Spacer(1, 6), table, Spacer(1, 10)]

    # ------------------------------------------------------------------
    # Note content section
    # ------------------------------------------------------------------

    def _build_note_content(self, dailynote):
        """Render markdown content using shared pipeline PDF renderer."""
        if not dailynote.content or not dailynote.content.strip():
            return []
        return self._build_compact_content(dailynote.content)

    # ------------------------------------------------------------------
    # Compact content renderer
    # ------------------------------------------------------------------

    def _add_compact_styles(self):
        """Add compact paragraph styles for clinical-print rendering."""
        self.styles.add(
            ParagraphStyle(
                name="CompactSectionBar",
                parent=self.styles["Normal"],
                fontSize=COMPACT_BODY_SIZE,
                fontName="Times-Bold",
                spaceBefore=COMPACT_PARA_SPACER,
                spaceAfter=COMPACT_PARA_SPACER,
                leading=COMPACT_LEADING,
                alignment=TA_LEFT,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CompactBody",
                parent=self.styles["Normal"],
                fontSize=COMPACT_BODY_SIZE,
                fontName="Times-Roman",
                spaceBefore=COMPACT_PARA_SPACER,
                spaceAfter=COMPACT_PARA_SPACER,
                leading=COMPACT_LEADING,
                alignment=TA_JUSTIFY,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CompactList",
                parent=self.styles["Normal"],
                fontSize=COMPACT_BODY_SIZE,
                fontName="Times-Roman",
                spaceBefore=COMPACT_PARA_SPACER,
                spaceAfter=COMPACT_PARA_SPACER,
                leading=COMPACT_LEADING,
                leftIndent=COMPACT_LIST_INDENT,
                alignment=TA_LEFT,
            )
        )

    def _build_compact_content(self, markdown_text):
        """Build compact content flowables using the shared markdown pipeline."""
        doc = parse_markdown(markdown_text)
        return render_markdown_pdf_flowables(doc, self.styles)

    # ------------------------------------------------------------------
    # Deprecated local regex helpers (retained for reference)
    # ------------------------------------------------------------------

    # The following methods are superseded by the shared pipeline:
    #   _extract_sections_from_markdown, _collect_list_items,
    #   _collect_paragraph_lines, _render_section_bar,
    #   _render_compact_paragraph, _render_compact_list,
    #   _inline_markdown_to_reportlab
    #
    # They have been replaced by apps.core.services.markdown_pipeline
    # .pdf_renderer.render_markdown_pdf_flowables

    # ------------------------------------------------------------------
    # Doctor info helper
    # ------------------------------------------------------------------

    def _doctor_info(self, dailynote):
        """Return doctor info dict for the signature section."""
        user = dailynote.created_by
        profession = (
            user.get_profession_type_display()
            if user.profession_type is not None
            else "Médico"
        )
        return {
            "name": user.get_full_name() or user.username,
            "profession": profession,
            "registration_number": user.professional_registration_number or "",
        }

    # ------------------------------------------------------------------
    # Override generate_pdf to use DailyNoteCanvas
    # ------------------------------------------------------------------

    def generate_pdf(
        self,
        content_elements,
        document_title="Document",
        patient_data=None,
        doctor_info=None,
        specialty_name="",
    ):
        """Generate PDF with the compact Daily Note canvas."""
        box_height_cm = _required_header_box_height_cm(
            patient_data or {}, specialty_name
        )
        return super().generate_pdf(
            content_elements=content_elements,
            document_title=document_title,
            patient_data=patient_data,
            doctor_info=doctor_info,
            canvasmaker=lambda filename, **kw: DailyNoteCanvas(
                filename,
                hospital_config=self.hospital_config,
                patient_data=patient_data,
                doctor_info=doctor_info,
                specialty_name=specialty_name,
                **kw,
            ),
            header_height_cm=self._header_reservation_cm(box_height_cm),
        )

    def _header_reservation_cm(self, box_height_cm: float) -> float:
        """Top-frame reservation keeping title/body below the header box."""
        return (
            _HEADER_TOP_OFFSET_CM
            + box_height_cm
            - self.margins["top"] / cm
            + _HEADER_FRAME_OFFSET_CM
            + _HEADER_FRAME_GAP_CM
        )

    # ------------------------------------------------------------------
    # Shared formatting helpers
    # ------------------------------------------------------------------

    def _two_column_table(self, fields):
        """Build a two-column key-value table from (label, value) pairs."""
        rows = []
        for idx in range(0, len(fields), 2):
            row = self._table_row(fields[idx : idx + 2])
            rows.append(row)
        available_width = (
            self.page_size[0] - self.margins["left"] - self.margins["right"]
        )
        table = Table(rows, colWidths=[available_width / 2] * 2)
        table.setStyle(self._table_style())
        return table

    def _table_row(self, pairs):
        """Create a single table row from up to two (label, value) pairs."""
        cells = []
        for label, value in pairs:
            text = f"<b>{escape(str(label))}:</b> {escape(str(value))}"
            cells.append(Paragraph(text, self.styles["PatientInfo"]))
        if len(cells) == 1:
            cells.append(Paragraph("", self.styles["PatientInfo"]))
        return cells

    @staticmethod
    def _table_style():
        return TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ]
        )

    @staticmethod
    def _format_date(value):
        if not value:
            return "—"
        return value.strftime("%d/%m/%Y")

    @staticmethod
    def _format_datetime(value):
        if not value:
            return "—"
        return value.strftime("%d/%m/%Y %H:%M")
