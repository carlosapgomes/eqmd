# Patient tag filtering

## Purpose

Make patient discovery consistent across list and ward map with visible multi-tag
filters, specialty-specific defaults and explicit user overrides that do not
change patient authorization.

## ADDED Requirements

### Requirement: Searchable multi-tag ANY and ALL filtering

The system SHALL support selecting multiple visible tags with ANY or ALL matching
on both patient list and map. ANY SHALL match at least one selected identity;
ALL SHALL require every selected identity. Other search/status/ward predicates
SHALL remain conjunctive and patient results SHALL be distinct.

#### Scenario: ANY and ALL yield different results

- **GIVEN** patient A has both selected tags and patient B has only the first
- **WHEN** the user changes matching from ANY to ALL
- **THEN** ANY returns A and B whereas ALL returns only A within page eligibility

### Requirement: Per-user specialty preference identity

The system SHALL persist selected tags and ANY/ALL mode separately for each
user-specialty pair and share that preference between list and map. The user
SHALL be able to omit the principal tag. An explicitly saved empty selection
SHALL be distinct from having no preference yet.

#### Scenario: Different teams retain independent preferences

- **WHEN** a user saves different tags/modes for CIRGER and CARDIO
- **THEN** each specialty retains its own choice
- **AND** list and map use the choice for the current specialty

#### Scenario: Saved empty selection suppresses principal fallback

- **WHEN** a user explicitly saves no selected tags for the active specialty
- **THEN** initial entry applies no tag predicate
- **AND** it does not silently reinsert the principal tag

### Requirement: Initial entry applies explicit specialty defaults

The system SHALL use the saved preference for a valid active specialty on initial
entry, or its valid principal tag with ANY matching if no preference exists.
Without a valid context/default the system SHALL apply no tag predicate.
Automatic filtering SHALL NOT change access to patient records.

#### Scenario: First entry without saved preferences

- **GIVEN** the active specialty has an active public principal tag
- **WHEN** the user opens list or map without manual filter state
- **THEN** that tag is visibly selected and applied with ANY matching

### Requirement: Manual override clear and reapply are distinct

The system SHALL prioritize explicit manual filters over defaults and preserve
an explicitly cleared selection. Clear SHALL show all otherwise eligible
patients; reapply preferences SHALL restore the active specialty's valid defaults.
Manual browsing SHALL NOT save preferences.

#### Scenario: Clear does not immediately reapply the default

- **WHEN** a user clears tag filters after an automatic specialty filter
- **THEN** no tag predicate is applied
- **AND** refresh and pagination retain the explicit cleared state

#### Scenario: Manual selection wins over saved defaults

- **WHEN** a user selects tags and mode on the page and follows result links
- **THEN** that manual state remains effective without changing saved preferences

### Requirement: Explicit preference save

The system SHALL offer Salvar como preferência da especialidade ativa as an
explicit authenticated mutation, saving tags and mode for that user's current
valid specialty only. It SHALL reject inaccessible or inactive/archived choices
and SHALL NOT expose another user's preference for modification.

#### Scenario: Save applies to only the current membership

- **WHEN** a user saves a manual active-tag selection in CIRGER
- **THEN** CIRGER preferences are updated and CARDIO preferences are unchanged
- **AND** forged user/specialty targets cannot alter another preference

### Requirement: Invalid automatic defaults warn without hiding patients

The system SHALL revalidate preferences on every request, omit inactive,
archived or inaccessible tags from automatic application, and display a warning.
If none remain it SHALL apply no tag predicate. Inaccessible names/IDs SHALL NOT
appear in warnings, and retained saved settings SHALL not be silently rewritten.

#### Scenario: All saved tags are unavailable

- **WHEN** every saved tag becomes inactive, archived or inaccessible
- **THEN** all otherwise eligible patients are shown without a tag predicate
- **AND** a visible generic warning explains the unavailable defaults

### Requirement: Historical manual filters preserve identity

The system SHALL permit explicit manual filtering by visible inactive/archived
tags through historical search, labelled by namespace and state. Inaccessible,
unknown or malformed explicit IDs SHALL produce a generic validation response,
not a silent unfiltered result or restricted metadata disclosure.

#### Scenario: Filter by an archived association

- **WHEN** a user selects an accessible archived tag using historical search
- **THEN** patients retaining that association can match in either filter mode
- **AND** the same tag remains unavailable for a new patient assignment

### Requirement: Legacy single-tag filter compatibility

The system SHALL accept existing single-tag URLs as explicit ANY filters while
supporting repeated tag selections and explicit manual-empty state. Pagination,
refresh and filter-removal links SHALL preserve the effective repeated selection,
matching mode and applicable non-tag filters.

#### Scenario: Old bookmark remains a single-tag query

- **WHEN** a user opens a legacy tag filter URL while other defaults are saved
- **THEN** the explicit single tag is applied with ANY mode instead of defaults

#### Scenario: Legacy empty tag parameter means explicit clear

- **WHEN** a user opens a legacy URL containing an explicitly empty tag parameter
- **THEN** no tag predicate is applied instead of reinserting specialty defaults

### Requirement: Map privacy and totals reflect filtered results

The system SHALL apply the same tag semantics and requester visibility to list
and map, while retaining each page's patient eligibility. Map totals SHALL reflect
the filtered result. A global cache SHALL NOT delay restricted visibility changes,
membership revocation or tag-assignment changes.

#### Scenario: Warm cache serves different team members safely

- **GIVEN** a map cache was populated before a tag became restricted
- **WHEN** an outsider and a team member request the map
- **THEN** each receives only currently authorized tag metadata
- **AND** both result counts reflect their valid selected filters

#### Scenario: Outpatient tag does not add patients to the ward map

- **GIVEN** a tag is associated only with outpatients
- **WHEN** the user filters the map by that tag
- **THEN** the map returns zero patients with matching totals
- **AND** filtering the list can still return those outpatients

### Requirement: Visible effective filter context

The system SHALL show selected tags, matching mode and whether defaults or manual
state are active on desktop/mobile. Historical tags SHALL be distinguishable;
zero results SHALL be distinct from unavailable defaults and stale map data.

#### Scenario: User understands the current specialty filter

- **WHEN** initial entry applies specialty defaults
- **THEN** the page shows the effective tags/mode and specialty context
- **AND** clear, reapply and explicit-save actions are distinguishable
