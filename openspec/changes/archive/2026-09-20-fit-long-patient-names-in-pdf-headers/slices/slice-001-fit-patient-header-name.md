# Slice 001 - Hybrid patient-name fitting and safe PDF geometry

## Objective

Deliver the complete shared-header fix in one vertical slice: generic clinical
PDFs keep short patient names on the current 18 pt line, shrink longer names to
a 12 pt floor, wrap when still necessary, preserve every character, and reserve
enough vertical space to prevent overlap. Prescription and discharge-report
PDFs must remain valid, and custom-canvas consumers must remain unchanged.

Implement exactly this slice, run its focused checks, report evidence, and stop.
Do not begin any unrelated PDF cleanup.

## Context for a zero-context implementer

Read these files completely, in order, before editing:

1. `AGENTS.md`
2. `docs/workflows/coding-standards.md`
3. `docs/workflows/llm-collab.md`
4. `openspec/changes/fit-long-patient-names-in-pdf-headers/proposal.md`
5. `openspec/changes/fit-long-patient-names-in-pdf-headers/design.md`
6. `openspec/changes/fit-long-patient-names-in-pdf-headers/specs/clinical-pdf-patient-header/spec.md`
7. `apps/pdfgenerator/services/pdf_generator.py`
8. `apps/pdfgenerator/tests/test_pdf_generation.py`
9. `apps/dailynotes/services/pdf_generator.py`, limited to imports,
   `DailyNoteCanvas`, and `DailyNotePDFGenerator.generate_pdf()`
10. `apps/dischargereports/services/pdf_generator.py`
11. `apps/dischargereports/tests/test_views.py`, limited to reading the existing
    PDF view setup as a test-pattern reference
12. This slice file

Current state:

- `NumberedCanvas.draw_header()` uses one fixed 18 pt `drawString()` at
  `x = 6 cm` without `stringWidth()`.
- The intended width to the configured 2 cm right margin is 13 cm.
- Separator position and default frame reservation are fixed.
- `pdf_generator.py` is already above the mandatory 450-line limit.
- `DailyNoteCanvas` subclasses `NumberedCanvas` through the current import path
  and supplies custom canvas/header geometry.
- The app container was stopped during planning. Do not start or recreate it
  without owner approval; report a blocker if it is not already running at
  implementation time.

Use only synthetic names in tests and evidence. Never copy production patient
information from the reported image or database.

## Requirements

### R1 - Preserve the short-name baseline

A line that fits at 18 pt must remain a single 18 pt line at the current origin
and baseline. Its separator position and default content-frame reservation must
remain unchanged.

### R2 - Shrink before wrapping

Measure with ReportLab `stringWidth()`. For a line that fails at 18 pt but fits
at or above 12 pt, select a deterministic smaller size and keep one line. Never
shrink below 12 pt.

### R3 - Wrap without data loss

At the 12 pt floor, wrap by words within the computed right boundary. Split a
single oversized token by character when needed. Every line must fit, and
recombining layout fragments must preserve the complete `Paciente: <nome>`
content in order, excluding only whitespace introduced by layout.

Realistic long names will usually use two lines. A valid exceptional value may
use more lines rather than being truncated, abbreviated, ellipsized, or rendered
below the font floor.

### R4 - Keep vertical geometry coherent

Use the same pure layout contract for canvas drawing and default frame
reservation. Wrapped text must move the separator and title/body start down by
the same required increment. No patient line may cross the separator, page
boundary, title, or body frame.

### R5 - Extract without breaking compatibility

Move the generic canvas and cohesive fitting helpers to
`apps/pdfgenerator/services/header_canvas.py`. Re-export `NumberedCanvas` from
`apps.pdfgenerator.services.pdf_generator` so existing imports and Daily Note
inheritance remain valid. Do not perform unrelated refactors.

### R6 - Preserve consumer behavior

`create_prescription_pdf()` and `DischargeReportPDFGenerator` must still produce
valid PDFs with synthetic long names. No consumer view, URL, permission, model,
template, or CSS behavior changes.

### R7 - Preserve explicit custom geometry

When `generate_pdf()` receives a custom `canvasmaker` and/or explicit
`header_height_cm`, do not replace the custom canvas or override the explicit
height. Daily Note focused PDF tests must remain green.

## Expected blast radius

```yaml
expected_files:
  - apps/pdfgenerator/services/header_canvas.py
  - apps/pdfgenerator/services/pdf_generator.py
  - apps/pdfgenerator/tests/test_pdf_generation.py
  - apps/dischargereports/tests/test_pdf_header.py
allowed_incidental_files: []
out_of_scope:
  - apps/dischargereports/tests/test_views.py
  - apps/outpatientprescriptions/views.py
  - apps/outpatientprescriptions/templates/
  - apps/outpatientprescriptions/static/
  - apps/dailynotes/services/pdf_generator.py
  - patient models, forms, migrations, or stored data
  - URLs, permissions, footer, signature, body, or pagination redesign
  - package or dependency changes
  - generated static assets
```

The worker must stop and escalate before touching an out-of-scope path. If the
compatibility re-export cannot preserve Daily Note behavior without editing the
Daily Note service, report the concrete blocker rather than widening scope.

The parent/orchestrator, not the worker, updates `tasks.md` after independent
review and final gates.

## Requirement -> file -> test/check matrix

<!-- markdownlint-disable MD013 -->

| Requirement | Expected file(s)                                | Test/check                                                                  |
| ----------- | ----------------------------------------------- | --------------------------------------------------------------------------- |
| R1          | `header_canvas.py`, `test_pdf_generation.py`    | Short name stays one line at 18 pt with unchanged coordinates               |
| R2          | `header_canvas.py`, `test_pdf_generation.py`    | Medium synthetic name selects one smaller size at or above 12 pt            |
| R3          | `header_canvas.py`, `test_pdf_generation.py`    | Long and oversized-token names preserve content and every line width fits   |
| R4          | `header_canvas.py`, `pdf_generator.py`, tests   | Separator and frame reservation gain the same wrapped-height increment      |
| R5          | Both service modules, tests                     | Compatibility import identity and file line-count inspection                |
| R6          | Generator and discharge tests                   | Prescription/discharge PDF buffers are valid for synthetic long names       |
| R7          | `pdf_generator.py`, shared and Daily Note tests | Explicit height/custom canvas remain authoritative; Daily Note suite passes |

<!-- markdownlint-enable MD013 -->

## TDD plan

### RED

Add focused tests before production edits. Cover at minimum:

1. a short line retains 18 pt, one line, and existing coordinates;
2. a medium line shrinks before wrapping and never below 12 pt;
3. a long accented name wraps and every line fits the available width;
4. an oversized single token is chunked without character loss;
5. wrapped layout moves separator and frame reservation coherently;
6. compatibility re-export remains importable by the Daily Note module;
7. explicit `header_height_cm` and custom `canvasmaker` remain authoritative;
8. prescription and discharge-report PDF generation remains valid with
   synthetic long names.

Run:

```bash
./scripts/test.sh apps.pdfgenerator.tests.test_pdf_generation
```

Expected RED: one or more new assertions fail because the generic header lacks
measurement, font fitting, wrapping, or dynamic reservation. Import, syntax,
database setup, or container failures are not valid RED evidence.

### GREEN

Implement only R1-R7. Prefer a typed immutable layout value and small pure
helpers. Use named constants for preferred font size, minimum font size, step,
line gap, origin, and boundary. Keep new or changed functions within the
project's 40-line recommended limit and add parameter/return annotations.

Run the same focused command until it passes:

```bash
./scripts/test.sh apps.pdfgenerator.tests.test_pdf_generation
```

### REFACTOR

After GREEN:

- remove duplicated width/height formulas;
- confirm the canvas consumes the pure fitted layout;
- confirm the generator derives default reservation from the same contract;
- keep the compatibility re-export explicit;
- ensure `pdf_generator.py` line count is reduced, not increased;
- remove no unrelated imports or behavior unless required by the extraction.

## Local verification

Run all commands below. Use `docker exec eqmd_dev` for Python tooling, as
required by `AGENTS.md`.

```bash
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev ruff check \
  apps/pdfgenerator/services/header_canvas.py \
  apps/pdfgenerator/services/pdf_generator.py \
  apps/pdfgenerator/tests/test_pdf_generation.py \
  apps/dischargereports/tests/test_pdf_header.py
docker exec eqmd_dev ruff format --check \
  apps/pdfgenerator/services/header_canvas.py \
  apps/pdfgenerator/services/pdf_generator.py \
  apps/pdfgenerator/tests/test_pdf_generation.py \
  apps/dischargereports/tests/test_pdf_header.py
./scripts/typecheck.sh \
  apps/pdfgenerator/services/header_canvas.py \
  apps/pdfgenerator/services/pdf_generator.py
./scripts/test.sh apps.pdfgenerator.tests.test_pdf_generation
./scripts/test.sh apps.dischargereports.tests.test_pdf_header
./scripts/test.sh apps.dailynotes.tests.test_pdf_generator
```

Focused validation is sufficient for the worker handoff. Do not run the full
suite inside the slice loop; the parent runs `./scripts/test.sh` once after
independent review.

## Mandatory inspection checks

```bash
rg -n "stringWidth|18|12|wrap|NumberedCanvas" \
  apps/pdfgenerator/services/header_canvas.py \
  apps/pdfgenerator/services/pdf_generator.py
rg -n "\.\.\.|ellipsis|abbrevi" \
  apps/pdfgenerator/services/header_canvas.py
rg -n "NumberedCanvas" \
  apps/dailynotes/services/pdf_generator.py \
  apps/pdfgenerator/services/pdf_generator.py
wc -l \
  apps/pdfgenerator/services/header_canvas.py \
  apps/pdfgenerator/services/pdf_generator.py
```

Expected interpretation:

- ReportLab width measurement and the named 18 pt/12 pt policy are present;
- no ellipsis or abbreviation path exists;
- the legacy import path remains available to Daily Note code;
- extraction reduces the oversized shared generator instead of growing it.

## Acceptance criteria

- [ ] R1-R7 each have direct automated or inspection evidence.
- [ ] RED failed for missing layout behavior, not infrastructure.
- [ ] Focused GREEN and all local verification commands exit 0.
- [ ] Every rendered name line stays within the computed boundary.
- [ ] Synthetic long and oversized-token names lose no characters.
- [ ] Short-name font, line count, origin, baseline, separator, and reservation
      remain unchanged.
- [ ] Wrapped-name separator and frame reservation remain coherent.
- [ ] Prescription and discharge-report PDF generation remain valid.
- [ ] Custom canvas and explicit header height remain authoritative.
- [ ] Daily Note PDF tests remain green without edits to its service.
- [ ] No persistence, route, permission, template, CSS, or dependency change.
- [ ] Only expected files changed.
- [ ] No real patient information appears in tests, logs, or reports.

## Worker handoff

Report only:

- status: complete or blocked;
- files changed, paths only;
- RED command and expected failing assertions;
- GREEN/local commands with exit codes;
- matrix R1-R7 -> evidence;
- inspection summary;
- blockers or residual risks;
- confirmation that no out-of-scope work, commit, push, package install, or
  container lifecycle action occurred.

Then stop. Independent review must evaluate behavior, tests, scope, and design
before the parent runs the final full-suite gate or updates `tasks.md`.
