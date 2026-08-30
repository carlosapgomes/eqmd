# Patients Specification Delta

## ADDED Requirements

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
