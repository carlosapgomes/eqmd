## ADDED Requirements

### Requirement: Discharge import closes active admission
When a discharge report is imported, the system SHALL close any active admission for the patient and update the patient status and denormalized fields accordingly.

#### Scenario: Discharge report for patient with active admission
- **WHEN** a discharge report is imported for a patient who has an active admission
- **THEN** the active admission is closed with the discharge date from the report
- **THEN** the patient status is updated to outpatient (or deceased if applicable)

#### Scenario: Discharge report for patient without active admission
- **WHEN** a discharge report is imported for a patient who has no active admission
- **THEN** the discharge report is stored and no active admission is modified

### Requirement: Firebase status sync reconciles existing patients
The nightly Firebase sync SHALL reconcile status changes for existing patients and keep admissions consistent with Firebase status.

#### Scenario: Firebase marks patient as outpatient or deceased
- **WHEN** an existing patient in the system is marked outpatient or deceased in Firebase
- **THEN** any active admission is closed
- **THEN** the patient status is updated to match Firebase

#### Scenario: Firebase marks patient as inpatient/emergency without active admission
- **WHEN** an existing patient is marked inpatient or emergency in Firebase and has no active admission
- **THEN** the system creates an active admission using lastAdmissionDate when provided

#### Scenario: Firebase status unchanged
- **WHEN** Firebase status for an existing patient matches the current system status
- **THEN** no status or admission changes are applied

### Requirement: Reconciliation is idempotent
Status reconciliation SHALL be safe to run repeatedly without creating duplicate closures or admissions.

#### Scenario: Repeated nightly runs with no changes
- **WHEN** the sync runs multiple times with unchanged Firebase data
- **THEN** no duplicate admissions or discharges are created

### Requirement: Reconciliation actions are reported
The system SHALL report how many patients were reconciled and how many admissions were closed or created in each run.

#### Scenario: Sync completion summary
- **WHEN** the import/sync finishes
- **THEN** a summary includes counts for reconciled patients and admission updates
