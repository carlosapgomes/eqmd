## ADDED Requirements

### Requirement: Procedure search naming convention

The system SHALL enable procedure search in hospital PDF forms when the field configuration includes both `procedure_code` and `procedure_description`.

#### Scenario: Naming convention enabled
- **WHEN** a PDF form template includes fields named `procedure_code` and `procedure_description`
- **THEN** the form MUST render a combined procedure search input

#### Scenario: Naming convention absent
- **WHEN** a PDF form template does not include both required field names
- **THEN** the form MUST render the fields normally without procedure search behavior

### Requirement: Procedure search by code or description

The system SHALL search procedures by code or description using the procedures search API and display matching results in a dropdown list.

#### Scenario: Search by code
- **WHEN** the user types a procedure code fragment into the combined search input
- **THEN** the system MUST display matching procedures in the dropdown list

#### Scenario: Search by description
- **WHEN** the user types a procedure description fragment into the combined search input
- **THEN** the system MUST display matching procedures in the dropdown list

### Requirement: Procedure selection populates fields

The system SHALL populate `procedure_code` and `procedure_description` from the selected procedure and prevent direct editing of those fields.

#### Scenario: Selection populates code and description
- **WHEN** the user selects a procedure from the dropdown
- **THEN** `procedure_code` MUST be set to the selected code
- **THEN** `procedure_description` MUST be set to the selected description

#### Scenario: Fields are not directly editable
- **WHEN** the procedure search feature is enabled
- **THEN** users MUST NOT be able to directly edit `procedure_code` or `procedure_description`

### Requirement: Procedure selection validation

The system SHALL enforce selection from valid procedures and reject free-text inputs not matched to a MedicalProcedure.

#### Scenario: Invalid procedure rejected
- **WHEN** the user submits the form with a procedure code/description that does not match a MedicalProcedure
- **THEN** the submission MUST be rejected with a validation error

#### Scenario: Required procedure missing
- **WHEN** the procedure fields are required and no procedure has been selected
- **THEN** the submission MUST be rejected with a validation error

### Requirement: Procedure search UX parity with APAC

The system SHALL match the APAC procedure search UX behavior for debounce and loading indicators.

#### Scenario: Search debouncing
- **WHEN** the user types rapidly in the procedure search input
- **THEN** the system MUST delay API requests until typing pauses for 300ms

#### Scenario: Spinner shown during search
- **WHEN** a search request is in progress
- **THEN** a loading spinner MUST be displayed in the input group

### Requirement: Procedure data capture

The system SHALL store only `procedure_code` and `procedure_description` in the PDF form submission data.

#### Scenario: Stored fields contain code and description only
- **WHEN** the user submits the form after selecting a procedure
- **THEN** the submission data MUST include `procedure_code` and `procedure_description`
- **THEN** the submission data MUST NOT include a procedure UUID
