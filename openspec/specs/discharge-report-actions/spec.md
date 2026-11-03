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

The system SHALL allow any authenticated
doctor/resident with patient access to edit a
discharge report draft at any time, regardless of
authorship or draft age. Re-saving as draft SHALL
keep `is_draft` true. Users whose profession is not
doctor/resident SHALL still be denied. An update
submission carrying neither the draft nor the
finalize action SHALL leave the report state
unchanged and SHALL return an explicit error naming
the valid actions.

#### Scenario: Other doctor edits and re-saves a draft

- **WHEN** a doctor/resident who did not create the
  draft opens the update view and re-saves as draft
- **THEN** access is granted and the report remains
  a draft

#### Scenario: Old draft remains editable

- **WHEN** a draft is older than 24h by `created_at`
- **THEN** the creator and any other doctor/resident
  can still edit it

#### Scenario: Non-doctor cannot edit a draft

- **WHEN** a nurse, physiotherapist, or student
  tries to open or submit the update view of a
  draft
- **THEN** access is denied

#### Scenario: Unknown update action preserves state

- **WHEN** an update submission carries neither the
  draft nor the finalize action
- **THEN** the report state is unchanged and the
  response names the valid actions

### Requirement: Discharge report edit action availability

The discharge report detail view and timeline card
SHALL show the edit action for a draft exactly when
the current user satisfies the single collaborative
draft predicate (doctor/resident with patient
access). The timeline permission check SHALL
dispatch discharge-report events to that predicate
instead of the generic event predicate. The model
method, the view helper, and the timeline check
SHALL return the same edit verdict for any
user/report pair.

#### Scenario: Edit action shown to collaborating doctor

- **WHEN** a doctor/resident views a draft created
  by someone else
- **THEN** the edit action is visible

#### Scenario: Edit action hidden from non-doctor

- **WHEN** a non-doctor views a draft
- **THEN** the edit action is not visible

#### Scenario: Timeline shows edit to collaborating doctor

- **WHEN** a doctor/resident views another author's
  draft in the patient timeline
- **THEN** the timeline card shows the edit action

#### Scenario: Timeline hides edit from non-doctor

- **WHEN** a non-doctor views a draft in the
  patient timeline
- **THEN** the timeline card hides the edit action

#### Scenario: Timeline hides edit on expired final

- **WHEN** a collaborator views a finalized report
  whose 24h finalization window expired
- **THEN** the timeline card hides the edit action

#### Scenario: Timeline shows edit on freshly finalized old draft

- **WHEN** the creator or finalizer views in the
  timeline a report finalized within 24h, even one
  created long ago
- **THEN** the timeline card shows the edit action

#### Scenario: Three doors stay equivalent

- **WHEN** any user/report pair is evaluated
- **THEN** the model method, the view helper, and
  the timeline check return the same edit verdict

### Requirement: Discharge report finalization window

The system SHALL allow any doctor/resident who can
edit a draft to finalize it. Finalizing SHALL set
`is_draft` to false and SHALL record `finalized_at`
(now) and `finalized_by` (the acting user).
Reverting a final back to draft SHALL clear both
fields. A finalized report SHALL be editable
within 24h of `finalized_at` by the creator OR the
finalizer (or `events.change_event` holders, still
window-bound); after the window it SHALL be
locked. A final with null `finalized_at` SHALL
fall back to the `created_at` anchor. Delete rules
for finals are unchanged.

#### Scenario: Other doctor finalizes a draft

- **WHEN** a doctor/resident submits another
  author's draft with the finalize action
- **THEN** the report becomes finalized with
  `finalized_at` and `finalized_by` recorded

#### Scenario: Old draft finalize opens a correction window

- **WHEN** a doctor finalizes a draft whose
  `created_at` is older than 24h
- **THEN** the report is editable for 24h from
  finalization by creator or finalizer

#### Scenario: Finalized report locks after 24h

- **WHEN** more than 24h passed since
  `finalized_at`
- **THEN** nobody can edit it via the update view

#### Scenario: Revert to draft clears the anchor

- **WHEN** a final is re-saved as draft within
  its window
- **THEN** `finalized_at` and `finalized_by`
  return to null and the report is a draft again

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
