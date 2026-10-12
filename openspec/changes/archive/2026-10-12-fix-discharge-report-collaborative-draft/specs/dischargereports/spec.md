# Dischargereports Specification Delta

## MODIFIED Requirements

### Requirement: Collaborative discharge report draft editing

The system SHALL allow any authenticated doctor/resident with
patient access to edit a discharge report draft at any time,
regardless of who created it and regardless of draft age.
Re-saving as draft SHALL keep `is_draft` true. Users whose
`profession_type` is not doctor/resident SHALL still be denied,
even with patient access.

#### Scenario: Other doctor edits a draft

- **WHEN** doctor B (not the creator) opens the update view
  of a draft created by doctor A
- **THEN** access is granted and re-saving as draft succeeds
- **AND** the report remains a draft

#### Scenario: Old draft remains editable

- **WHEN** a draft is older than 24h (by `created_at`)
- **THEN** the creator and any other doctor/resident can
  still edit and re-save it as draft

#### Scenario: Non-doctor cannot edit a draft

- **WHEN** a nurse, physiotherapist, or student tries to open
  or submit the update view of a draft
- **THEN** access is denied with 403 (or false predicate)

### Requirement: Collaborative discharge report finalization

The system SHALL allow any doctor/resident who can edit a
draft to finalize it. Finalizing SHALL set `is_draft` to
false. After finalization the standard finalized-report
rules SHALL apply.

#### Scenario: Other doctor finalizes a draft

- **WHEN** doctor B submits the update view of doctor A's
  draft with the finalize action
- **THEN** the report becomes finalized (`is_draft` false)

#### Scenario: Finalized report keeps the 24h creator rule

- **WHEN** a report is finalized
- **THEN** only the creator (or `events.change_event`
  holders) can edit it and only within 24h of creation

### Requirement: Discharge report draft edit action visibility

The detail view and timeline card SHALL show the edit action
for a draft exactly when the current user satisfies the
collaborative draft predicate (doctor/resident with patient
access).

#### Scenario: Edit action shown to collaborating doctor

- **WHEN** doctor B views a draft created by doctor A
- **THEN** the edit action is visible

#### Scenario: Edit action hidden from non-doctor

- **WHEN** a non-doctor views a draft
- **THEN** the edit action is not visible
