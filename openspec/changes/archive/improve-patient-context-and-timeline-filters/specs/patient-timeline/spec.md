## ADDED Requirements

### Requirement: Patient timeline SHALL surface patient context before the event list

The patient timeline SHALL display patient context above the event list so users
can orient themselves without leaving the page.

#### Scenario: Timeline exposes patient context above events

- **WHEN** an authorized user opens the patient timeline
- **THEN** the page shows patient context above the timeline events

### Requirement: Timeline filters SHALL be available on demand through offcanvas UI

The patient timeline SHALL make filters available through an on-demand offcanvas
interaction rather than a permanently visible desktop sidebar.

#### Scenario: Desktop timeline uses offcanvas filters instead of fixed sidebar

- **WHEN** a user opens the patient timeline on a desktop viewport after phase 2
- **THEN** the page shows a filter trigger that opens an offcanvas panel
- **AND** the page does not render the old fixed desktop filter sidebar

#### Scenario: Existing filter semantics are preserved

- **WHEN** a user applies filters through the timeline offcanvas
- **THEN** the timeline uses the same querystring-based filtering behavior and
  result set semantics as before the offcanvas migration

### Requirement: Timeline SHALL indicate when filters are active

The patient timeline SHALL indicate when any timeline filters are active so the
user can quickly understand that the current event list is filtered.

#### Scenario: Active filters update the trigger state

- **WHEN** the timeline request contains active filter parameters
- **THEN** the filter trigger shows an active state indicator
- **AND** the clear-filters flow remains available
