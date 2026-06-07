## ADDED Requirements

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
