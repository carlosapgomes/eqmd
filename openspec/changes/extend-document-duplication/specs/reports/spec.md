# Reports — delta

## ADDED Requirements

### Requirement: Report duplication

The system SHALL provide a duplicate action that creates a new report
from an existing report of the same patient, pre-filling the editable
creation form with the source title and content.

#### Scenario: Duplicate form pre-filled from source

- **WHEN** an authorized user opens the duplicate action for a report
- **THEN** the system renders the report creation form with the source
  report's title and content, and today's document date

#### Scenario: Duplicate creates an independent copy

- **WHEN** an authorized user submits the duplicate form
- **THEN** the system creates a new report for the same patient,
  attributed to the submitting user, with a fresh event datetime
- **AND** the new report is editable within its own 24-hour window
- **AND** the system redirects to the patient timeline

#### Scenario: Source report unchanged

- **WHEN** a duplicate is created
- **THEN** the source report's content, title, author, and event
  datetime remain unchanged

#### Scenario: Template provenance not copied

- **WHEN** the source report was created from a template
- **AND** a duplicate is created from it
- **THEN** the duplicate is saved without a template association and
  its content is the source's stored content (no template re-render)

#### Scenario: Unauthorized duplication denied

- **WHEN** a user without `events.add_event` or without access to the
  patient opens or submits the duplicate action
- **THEN** the system denies the request

#### Scenario: Duplicate action on the timeline card

- **WHEN** a user with `events.add_event` views a report event on the
  patient timeline
- **THEN** the report card exposes a duplicate action linking to the
  duplicate form
- **AND** users without the permission do not see the action
