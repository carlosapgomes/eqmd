## ADDED Requirements

### Requirement: ICD-10 code search

The system SHALL provide searchable autocomplete inputs for ICD-10 (CID) diagnosis codes in the APAC form, with one required main code and two optional secondary codes, each selected via search by code or description.

#### Scenario: Main ICD-10 code required

- **WHEN** the user submits the APAC form without a main ICD-10 code
- **THEN** the submission MUST be rejected with a validation error

#### Scenario: Secondary ICD-10 codes optional

- **WHEN** the user leaves secondary_icd or other_icd blank
- **THEN** the submission MUST be accepted without error

#### Scenario: ICD-10 search by code

- **WHEN** the user types an ICD-10 code (e.g., "A00.0") in any ICD-10 search field
- **THEN** the system MUST display matching ICD-10 codes in a dropdown list

#### Scenario: ICD-10 search by description

- **WHEN** the user types a description term (e.g., "cholera") in any ICD-10 search field
- **THEN** the system MUST display matching ICD-10 codes in a dropdown list

### Requirement: ICD-10 data capture

The system SHALL store UUID, code, and description for the ICD-10 codes in the APAC submission data using the following keys:

- main: `main_icd_id`, `main_icd_code`, `main_icd_description`
- secondary: `secondary_icd_id`, `secondary_icd_code`, `secondary_icd_description`
- other: `other_icd_id`, `other_icd_code`, `other_icd_description`

#### Scenario: ICD-10 values persisted

- **WHEN** the user selects a main ICD-10 code and one secondary ICD-10 code
- **THEN** the submission data MUST contain UUID, code, and description for the selected codes using the defined keys

### Requirement: ICD-10 display format

The system SHALL display search results showing both code and description for user reference, but the input field shall be populated only with the code after selection.

#### Scenario: ICD-10 search results display code and description

- **WHEN** the system displays ICD-10 search results in the dropdown
- **THEN** each result MUST show both the code and description (e.g., "A00.0 - Cólera devida a Vibrio cholerae 01, variedade cholerae")

#### Scenario: ICD-10 code displayed after selection

- **WHEN** the user selects an ICD-10 code from the dropdown
- **THEN** the search field MUST be updated to show only the code (e.g., "A00.0")
- **THEN** the hidden UUID field MUST be populated with the selected code's ID

### Requirement: ICD-10 validation from suggestions

The system SHALL require ICD-10 codes to be selected from the search suggestions and reject plain text input not matching a valid ICD-10 code.

#### Scenario: Invalid ICD-10 code rejected

- **WHEN** the user submits the APAC form with a plain text ICD-10 code that was not selected from suggestions
- **THEN** the submission MUST be rejected with a validation error

### Requirement: ICD-10 search debouncing

The system SHALL implement a 300ms debounce delay before performing ICD-10 search API calls to avoid excessive requests.

#### Scenario: Search debouncing

- **WHEN** the user types rapidly in an ICD-10 search field
- **THEN** the system MUST only send search requests after typing pauses for 300ms

### Requirement: ICD-10 search loading indicator

The system SHALL display a loading spinner in the search input while waiting for ICD-10 search API responses, using the same styling and behavior as the procedure search spinner for UI/UX consistency.

#### Scenario: Spinner shown during search

- **WHEN** a search request is in progress
- **THEN** a spinner MUST be displayed in the input group matching the procedure search spinner styling

### Requirement: PDF overlay mapping support for ICD-10

The system SHALL support rendering ICD-10 code and description values in APAC PDF overlays using the stored keys.

#### Scenario: Download APAC PDF with ICD-10

- **WHEN** a user downloads an APAC submission PDF
- **THEN** the overlay MUST render the stored ICD-10 codes and descriptions at the mapped field positions
