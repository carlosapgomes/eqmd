# outpatientprescriptions Specification

## Purpose

Rules for duplicating an outpatient prescription into a new editable
draft ("duplicate and edit"), synced from change
`2026-10-12-duplicate-outpatient-prescription`.

## Requirements

### Requirement: Duplicate outpatient prescription into a new draft

The system SHALL provide a duplicate action that creates a new draft
`OutpatientPrescription` for the same patient, copying only the
listed header fields (patient, instructions) and the items as
independent rows.

#### Scenario: Duplicate finalized prescription

- **WHEN** an authorized user submits the duplicate action on a
  finalized prescription
- **THEN** a new draft is created with the configured-local date,
  copied instructions and items, and the user is redirected to edit
  the copy

#### Scenario: Copy is independent from source

- **WHEN** the duplicated draft is edited afterwards
- **THEN** the source prescription and its items remain unchanged

#### Scenario: Duplication does not inflate template statistics

- **WHEN** items are cloned
- **THEN** no `DrugTemplate.usage_count` is incremented

### Requirement: Duplicate action permissions

The system SHALL require `events.add_event` and patient access on the
source prescription. Users without access SHALL be denied, and GET
SHALL be rejected.

#### Scenario: Unauthorized duplication denied

- **WHEN** a user without patient access or without `add_event`
  submits the duplicate action
- **THEN** access is denied and nothing is created

### Requirement: Duplicate action availability

The prescription detail view SHALL show a "Duplicar" control exactly
when the current user holds `events.add_event` (patient access is
already required to view the page).

#### Scenario: Button shown to authorized user

- **WHEN** a user with `add_event` views a prescription detail page
- **THEN** the duplicate control is visible

#### Scenario: Button hidden without permission

- **WHEN** a user without `add_event` views the page
- **THEN** the duplicate control is not visible
