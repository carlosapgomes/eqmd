## ADDED Requirements

### Requirement: APAC procedure slots
The system SHALL provide one required main procedure and five optional secondary procedures in the APAC form, each selected via search by code or description.

#### Scenario: Main procedure required
- **WHEN** the user submits the APAC form without a main procedure
- **THEN** the submission MUST be rejected with a validation error

#### Scenario: Secondary procedures optional
- **WHEN** the user leaves any secondary procedure blank
- **THEN** the submission MUST be accepted without error

### Requirement: Procedure data capture
The system SHALL store UUID, code, and description for the main and secondary procedures in the APAC submission data using the following keys:
- main: `main_procedure_id`, `main_procedure_code`, `main_procedure_description`
- secondary 1..5: `secondary_procedure_{n}_id`, `secondary_procedure_{n}_code`, `secondary_procedure_{n}_description`

#### Scenario: Procedure values persisted
- **WHEN** the user selects a main procedure and two secondary procedures
- **THEN** the submission data MUST contain UUID, code, and description for the selected procedures using the defined keys

### Requirement: Duplicate prevention
The system SHALL reject duplicate procedure selections across the main and secondary slots.

#### Scenario: Duplicate procedure selection
- **WHEN** a procedure is selected more than once across main and secondary slots
- **THEN** the submission MUST be rejected with a validation error

### Requirement: PDF overlay mapping support
The system SHALL support rendering procedure code and description values in APAC PDF overlays using the stored keys.

#### Scenario: Download APAC PDF
- **WHEN** a user downloads an APAC submission PDF
- **THEN** the overlay MUST render the stored procedure codes and descriptions at the mapped field positions
