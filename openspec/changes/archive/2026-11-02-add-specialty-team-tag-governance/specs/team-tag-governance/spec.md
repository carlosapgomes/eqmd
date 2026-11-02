# Team tag governance

## Purpose

Govern the tag catalogue and patient assignments for specialty-based assistential
teams, separating administration, team ownership and visibility without limiting
which patients clinical users can access.

## ADDED Requirements

### Requirement: Independent tag origin and visibility

The system SHALL classify each tag independently as system/custom and
public/restricted. A restricted tag SHALL belong to exactly one specialty team.
Each tag SHALL retain its stable identity, creator and namespace.

#### Scenario: Administrator creates classifications

- **WHEN** an authorized administrator creates a system or custom tag
- **THEN** the administrator can choose public or restricted visibility
- **AND** restricted visibility requires exactly one specialty team

#### Scenario: Preserve existing catalogue

- **WHEN** existing catalogue data is upgraded
- **THEN** IDs, names, patient associations and history are retained
- **AND** existing tags become public/custom without inferred team ownership

### Requirement: Reserved names within namespaces

The system SHALL reserve trimmed case-insensitive tag names within each specialty
namespace or the global namespace across active, inactive and archived states.
Display labels SHALL identify specialty namespaces using their abbreviations.

#### Scenario: Same label in different teams

- **WHEN** two teams create a tag named Reavaliar in their own namespaces
- **THEN** both definitions can exist and selectors distinguish their team siglas

#### Scenario: Archived name cannot be reused

- **GIVEN** CIRGER has an archived Reavaliar tag
- **WHEN** someone creates another Reavaliar in CIRGER with case/space variations
- **THEN** creation is rejected without cloning or replacing the archived identity

### Requirement: Public principal tag for each team

The system SHALL allow an administrator to configure at most one principal public
tag per team in that team's namespace. The principal tag SHALL remain publicly
readable/filterable while assignment/removal requires team membership or
administrator authority. Existing unmapped teams SHALL not receive inferred tags.

#### Scenario: Outsider can filter but cannot assign principal tag

- **WHEN** an authorized clinical user outside CIRGER selects its principal tag
- **THEN** the user can filter patients by it
- **AND** attempts to add or remove it from a patient are denied

#### Scenario: Principal tag becomes unavailable

- **WHEN** an administrator deactivates or archives a team's principal tag
- **THEN** its identity, mapping and existing assignments remain preserved
- **AND** automatic filtering omits it with a warning and creates no replacement

### Requirement: Administrator catalogue control

The system SHALL provide authorized administrators with all catalogue records and
administrative lifecycle, classification, namespace and responsibility operations
through Django Admin. Administrative tag privileges SHALL not be inferred from
staff status alone.

#### Scenario: Administrator handles another leader's restricted tag

- **WHEN** an authorized administrator opens a leader-created restricted tag
- **THEN** the administrator can edit, deactivate, reactivate or archive it
- **AND** the operation records its actor and time

#### Scenario: Ordinary staff cannot bypass tag governance

- **WHEN** staff without the relevant administrative permissions attempt a
  catalogue mutation or a direct protected action
- **THEN** it is denied even if a control or URL is known

### Requirement: Responsible leader self-service

The system SHALL provide leaders a team tag page. An active leader SHALL create
only custom restricted tags in their own team and edit/deactivate/reactivate only
tags for which they are the current responsible leader. Leaders SHALL NOT change
origin, visibility, namespace, responsibility or archival state.

#### Scenario: Leader creates a private team tag

- **WHEN** a current team leader creates a tag through the team page
- **THEN** the tag is custom/restricted in that team with the leader responsible
- **AND** forged administrative fields are rejected or server-controlled

#### Scenario: Other leader and former leader are denied

- **WHEN** another leader without responsibility or a revoked leader submits an
  edit/deactivate/reactivate request
- **THEN** the operation is denied with no catalogue or audit side effect

### Requirement: Transfer responsibility without changing creator

The system SHALL allow an administrator to transfer a restricted tag to another
current leader of the same team. The original creator SHALL remain unchanged.
Management rights SHALL follow current responsibility and membership/leadership.

#### Scenario: New responsible leader takes over

- **WHEN** an administrator transfers responsibility from leader A to leader B
- **THEN** B gains management rights and A loses them
- **AND** the creator and transfer history remain preserved

### Requirement: Active inactive and archived lifecycle

The system SHALL distinguish active, inactive and archived tags. Inactivation
SHALL be reversible by the authorized responsible leader or administrator.
Archival SHALL be administrator-only soft-delete. Neither operation SHALL remove
patient associations, preferences, principal mapping or audit history.

#### Scenario: Inactive tag retains its associations

- **WHEN** an authorized leader deactivates a tag
- **THEN** existing associations remain visible to authorized viewers as inactive
- **AND** new assignments are denied

#### Scenario: Archive bypass is denied

- **WHEN** a leader attempts archival or an administrative bulk action bypass
- **THEN** it is denied and all data remain unchanged

### Requirement: Administrator restoration preserves tag identity

The system SHALL allow only administrators to restore archived tags. Restoration
SHALL return the same identity inactive, with the same namespace, creator,
associations and history, and SHALL require a separate activation operation.

#### Scenario: Restore is not recreation or activation

- **WHEN** an administrator restores an archived tag
- **THEN** its original ID is retained and no new assignments are created
- **AND** it remains ineligible for new assignment and automatic filtering

### Requirement: Request-time restricted visibility

The system SHALL expose restricted metadata only to administrators and current
members of its active team, using the union of all active memberships rather than
only the selected specialty. Names, colors, notes, identifiers and descriptions
SHALL NOT leak through selectors, HTML, JSON, counters, errors or shared caches.

#### Scenario: Multi-team user sees both teams

- **GIVEN** a user belongs to CIRGER and CARDIO and selects CARDIO as current
- **WHEN** the user views tags
- **THEN** visible tags include both teams' restricted tags plus public tags

#### Scenario: Revocation applies to an existing session and warm cache

- **WHEN** membership is revoked after a page or cache was populated
- **THEN** the next response omits that team's restricted metadata everywhere
- **AND** knowing a tag ID does not permit reading or filtering by it

### Requirement: Policy-checked patient tag assignments

The system SHALL retain clinical patient-access/mutation gates and additionally
check each tag. Restricted tags require their team membership; principal tags
require their team membership or administrator override. Any eligible member
need not be a leader. Only active tags can be newly assigned.

#### Scenario: Member applies a restricted tag

- **WHEN** a member with clinical mutation permission assigns an active team tag
- **THEN** exactly one patient association is created
- **AND** a duplicate attempt does not create a second association

#### Scenario: Historical association can be removed by authorized actor

- **WHEN** an actor satisfying the tag's per-team and clinical permissions removes
  an inactive or archived tag from a patient
- **THEN** removal is allowed and audited without deleting catalogue history

#### Scenario: Bulk removal preserves other teams' tags

- **WHEN** a user requests bulk removal of their manageable patient tags
- **THEN** only the authorized set is removed
- **AND** hidden or otherwise unauthorized associations are preserved

### Requirement: Patient tags survive clinical transitions

The system SHALL allow multiple teams' tags on the same patient. Assignments
SHALL persist across admission, discharge and specialty switching until explicitly
removed by an authorized actor.

#### Scenario: Discharge does not clear team classifications

- **GIVEN** a patient carries tags from two teams
- **WHEN** the patient is discharged
- **THEN** both teams' tag associations remain unchanged

### Requirement: Searchable historical catalogue

The system SHALL offer a searchable selector showing active visible tags by
default and an explicit Incluir tags antigas option for visible inactive/archived
tags. Historical states SHALL be labelled and selectable for manual filtering,
not new assignment or automatic preferences.

#### Scenario: Find an archived tag without cluttering normal choices

- **WHEN** a user searches with historical tags enabled
- **THEN** matching visible inactive/archived tags appear with state and namespace
- **AND** default active-only selection does not list them
