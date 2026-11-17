# Patient-map filter actions delta

## MODIFIED Requirements

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

## ADDED Requirements

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
