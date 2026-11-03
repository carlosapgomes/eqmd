# Patients Specification Delta

## ADDED Requirements

### Requirement: Temporary record generation on patient creation

The system SHALL allow creating a patient without a definitive hospital
record number. When the temporary option is selected, the system SHALL
generate the record number server-side with the reserved `TMP-` prefix,
SHALL require a reason, and SHALL record that reason in the record-number
audit trail. The generated number SHALL be unique under the lifetime
record-number constraint. The definitive-number creation flow SHALL remain
unchanged.

#### Scenario: Create patient with temporary record

- **WHEN** a user creates a patient selecting the temporary option with a
  reason
- **THEN** the patient's current record number starts with `TMP-`
- **AND** the current record-number row stores the informed reason in its
  change-reason audit field

#### Scenario: Temporary creation without reason is rejected

- **WHEN** a user submits the temporary option with an empty reason
- **THEN** the form is rejected with a validation error on the reason field

#### Scenario: Definitive creation flow is unchanged

- **WHEN** a user creates a patient typing an initial record number without
  the temporary option
- **THEN** behavior is identical to the pre-existing flow, including the
  default initial change reason

### Requirement: Temporary record prefix is reserved for generated records

The system SHALL reserve the `TMP-` prefix for system-generated temporary
numbers. Manually typed values starting with `TMP-` SHALL be rejected at
every manual write door (creation form, record-number update forms, and
the managed record-number update method). Regularization of a temporary
number to a definitive number SHALL reuse the existing record-number
change flow and SHALL preserve the temporary row in history.

#### Scenario: Manually typed temporary prefix is rejected

- **WHEN** a user types a number starting with `TMP-` in the creation form
  or in any record-number update form
- **THEN** the value is rejected with a message explaining the prefix is
  reserved for generated temporary records

#### Scenario: Managed update cannot introduce a temporary prefix

- **WHEN** the managed record-number update method is called with a value
  starting with `TMP-`
- **THEN** it raises a validation error before any write

#### Scenario: Regularization preserves history

- **WHEN** a patient with a generated temporary number is updated to a
  definitive number through the existing change flow
- **THEN** the definitive number becomes the current row
- **AND** the temporary row is retained with `is_current` false
- **AND** the new row records the temporary number as its previous number

### Requirement: Temporary record pending dashboard

The system SHALL provide a staff-only dashboard listing patients whose
current record number is temporary, ordered oldest first, showing the
temporary number, pending age, informed reason, and creator, plus an
aggregate count of pending temporaries by creator. Patients without a
temporary current record number SHALL be excluded.

#### Scenario: Staff lists pending temporary records

- **WHEN** a staff user opens the pending dashboard and temporary records
  exist
- **THEN** the dashboard lists them oldest first with number, pending age,
  reason, and creator
- **AND** shows the aggregate count by creator

#### Scenario: Non-staff user is denied

- **WHEN** an authenticated non-staff user requests the dashboard
- **THEN** access is denied

#### Scenario: Definitive patients are excluded

- **WHEN** the dashboard is rendered
- **THEN** only patients whose current record number starts with the
  temporary prefix are listed
