# patient-tag-filtering Specification

## Purpose

Make patient discovery consistent across list and ward map with visible multi-tag
filters, specialty-specific defaults and explicit user overrides that do not
change patient authorization.

## Requirements

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

### Requirement: Compact accessible selector results

The tag selector search results SHALL render each visible tag as a single
compact activation row on both the patient list and the ward map. Each row
SHALL present the plain tag name, the team abbreviation at most once as a
discrete affordance, and any lifecycle state as text. The full row SHALL be
the activation target. Results already in the current selection SHALL be
identifiable and non-duplicating, and removing a selected chip SHALL restore
the matching result. The selector SHALL remain operable by keyboard and
SHALL announce searching, result counts and selection changes politely.

#### Scenario: Results show no redundant abbreviation

- **GIVEN** a team tag "CirVascular" with abbreviation "CVASC"
- **WHEN** the user opens the search results
- **THEN** the row shows the name once and the abbreviation once as a pill
- **AND** no second line repeats the abbreviation

#### Scenario: Full row activates

- **GIVEN** rendered search results
- **WHEN** the user clicks anywhere on a result row
- **THEN** the tag is added to the selection exactly once

#### Scenario: Already selected result is inert but visible

- **GIVEN** a result whose tag is already selected
- **WHEN** the user activates that row
- **THEN** the selection is unchanged and focus is preserved
- **AND** the row is labelled as selected

#### Scenario: Chip removal re-enables the result

- **GIVEN** a selected tag with its chip shown and its result inert
- **WHEN** the user removes the chip
- **THEN** the matching search result becomes activatable again
- **AND** the removal is announced politely

#### Scenario: Keyboard operation

- **GIVEN** the selector search field focused
- **WHEN** the user presses ArrowDown, moves with ArrowUp or Home and End,
  activates with Enter or Space and closes with Esc
- **THEN** results open, focus moves between rows, the tag is added and focus
  returns to the search field without clearing the term

#### Scenario: Status announcements

- **WHEN** the user searches, results load, more results are loaded or a tag
  is added or removed
- **THEN** a polite live region announces searching, found count, loaded
  count or the selection change respectively
- **AND** a stale response never overwrites newer results

#### Scenario: No-JavaScript fallback preserved

- **GIVEN** JavaScript disabled
- **WHEN** the user opens the patient list or the ward map
- **THEN** the native multi-select still submits the same filter parameters

### Requirement: Explicit draft and applied filter states

Patient list and ward map SHALL distinguish the complete last-applied predicate
from the current draft controls. Ordinary edits to patient name search, status,
ward, selected tags, matching mode or empty-ward visibility SHALL NOT change
result predicates before the user chooses `Aplicar filtros`. The control for
searching tag options SHALL NOT be treated as the patient name predicate.

With JavaScript enhancement, the interface SHALL show `Alterações não
aplicadas` whenever normalized draft and applied values differ. Returning the
draft to the applied values SHALL clear that indication. Apply SHALL submit the
complete draft, while existing explicit clear/reapply, badge-removal and
pagination actions SHALL retain their scoped behavior without saving
preferences or silently applying unrelated draft edits.

#### Scenario: Typed then reverted query is not pending

- **GIVEN** applied patient results and a clean filter form
- **WHEN** the user edits the patient name and restores its original value
  without applying
- **THEN** the results remain unchanged throughout
- **AND** the unapplied-change indication disappears after the values again match

#### Scenario: Apply commits all current predicates

- **GIVEN** a draft with patient name, status, two tags and ALL matching
- **WHEN** the user chooses Aplicar filtros
- **THEN** successful results use every visible predicate conjunctively
- **AND** applied and draft state agree without writing specialty preferences

#### Scenario: Empty wards cannot submit an unrelated draft

- **GIVEN** unapplied name and tag edits on the ward map
- **WHEN** the user toggles Mostrar alas vazias without applying
- **THEN** neither ward visibility nor the unrelated draft changes applied results
- **AND** the unapplied-change indication remains visible

#### Scenario: Scoped action does not replay pending edits

- **GIVEN** applied filters A and a different pending draft B
- **WHEN** the user follows a clear, applied-badge-removal or pagination action
- **THEN** that action changes only its named scope from applied state A
- **AND** draft B is absent from the resulting full-page GET
- **AND** the newly rendered controls and summary describe only the resulting
  applied state rather than claiming B was applied

### Requirement: Task-oriented filters and filtered-empty recovery

The patient surfaces SHALL use `Pelo menos uma selecionada (OU)` and
`Todas as selecionadas (E)` for matching, label the mode `Correspondência`,
and distinguish `Filtro personalizado` from automatic preference context.
`Sem filtro de tags` SHALL NOT be presented as a predicate for patients that
have no tags. Clear and reapply actions SHALL use respectively `Remover filtro
de tags` and `Restaurar padrão da especialidade`; historical choices SHALL use
`Mostrar inativas e arquivadas no seletor`.

An empty result with effective search/status/ward/tag predicates SHALL explain
that no patient corresponds to those filters and expose applicable scoped
recovery actions. The instruction to add the first patient SHALL appear only
for a genuinely unfiltered empty eligible collection. Filter-origin,
unavailable-default and stale-map messages SHALL remain distinguishable.

#### Scenario: Matching words identify selected identities

- **WHEN** two tags are selected in either patient surface
- **THEN** correspondence identifies whether ANY or ALL of those selected tags
  is required rather than mentioning every tag in the catalogue

#### Scenario: Filtered zero does not invite first-patient creation

- **GIVEN** patients exist outside the current eligibility or filter result
- **WHEN** a name/status/tag combination returns zero patients
- **THEN** the page describes no match for current filters
- **AND** it offers applicable remove-tag, filter-removal or restore-default
  recovery instead of presenting only Adicionar Paciente

#### Scenario: Manual empty is no predicate

- **WHEN** the user explicitly clears only the tag predicate
- **THEN** the context says there is no tag filter
- **AND** otherwise eligible patients with and without tags remain eligible

### Requirement: Bounded dismissible tag options

The enhanced option results on patient list and ward map SHALL remain within a
selector-anchored overlay at most `min(18rem, 50vh)` high with internal vertical
scrolling. Opening the panel and loading more options SHALL NOT increase the
host filter card height merely because the panel opened. Existing
search/selection state and the Apply action SHALL remain reachable at desktop
and narrow widths.

Clicking outside and Escape SHALL close the panel without changing selection.
Escape SHALL restore focus to the search field while preserving its term.
Focusing or clicking the field afterward SHALL reopen already-loaded results.
Existing arrow/Home/End navigation, activation, selected-row behavior,
`Carregar mais` and polite announcements SHALL be preserved.

#### Scenario: Twenty-more options do not displace Apply

- **GIVEN** an open option panel with twenty loaded rows and another page
- **WHEN** the user chooses Carregar mais
- **THEN** additional rows are reached within the bounded scrolling panel
- **AND** the host card height and Apply position do not grow with the rows

#### Scenario: Close and reopen retain work

- **GIVEN** typed option-search text and selected chips
- **WHEN** the user presses Escape or clicks outside and later focuses the field
- **THEN** the panel closes and reopens without losing text, loaded rows or chips

#### Scenario: Option lookup failure retains selection

- **WHEN** a tag-option request fails after tags have been selected
- **THEN** the selected and last-applied filter state remain intact
- **AND** a visible polite error permits a subsequent focus/search retry

### Requirement: Accessible patient filter actions

Apply SHALL expose visible `Aplicar filtros` text on patient list and map.
Every selected-draft or applied-filter removal action SHALL have an accessible
name identifying its tag and scope. Result rows, close controls and badges SHALL
remain usable with long names and narrow widths.

Filter-editor chips SHALL use a consistent neutral light background and dark
text meeting WCAG AA normal-text contrast on both surfaces. Custom tag colors
SHALL NOT determine chip text contrast. Remove hit areas SHALL be at least
24x24 CSS px and at least 44x44 CSS px in coarse-pointer/mobile presentation;
long names SHALL wrap without introducing horizontal page overflow.

#### Scenario: Screen reader distinguishes removal scope

- **GIVEN** a draft chip and an applied-filter badge for the same tag
- **WHEN** their remove actions receive accessibility focus
- **THEN** each announces the tag name and whether removal affects the draft or
  the applied filter

#### Scenario: Coarse-pointer chip removal

- **WHEN** a selected chip is displayed in the mobile presentation
- **THEN** its visible label remains readable and its remove target measures at
  least 44x44 CSS pixels

### Requirement: Cache-safe first-load tag filter rendering

Tag-option lookup SHALL display its returned selectable rows on first entry
independently of previously visited pages and cached older static assets.
The option panel SHALL align directly below the search input. Search, mode
and action controls SHALL remain readable and usable at desktop/mobile widths
without changing explicit Apply or filter semantics.

#### Scenario: Legacy assets cannot hide found rows

- **GIVEN** a browser previously cached the legacy selector URL
- **WHEN** the updated patient list or map loads and a tag name is searched
- **THEN** current versioned assets display clickable matching rows immediately
- **AND** no visit to another page is necessary.

#### Scenario: Responsive filter controls

- **WHEN** filters render at 1440, 390 or 320 CSS pixels viewport width
- **THEN** labels, mode and Apply remain visible without horizontal overflow
- **AND** opening options does not grow the filter card.
