# pdf-forms — delta

## MODIFIED Requirements

### Requirement: Exam batch capture page

The system SHALL provide a dedicated batch page for the "Solicitação de
Exames SUS" template with shared fields (justificativa, data, médico, with
current auto-fills) and a dynamic formset of 1–N exams (free text +
optional code + optional per-exam justificativa defaulting to the shared
value).

#### Scenario: Shared values applied to all exams

- **WHEN** the user fills the shared motivo/data/médico once and adds 3 exams
  without editing any per-exam justificativa
- **THEN** each created submission MUST carry the same shared values with its
  own `examRequested`/`examCode`

#### Scenario: Per-exam justificativa overrides the shared value

- **WHEN** the user edits the justificativa of one exam row and submits the
  batch
- **THEN** that exam's submission MUST store the edited justificativa while
  the remaining exams keep the shared value

#### Scenario: Blur copy respects manual edits

- **WHEN** the shared justificativa field loses focus
- **THEN** its value MUST be copied only to the per-exam justificativa
  fields not marked as manually edited
- **AND** manually edited per-exam justificativa fields MUST be preserved,
  including ones manually emptied (they stay empty in the UI and fall back
  to the shared value on submit)

#### Scenario: Shared justificativa cleared mirrors untouched rows

- **WHEN** the user clears the shared justificativa and the field loses
  focus
- **THEN** the untouched per-exam justificativa fields MUST mirror the
  empty value while manually edited fields keep their content

#### Scenario: Empty per-exam justificativa falls back to shared

- **WHEN** the batch is submitted with a per-exam justificativa empty or
  blank (including a direct POST without JavaScript)
- **THEN** that exam's submission MUST store the shared justificativa

#### Scenario: New exam row pre-filled

- **WHEN** the user adds a new exam row after filling the shared
  justificativa
- **THEN** the new row's justificativa field MUST be pre-filled with the
  shared value

#### Scenario: Unused added row ignored

- **WHEN** the user adds an exam row, leaves the exam name and code empty
  and submits the batch
- **THEN** that row MUST be ignored (no submission created for it and no
  validation error), as long as its justificativa still mirrors the shared
  value

#### Scenario: Empty exam rows rejected

- **WHEN** the user submits the batch with an exam row partially filled
  (e.g. code or an individually typed justificativa without the exam name)
- **THEN** the submission MUST be rejected with a validation error and no
  submission created
