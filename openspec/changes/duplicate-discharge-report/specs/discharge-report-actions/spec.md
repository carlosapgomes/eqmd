# Discharge report actions — delta

## ADDED Requirements

### Requirement: Discharge report duplication

The system SHALL provide a duplicate action that opens the discharge
report creation form pre-filled from an existing report of the same
patient, creating an independent new report owned by the submitting
user.

#### Scenario: Duplicate form pre-filled from source

- **WHEN** an authorized user opens the duplicate action for a
  discharge report
- **THEN** the form shows the source's clinical content fields
  (specialty, admission history, problems and diagnosis, exams,
  procedures, inpatient history, discharge status,
  recommendations) and the source's admission and discharge dates
- **AND** the event datetime field defaults to now, not to the
  source's datetime

#### Scenario: Duplicate creates an independent draft copy

- **WHEN** the user submits the duplicate form without the
  final-save action
- **THEN** the system creates a new draft discharge report for the
  same patient, attributed to the submitting user
- **AND** the copy has no finalization metadata
- **AND** editing rights for the copy follow the collaborative draft
  rules
- **AND** the system redirects to the patient timeline

#### Scenario: Duplicate of a finalized report never copies state

- **WHEN** the source report is finalized and a duplicate is created
- **THEN** the copy is born a draft with empty `finalized_at` and
  `finalized_by`
- **AND** the source keeps its finalization metadata, author and
  timestamps unchanged

#### Scenario: Source report unchanged

- **WHEN** a duplicate is created
- **THEN** the source's content, dates, authorship, draft/final
  state and finalization metadata remain unchanged

#### Scenario: Timeline card duplicate action is gated

- **WHEN** a user holding `events.add_event` views the patient
  timeline
- **THEN** the discharge report card shows a duplicate action
- **WHEN** a user without `events.add_event` views the timeline
- **THEN** the discharge report card shows no duplicate action

#### Scenario: Patient access required

- **WHEN** a user without access to the source report's patient
  opens the duplicate action
- **THEN** the system denies the request with an access error and no
  report is created
