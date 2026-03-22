## ADDED Requirements

### Requirement: SimpleNote form MUST persist canonical event description
The system SHALL persist a canonical description for `SimpleNote` events when saving through `SimpleNoteForm`, without requiring manual description assignment in the view layer.

#### Scenario: Form save sets canonical description
- **WHEN** a user submits `SimpleNoteForm` with valid data
- **THEN** the saved `SimpleNote` has description equal to the canonical label for `SIMPLE_NOTE_EVENT`

#### Scenario: Form save keeps audit ownership
- **WHEN** `SimpleNoteForm` receives `user` and saves a new note
- **THEN** `created_by` and `updated_by` are set to the current user

### Requirement: SimpleNote form MUST avoid debug side effects
The system SHALL NOT emit console debug output during normal `SimpleNoteForm` initialization.

#### Scenario: Form initialization has no stdout debug print
- **WHEN** `SimpleNoteForm` is instantiated in normal execution
- **THEN** it does not print debug data to stdout

### Requirement: SimpleNote essential CRUD flow MUST be covered by tests
The project SHALL maintain automated tests for the essential `simplenotes` create/update/delete flow and expected permission gates.

#### Scenario: Create flow is covered
- **WHEN** a valid create request is submitted for an accessible patient
- **THEN** a test verifies the note is persisted and visible in expected redirect flow

#### Scenario: Edit/delete permission path is covered
- **WHEN** a user interacts with update/delete endpoints
- **THEN** tests verify expected allowed/denied behavior under current permission rules
