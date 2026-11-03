# Development quality gates — delta

## ADDED Requirements

### Requirement: Sample data seeds are skipped in test databases

The system SHALL keep sample/bootstrap data migrations from
populating test databases, so that tests create the rows they need
explicitly.

#### Scenario: Test database contains no sample specialties

- **WHEN** a test database is created with the project test settings
- **THEN** no sample `MedicalSpecialty` rows from the bootstrap
  migration exist in it
- **AND** a canary test fails if any seeded sample row is present

#### Scenario: Non-test installs keep bootstrap behavior

- **WHEN** a fresh non-test environment runs migrations
- **THEN** the sample specialty seed still populates (default on),
  unless the environment explicitly disables it via settings
