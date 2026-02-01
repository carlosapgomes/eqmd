## ADDED Requirements

### Requirement: Discharge report PDF action availability
The discharge report detail view and timeline card SHALL provide a PDF download action that uses the standard PDF download behavior.

#### Scenario: Detail view shows PDF action
- **WHEN** a user views a discharge report detail page
- **THEN** the UI provides a PDF download action for that report

#### Scenario: Timeline card shows PDF action
- **WHEN** a discharge report appears in the patient timeline
- **THEN** the UI provides a PDF download action for that report

### Requirement: Discharge report delete action permissions
The system SHALL allow deletion of finalized discharge reports within the standard event deletion window for the creator or users with `events.delete_event` permission, and SHALL allow draft deletion for the creator or users with `events.delete_event` permission.

#### Scenario: Final report deletion within window
- **WHEN** the report is finalized and within the allowed deletion window
- **THEN** the creator or a user with `events.delete_event` can delete it

#### Scenario: Draft report deletion
- **WHEN** the report is a draft
- **THEN** the creator or a user with `events.delete_event` can delete it

### Requirement: Discharge report delete action availability
The discharge report timeline card SHALL display a delete action only when the current user is permitted to delete the report.

#### Scenario: Timeline delete action is gated
- **WHEN** the current user lacks delete permission for the report
- **THEN** the delete action is not shown on the timeline card

