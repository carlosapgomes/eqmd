# Patients Specification Delta

## ADDED Requirements

### Requirement: Record numbers must contain at least one alphanumeric character

The system SHALL reject record numbers that contain no letter or digit
(placeholder-only values such as `---`), at form validation, at the
managed renumber flow, and at consolidation plan validation.

#### Scenario: Form rejects placeholder-only record number

- **WHEN** a user submits a record number containing only punctuation
  (for example `---`) through any patient or record-number form
- **THEN** validation fails with a clear message stating the number
  must contain at least one letter or digit

#### Scenario: Managed renumber flow rejects placeholder-only value

- **WHEN** `update_current_record_number` is called with a
  placeholder-only value from any programmatic path
- **THEN** it raises a `ValidationError` before writing anything

#### Scenario: Consolidation plan validation rejects junk renumber target

- **WHEN** a consolidation plan contains a `renumber` action whose
  `new_record_number` contains no letter or digit
- **THEN** plan validation fails with a precise message and execution
  is refused
