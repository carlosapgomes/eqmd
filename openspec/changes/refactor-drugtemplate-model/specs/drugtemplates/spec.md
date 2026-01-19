## MODIFIED Requirements

### Requirement: Drug Template Data Structure

The system SHALL store medication templates with separate pharmaceutical information fields instead of combined presentation data to support structured medication import and better data organization.

#### Scenario: User creates custom drug template

- **WHEN** medical staff creates a custom drug template
- **THEN** system requires concentration, pharmaceutical form, and usage instructions
- **AND** template is marked as user-created (not imported)

#### Scenario: System imports medication from external source

- **WHEN** system imports medication data from CSV or external source
- **THEN** system stores concentration and pharmaceutical form separately
- **AND** usage instructions are optional for imported medications
- **AND** template is marked as imported with source tracking

#### Scenario: Display drug template information

- **WHEN** user views a drug template
- **THEN** system displays concentration and pharmaceutical form separately
- **AND** maintains backward compatibility by showing combined presentation when needed

## ADDED Requirements

### Requirement: Medication Data Import

The system SHALL support importing structured medication data from external sources with proper data validation and duplicate handling.

#### Scenario: Import CSV medication data

- **WHEN** administrator runs medication import command with valid CSV file
- **THEN** system parses medication records with Brazilian common names, concentrations, and pharmaceutical forms
- **AND** creates DrugTemplate records marked as imported
- **AND** assigns system user as creator for imported medications
- **AND** reports import statistics and any errors

#### Scenario: Handle duplicate medications during import

- **WHEN** import encounters medication with same name and concentration as existing record
- **THEN** system skips duplicate and logs warning
- **AND** continues processing remaining medications
- **AND** provides summary of skipped duplicates in final report

#### Scenario: Validate imported medication data

- **WHEN** processing each medication during import
- **THEN** system validates required fields (name, concentration, pharmaceutical form)
- **AND** sanitizes and normalizes field values
- **AND** rejects invalid records with detailed error logging

### Requirement: Drug Template Source Tracking

The system SHALL distinguish between user-created templates and imported reference data for proper management and display.

#### Scenario: Filter drug templates by source

- **WHEN** medical staff views drug template list
- **THEN** system allows filtering between user-created and imported templates
- **AND** displays import source information for imported templates
- **AND** shows appropriate edit/delete permissions based on template source

#### Scenario: Prevent modification of imported reference data

- **WHEN** user attempts to edit imported drug template
- **THEN** system prevents modification of core imported fields (name, concentration, form)
- **AND** allows adding user-specific usage instructions if needed
- **AND** maintains data integrity of reference medication information

