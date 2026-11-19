"""Render the already-resolved ward map as an XLSX workbook.

The map owns filtering, permissions and cache reading (design D1); this module
only turns the surviving rows into sheets. Enrichment stays batched as design
D3 requires: one identity query and one ``DISTINCT ON`` evolution query for the
bounded patient set. Cached payload values are untyped JSON, so ``Any`` marks
row values only.

Every exported value is written as literal text with an explicit string data
type: a leading ``=`` in a note or a bed never becomes a formula, XML-illegal
characters (C0 controls plus the U+FFFE/U+FFFF noncharacters) are stripped
from cell values and sheet titles alike, and the 32,767-character Excel cell
limit is enforced (design D2).

Split plan if this module outgrows the 300-line target: the title helpers
(``_title_base`` … ``_suffixed_title``), the cell writers (``_write_header`` …
``_literal_text``) and the enrichment queries (``_cached_patient_ids`` …
``_note_author``) are already independent seams and can move to sibling
modules without changing this module's public functions.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from apps.dailynotes.models import DailyNote
from apps.patients.models import Patient

if TYPE_CHECKING:
    from apps.accounts.models import EqmdCustomUser

COLUMN_HEADERS: tuple[str, ...] = (
    "Leito",
    "Identificação",
    "Médico/Interno",
    "Evolução",
    "Conduta",
)
COLUMN_WIDTHS: tuple[int, ...] = (12, 48, 32, 72, 45)
HEADER_ROW = 1
FIRST_DATA_ROW = 2
CELL_TEXT_LIMIT = 32_767
SHEET_TITLE_MAX_LENGTH = 31
FALLBACK_SHEET_TITLE = "Ala"
FIRST_DUPLICATE_INDEX = 2
DATE_FORMAT = "%d/%m/%Y"
FILENAME_PREFIX = "mapa_pacientes_"
FILENAME_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
FILE_EXTENSION = ".xlsx"

_IDENTITY_FIELDS = (
    "pk",
    "gender",
    "birthday",
    "current_record_number",
    "last_admission_date",
)
_FORBIDDEN_TITLE_CHARACTERS = re.compile(r"[:\\/?*\[\]]")
# XML 1.0 forbids the C0 controls that openpyxl rejects plus the U+FFFE and
# U+FFFF noncharacters, which produce an unreadable part on reopen.
_XML_ILLEGAL_CHARACTERS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
_LINE_BREAKS = re.compile(r"[\r\n]+")
_TRAILING_TITLE_SUFFIX = re.compile(r"^(?P<root>.+?) \(\d+\)$")
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
_HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")
_BODY_ALIGNMENT = Alignment(vertical="top", wrap_text=True)


def build_ward_map_workbook(
    ward_data: Sequence[Mapping[str, Any]], *, today: date
) -> Workbook:
    """Return one sheet per surviving ward, enriched in two batched queries."""
    patient_ids = _cached_patient_ids(ward_data)
    identity = _identity_by_patient(patient_ids)
    evolution = _latest_evolution_by_patient(patient_ids)
    workbook = Workbook()
    taken_titles: set[str] = set()
    for position, ward_info in enumerate(ward_data):
        sheet = _sheet_for_ward(
            workbook, ward_info, position=position, taken_titles=taken_titles
        )
        _write_ward_sheet(
            sheet,
            ward_info,
            identity=identity,
            evolution=evolution,
            today=today,
        )
    return workbook


def export_filename(*, now: datetime) -> str:
    """Return the ASCII attachment filename for one export moment (design D5)."""
    timestamp = now.strftime(FILENAME_TIMESTAMP_FORMAT)
    return f"{FILENAME_PREFIX}{timestamp}{FILE_EXTENSION}"


def _cached_patient_ids(ward_data: Sequence[Mapping[str, Any]]) -> list[UUID]:
    """Return the distinct patient identifiers the cached rows reference."""
    identifiers: dict[str, UUID] = {}
    for ward_info in ward_data:
        for patient_info in ward_info.get("patients", []):
            raw_id = str(patient_info["patient"]["pk"]).strip()
            if raw_id and raw_id not in identifiers:
                identifiers[raw_id] = UUID(raw_id)
    return list(identifiers.values())


def _identity_by_patient(patient_ids: Sequence[UUID]) -> dict[UUID, dict[str, Any]]:
    """Read the identity fields of the bounded patient set in one query."""
    if not patient_ids:
        return {}
    rows = Patient.objects.filter(pk__in=patient_ids).values(*_IDENTITY_FIELDS)
    return {row["pk"]: row for row in rows}


def _latest_evolution_by_patient(
    patient_ids: Sequence[UUID],
) -> dict[UUID, tuple[str, str]]:
    """Read each patient's latest published note and author in one query.

    ``DailyNote.objects`` is the default manager, so drafts (human and bot) and
    soft-deleted notes are excluded for free. The primary key is the final
    tie-break, so equal timestamps stay deterministic (design D3).
    """
    if not patient_ids:
        return {}
    notes = (
        DailyNote.objects.filter(patient_id__in=patient_ids)
        .select_related("created_by")
        .order_by("patient_id", "-event_datetime", "-created_at", "-pk")
        .distinct("patient_id")
    )
    return {
        note.patient_id: (_note_author(note.created_by), note.content or "")
        for note in notes
    }


def _note_author(author: EqmdCustomUser) -> str:
    """Return the author's full name, falling back to the login username."""
    return author.get_full_name() or author.username


def _sheet_for_ward(
    workbook: Workbook,
    ward_info: Mapping[str, Any],
    *,
    position: int,
    taken_titles: set[str],
) -> Worksheet:
    """Create the ward's sheet, reusing the default one for the first ward."""
    title = _unique_sheet_title(_title_base(ward_info.get("ward") or {}), taken_titles)
    if position == 0:
        sheet = workbook.active
        sheet.title = title
        return sheet
    return workbook.create_sheet(title=title)


def _title_base(ward: Mapping[str, Any]) -> str:
    """Apply the abbreviation, then name, then ``Ala`` fallback chain."""
    return (
        _sanitized_title(ward.get("abbreviation"))
        or _sanitized_title(ward.get("name"))
        or FALLBACK_SHEET_TITLE
    )


def _sanitized_title(value: Any) -> str:
    """Strip XML-illegal and Excel-forbidden characters, then cap the title."""
    text = _XML_ILLEGAL_CHARACTERS.sub("", str(value or ""))
    text = _FORBIDDEN_TITLE_CHARACTERS.sub("", text).strip()
    return text[:SHEET_TITLE_MAX_LENGTH]


def _unique_sheet_title(base: str, taken_titles: set[str]) -> str:
    """Deduplicate titles case-insensitively, also against suffixed ones."""
    if base.casefold() not in taken_titles:
        taken_titles.add(base.casefold())
        return base
    root = _title_root(base)
    index = FIRST_DUPLICATE_INDEX
    candidate = _suffixed_title(root, index)
    while candidate.casefold() in taken_titles:
        index += 1
        candidate = _suffixed_title(root, index)
    taken_titles.add(candidate.casefold())
    return candidate


def _title_root(base: str) -> str:
    """Return the base title without an already generated numeric suffix."""
    match = _TRAILING_TITLE_SUFFIX.match(base)
    return match.group("root") if match else base


def _suffixed_title(root: str, index: int) -> str:
    """Return ``root`` with a numeric suffix that still fits the cap."""
    suffix = f" ({index})"
    return f"{root[: SHEET_TITLE_MAX_LENGTH - len(suffix)]}{suffix}"


def _write_ward_sheet(
    sheet: Worksheet,
    ward_info: Mapping[str, Any],
    *,
    identity: Mapping[UUID, dict[str, Any]],
    evolution: Mapping[UUID, tuple[str, str]],
    today: date,
) -> None:
    """Write the header row and one row per cached patient still live."""
    _write_header(sheet)
    row_number = FIRST_DATA_ROW
    for patient_info in ward_info.get("patients", []):
        patient_id = UUID(str(patient_info["patient"]["pk"]))
        identity_row = identity.get(patient_id)
        if identity_row is None:
            continue
        _write_patient_row(
            sheet,
            row_number,
            patient_info,
            identity_row,
            evolution.get(patient_id),
            today=today,
        )
        row_number += 1


def _write_header(sheet: Worksheet) -> None:
    """Write the styled header row and the fixed column widths."""
    for column, header in enumerate(COLUMN_HEADERS, start=1):
        cell = sheet.cell(row=HEADER_ROW, column=column, value=header)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGNMENT
    for column, width in enumerate(COLUMN_WIDTHS, start=1):
        sheet.column_dimensions[get_column_letter(column)].width = width


def _write_patient_row(
    sheet: Worksheet,
    row_number: int,
    patient_info: Mapping[str, Any],
    identity_row: Mapping[str, Any],
    evolution: tuple[str, str] | None,
    *,
    today: date,
) -> None:
    """Write the five cells of one patient row."""
    author, content = evolution or ("", "")
    values = (
        patient_info.get("bed") or "",
        _identification_text(patient_info, identity_row, today=today),
        author,
        content,
        "",
    )
    for column, value in enumerate(values, start=1):
        _write_text_cell(sheet, row_number, column, value)


def _identification_text(
    patient_info: Mapping[str, Any], identity_row: Mapping[str, Any], *, today: date
) -> str:
    """Build the labeled multi-line identification cell (design D2)."""
    name = str(patient_info["patient"].get("name") or "")
    admission = identity_row["last_admission_date"]
    lines = [
        _labeled_line("Nome", name),
        _labeled_line("Sexo", _gender_label(identity_row["gender"])),
        _labeled_line("Idade", _age_text(identity_row["birthday"], today)),
        _labeled_line("Registro", str(identity_row["current_record_number"] or "")),
        _labeled_line("Admissão", _date_text(admission)),
    ]
    if admission is not None:
        days = _quantity_text((today - admission).days, "dia", "dias")
        lines.append(f"Internação: {days}")
    return "\n".join(lines)


def _labeled_line(label: str, value: str) -> str:
    """Keep the label even when the value is missing; one line per label."""
    return f"{label}: {_single_line(value)}".rstrip()


def _single_line(value: str) -> str:
    """Collapse CR/LF runs so a cached value cannot forge an extra line."""
    return _LINE_BREAKS.sub(" ", value).strip()


def _gender_label(code: Any) -> str:
    """Return the sex label, the same source ``get_gender_display`` reads."""
    try:
        return Patient.GenderChoices(code).label
    except ValueError:
        return ""


def _age_text(birthday: date | None, today: date) -> str:
    """Return the completed years lived at ``today``, blank without a birthday."""
    if birthday is None:
        return ""
    years = (
        today.year
        - birthday.year
        - ((today.month, today.day) < (birthday.month, birthday.day))
    )
    return _quantity_text(years, "ano", "anos")


def _quantity_text(value: int, singular: str, plural: str) -> str:
    """Return a counted noun with the matching number word."""
    return f"{value} {singular if value == 1 else plural}"


def _date_text(value: date | None) -> str:
    """Return the ``DD/MM/AAAA`` form or a blank value when absent."""
    return value.strftime(DATE_FORMAT) if value else ""


def _write_text_cell(
    sheet: Worksheet, row_number: int, column: int, value: Any
) -> None:
    """Write one literal-text cell: never a formula, never illegal XML."""
    cell = sheet.cell(row=row_number, column=column)
    cell.value = _literal_text(value)
    cell.data_type = "s"
    cell.alignment = _BODY_ALIGNMENT


def _literal_text(value: Any) -> str:
    """Return one cell string without XML-illegal characters, capped."""
    text = "" if value is None else str(value)
    return _XML_ILLEGAL_CHARACTERS.sub("", text)[:CELL_TEXT_LIMIT]
