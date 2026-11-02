# Patient tag audit

## Purpose

Provide reliable, attributable tag history and current tag context on patient
surfaces while respecting present-day team visibility for historical events.

## ADDED Requirements

### Requirement: Atomic patient assignment audit

The system SHALL commit each patient-tag addition/removal and its attributable
timeline event atomically, including administrative and bulk entry points. Failed
or denied operations SHALL NOT leave a changed association or misleading event.
No justification SHALL be mandatory.

#### Scenario: Event write fails after an attempted addition

- **WHEN** event persistence fails during an assignment operation
- **THEN** no patient association remains from that operation
- **AND** the request reports failure

#### Scenario: Administrative assignment is also audited

- **WHEN** an administrator assigns or removes a patient tag through Django Admin
- **THEN** the corresponding patient timeline action records actor and time
- **AND** bulk paths cannot bypass per-tag authorization or atomicity

### Requirement: Stable catalogue identity in timeline events

The system SHALL associate new tag events with stable catalogue identities and
retain action-time snapshots and team attribution. Removing an assignment,
renaming a tag, transferring responsibility or archiving SHALL NOT destroy those
references or historical content.

#### Scenario: Renaming does not detach an older event

- **WHEN** a catalogue tag is renamed after its assignment event was recorded
- **THEN** the event remains linked to the same tag identity
- **AND** its authorized historical presentation retains action-time context

#### Scenario: Unresolved legacy event is not guessed

- **WHEN** a legacy snapshot cannot be unambiguously associated with a tag
- **THEN** its stored history remains intact
- **AND** non-admin output is generic rather than exposing unresolved metadata

### Requirement: Restricted timeline actions are generically visible

The system SHALL show outsiders that a restricted tag was added or removed,
including actor, team abbreviation and timestamp, without exposing tag name,
color, description, notes or identifiers. Team members and administrators SHALL
receive the authorized detailed presentation.

#### Scenario: Outsider sees a restricted change

- **WHEN** an outsider views another team's restricted-tag addition
- **THEN** the timeline shows a generic restricted-tag action, actor, team and time
- **AND** restricted metadata is absent from HTML, attributes, JSON and print output

### Requirement: Current visibility governs historical events

The system SHALL reevaluate historical presentation using current tag visibility
and current memberships on every request. Reclassifying a public tag as restricted
SHALL also protect its old descriptions and snapshots.

#### Scenario: Public-to-restricted reclassification protects old output

- **GIVEN** an old event originally contained a public tag's name
- **WHEN** the tag becomes restricted and an outsider requests that event
- **THEN** all response variants use the generic restricted presentation
- **AND** old cached payloads do not bypass the restriction

### Requirement: Mixed bulk events redact each hidden classification

The system SHALL present bulk actions with details for authorized tags and generic
actions for restricted tags outside the viewer's teams. Stored concatenated names
SHALL NOT bypass per-tag presentation rules.

#### Scenario: One bulk event covers visible and hidden tags

- **WHEN** a viewer can see only some of the tags removed in a bulk event
- **THEN** visible entries are detailed and hidden entries are generic
- **AND** hidden names and IDs are absent from summaries and API responses

### Requirement: Current tags are visible on the patient timeline

The system SHALL show current requester-visible patient tags near the timeline
header on desktop and mobile. Current status SHALL be distinct from historical
operations; inactive/archived associations SHALL retain explicit status labels.

#### Scenario: Patient with current and removed tags

- **WHEN** a user opens the timeline of a patient with one current tag and one
  previously removed tag
- **THEN** the header shows only the current visible association
- **AND** historical removal remains represented below

### Requirement: Catalogue lifecycle and ownership audit

The system SHALL record catalogue creation/edits, activation, deactivation,
archival, restoration, responsibility transfer and visibility changes with actor
and timestamp. Latest-action fields SHALL supplement, not replace, full history.
Original creator SHALL remain immutable and reasons SHALL be optional.

#### Scenario: Multiple lifecycle cycles retain every actor

- **WHEN** different authorized actors deactivate, reactivate, archive and restore
  the same tag
- **THEN** each transition is retained in order with actor and time
- **AND** latest-action fields describe the corresponding most recent actions

### Requirement: Tag audit is immutable in ordinary patient workflows

The system SHALL NOT offer ordinary clinical edit/delete operations for tag audit
events. Correcting an assignment SHALL create a new opposing operation rather
than modifying or hiding the earlier event.

#### Scenario: Correct an accidental addition

- **WHEN** an authorized user removes a mistakenly added patient tag
- **THEN** the original addition remains and a removal event is appended
- **AND** knowing the audit-event ID does not allow editing/deleting its history
