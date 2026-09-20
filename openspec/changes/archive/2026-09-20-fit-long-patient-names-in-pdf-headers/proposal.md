# Proposal: Fit long patient names in shared PDF headers

## Why

The shared ReportLab header draws `Paciente: <nome>` once at a fixed `x = 6 cm`
position in 18 pt Times Bold. `drawString()` does not measure, shrink, or wrap
text, so a long patient name crosses the A4 media box and is visibly cut off.
The database value remains complete; the defect is confined to PDF rendering.

The same `NumberedCanvas` header is used by outpatient prescriptions and
discharge reports. The reported photograph shows the identical truncation in
both document types, making this a shared clinical-identification defect rather
than a prescription-only styling issue.

Patient identification on a clinical document must remain complete and legible
on every page. Short names should keep the current visual hierarchy, while long
names need deterministic fitting without ellipsis or silent abbreviation.

## What Changes

- Add a shared hybrid fitting policy for the patient-name header:
  - keep the current preferred 18 pt single line when it fits;
  - reduce the font deterministically to a legible minimum when necessary;
  - wrap by words at the minimum size when one line still does not fit;
  - split an exceptional oversized token without dropping characters.
- Make separator position and content-frame reservation derive from the fitted
  patient-name block so wrapped text cannot overlap the document title or body.
- Preserve the current short-name layout and repeat the fitted full name on
  every page.
- Keep custom-canvas consumers, especially Daily Note PDFs, isolated from the
  generic-header geometry change.
- Add focused geometry and regression tests with synthetic short, long,
  accented, and unbreakable names.

## Capabilities

### New Capabilities

- `clinical-pdf-patient-header`: Shared clinical PDFs render the complete
  patient name within page bounds using deterministic shrink-then-wrap layout.

### Modified Capabilities

None. No existing OpenSpec capability defines the shared patient-name header
contract across prescriptions and discharge reports.

## Impact

- Primary implementation: `apps/pdfgenerator/services/`
- Primary tests: `apps/pdfgenerator/tests/test_pdf_generation.py`
- Consumers covered by the shared behavior:
  - outpatient prescription PDFs;
  - discharge report PDFs;
  - generic PDF endpoints that pass `patient_data["name"]`.
- Daily Note PDFs retain their dedicated `DailyNoteCanvas` and explicit header
  reservation contract.
- No model, migration, persistence, URL, permission, template, CSS, or frontend
  change.
- No patient name is truncated, abbreviated, or replaced with an ellipsis.
