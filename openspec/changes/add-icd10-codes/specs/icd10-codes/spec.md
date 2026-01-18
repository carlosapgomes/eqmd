## ADDED Requirements

### Requirement: ICD-10 Code Storage

The system SHALL store ICD-10 (CID) codes with a unique code, description, active flag, and timestamps.

#### Scenario: Create ICD-10 code

- **WHEN** an ICD-10 code is created
- **THEN** the code is saved in uppercase and is uniquely identified by its code

### Requirement: ICD-10 Search API

The system SHALL provide authenticated API endpoints to search, list, and retrieve ICD-10 codes.

#### Scenario: Search ICD-10 codes

- **WHEN** a user requests /api/icd10/search/ with a valid query
- **THEN** matching active ICD-10 codes are returned with code and description

### Requirement: ICD-10 Import Command

The system SHALL import ICD-10 codes from CSV or JSON files with support for updates and deactivation of missing codes.

#### Scenario: Import ICD-10 codes from CSV

- **WHEN** the import command is run with a valid CSV file
- **THEN** ICD-10 codes are created or updated and search vectors are refreshed
