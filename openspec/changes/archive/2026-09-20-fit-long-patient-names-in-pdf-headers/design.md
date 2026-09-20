# Design: Hybrid patient-name fitting for shared PDF headers

## Context

`OutpatientPrescriptionPDFView` passes the full database value as
`patient_data["name"]` to `HospitalLetterheadGenerator`. Discharge reports pass
the same value through `DischargeReportPDFGenerator`. The shared
`NumberedCanvas.draw_header()` currently renders it with:

- a fixed 18 pt `Times-Bold` font;
- a fixed `x = 6 cm` origin;
- one `drawString()` call;
- no width measurement or wrapping;
- a fixed separator and content-frame reservation.

On A4, the intended span from that origin to the configured 2 cm right margin
is 13 cm. A long name can also exceed the physical page edge. This matches the
reported cut point and proves that storage and view orchestration are not the
cause.

The shared generator file is already above the project's mandatory 450-line
limit. The change must not add more layout responsibility to that file without
a containment plan.

## Goals / Non-Goals

### Goals

- Preserve every character of the patient name in the repeated generic PDF
  header.
- Keep normal names on the existing 18 pt single-line layout.
- Prefer deterministic font reduction before adding header height.
- Wrap long names at a legible minimum size and keep every line inside the
  configured horizontal boundary.
- Reserve matching vertical space so header, separator, title, and body cannot
  overlap.
- Apply the shared behavior to prescriptions and discharge reports without
  changing their views or routes.
- Preserve custom-canvas behavior and public import compatibility.

### Non-Goals

- Changing patient data, validation, or the 255-character model limit.
- Abbreviating names, adding ellipses, or selecting a preferred surname.
- Redesigning the hospital logo/name row, footer, signature, or body content.
- Changing the legacy browser-print template or CSS.
- Replacing the dedicated Daily Note header.
- General PDF typography or pagination refactoring unrelated to this defect.

## Decisions

### 1. Fix the shared generic header

The correction belongs in the shared generic header because both prescriptions
and discharge reports exhibit the same behavior and pass the same patient-name
input. App-specific workarounds would duplicate logic and leave other generic
PDF endpoints vulnerable.

The consumer views and services remain unchanged unless a failing integration
test proves an existing consumer violates the documented input contract.

### 2. Use a deterministic shrink-then-wrap algorithm

The patient line starts with the literal prefix `Paciente:` plus a space and
uses these rules:

1. Measure the complete line with ReportLab `stringWidth()` at the preferred
   18 pt size.
2. If it does not fit, reduce the size in fixed steps until it fits or reaches
   a 12 pt minimum.
3. At the minimum size, wrap by words within the available width.
4. If one token is wider than the available width, split it by character while
   preserving every character.
5. Return an immutable or otherwise explicit layout result containing the
   chosen font size, rendered lines, line gap, and block height.

Realistic long names should normally occupy two lines. If a valid stored value
requires more, the header grows rather than truncating text or shrinking below
the legibility floor.

The algorithm must be pure and independently testable. Width comparison may
allow only a small floating-point tolerance.

### 3. Preserve the short-name baseline

When the full patient line fits at 18 pt:

- render exactly one line;
- keep the existing horizontal origin;
- keep the existing patient baseline;
- keep the existing separator position;
- keep the existing default content-frame reservation.

This minimizes visual regression for the common case.

### 4. Derive vertical geometry from one layout decision

For wrapped names, the separator moves below the final patient line and the
content frame reserves the same additional height. A single layout calculation
must drive both decisions; independent magic offsets in the canvas and
generator are not acceptable.

The layout contract must ensure:

- every line baseline and glyph block remains above the separator;
- the separator remains above the document title;
- the content frame begins below the complete header;
- the calculation repeats identically on every page.

The implementation may calculate the pure layout twice from identical inputs,
or pass one explicit layout value through the canvas factory. It must not
maintain divergent width or height formulas.

### 5. Extract the generic canvas without breaking imports

Move the generic canvas and its fitting helpers into a focused module such as
`apps/pdfgenerator/services/header_canvas.py`. Keep
`NumberedCanvas` importable from
`apps.pdfgenerator.services.pdf_generator` through a compatibility re-export,
because Daily Note code and existing tests import it from that path.

This extraction:

- keeps the new layout logic cohesive;
- reduces `pdf_generator.py` toward the project size limit;
- avoids adding another responsibility to an already oversized module;
- preserves existing caller behavior.

No unrelated cleanup of PDF generation is included.

### 6. Keep custom canvases isolated

`HospitalLetterheadGenerator.generate_pdf()` already accepts `canvasmaker` and
`header_height_cm`. Daily Note PDFs provide both and own their header geometry.
The generic fitting reservation must therefore apply only to the default
`NumberedCanvas` path when no explicit header height overrides it.

The following must remain true:

- `DailyNoteCanvas` still subclasses the compatibility-exported
  `NumberedCanvas`;
- an explicit `header_height_cm` remains authoritative;
- a caller-supplied `canvasmaker` is not replaced;
- Daily Note focused PDF tests remain green.

### 7. Test geometry, not only text presence

Existing coverage proves only that `drawString()` receives `Paciente: Test
Patient`. That assertion passes even when text is outside the page.

Focused tests must instead prove:

- short-name baseline compatibility;
- font reduction before wrapping;
- minimum font floor;
- every rendered line width is within the computed budget;
- long and oversized-token inputs preserve all non-layout characters in order;
- wrapped geometry moves the separator and frame reservation coherently;
- a generated prescription PDF remains valid and contains the complete name;
- a generated discharge report remains valid under the shared header;
- explicit custom-canvas/header-height behavior is unchanged.

PDF text extraction may supplement these checks but cannot replace coordinate
and width assertions because off-page text can remain extractable.

## Risks / Trade-offs

- **Shared-header regression:** a base change can affect several PDF types.
  Mitigation: preserve the short-name baseline and run shared, prescription,
  discharge-report, and Daily Note focused regressions.
- **Canvas/frame drift:** separate geometry calculations could overlap body
  content. Mitigation: one pure layout contract feeds both drawing and frame
  reservation.
- **Very long values increase header height:** preserving full identification
  may consume additional vertical space. This is preferable to truncation and
  applies only when required.
- **Extraction compatibility:** moving `NumberedCanvas` can break imports.
  Mitigation: compatibility re-export plus existing Daily Note tests.
- **Brittle visual tests:** exact PDF raster comparisons can vary. Mitigation:
  assert deterministic width, coordinate, text-preservation, and PDF-validity
  contracts instead of pixel snapshots.

## Rollout and Verification

1. Add focused failing tests for hybrid fitting and geometry.
2. Extract the generic canvas with compatibility re-export.
3. Implement the pure fitting result and dynamic header reservation.
4. Run shared PDF generator tests.
5. Run outpatient prescription, discharge report, and Daily Note PDF
   regressions.
6. Complete independent review of behavior, tests, scope, and design.
7. Run the project-wide final quality gate once.

No data migration or rollback operation is required. Rolling back the code
restores the previous rendering behavior without changing persisted data.
