# Design: Ward-map XLSX export

## Context

The map resolves its result through `WardPatientMapView.get_context_data`:
request filters (`q`, `ward`, `show_empty_wards`), tag selection
(`tag_preferences.resolve_request_state`), requester-aware projection and
filtering of the cached ward rows, and page totals recomputed from the
surviving rows. The cached rows carry only patient `pk`, `name`, `bed` and
display strings; the export needs identity fields and the last published
evolution, which live in the database.

The dev cache is currently expired, so the map shows its updating alert and
an empty tree. Production refreshes the cache every five minutes. Cache
health is an operational prerequisite, not a defect to repair here; the export
simply refuses an empty result.

## D1. Parity by construction

`WardMapExportXlsxView(WardMapFilterActionsView)` overrides only `get()`,
calls the inherited `get_context_data()` once, and either refuses (empty
result) or builds the workbook from `context["ward_data"]`. The endpoint
never re-resolves preferences, never re-implements filtering and never reads
the cache directly. Same query string, same rows, same viewer projection as
the page. No new permission: login + `patients.view_patient` are inherited.

Refusal rule (single, owner-approved): when `context["total_patients"] == 0`
the endpoint answers 409 with a plain-text message and no attachment. A cold
cache produces an empty result and falls under the same rule; there is no
special `updating` criterion.

## D2. Workbook contract

One sheet per surviving ward, in the cache's ward order; a ward kept
visible by `show_empty_wards` still gets a sheet with only the header row.

- Sheet title: sanitized `Ward.abbreviation` (unique, ≤10 chars): strip
  Excel-forbidden characters (`: \ / ? * [ ]`), trim whitespace, cap at 31;
  an empty result falls back to the sanitized ward name; a collision gets a
  numeric suffix that fits inside the 31-character cap.
- One header row (bold, white on fill #366092, centered — the existing
  research-export style) with the five fixed columns in order: `Leito`,
  `Identificação`, `Médico/Interno`, `Evolução`, `Conduta`.
- `Conduta` is always empty.
- Fixed widths (Excel character units, module constants): `Leito` 12,
  `Identificação` 48, `Médico/Interno` 32, `Evolução` 72, `Conduta` 45.
- `Identificação` is one labeled multi-line cell (`wrap_text`, top aligned):
  Nome / Sexo (`get_gender_display`) / Idade / Registro / Admissão
  (`DD/MM/AAAA`) / `Internação: N dias`. Labels are always present; values
  are blank when missing; the Internação line is omitted when the patient
  has no admission date.
- `Evolução` holds the raw note content (`wrap_text`, top aligned),
  truncated to the 32,767-character Excel cell limit.
- Filename: `mapa_pacientes_YYYYMMDD_HHMMSS.xlsx` (ASCII, no accents) with
  `Content-Disposition: attachment`.

## D3. Enrichment queries (batched, at most two)

1. Identity: `Patient.objects.filter(pk__in=ids).values(...)` for gender,
   birthday, current record number and last admission date. Age and
   inpatient days are computed against an injected `today` date so tests are
   deterministic.
2. Evolution: one PostgreSQL `DISTINCT ON` query over `DailyNote` for the
   bounded patient set, ordered by `patient_id, -event_datetime,
-created_at, -pk` (the primary key is the final deterministic tie-break),
   `select_related("created_by")`. The default manager already
   excludes drafts (human and bot) and soft-deleted rows, which implements
   D1 exactly. Author cell: `created_by.get_full_name()` or `username`.

Row freshness: a patient soft-deleted during the cache TTL can appear in
the cached rows while being absent from the identity query (the default
manager excludes soft-deleted patients). The live server state is the
authority: such a row is dropped entirely — identity lines and evolution
included — because the system has already retracted that patient, and the
build never fails on the missing lookup. This covers absence from the live
default manager (soft or hard delete) only; an ordinary status change
inside the window (for example a discharge) keeps the row, because the
patient still exists and eligibility freshness remains the cache's own
contract. During the cache window the page may still render the stale row;
the workbook being fresher than the page is accepted and preferable to
exporting retracted data.

At most two enrichment queries run regardless of patient count (exactly
two in the representative nonempty test; an empty patient set needs none).

## D4. Button and disabled state

The full map template gains one action row between the updating alert and
the results card: right-aligned anchor, Bootstrap icon, no JavaScript.

- Enabled: href `{% url 'patients:patient_map_export' %}` plus the current
  query string (the `?` is omitted entirely when there are no parameters).
- Disabled (`total_patients == 0`): no `href`, Bootstrap `disabled` class,
  `aria-disabled="true"`, `tabindex="-1"` and
  `title="Nenhum paciente no resultado da busca"`. An anchor is never
  disabled by CSS alone.
- Never rendered in `ward_patient_map_tree_only.html`; never inside the
  filter `<form>` or the `data-patient-filter-panel`.

## D5. Response

`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`,
attachment filename per D2, workbook serialized through `BytesIO`. The
browser stays on `/patients/map`. No streaming (bounded result size).

## D6. Code placement

The view stays thin (`get()` + refusal + response); all workbook logic
lives in the typed service module; widths, columns and limits are named
constants. The 1948-line legacy `views.py` is not touched; new modules
follow the `views_ward_map_filters.py` seam pattern.
