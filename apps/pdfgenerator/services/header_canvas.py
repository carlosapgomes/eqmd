"""Shared canvas and layout helpers for generic clinical PDF headers."""

import os
import re
from collections.abc import Sequence
from dataclasses import dataclass

from django.contrib.staticfiles.finders import find
from reportlab.lib.colors import black, grey
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

PATIENT_FONT_NAME = "Times-Bold"
PATIENT_FONT_SIZE = 18
PATIENT_FONT_MIN_SIZE = 12
PATIENT_FONT_STEP = 1
PATIENT_LINE_GAP = 14
HEADER_ORIGIN_X = 6 * cm
PATIENT_BASELINE_Y = A4[1] - 3 * cm
DEFAULT_SEPARATOR_Y = A4[1] - 3.2 * cm
DEFAULT_HEADER_HEIGHT_CM = 2.4
PATIENT_RIGHT_MARGIN = 2 * cm
PATIENT_AVAILABLE_WIDTH = A4[0] - PATIENT_RIGHT_MARGIN - HEADER_ORIGIN_X


@dataclass(frozen=True)
class PatientHeaderLayout:
    """Complete, deterministic geometry for one generic patient header."""

    lines: Sequence[str]
    font_size: float
    line_gap: float
    available_width: float
    origin_x: float
    baseline_y: float
    extra_height: float

    @property
    def block_height(self) -> float:
        """Return the baseline-to-baseline height of the rendered block."""
        if not self.lines:
            return 0.0
        return (len(self.lines) - 1) * self.line_gap + self.font_size

    @property
    def separator_y(self) -> float:
        """Return the separator position below the fitted patient block."""
        return DEFAULT_SEPARATOR_Y - self.extra_height

    @property
    def header_height_cm(self) -> float:
        """Return the matching default frame reservation in centimetres."""
        return DEFAULT_HEADER_HEIGHT_CM + self.extra_height / cm


def _chunk_oversized_token(token: str, max_width: float, font_size: float) -> list[str]:
    """Split an unbreakable token while preserving every character."""
    chunks: list[str] = []
    current = ""
    for character in token:
        candidate = current + character
        if current and stringWidth(candidate, PATIENT_FONT_NAME, font_size) > max_width:
            chunks.append(current)
            current = character
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _wrap_patient_line(line: str, font_size: float) -> list[str]:
    """Wrap a patient line while retaining whitespace on each line."""
    wrapped: list[str] = []
    current = ""
    pending_whitespace = ""
    for part in re.findall(r"\s+|\S+", line):
        if part.isspace():
            pending_whitespace = part
            continue
        word = part
        if not current:
            current = word
            pending_whitespace = ""
            continue
        candidate = current + pending_whitespace + word
        if stringWidth(candidate, PATIENT_FONT_NAME, font_size) <= (
            PATIENT_AVAILABLE_WIDTH
        ):
            current = candidate
            pending_whitespace = ""
            continue
        wrapped.append(current)
        pending_whitespace = ""
        if stringWidth(word, PATIENT_FONT_NAME, font_size) > PATIENT_AVAILABLE_WIDTH:
            wrapped.extend(
                _chunk_oversized_token(word, PATIENT_AVAILABLE_WIDTH, font_size)
            )
            current = ""
        else:
            current = word
    if current:
        wrapped.append(current)
    return wrapped


def fit_patient_header(name: str) -> PatientHeaderLayout:
    """Choose a shrink-then-wrap layout for the complete patient line."""
    if not name:
        return PatientHeaderLayout(
            (),
            PATIENT_FONT_SIZE,
            PATIENT_LINE_GAP,
            PATIENT_AVAILABLE_WIDTH,
            HEADER_ORIGIN_X,
            PATIENT_BASELINE_Y,
            0,
        )
    full_line = f"Paciente: {name}"
    font_size = PATIENT_FONT_SIZE
    while font_size >= PATIENT_FONT_MIN_SIZE:
        if (
            stringWidth(full_line, PATIENT_FONT_NAME, font_size)
            <= PATIENT_AVAILABLE_WIDTH
        ):
            lines = [full_line]
            break
        font_size -= PATIENT_FONT_STEP
    else:
        font_size = PATIENT_FONT_MIN_SIZE
        lines = _wrap_patient_line(full_line, font_size)
    extra_height = max(0, len(lines) - 1) * PATIENT_LINE_GAP
    return PatientHeaderLayout(
        tuple(lines),
        font_size,
        PATIENT_LINE_GAP,
        PATIENT_AVAILABLE_WIDTH,
        HEADER_ORIGIN_X,
        PATIENT_BASELINE_Y,
        extra_height,
    )


class NumberedCanvas(canvas.Canvas):
    """Custom canvas class for page numbering and generic headers/footers."""

    def __init__(self, *args, **kwargs):
        self.hospital_config = kwargs.pop("hospital_config", {})
        self.patient_data = kwargs.pop("patient_data", {})
        self.doctor_info = kwargs.pop("doctor_info", {})
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self.page_count = 0
        self.header_height_cm = self._patient_header_height_cm()

    def _patient_header_height_cm(self) -> float:
        """Return the frame reservation matching the rendered patient block."""
        name = self.patient_data.get("name") if self.patient_data else None
        if not name:
            return 2.0
        return fit_patient_header(name).header_height_cm

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        """Add page info to each page (page x of y)."""
        num_pages = len(self._saved_page_states)
        for page_num, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            current_page = page_num + 1
            is_last_page = current_page == num_pages
            self.draw_page_number(current_page, num_pages)
            self.draw_header()
            self.draw_footer()
            if not is_last_page and num_pages > 1:
                self.draw_page_signature()
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_num: int, num_pages: int) -> None:
        """Draw page number at bottom right."""
        self.setFont("Times-Roman", 9)
        self.setFillColor(grey)
        self.drawRightString(A4[0] - 2 * cm, 1 * cm, f"Página {page_num}/{num_pages}")

    def draw_header(self) -> None:
        """Draw hospital header on each page."""
        self._draw_logo()
        self._draw_hospital_name()
        layout = self._draw_patient_name()
        line_y = layout.separator_y if layout else A4[1] - 2.8 * cm
        self.setStrokeColor(black)
        self.setLineWidth(1)
        self.line(2 * cm, line_y, A4[0] - 2 * cm, line_y)

    def _draw_logo(self) -> None:
        """Draw the configured logo when it resolves to a local file."""
        logo_path = self._get_logo_path()
        if not logo_path or not os.path.exists(logo_path):
            return
        try:
            self.drawImage(
                logo_path,
                2 * cm,
                A4[1] - 2.5 * cm,
                width=2 * cm,
                height=1.5 * cm,
                preserveAspectRatio=True,
            )
        except (OSError, ValueError, TypeError):
            return

    def _draw_hospital_name(self) -> None:
        """Draw the hospital name at its existing position."""
        hospital_name = self.hospital_config.get("name", "Medical Center")
        self.setFont("Times-Bold", 20)
        self.setFillColor(black)
        self.drawString(6 * cm, A4[1] - 2.0 * cm, hospital_name)

    def _draw_patient_name(self) -> PatientHeaderLayout | None:
        """Draw the fitted patient block and return its geometry."""
        name = self.patient_data.get("name") if self.patient_data else None
        if not name:
            return None
        layout = fit_patient_header(name)
        self.setFont(PATIENT_FONT_NAME, layout.font_size)
        self.setFillColor(black)
        for index, line in enumerate(layout.lines):
            self.drawString(
                layout.origin_x,
                layout.baseline_y - index * layout.line_gap,
                line,
            )
        return layout

    def draw_footer(self) -> None:
        """Draw hospital footer on each page."""
        footer_text = self.hospital_config.get("name", "Medical Center")
        if self.hospital_config.get("address"):
            footer_text += f" - {self.hospital_config['address']}"
        self.setFont("Times-Roman", 9)
        self.setFillColor(grey)
        self.drawCentredString(A4[0] / 2, 2 * cm, footer_text)
        self.setStrokeColor(grey)
        self.setLineWidth(0.5)
        self.line(2 * cm, 2.5 * cm, A4[0] - 2 * cm, 2.5 * cm)

    def draw_page_signature(self) -> None:
        """Draw small signature area on non-final pages."""
        doctor_name = (
            self.doctor_info.get("name", "Médico Responsável")
            if self.doctor_info
            else "Médico Responsável"
        )
        registration_number = (
            self.doctor_info.get("registration_number", "") if self.doctor_info else ""
        )
        crm_field = registration_number if registration_number else "___________"
        x_pos = A4[0] - 7 * cm
        y_pos = 2.5 * cm
        self.setFont("Times-Roman", 8)
        self.setFillColor(black)
        right_x = x_pos + 4.8 * cm
        self.drawRightString(right_x, y_pos + 0.5 * cm, f"{doctor_name}")
        self.drawRightString(right_x, y_pos + 0.2 * cm, f"CRM: {crm_field}")
        self.setLineWidth(0.3)
        self.line(x_pos + 1.8 * cm, y_pos + 0.8 * cm, right_x, y_pos + 0.8 * cm)

    def _get_logo_path(self) -> str | None:
        """Get the path to the hospital logo."""
        if self.hospital_config.get("logo_path"):
            logo_path = self.hospital_config["logo_path"]
            static_path = find(logo_path.replace("static/", ""))
            if static_path and os.path.exists(static_path):
                return static_path
            if os.path.exists(logo_path):
                return logo_path
        return None
