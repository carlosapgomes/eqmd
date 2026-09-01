# Patients Specification Delta

## ADDED Requirements

### Requirement: Patient profile update behavior

The system SHALL preserve inpatient location (`ward` and `bed`) when updating
only personal/contact information in the patient update flow.

#### Scenario: Update personal data for admitted patient

- **GIVEN** a patient with active admission and existing `ward`/`bed`
- **WHEN** a user updates personal/contact fields in patient update
- **THEN** the patient personal data is updated
- **AND** `ward` and `bed` remain unchanged
- **AND** the active admission remains active

### Requirement: Admission denormalization consistency

The system SHALL synchronize both `ward` and `bed` from active admission into
patient denormalized fields.

#### Scenario: Active admission saves patient location

- **GIVEN** an active admission with `ward` and bed data
- **WHEN** the admission save signal updates denormalized patient fields
- **THEN** patient `ward` equals admission `ward`
- **AND** patient `bed` equals admission bed (`final_bed` or `initial_bed`)
