# Clinical PDF Patient Header Specification

## ADDED Requirements

### Requirement: Generic clinical PDF headers preserve the complete patient name

A generic clinical PDF that receives a patient name SHALL render the complete
`Paciente: <nome>` value inside the horizontal page boundary on every page. It
SHALL NOT abbreviate, ellipsize, or silently discard characters.

#### Scenario: Short patient name preserves the current layout

- **GIVEN** the complete patient line fits at the preferred 18 pt size
- **WHEN** the generic clinical PDF header is rendered
- **THEN** the line remains at 18 pt on one line
- **AND** its existing origin, baseline, separator, and frame reservation remain
  unchanged

#### Scenario: Long patient name first reduces font size

- **GIVEN** the complete patient line does not fit at 18 pt
- **AND** it can fit on one line at or above the 12 pt minimum
- **WHEN** the generic clinical PDF header is rendered
- **THEN** the renderer chooses a deterministic smaller font size
- **AND** the complete line remains within the configured right boundary

#### Scenario: Patient name wraps at the legibility floor

- **GIVEN** the complete patient line cannot fit on one line at 12 pt
- **WHEN** the generic clinical PDF header is rendered
- **THEN** the text wraps by words into as many lines as required
- **AND** every line remains within the configured horizontal boundary
- **AND** joining the rendered content preserves the complete patient line in
  order

#### Scenario: Oversized token is preserved

- **GIVEN** one patient-name token is wider than the complete line width at the
  minimum font size
- **WHEN** the generic clinical PDF header is rendered
- **THEN** the token is split into fitting fragments
- **AND** no character is lost, replaced, or abbreviated

### Requirement: Header geometry reserves fitted patient-name height

The generic clinical PDF SHALL derive separator placement and body-frame
reservation from the fitted patient-name block so header content cannot overlap
the document title or body.

#### Scenario: Wrapped name expands the header coherently

- **GIVEN** the patient line wraps to multiple lines
- **WHEN** the PDF page is laid out
- **THEN** the separator appears below the final rendered line
- **AND** the document title and body frame begin below the expanded header
- **AND** the same geometry is used on every page

#### Scenario: Normal name does not add vertical space

- **GIVEN** the patient line fits at the preferred size
- **WHEN** the PDF page is laid out
- **THEN** no extra header or frame height is reserved

### Requirement: Shared consumers receive the corrected header safely

The shared behavior SHALL apply to outpatient prescription and discharge report
PDFs while preserving document-specific and custom-canvas contracts.

#### Scenario: Prescription uses the fitted shared header

- **GIVEN** an outpatient prescription for a patient with a long name
- **WHEN** its PDF is generated
- **THEN** the generic repeated header follows the shrink-then-wrap contract
- **AND** the PDF remains valid

#### Scenario: Discharge report uses the fitted shared header

- **GIVEN** a discharge report for a patient with a long name
- **WHEN** its PDF is generated
- **THEN** the generic repeated header follows the shrink-then-wrap contract
- **AND** the PDF remains valid

#### Scenario: Explicit custom header geometry remains authoritative

- **GIVEN** a PDF consumer supplies a custom canvas and explicit header height
- **WHEN** the shared generator builds the document
- **THEN** the generic patient-name reservation does not replace that explicit
  geometry
- **AND** existing custom-canvas behavior remains unchanged
