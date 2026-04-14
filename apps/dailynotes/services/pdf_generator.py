"""
PDF generator for daily notes.

Produces a compact clinical-print PDF with a repeated patient-context
header on every page, compact note metadata, markdown-rendered content,
and a signature section reserved for the end of the document.
"""

import re
from html import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.lib.units import cm
from reportlab.lib.colors import black, grey
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas

from apps.pdfgenerator.services.pdf_generator import (
    HospitalLetterheadGenerator,
    NumberedCanvas,
)


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
    _BOX_LEFT = 2 * cm
    _BOX_TOP_Y = A4[1] - 1.2 * cm
    _BOX_WIDTH = A4[0] - 4 * cm  # page width minus both margins
    _BOX_HEIGHT = 1.6 * cm
    _BOX_PAD = 0.25 * cm
    _BOX_LINE_WIDTH = 0.6

    def __init__(self, *args, **kwargs):
        self.specialty_name = kwargs.pop("specialty_name", "")
        self.hospital_config = kwargs.pop("hospital_config", {})
        self.patient_data = kwargs.pop("patient_data", {})
        self.doctor_info = kwargs.pop("doctor_info", {})
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self.page_count = 0

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
        import os
        from django.contrib.staticfiles import finders
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
        by = self._BOX_TOP_Y - self._BOX_HEIGHT
        bw = self._BOX_WIDTH
        bh = self._BOX_HEIGHT
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
            try:
                logo_h = col_height - 2 * pad
                logo_w = logo_h  # square aspect
                logo_x = col_x + pad
                logo_y = col_y + pad
                self.drawImage(
                    logo_path,
                    logo_x, logo_y,
                    width=logo_w, height=logo_h,
                    preserveAspectRatio=True,
                    anchor="sw",
                )
                # Name to the right of the logo
                text_x = logo_x + logo_w + pad
            except Exception:
                pass  # Fall through: draw name at default position

        # Hospital name
        name_y = col_y + col_height / 2 - 0.15 * cm
        self.setFont("Times-Bold", 14)
        self.setFillColor(black)
        self.drawString(text_x, name_y, hospital_name)

    def _draw_right_column(self, col_x, col_y, col_height):
        """Render patient context vertically centred in the right column."""
        pd = self.patient_data or {}
        pad = self._BOX_PAD
        text_x = col_x + pad
        font_size = 7.5
        line_height = 0.35 * cm

        # Build context lines
        lines = []
        patient_name = pd.get("name", "")
        if patient_name:
            lines.append(f"Paciente: {patient_name}")
        record_number = pd.get("record_number", "")
        if record_number:
            lines.append(f"Prontuário: {record_number}")
        ward = pd.get("ward", "")
        bed = pd.get("bed", "")
        if ward or bed:
            parts = []
            parts.append(f"Setor: {ward}" if ward else "Setor: —")
            parts.append(f"Leito: {bed}" if bed else "Leito: —")
            lines.append(" | ".join(parts))
        if self.specialty_name:
            lines.append(self.specialty_name)

        # Vertically centre the block within the column
        block_height = len(lines) * line_height
        available = col_height - 2 * pad
        start_y = col_y + col_height / 2 + block_height / 2 - font_size * 0.35

        self.setFont("Times-Roman", font_size)
        self.setFillColor(black)
        for i, line in enumerate(lines):
            y = start_y - i * line_height
            self.drawString(text_x, y, line)

    def _draw_page_number(self, page_num, num_pages):
        pad = self._BOX_PAD
        # Position inside the top-right corner of the box, with padding
        page_x = self._BOX_LEFT + self._BOX_WIDTH - pad
        page_y = self._BOX_TOP_Y - pad - 0.1 * cm
        self.setFont("Times-Roman", 8)
        self.setFillColor(grey)
        self.drawRightString(
            page_x, page_y,
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
    except Exception:
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
        return {
            "name": patient.name,
            "record_number": record_number,
            "ward": ward_display,
            "bed": patient.bed or "",
        }

    # ------------------------------------------------------------------
    # Compact metadata (replaces old patient-info + metadata blocks)
    # ------------------------------------------------------------------

    def _build_compact_metadata(self, dailynote):
        """Build compact metadata: event date/time and author only.

        Omits the generic description field.
        """
        author = (
            dailynote.created_by.get_full_name()
            or dailynote.created_by.username
        )
        fields = [
            ("Data/Hora do Evento",
             self._format_datetime(dailynote.event_datetime)),
            ("Autor", author),
        ]
        table = self._two_column_table(fields)
        return [Spacer(1, 6), table, Spacer(1, 10)]

    # ------------------------------------------------------------------
    # Note content section
    # ------------------------------------------------------------------

    def _build_note_content(self, dailynote):
        """Render markdown content using compact clinical-print renderer."""
        if not dailynote.content or not dailynote.content.strip():
            return []
        return self._build_compact_content(dailynote.content)

    # ------------------------------------------------------------------
    # Compact content renderer
    # ------------------------------------------------------------------

    def _add_compact_styles(self):
        """Add compact paragraph styles for clinical-print rendering."""
        self.styles.add(ParagraphStyle(
            name="CompactSectionBar",
            parent=self.styles["Normal"],
            fontSize=COMPACT_BODY_SIZE,
            fontName="Times-Bold",
            spaceBefore=COMPACT_PARA_SPACER,
            spaceAfter=COMPACT_PARA_SPACER,
            leading=COMPACT_LEADING,
            alignment=TA_LEFT,
        ))
        self.styles.add(ParagraphStyle(
            name="CompactBody",
            parent=self.styles["Normal"],
            fontSize=COMPACT_BODY_SIZE,
            fontName="Times-Roman",
            spaceBefore=COMPACT_PARA_SPACER,
            spaceAfter=COMPACT_PARA_SPACER,
            leading=COMPACT_LEADING,
            alignment=TA_JUSTIFY,
        ))
        self.styles.add(ParagraphStyle(
            name="CompactList",
            parent=self.styles["Normal"],
            fontSize=COMPACT_BODY_SIZE,
            fontName="Times-Roman",
            spaceBefore=COMPACT_PARA_SPACER,
            spaceAfter=COMPACT_PARA_SPACER,
            leading=COMPACT_LEADING,
            leftIndent=COMPACT_LIST_INDENT,
            alignment=TA_LEFT,
        ))

    def _build_compact_content(self, markdown_text):
        """Build compact content flowables from markdown."""
        blocks = self._extract_sections_from_markdown(markdown_text)
        flowables = []
        for block in blocks:
            handler = {
                "heading": lambda b: self._render_section_bar(b["text"]),
                "paragraph": lambda b: self._render_compact_paragraph(
                    b["text"]
                ),
                "list": lambda b: self._render_compact_list(
                    b["items"], b["ordered"]
                ),
            }.get(block["type"])
            if handler:
                flowables.extend(handler(block))
        return flowables

    def _extract_sections_from_markdown(self, markdown_text):
        """Parse markdown into compact semantic blocks."""
        blocks = []
        lines = markdown_text.split("\n")
        idx = 0
        while idx < len(lines):
            stripped = lines[idx].strip()
            if not stripped:
                idx += 1
                continue

            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            if heading_match:
                blocks.append({
                    "type": "heading",
                    "level": len(heading_match.group(1)),
                    "text": heading_match.group(2).strip(),
                })
                idx += 1
                continue

            items, idx, ordered = self._collect_list_items(lines, idx)
            if items is not None:
                blocks.append({
                    "type": "list", "items": items,
                    "ordered": ordered,
                })
                continue

            para_lines, idx = self._collect_paragraph_lines(lines, idx)
            if para_lines:
                blocks.append({
                    "type": "paragraph",
                    "text": " ".join(para_lines),
                })
        return blocks

    def _collect_list_items(self, lines, start):
        """Collect consecutive list items starting at *start*."""
        stripped = lines[start].strip()
        ul_match = re.match(r'^[-*]\s+(.+)$', stripped)
        ol_match = re.match(r'^\d+\.\s+(.+)$', stripped)
        if not ul_match and not ol_match:
            return None, start, False

        ordered = bool(ol_match)
        pattern = r'^\d+\.\s+(.+)$' if ordered else r'^[-*]\s+(.+)$'
        items = []
        idx = start
        while idx < len(lines):
            m = re.match(pattern, lines[idx].strip())
            if not m:
                break
            items.append(m.group(1).strip())
            idx += 1
        return items, idx, ordered

    def _collect_paragraph_lines(self, lines, start):
        """Collect consecutive non-special lines as a paragraph."""
        para_lines = []
        idx = start
        while idx < len(lines):
            s = lines[idx].strip()
            if not s:
                break
            if re.match(r'^#{1,6}\s+', s):
                break
            if re.match(r'^[-*]\s+', s):
                break
            if re.match(r'^\d+\.\s+', s):
                break
            para_lines.append(s)
            idx += 1
        return para_lines, idx

    def _render_section_bar(self, title):
        """Render a compact left-aligned section heading bar."""
        text = self._inline_markdown_to_reportlab(title)
        para = Paragraph(f"<b>{text}</b>",
                         self.styles["CompactSectionBar"])
        return [Spacer(1, COMPACT_SECTION_SPACER), para,
                Spacer(1, COMPACT_PARA_SPACER)]

    def _render_compact_paragraph(self, text):
        """Render a paragraph with tight leading for clinical printing."""
        formatted = self._inline_markdown_to_reportlab(text)
        para = Paragraph(formatted, self.styles["CompactBody"])
        return [para]

    def _render_compact_list(self, items, ordered=False):
        """Render a list with compact bullets and minimal spacing."""
        flowables = [Spacer(1, COMPACT_PARA_SPACER)]
        for i, item in enumerate(items, 1):
            bullet = f"{i}. " if ordered else "\u2022 "
            formatted = self._inline_markdown_to_reportlab(item)
            para = Paragraph(f"{bullet}{formatted}",
                             self.styles["CompactList"])
            flowables.append(para)
        flowables.append(Spacer(1, COMPACT_PARA_SPACER))
        return flowables

    @staticmethod
    def _inline_markdown_to_reportlab(text):
        """Convert inline markdown formatting to ReportLab markup."""
        text = escape(text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        return text

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
            "registration_number":
                user.professional_registration_number or "",
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
            header_height_cm=1.8,
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
            self.page_size[0]
            - self.margins["left"]
            - self.margins["right"]
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
