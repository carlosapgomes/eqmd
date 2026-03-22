## MODIFIED Requirements

### Requirement: HistoryAndPhysical form MUST persist canonical event description

The system SHALL persist canonical event description for `HistoryAndPhysical`
when saving through `HistoryAndPhysicalForm`, without relying on view-level
manual assignment.

#### Scenario: Form save sets canonical description

- **WHEN** a valid `HistoryAndPhysicalForm` is saved
- **THEN** the resulting event description matches the canonical label for
  `HISTORY_AND_PHYSICAL_EVENT`

#### Scenario: Form save keeps audit ownership

- **WHEN** `HistoryAndPhysicalForm` receives `user` and saves a new instance
- **THEN** `created_by` and `updated_by` are set to the current user

### Requirement: HistoryAndPhysical form MUST avoid debug stdout side effects

The system SHALL NOT emit debug `print` output during normal form
initialization.

#### Scenario: Form initialization has no stdout debug output

- **WHEN** `HistoryAndPhysicalForm` is instantiated
- **THEN** no debug output is written to stdout

### Requirement: Essential HistoryAndPhysical CRUD flow MUST remain covered by tests

The project SHALL maintain automated coverage for essential create/update/delete
flow and current permission expectations.

#### Scenario: Create flow is covered

- **WHEN** a valid create request is submitted for accessible patient
- **THEN** tests confirm successful persistence and redirect behavior

#### Scenario: Permission denial path is covered

- **WHEN** a non-authorized user accesses protected update/delete path
- **THEN** tests confirm deny behavior under current rules
