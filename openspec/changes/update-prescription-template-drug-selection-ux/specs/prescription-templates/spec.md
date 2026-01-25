## ADDED Requirements

### Requirement: Drug Name Autocomplete in Prescription Templates

The system SHALL provide autocomplete search for drug names when creating or editing prescription templates.

#### Scenario: Search displays matching drugs

- **WHEN** a user types at least 2 characters in the drug name field
- **THEN** a dropdown displays matching drug templates
- **AND** results show drug name, presentation, and creator information
- **AND** search is case-insensitive and accent-insensitive

#### Scenario: Selecting drug populates fields

- **WHEN** a user selects a drug from the autocomplete dropdown
- **THEN** the drug name, presentation, usage instructions, and quantity fields are auto-populated
- **AND** a search spinner is shown during the search
- **AND** the quantity field is focused after population

### Requirement: Consistent Drug Selection UX

The system SHALL provide the same drug selection user experience for prescription templates and outpatient prescriptions.

#### Scenario: Shared components

- **WHEN** a user creates or edits a prescription template
- **THEN** the drug selection UI uses the same autocomplete widget as outpatient prescriptions
- **AND** the same formset management JavaScript is used
- **AND** the same styling is applied

#### Scenario: Manual entry remains available

- **WHEN** a user does not select from autocomplete dropdown
- **THEN** they can still manually type drug name and other fields
- **AND** validation works the same as outpatient prescriptions
