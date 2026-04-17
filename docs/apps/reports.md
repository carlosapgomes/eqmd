# Reports (apps/reports)

**Generic report templates and patient reports with Markdown and PDF output.**

## Overview

The reports app provides a low-volume, generic document workflow
(referrals, reimbursement letters, internal communications) without creating a
dedicated app per document type. It extends the Event model and integrates with
the patient timeline.

## Core Behavior

- Reports are Event subtypes (Event.REPORT_EVENT).
- Reports are editable/deletable within the standard 24h window by the creator.
- Reports use Markdown content (EasyMDE on creation/edit).
- PDF output uses hospital letterhead, page breaks, and signature section.
- No attachments.
- Both web and PDF use the shared markdown pipeline (`easymd_v1`).

## Template Visibility and Permissions

- Templates can be created/updated by admin/staff, doctors, and residents.
- Templates can be **public** (visible system-wide) or **private** (creator only).
- Report creation can use any visible template.

## Placeholders

Templates support a strict placeholder allowlist. Any other placeholder causes validation errors.

### Allowed placeholders

- `{{patient_name}}` (required)
- `{{patient_record_number}}`
- `{{patient_birth_date}}`
- `{{patient_age}}`
- `{{patient_gender}}`
- `{{patient_fiscal_number}}`
- `{{patient_healthcard_number}}`
- `{{patient_ward}}`
- `{{patient_bed}}`
- `{{patient_status}}`
- `{{doctor_name}}`
- `{{doctor_profession}}`
- `{{doctor_registration_number}}`
- `{{doctor_specialty}}`
- `{{document_date}}`
- `{{document_datetime}}`
- `{{hospital_name}}`
- `{{hospital_city}}`
- `{{hospital_state}}`
- `{{hospital_address}}`
- `{{page_break}}` (optional, inserts a PDF page break)

### Format rules

- Placeholders must be exactly `{{placeholder}}` (no spaces).
- Templates that omit required placeholders are rejected.
- Templates that include unknown placeholders are rejected.

### Page breaks

Use `{{page_break}}` to split the PDF into multiple pages.
The renderer replaces it with a page break token used by the PDF
generator.

## Example Template

```text
RELATORIO

Paciente: {{patient_name}}
Prontuario: {{patient_record_number}}

Conteudo inicial...

{{page_break}}

Nova pagina...
```

## Report Creation Flow

1. User selects a template (optional).
2. The system renders required placeholders server-side.
3. User edits the Markdown content in EasyMDE.
4. Report is saved as an Event and appears in the patient timeline.

## PDF Output

- Uses the custom report PDF generator (letterhead + signature section).
- Respects page breaks inserted with `{{page_break}}`.

## Markdown Rendering (Shared Pipeline)

Reports use the unified markdown pipeline (`easymd_v1` dialect) for both
web detail and PDF output, ensuring semantic parity:

- **Web detail**: the `markdown_filter` in `reports_extras.py` delegates to
  `render_markdown_html` from the shared pipeline. Supports headings, inline
  formatting, nested lists, blockquotes, code blocks, tables, and task lists.
- **PDF output**: `ReportPDFGenerator` uses `parse_markdown` +
  `render_markdown_pdf_flowables` from the shared pipeline. The former
  `MarkdownToPDFParser` import has been removed.

Both renderers produce semantically equivalent output for the same markdown
input, verified by parity tests in `test_markdown_parity.py`.

See `docs/workflows/markdown-rendering-pipeline.md` for the full pipeline
architecture and integration guide.

## Related Code

- Placeholder rendering: `apps/reports/services/renderer.py`
- Context builder: `apps/reports/services/context_builder.py`
- PDF generator: `apps/reports/services/pdf_generator.py`
