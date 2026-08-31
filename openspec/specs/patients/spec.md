# patients Specification

## Purpose

Define patient creation and update behavior for hospital record number handling.

## Requirements

### Requirement: Patient creation with initial record number

The system SHALL require an initial hospital record number when creating a
patient through the patient creation flow.

#### Scenario: Create patient with initial record number

- **GIVEN** an authenticated user with permission to add patients
- **WHEN** the user submits the patient creation form with valid patient data
  and a valid initial record number
- **THEN** the system creates the `Patient`
- **AND** the system creates exactly one related `PatientRecordNumber`
- **AND** the created record number is marked as current
- **AND** `Patient.current_record_number` equals the submitted record number
- **AND** the user is redirected to the patient detail page

#### Scenario: Missing initial record number blocks patient creation

- **GIVEN** an authenticated user with permission to add patients
- **WHEN** the user submits the patient creation form without an initial record
  number
- **THEN** the form is invalid
- **AND** no `Patient` is created
- **AND** no `PatientRecordNumber` is created

#### Scenario: Invalid initial record number blocks patient creation

- **GIVEN** an authenticated user with permission to add patients
- **WHEN** the user submits the patient creation form with an invalid initial
  record number format
- **THEN** the form is invalid using the existing record number format rules
- **AND** no `Patient` is created
- **AND** no `PatientRecordNumber` is created

#### Scenario: Record number persistence failure rolls back patient creation

- **GIVEN** valid patient data and a valid initial record number
- **WHEN** persisting `PatientRecordNumber` fails after patient persistence has
  started
- **THEN** the database transaction is rolled back
- **AND** no partial `Patient` remains saved
- **AND** no partial `PatientRecordNumber` remains saved

### Requirement: Patient creation UI exposes record number field

The system SHALL show the initial hospital record number field only on the
current patient creation page.

#### Scenario: Patient creation page shows record number field

- **GIVEN** an authenticated user with permission to add patients
- **WHEN** the user opens the patient creation page
- **THEN** the page shows a "Prontuário Hospitalar" section
- **AND** the page shows the `initial_record_number` input
- **AND** the field communicates that future changes must use the proper
  prontuário flow

#### Scenario: Patient update page does not show record number field

- **GIVEN** an authenticated user with permission to change a patient
- **WHEN** the user opens the patient update page
- **THEN** the page does not show the `initial_record_number` input
- **AND** the page does not show the "Prontuário Hospitalar" creation section

### Requirement: Patient update does not change record number

The system SHALL keep patient record number changes restricted to the dedicated
record number workflow after patient creation.

#### Scenario: Updating patient profile ignores posted initial record number

- **GIVEN** a patient with an existing current `PatientRecordNumber`
- **WHEN** a user submits the patient update form with personal/contact changes
  and an unexpected `initial_record_number` POST value
- **THEN** the patient personal/contact data is updated
- **AND** no new `PatientRecordNumber` is created
- **AND** the existing current record number remains unchanged

### Requirement: Similar patient identity review during creation

The system SHALL search active and soft-deleted patients before interactive
patient creation using normalized name and the same date of birth. Name
normalization SHALL ignore case, diacritics, punctuation, and repeated spaces.
A different normalized name SHALL be a candidate when PostgreSQL trigram
similarity is at least 0.80.

#### Scenario: Exact normalized name and birthday require review

- **GIVEN** an existing patient whose normalized name and birthday match the
  submitted patient
- **WHEN** an authorized user submits the patient creation form
- **THEN** no new patient is created on that submission
- **AND** the form shows a possible-duplicate warning
- **AND** the user can open the existing patient for review
- **AND** the user can explicitly confirm creation if there is no strong
  identifier or record-number conflict

#### Scenario: Similar name and same birthday require review

- **GIVEN** an existing patient with the same birthday
- **AND** the normalized names are different
- **AND** their trigram similarity is at least 0.80
- **WHEN** an authorized user submits the patient creation form
- **THEN** no new patient is created on that submission
- **AND** the form shows a possible-duplicate warning
- **AND** the user can explicitly confirm creation if there is no strong
  identifier or record-number conflict

#### Scenario: Similar name with different birthday does not warn

- **GIVEN** an existing patient with a similar normalized name
- **AND** the existing birthday differs from the submitted birthday
- **WHEN** an authorized user submits otherwise valid patient data
- **THEN** this existing patient is not returned by the name-based review
- **AND** creation proceeds when no other conflict exists

#### Scenario: Explicit confirmation permits a possible homonym

- **GIVEN** only advisory name-and-birthday candidates exist
- **WHEN** the user reviews the warning and explicitly confirms creation
- **THEN** the system reruns the candidate search on the confirmed POST
- **AND** the system creates the patient if no strong identifier or
  record-number conflict exists

#### Scenario: Soft-deleted patient is included in review

- **GIVEN** a soft-deleted patient whose normalized name and birthday match
- **WHEN** an authorized user submits the patient creation form
- **THEN** the soft-deleted patient appears as a candidate
- **AND** the warning identifies its deleted state
- **AND** no patient is created without explicit review

### Requirement: Strong CPF and CNS conflict prevention

The system SHALL normalize and validate non-empty CPF and CNS values entered in
interactive patient create and profile-update flows. An exact valid CPF or CNS
match with another active or soft-deleted patient SHALL be a strong conflict,
not an advisory name match.

#### Scenario: Existing valid CPF blocks patient creation

- **GIVEN** another patient has the submitted valid normalized CPF
- **WHEN** a user submits the patient creation form
- **THEN** the form is invalid
- **AND** no patient or record number is created
- **AND** duplicate-review confirmation cannot override the conflict

#### Scenario: Existing valid CNS blocks patient creation

- **GIVEN** another patient has the submitted valid normalized CNS
- **WHEN** a user submits the patient creation form
- **THEN** the form is invalid
- **AND** no patient or record number is created
- **AND** duplicate-review confirmation cannot override the conflict

#### Scenario: Existing valid identifier blocks profile reassignment

- **GIVEN** two different patients
- **AND** one patient owns a valid normalized CPF or CNS
- **WHEN** a user updates the other patient with that identifier
- **THEN** the profile form is invalid
- **AND** the other patient's profile remains unchanged

#### Scenario: Own identifier is accepted on profile update

- **GIVEN** a patient already has a valid CPF or CNS
- **WHEN** the profile form is submitted without changing that identifier
- **THEN** the patient is excluded from its own conflict search
- **AND** the unchanged identifier does not create a conflict

#### Scenario: Invalid new CPF or CNS is rejected

- **GIVEN** a non-empty new or changed CPF or CNS fails its digit count or
  checksum validation
- **WHEN** the create or profile-update form is validated
- **THEN** the corresponding field has a validation error
- **AND** no change is persisted

#### Scenario: Unchanged invalid legacy identifier does not block unrelated edit

- **GIVEN** a patient has an invalid legacy CPF or CNS value
- **WHEN** a user edits another profile field without changing that identifier
- **THEN** the unchanged legacy value does not by itself invalidate the form
- **AND** the unrelated valid profile change can be saved

### Requirement: Minimal duplicate-candidate disclosure

The system SHALL minimize the patient data disclosed by duplicate warnings.

#### Scenario: Warning omits raw personal identifiers

- **GIVEN** one or more duplicate candidates are shown during patient creation
- **WHEN** the warning is rendered
- **THEN** it may show name, birthday, current record number, deletion state,
  and evidence type
- **AND** it does not show raw CPF, CNS, address, or phone values
- **AND** existing authentication, authorization, and CSRF protections remain
  enforced

### Requirement: CNS terminology in patient forms

The system SHALL describe `healthcard_number` as CNS or Cartão Nacional de
Saúde in patient create and profile-update interfaces.

#### Scenario: Patient forms use CNS terminology

- **WHEN** an authorized user opens patient create or profile update
- **THEN** the health-card field is labeled as CNS or Cartão Nacional de Saúde
- **AND** no patient form describes it as a private health-plan card

### Requirement: Lifetime reservation of hospital record numbers

The system SHALL reserve every persisted hospital record number globally for
its entire retained history. The canonical comparison SHALL ignore leading and
trailing whitespace and letter case and SHALL include current, historical, and
soft-deleted patient records.

#### Scenario: Current record number owned by another patient is rejected

- **GIVEN** a current record number is assigned to one patient
- **WHEN** creation or record-change flow submits its canonical equivalent for
  another patient
- **THEN** the form is invalid
- **AND** no patient or record assignment is created or changed

#### Scenario: Historical record number cannot be reused

- **GIVEN** a record number exists as a historical assignment
- **WHEN** any patient creation or record-change flow submits its canonical
  equivalent
- **THEN** the form is invalid
- **AND** the historical assignment remains unchanged

#### Scenario: Same patient cannot reactivate an old number

- **GIVEN** a patient has a historical record number
- **WHEN** a user tries to assign its canonical equivalent again to that same
  patient
- **THEN** the form is invalid
- **AND** no repeated assignment is created

#### Scenario: Soft-deleted patient keeps record numbers reserved

- **GIVEN** a record number belongs to a soft-deleted patient
- **WHEN** another patient creation or record-change flow submits its canonical
  equivalent
- **THEN** the form is invalid
- **AND** the number remains reserved

#### Scenario: Record change is atomic on conflict

- **GIVEN** a patient has a current record number
- **WHEN** a requested new number conflicts or persistence fails
- **THEN** the previous assignment remains current
- **AND** the denormalized current record number remains unchanged
- **AND** no partial assignment is saved

#### Scenario: Concurrent assignment has one winner

- **GIVEN** two concurrent transactions submit the same available canonical
  record number
- **WHEN** both transactions attempt to persist it
- **THEN** exactly one transaction creates the assignment
- **AND** the other receives the known duplicate-record outcome
- **AND** the database contains exactly one assignment for that canonical key

### Requirement: Record-number history is immutable in ordinary flows

The system SHALL preserve persisted record-number assignments as audit history.
Ordinary application and admin flows SHALL create a new assignment for a
change and SHALL NOT mutate or delete the assigned number.

#### Scenario: Existing assignment number cannot be edited

- **GIVEN** a persisted record-number assignment
- **WHEN** a user or admin attempts to change its `record_number` value
- **THEN** the change is rejected
- **AND** the stored assignment remains unchanged

#### Scenario: Existing assignment cannot be deleted ordinarily

- **GIVEN** a persisted current or historical record-number assignment
- **WHEN** a user or admin invokes an ordinary delete action
- **THEN** deletion is rejected
- **AND** the number remains reserved

### Requirement: Safe activation of the global record constraint

The system SHALL add the global canonical record-number constraint only after a
non-mutating preflight confirms that no current or historical collisions
remain.

#### Scenario: Dirty database blocks constraint activation

- **GIVEN** two retained assignments share a canonical record-number key
- **WHEN** the constraint migration is applied
- **THEN** the migration aborts before changing the schema
- **AND** it reports aggregate collision counts without exposing record numbers
  or patient identifiers
- **AND** it does not merge, delete, or rewrite data

#### Scenario: Clean database activates constraint

- **GIVEN** all retained record-number assignments have distinct canonical keys
- **WHEN** the constraint migration is applied
- **THEN** the global PostgreSQL constraint is created
- **AND** existing assignments remain otherwise unchanged

### Requirement: Audited consolidation of record-number collisions

The system SHALL resolve canonical record-number collision groups only
through operator-recorded clinical decisions, with an auditable trail on
every touched row and a zero-collision verification before the lifetime
constraint may be applied.

#### Scenario: Discovery reports collision groups

- **GIVEN** retained `PatientRecordNumber` rows whose canonical
  `Lower(Trim(record_number))` values collide
- **WHEN** the consolidation discovery runs
- **THEN** it reports the number of collision groups and involved rows in
  aggregate
- **AND** per-record detail is shown only through an explicit
  operator-facing option
- **AND** patient names and birthdays may appear only under the explicit
  operator-console clinical flag, which also marks rows whose patients
  likely are the same person (normalized name plus birthday match)
- **AND** CPF and CNS never appear in command output, logs, or reports

#### Scenario: Same-person groups may be pre-drafted

- **GIVEN** the operator authorizes the matching criterion (normalized
  name plus birthday equality)
- **WHEN** a decision scaffold is emitted with pre-drafting enabled
- **THEN** groups whose every row matches the criterion receive drafted
  keep and void/renumber actions with a recorded rationale
- **AND** groups with any non-matching row keep their placeholders
- **AND** nothing is mutated; execution still requires the operator's
  reviewed plan

#### Scenario: Dry run mutates nothing

- **GIVEN** a validated decision plan
- **WHEN** the consolidation command runs without `--execute`
- **THEN** every planned operation is attempted inside a rolled-back
  transaction
- **AND** the database state is byte-identical afterwards

#### Scenario: Erroneous historical row is voided, not deleted

- **GIVEN** an operator decision that an assignment does not own the
  colliding number
- **WHEN** the consolidation executes on a non-current historical row
- **THEN** the row's `record_number` is rewritten to a derived marker
  that preserves the original value verbatim, carries the decision
  reference, and is unique per row
- **AND** `change_reason` records the clinical rationale plus the
  decision reference
- **AND** `updated_by` records the operator
- **AND** the row is never deleted

#### Scenario: Erroneous current number is renumbered through the append flow

- **GIVEN** an operator decision to renumber a patient whose current
  assignment holds the colliding number
- **WHEN** the consolidation executes
- **THEN** the patient receives the decided new number through the
  existing audited append flow, deactivating the old row
- **AND** the deactivated old row is then voided with the derived marker

#### Scenario: Execution verifies zero collisions before finishing

- **GIVEN** a decision plan covering every live collision group
- **WHEN** the consolidation executes with `--execute`
- **THEN** all operations and a discovery re-run happen in one
  transaction
- **AND** any error or any remaining collision group rolls back
  everything
- **AND** the lifetime constraint migration remains applicable only
  against databases whose aggregate collision count is zero
