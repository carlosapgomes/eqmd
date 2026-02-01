## ADDED Requirements

### Requirement: Discharge report PDF generation
The system SHALL allow users to download a discharge report as a PDF with hospital letterhead, pagination, page numbering, document date, and doctor signature.

#### Scenario: Download discharge report PDF
- **WHEN** an authenticated user requests a discharge report PDF for a patient they can access
- **THEN** the system returns a non-empty `application/pdf` response with a safe attachment filename

### Requirement: Discharge report PDF content structure
The generated discharge report PDF MUST include the same content sections and ordering as the current discharge report print layout, including admission/discharge dates and clinical sections when present.

#### Scenario: Include discharge report sections in order
- **WHEN** a discharge report has content in multiple clinical fields
- **THEN** the PDF includes sections for each populated field in the same order as the print layout

