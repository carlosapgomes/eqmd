# patient-tag-filtering delta: explicit and accessible discovery UX

## ADDED Requirements

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
