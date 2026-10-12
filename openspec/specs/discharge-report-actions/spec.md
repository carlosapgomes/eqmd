# discharge-report-actions Specification

## Purpose

TBD - created by archiving change discharge-report-pdf. Update Purpose after
archive.

## Requirements

### Requirement: Discharge report PDF action availability

The discharge report detail view and timeline card SHALL provide a PDF download
action that uses the standard PDF download behavior.

#### Scenario: Detail view shows PDF action

- **WHEN** a user views a discharge report detail page
- **THEN** the UI provides a PDF download action for that report

#### Scenario: Timeline card shows PDF action

- **WHEN** a discharge report appears in the patient timeline
- **THEN** the UI provides a PDF download action for that report

### Requirement: Discharge report delete action permissions

The system SHALL allow deletion of finalized discharge reports within the
standard event deletion window for the creator or users with
`events.delete_event` permission, and SHALL allow draft deletion for the creator
or users with `events.delete_event` permission.

#### Scenario: Final report deletion within window

- **WHEN** the report is finalized and within the allowed deletion window
- **THEN** the creator or a user with `events.delete_event` can delete it

#### Scenario: Draft report deletion

- **WHEN** the report is a draft
- **THEN** the creator or a user with `events.delete_event` can delete it

### Requirement: Discharge report delete action availability

The discharge report timeline card SHALL display a delete action only when the
current user is permitted to delete the report.

#### Scenario: Timeline delete action is gated

- **WHEN** the current user lacks delete permission for the report
- **THEN** the delete action is not shown on the timeline card

### Requirement: Discharge report collaborative draft editing

The system SHALL allow any authenticated doctor/resident with patient access
to edit a discharge report draft at any time, regardless of authorship or
draft age. Re-saving as draft SHALL keep `is_draft` true. Users whose
profession is not doctor/resident SHALL still be denied.

#### Scenario: Other doctor edits and re-saves a draft

- **WHEN** a doctor/resident who did not create the draft opens the update
  view and re-saves as draft
- **THEN** access is granted and the report remains a draft

#### Scenario: Old draft remains editable

- **WHEN** a draft is older than 24h by `created_at`
- **THEN** the creator and any other doctor/resident can still edit it

#### Scenario: Non-doctor cannot edit a draft

- **WHEN** a nurse, physiotherapist, or student tries to open or submit the
  update view of a draft
- **THEN** access is denied

### Requirement: Discharge report collaborative finalization

The system SHALL allow any doctor/resident who can edit a draft to finalize
it. Finalizing SHALL set `is_draft` to false. After finalization the standard
finalized-report rules SHALL apply (creator-only edit within 24h).

#### Scenario: Other doctor finalizes a draft

- **WHEN** a doctor/resident submits another author's draft with the finalize
  action
- **THEN** the report becomes finalized

#### Scenario: Finalized report keeps the 24h creator rule

- **WHEN** a report is finalized
- **THEN** only the creator (or `events.change_event` holders) can edit it
  and only within 24h of creation

### Requirement: Discharge report edit action availability

The discharge report detail view and timeline card SHALL show the edit action
for a draft exactly when the current user satisfies the collaborative draft
predicate (doctor/resident with patient access).

#### Scenario: Edit action shown to collaborating doctor

- **WHEN** a doctor/resident views a draft created by someone else
- **THEN** the edit action is visible

#### Scenario: Edit action hidden from non-doctor

- **WHEN** a non-doctor views a draft
- **THEN** the edit action is not visible
