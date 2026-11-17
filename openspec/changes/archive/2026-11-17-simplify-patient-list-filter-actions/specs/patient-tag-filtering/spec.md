# Patient-list filter actions delta

## MODIFIED Requirements

### Requirement: Task-oriented filters and filtered-empty recovery

The patient surfaces SHALL use `Pelo menos uma selecionada (OU)` and
`Todas as selecionadas (E)` for matching, label the mode `Correspondência`,
and distinguish `Filtro personalizado` from automatic preference context.
`Sem filtro de tags` SHALL NOT be presented as a predicate for patients that
have no tags. On the ward map, clear and reapply actions SHALL retain
`Remover filtro de tags` and `Restaurar padrão da especialidade`. The patient
list SHALL use its canonical action bar and local draft controls instead of
repeating those links. Historical choices SHALL retain
`Mostrar inativas e arquivadas no seletor` on both surfaces.

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
- **AND** the map offers its applicable scoped recovery actions
- **AND** the list directs users to its single filter action bar without
  duplicating those actions or presenting only Adicionar Paciente

#### Scenario: Manual empty is no predicate

- **WHEN** the user explicitly clears only the tag predicate
- **THEN** the context says there is no tag filter
- **AND** otherwise eligible patients with and without tags remain eligible

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

- **GIVEN** a draft chip and an applied-filter badge for the same tag on the map
- **WHEN** their remove actions receive accessibility focus
- **THEN** each announces the tag name and whether removal affects the draft or
  the applied filter

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
