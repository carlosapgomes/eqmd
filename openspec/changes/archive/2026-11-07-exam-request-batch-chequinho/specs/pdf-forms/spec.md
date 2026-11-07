# pdf-forms — delta

## ADDED Requirements

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
