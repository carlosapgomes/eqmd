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
the rendered patient/ward result. A global cache SHALL NOT delay restricted
visibility changes, membership revocation or tag-assignment changes.

Both map variants SHALL label totals as filtered only when applied search,
ward or effective tag predicates constrain results. Manual origin, empty tag
selection, mode alone and empty-ward visibility alone SHALL NOT trigger that
label. Applied-origin context SHALL remain independently visible.

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

#### Scenario: Manual-empty totals are not labelled filtered

- **GIVEN** explicit manual-empty tags, no search and no ward selection
- **WHEN** the full map or AJAX fragment renders
- **THEN** totals omit the filtered-result label
- **AND** manual context can still be shown
- **AND** mode-only or empty-ward visibility changes do not create a predicate

#### Scenario: Automatic tags are effective predicates

- **WHEN** saved or principal defaults contain valid effective tags
- **THEN** the map labels its totals as a filtered result
- **AND** pending edits do not change that applied label before Apply

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
complete draft. Available clear, restore and pagination actions, and legacy
scoped URLs, SHALL derive their named scope from applied state without saving
preferences or silently applying unrelated draft edits. Removing applied-badge
controls from the UI SHALL NOT invalidate legacy scoped URLs.

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
- **WHEN** the user follows clear, restore, pagination or a legacy scoped URL
- **THEN** that action changes only its named scope from applied state A
- **AND** draft B is absent from the resulting full-page GET
- **AND** the newly rendered controls and summary describe only the resulting
  applied state rather than claiming B was applied

### Requirement: Task-oriented filters and filtered-empty recovery

The patient surfaces SHALL use `Pelo menos uma selecionada (OU)` and
`Todas as selecionadas (E)` for matching, label the mode `Correspondência`,
and distinguish `Filtro personalizado` from automatic preference context.
`Sem filtro de tags` SHALL NOT be presented as a predicate for patients that
have no tags. Both patient list and ward map SHALL use their canonical action
bar and local draft controls instead of repeating applied-clear/restore links.
Historical choices SHALL retain
`Mostrar inativas e arquivadas no seletor` on both surfaces.

An empty result with effective search/status/ward/tag predicates SHALL explain
that no patient corresponds to those filters and refer to the single filter
action bar without duplicating recovery controls. The instruction to add the
first patient SHALL appear only
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
- **AND** both surfaces direct users to their single filter action bar without
  duplicating those actions or presenting only Adicionar Paciente

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
Every selected-draft removal action SHALL have an accessible name identifying
its tag and selection scope. Applied summaries SHALL be informational and global
actions SHALL have distinct accessible names. Result rows, close controls and
badges SHALL remain usable with long names and narrow widths.

Filter-editor chips SHALL use a consistent neutral light background and dark
text meeting WCAG AA normal-text contrast on both surfaces. Custom tag colors
SHALL NOT determine chip text contrast. Remove hit areas SHALL be at least
24x24 CSS px and at least 44x44 CSS px in coarse-pointer/mobile presentation;
long names SHALL wrap without introducing horizontal page overflow.

#### Scenario: Screen reader distinguishes removal scope

- **GIVEN** draft chips, applied summaries and the action bar on either surface
- **WHEN** filter controls receive accessibility focus
- **THEN** draft removal announces its tag and selection scope
- **AND** global actions identify clearing all filters or restoring tag defaults
- **AND** applied summaries expose no competing removal controls

#### Scenario: Coarse-pointer chip removal

- **WHEN** a selected chip is displayed in the mobile presentation
- **THEN** its visible label remains readable and its remove target measures at
  least 44x44 CSS pixels

#### Scenario: Patient-list summary is informational

- **WHEN** the patient list shows applied filters and editable draft chips
- **THEN** the applied summary is read-only
- **AND** draft-chip removal identifies its tag and selection scope
- **AND** the single action bar retains clearly named global actions.

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

### Requirement: Canonical patient-list filter actions

The patient list SHALL offer one global action bar with `Aplicar filtros`,
`Limpar todos os filtros` and, under manual tag state with a valid specialty
and configured saved/principal default, `Usar padrão de tags da especialidade`.
It SHALL NOT repeat applied
tag-clear/default-restore actions in the selector, summary or empty state.
Applied-filter badges SHALL be read-only; editing controls remain distinct.

#### Scenario: No duplicate actions in manual or empty states

- **GIVEN** manual tag state and a valid specialty with a configured default
- **WHEN** the list renders populated or filtered-empty results
- **THEN** each global action appears once in the action bar
- **AND** no applied `Remover filtro de tags` link or old `Limpar filtros`
  label competes with it
- **AND** empty recovery refers to the controls above.

#### Scenario: Initial entry avoids a redundant restore action

- **WHEN** initial entry already uses automatic defaults, or there is no valid
  specialty or configured default
- **THEN** the restore-default action is absent
- **AND** Apply and clear-all remain available.

### Requirement: Patient-list clear-all means no filter predicates

`Limpar todos os filtros` SHALL immediately navigate to explicit manual-empty
state with ANY mode, no name/status/admission/tag predicates and first-page
results. Automatic tags SHALL NOT reappear on refresh or pagination of that
state. Access eligibility and saved preferences SHALL remain unchanged.
An independent later parameter-free entry SHALL still apply existing defaults.

#### Scenario: Clear removes search and tags without changing preferences

- **GIVEN** saved defaults X, applied name/status/tags Y and pending draft edits
- **WHEN** clear-all is chosen
- **THEN** name, status, admission and tags are empty and mode is ANY
- **AND** all otherwise eligible patients can match
- **AND** untagged eligible patients are not excluded
- **AND** pending edits are discarded and defaults X are not reapplied
- **AND** saved tags/mode and membership records remain unchanged.

#### Scenario: Empty state survives reload but not a new initial entry

- **WHEN** the cleared URL is refreshed or paginated
- **THEN** no default tag predicate is inserted
- **AND** a separate parameter-free visit still uses normal profile defaults.

### Requirement: Patient-list specialty restore is tag-scoped

`Usar padrão de tags da especialidade` SHALL immediately recompute the active
specialty's existing defaults and mode, preserving applied name/status/admission
predicates and resetting pagination. It SHALL discard unrelated pending edits,
not silently apply them. Saved-empty, principal fallback, unavailable-default
warnings and tag authorization SHALL retain existing semantics.

#### Scenario: Restore differs from clear-all

- **GIVEN** applied name Ana and status Internado
- **AND** saved defaults X and manual tags Y
- **WHEN** the user restores the specialty tag default
- **THEN** Ana and Internado remain, X and its saved mode replace Y
- **AND** the page returns to the first page and labels the automatic origin.

#### Scenario: Restore ignores unrelated pending drafts

- **GIVEN** applied name Ana, pending name Bruno and manual tags Y
- **WHEN** the specialty default is restored
- **THEN** applied name Ana remains rather than committing Bruno
- **AND** newly rendered controls describe the applied state.

### Requirement: Patient-list draft removal remains local

Individual draft-chip × controls SHALL remove only their selected draft tags,
preserve other draft fields and mode, and require Apply before results change.
This delivery SHALL NOT introduce a bulk `Limpar seleção` button. Without JS,
native deselection plus Apply SHALL support explicit empty selection.

#### Scenario: Draft-chip removal does not apply or save

- **GIVEN** selected draft tags, unapplied name/status edits and result set A
- **WHEN** the user removes the selected tags using their × controls
- **THEN** only draft tags change and other pending controls remain
- **AND** results, URL and applied summary remain A without a patient-result
  request or preference save
- **AND** the normal dirty indicator reflects normalized draft versus applied.

#### Scenario: No-JavaScript empty Apply suppresses defaults

- **GIVEN** default tags are present and JavaScript is disabled
- **WHEN** the user deselects every native tag option and chooses Apply
- **THEN** the request explicitly represents manual-empty state
- **AND** default tags do not silently replace that selection.

### Requirement: Patient-list preference status is truthful

The list SHALL distinguish a preference existing from it being applied.
Preference text SHALL derive from the effective applied source, not merely
record existence. Manual filters, saved defaults, principal fallback, no default
and invalid/unavailable defaults SHALL remain distinguishable. Draft edits
SHALL NOT relabel still-applied results as though they were applied.

#### Scenario: Saved preference is not falsely reported as in use

- **GIVEN** saved default X and an applied manual selection Y
- **WHEN** the preference panel renders
- **THEN** it identifies personalized applied filters rather than saying the
  saved preference is in use
- **AND** the existing explicit preference-save action remains separate.

#### Scenario: Empty and unavailable defaults are not hidden

- **WHEN** automatic evaluation yields a saved empty preference or unavailable
  saved tags
- **THEN** the page indicates no effective tag predicate as appropriate
- **AND** existing generic unavailable-default warnings remain visible.

### Requirement: Canonical patient-map filter actions

The map SHALL offer one action bar with `Aplicar filtros`,
`Limpar todos os filtros` and conditional
`Usar padrão de tags da especialidade`. Restore SHALL require manual tag state,
a valid active specialty and a configured saved/principal default; saved-empty
counts as configured. Applied summaries SHALL be read-only. The selector and
empty states SHALL NOT repeat applied-clear/restore controls.

#### Scenario: Unique actions in populated and empty results

- **GIVEN** manual tags and a valid specialty with configured defaults
- **WHEN** the full map renders matches or filtered-empty results
- **THEN** each global action appears once in the filter action bar
- **AND** no old applied tag-clear or "Limpar filtros" action competes with it
- **AND** the AJAX fragment introduces no duplicate recovery controls

#### Scenario: Restore is not always available

- **WHEN** entry is automatic, specialty is invalid or no default is configured
- **THEN** restore is absent
- **AND** Apply and clear-all remain available

### Requirement: Patient-map clear-all suppresses automatic defaults

Clear-all SHALL immediately navigate to explicit manual-empty state in ANY
mode, without search, ward, tag or empty-ward visibility parameters. It SHALL
preserve eligibility and stored preferences. Refresh SHALL retain manual-empty;
an independent later parameter-free visit SHALL retain automatic defaults.

#### Scenario: Clear applied and pending map filters

- **GIVEN** saved X, applied search/ward/manual Y and empty-ward visibility
- **AND** different pending draft edits
- **WHEN** clear-all is chosen
- **THEN** search/ward/tags are empty, mode is ANY and empty wards are hidden
- **AND** eligible untagged inpatients can match without including outpatients
- **AND** saved defaults do not reappear on refresh
- **AND** preferences and memberships are unchanged

### Requirement: Patient-map specialty restore is tag-scoped

Restore SHALL recompute current specialty tags/mode, preserving applied search,
ward and empty-ward visibility while discarding pending drafts. Saved-empty,
principal fallback, inaccessible/unavailable defaults and explicit-save
authorization SHALL keep existing semantics.

#### Scenario: Restore preserves applied map controls

- **GIVEN** applied Ana, ward A, manual Y and show-empty enabled
- **AND** saved X/ALL and pending Bruno, ward B and show-empty disabled
- **WHEN** restore is chosen
- **THEN** Ana, ward A and show-empty enabled remain applied
- **AND** X/ALL returns without saving preferences or committing pending edits

### Requirement: Patient-map draft removal remains local

Draft × SHALL change only selected draft tags and require Apply before results
change. No bulk "Limpar seleção" control SHALL be added. Native empty Apply SHALL
explicitly suppress defaults; clean enhanced Apply SHALL issue no result request.

#### Scenario: Native deselect-all is explicit manual-empty

- **GIVEN** automatic default tags and JavaScript disabled
- **WHEN** all native tags are deselected and Apply is chosen
- **THEN** the request represents manual-empty, rather than automatic entry
- **AND** other submitted visible draft fields remain effective

#### Scenario: Chip removal retains unrelated draft edits

- **GIVEN** pending search/ward/empty-ward edits and applied result A
- **WHEN** a selected draft chip is removed
- **THEN** only draft tags change, with the normal dirty indication
- **AND** URL/results/summary remain A until Apply
- **AND** normalized restoration of the draft makes enhanced Apply a no-op

### Requirement: Patient-map preference status is truthful

Preference text SHALL describe effective applied source/tags rather than record
existence. Manual, saved, saved-empty, principal, no-default, invalid and
unavailable subset/all states SHALL remain distinct. Draft edits SHALL NOT
relabel applied results; the existing preference-save action remains separate.

#### Scenario: Manual Y is not described as saved X in use

- **GIVEN** saved X and applied manual Y
- **WHEN** the preference panel renders
- **THEN** it identifies personalized filters
- **AND** unavailable/invalid states retain generic errors/warnings
- **AND** no GET or draft interaction changes the stored preference

### Requirement: Patient-map empty messages reflect applied predicates

The map SHALL retain "Mostrar alas vazias" with helper
"Inclui alas sem pacientes correspondentes aos filtros atuais."
A zero-match ward under search/tag predicates SHALL say
"Nenhum paciente corresponde aos filtros atuais nesta ala."
Without patient-narrowing predicates it SHALL say
"Nenhum paciente internado nesta ala." Ward selection alone is not a
patient-narrowing predicate inside a retained ward.

With valid available data, effective filters, zero total patients, show-empty
enabled and wards still rendered, one visible notice SHALL explain:
"Nenhum paciente corresponde aos filtros atuais. As alas continuam visíveis
porque 'Mostrar alas vazias' está ativado."
It SHALL appear before the tree without duplicate recovery actions.
Per-ward/global messages SHALL agree in full and AJAX variants. The checkbox
and helper remain in the full-page form, not duplicated in the tree fragment.
Numeric results/cache behavior SHALL remain unchanged; no pre-filter patient
counts SHALL be added.

#### Scenario: Filtering does not claim a physically empty ward

- **GIVEN** a ward contains eligible inpatients outside the selected search/tags
- **WHEN** show-empty retains that ward without matches
- **THEN** its message describes no matching patients, not no actual inpatients

#### Scenario: Genuine empty ward keeps its existing meaning

- **GIVEN** no applied patient search or effective tag predicate
- **WHEN** a retained ward has no inpatients, including a ward-only selection
- **THEN** it uses the genuine no-inpatients message
- **AND** manual-empty or mode alone does not change that wording

#### Scenario: Zero matches remain understandable with displayed wards

- **GIVEN** a valid map result, applied filters and show-empty enabled
- **WHEN** zero patients match but at least one ward remains displayed
- **THEN** one global notice explains both zero matches and visible wards
- **AND** it is visible without expanding a ward
- **AND** an unfiltered empty result does not make that filtered-result claim

#### Scenario: Unavailable cache is not a successful empty search

- **WHEN** existing behavior reports unavailable/updating map data
- **THEN** new filtered-empty notices do not reinterpret fallback zero totals
- **AND** existing cache generation and stale-data handling remain unchanged

### Requirement: Consistent patient filter layout

Patient list and map SHALL present their canonical filter actions left-aligned
with the search fields, using the same order, button styles and responsive
wrapping. Pending-change status SHALL remain near Apply and describe the whole
draft. Specialty preference saving SHALL remain in a separate card and an
independent POST form, never nested inside the GET filter form.

The map SHALL place "Mostrar alas vazias", its explanatory text and the existing
expand/collapse/refresh controls in a bordered "Visualização do mapa" section
after and outside the tag-filter panel. The checkbox SHALL remain inside the
same GET form and require Apply; tree controls SHALL remain non-submit actions.
The AJAX tree fragment SHALL NOT duplicate those full-page controls.

#### Scenario: Matching action bars across patient surfaces

- **GIVEN** a manual selection and a restorable specialty default
- **WHEN** list and map render at desktop or narrow viewport widths
- **THEN** Apply, clear-all and specialty restore appear in that order on the left
- **AND** the buttons wrap without adding page overflow
- **AND** preference saving remains separate from applying the draft

#### Scenario: Map display options are separate but use the same Apply

- **WHEN** the user edits the empty-ward checkbox in the bordered display section
- **THEN** the pending-change indication appears by the main filter actions
- **AND** results do not change until Apply
- **AND** Apply submits that checkbox with the other draft fields, with or
  without JavaScript
- **AND** the display section remains below the complete filter panel
