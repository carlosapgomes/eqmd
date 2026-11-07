# pdf-forms Specification

## Purpose

TBD - created by archiving change add-apac-secondary-procedures. Update Purpose
after archive.

## Requirements

### Requirement: APAC procedure slots

The system SHALL provide one required main procedure and five optional secondary
procedures in the APAC form, each selected via search by code or description.

#### Scenario: Main procedure required

- **WHEN** the user submits the APAC form without a main procedure
- **THEN** the submission MUST be rejected with a validation error

#### Scenario: Secondary procedures optional

- **WHEN** the user leaves any secondary procedure blank
- **THEN** the submission MUST be accepted without error

### Requirement: Procedure data capture

The system SHALL store UUID, code, and description for the main and secondary
procedures in the APAC submission data using the following keys:

- main: `main_procedure_id`, `main_procedure_code`, `main_procedure_description`
- secondary 1..5: `secondary_procedure_{n}_id`, `secondary_procedure_{n}_code`,
  `secondary_procedure_{n}_description`

#### Scenario: Procedure values persisted

- **WHEN** the user selects a main procedure and two secondary procedures
- **THEN** the submission data MUST contain UUID, code, and description for the
  selected procedures using the defined keys

### Requirement: Duplicate prevention

The system SHALL reject duplicate procedure selections across the main and
secondary slots.

#### Scenario: Duplicate procedure selection

- **WHEN** a procedure is selected more than once across main and secondary
  slots
- **THEN** the submission MUST be rejected with a validation error

### Requirement: PDF overlay mapping support

The system SHALL support rendering procedure code and description values in APAC
PDF overlays using the stored keys.

#### Scenario: Download APAC PDF

- **WHEN** a user downloads an APAC submission PDF
- **THEN** the overlay MUST render the stored procedure codes and descriptions
  at the mapped field positions

### Requirement: Exam batch capture page

The system SHALL provide a dedicated batch page for the "Solicitação de
Exames SUS" template with shared fields (justificativa, data, médico, with
current auto-fills) and a dynamic formset of 1–N exams (free text +
optional code).

#### Scenario: Shared values applied to all exams

- **WHEN** the user fills the shared motivo/data/médico once and adds 3 exams
- **THEN** each created submission MUST carry the same shared values with its
  own `examRequested`/`examCode`

#### Scenario: Empty exam rows rejected

- **WHEN** the user submits the batch with an exam row missing the exam name
- **THEN** the submission MUST be rejected with a validation error and no
  submission created

### Requirement: One submission per exam with batch grouping

The system SHALL create one `PDFFormSubmission` per exam in a single
transaction, each in the current `form_data` format plus a shared `batch_id`.

#### Scenario: Atomic batch creation

- **WHEN** the user submits a valid batch of N exams
- **THEN** the system MUST create exactly N submissions sharing one `batch_id`

#### Scenario: Legacy submissions unaffected

- **WHEN** a submission without `batch_id` is viewed or downloaded
- **THEN** it MUST behave exactly as before (single print, detail, edit,
  delete)

### Requirement: Batch 3-up A4 printing

The system SHALL compose batch downloads with up to 3 vias per A4 sheet at
100% size (fixed crop top 1.0cm / base 10.0cm), each via identical to the
single print, with dashed cut lines only between printed vias.

#### Scenario: Three exams on one sheet

- **WHEN** downloading a batch of 3 final exams
- **THEN** the PDF MUST contain 1 A4 page with 3 vias and 2 cut lines

#### Scenario: Partial last sheet

- **WHEN** downloading a batch of 4 final exams
- **THEN** the PDF MUST contain 2 pages (3 vias + 1 via, no stray cut line)

#### Scenario: Via content identical to single print

- **WHEN** comparing a batch via with the single download of the same
  submission
- **THEN** the rendered content MUST be identical (same overlay, same size)

### Requirement: Deterministic batch pagination

The system SHALL place exam N at slot `(N-1)%3` of sheet `(N-1)//3`,
preserving exam order top-to-bottom, sheet after sheet.

#### Scenario: Ninth exam position

- **WHEN** downloading a batch of 9 exams
- **THEN** the PDF MUST contain 3 full sheets with exam 9 at the bottom slot
  of sheet 3

### Requirement: Batch download draft gating and permissions

The system SHALL include only final submissions in batch composition and
enforce per-submission download permission.

#### Scenario: Draft excluded from batch

- **WHEN** a batch contains a draft submission
- **THEN** the download MUST NOT include the draft (404 if the batch
  resolves to drafts only, mirroring single-download behavior)

#### Scenario: Unauthorized patient denied

- **WHEN** the user lacks access to the batch patient
- **THEN** the download MUST be denied

### Requirement: Timeline batch actions

The system SHALL keep the existing single-exam PDF button unchanged on
timeline cards and add a batch download button on EVERY card of a batch
(shown only when the submission has a `batch_id` with final siblings),
plus a batch banner on `submission_detail`.

#### Scenario: Single button unchanged

- **WHEN** the user clicks the existing PDF button on a batch exam card
- **THEN** the system MUST download only that exam's single via

#### Scenario: Batch button on all cards

- **WHEN** a batch has N final exams
- **THEN** all N timeline cards MUST show the "Baixar lote 3-up (N vias)"
  button linking to the same batch download

#### Scenario: No batch button for single exams

- **WHEN** a submission has no `batch_id` or no final siblings
- **THEN** the card MUST NOT show the batch button

#### Scenario: Detail banner

- **WHEN** viewing the detail of a batch exam
- **THEN** the page MUST show a "Parte do lote de N exames" banner with
  batch download and sibling links

### Requirement: Batch supervision parity

The system SHALL replicate the draft/final supervision actions
(`save_draft`/`save_final`, doctor-or-resident approval) on the batch page.

#### Scenario: Student batch stays supervised

- **WHEN** a student submits a batch
- **THEN** all N submissions MUST be drafts until a doctor or resident
  finalizes them

### Requirement: Authenticated PDF template preview

The system SHALL serve blank PDF form templates through an
authenticated preview view that works regardless of `DEBUG`,
instead of linking raw `/media/...` URLs.

#### Scenario: Authenticated user previews a template

- **WHEN** an authenticated user requests the preview route
  for a template with a file on disk
- **THEN** the system returns the PDF bytes with
  `Content-Type: application/pdf` and an inline
  `Content-Disposition`
- **AND** the response is privately cacheable only

#### Scenario: Preview requires authentication

- **WHEN** an anonymous user requests the preview route
- **THEN** the system redirects to login

#### Scenario: Missing file on disk is a 404

- **WHEN** the preview route is requested for a template
  whose file is absent from storage
- **THEN** the system returns 404

#### Scenario: Unknown template is a 404

- **WHEN** the preview route is requested with an unknown
  template id
- **THEN** the system returns 404

#### Scenario: Inactive templates preview too

- **WHEN** an authenticated user requests the preview route
  for an inactive template
- **THEN** the system returns the PDF (the list filters
  actives; staff preview from the admin must still work)

#### Scenario: Admin links to the preview route

- **WHEN** staff views a template in the Django admin
- **THEN** the "View PDF" link points to the preview route,
  not to the raw media URL

#### Scenario: Admin change-form widget links the preview route

- **WHEN** staff opens a template change form with an
  uploaded file
- **THEN** the existing-file widget link points to the
  preview route, not to the raw media URL

#### Scenario: Template list links to the preview route

- **WHEN** a user opens the PDF template list
- **THEN** the "Ver PDF" button points to the preview route,
  not to the raw media URL
