# Reports delta: explicit and accessible template discovery UX

## ADDED Requirements

### Requirement: Explicit report discovery draft state

Both report discovery surfaces SHALL separate the last-applied result predicate
from draft name, tags and correspondence controls. Ordinary edits SHALL expose
`Alterações não aplicadas` without changing result predicates. `Aplicar filtros`
SHALL apply the complete normalized draft and reconcile applied state, result
summary and controls only after success. The tag-option search field SHALL NOT
be treated as the model-name predicate.

Clear/reapply, applied-badge removal and pagination SHALL use the last-applied
predicate for their named action and SHALL NOT silently replay or commit the
rest of a pending draft. Unrelated pending controls remain visibly pending.
Historical-option lookup MAY update choices independently, but SHALL NOT alter
result predicates or discard pending choices.

#### Scenario: Pending correspondence does not describe current results

- **GIVEN** models filtered with ANY and two selected tags
- **WHEN** the user changes the visible correspondence to ALL without Apply
- **THEN** the existing models and their applied summary remain ANY
- **AND** the page visibly reports unapplied changes rather than presenting ALL
  as the source of the current results

#### Scenario: Apply succeeds atomically in the UI

- **GIVEN** a draft name query, selected tags and ALL correspondence
- **WHEN** Apply returns a successful matching response
- **THEN** results, applied tags/mode, canonical URL and draft reflect that same
  state and the unapplied-change indication clears

#### Scenario: Failure does not masquerade as empty results

- **WHEN** an Apply or scoped discovery request fails
- **THEN** last-applied results and URL remain associated with the previous state
- **AND** the draft and unapplied/error indications remain available for retry

#### Scenario: Scoped navigation does not commit pending edits

- **GIVEN** pending changes that differ from the applied predicate
- **WHEN** the user paginates, removes an applied badge, clears tags or
  reapplies the specialty default
- **THEN** only the named change is applied to the previous applied predicate
- **AND** the unrelated pending controls remain draft and visibly dirty

### Requirement: Searchable report tag selection

With JavaScript enhancement, both report discovery surfaces SHALL use the
visibility-checked searchable lookup, selected chips, lifecycle/team labels,
bounded option panel and predictable open/close behavior established for
patient tag filtering. Duplicate option rendering or a native multi-select that
requires it for routine enhanced use SHALL NOT remain on those surfaces.

The reports lookup SHALL use the report discovery read boundary and existing
requester-safe tag catalogue query/projection. It SHALL NOT require patient
record permission, weaken the existing patient lookup permission or expose
hidden metadata. Historical option updates SHALL be lookup-only.

Without JavaScript, the existing native repeated-tag GET contract SHALL remain
available with readable active options and explicitly requested historical
choices. Existing name validation, 20-model pagination, eligibility and ANY/ALL
matching SHALL NOT change as a consequence of selector reuse.

#### Scenario: Template-only and historical tags are discoverable

- **GIVEN** an active readable tag used only on templates and a readable archived
  tag retained by a template
- **WHEN** the enhanced reader searches accordingly and requests historical
  options
- **THEN** each can be selected with correct namespace/state and applied manually
- **AND** hiding historical options does not discard the selected archived tag

#### Scenario: Outsider lookup remains metadata-safe

- **WHEN** an authenticated report reader without access to another team's
  restricted metadata queries tag options
- **THEN** response and DOM contain neither that restricted tag's identity,
  label nor hidden count
- **AND** access depends on report/catalogue visibility rather than permission
  to view patient records

#### Scenario: No-JavaScript native filtering still applies

- **GIVEN** JavaScript is unavailable
- **WHEN** the user chooses two native tag options and Aplicar filtros
- **THEN** the GET request carries repeated tags and manual correspondence
- **AND** full-page results and controls preserve the effective state

### Requirement: Restorable report discovery history

Enhanced catalogue and creation discovery SHALL add a history entry only when
a successful explicit application or deliberate scoped navigation changes the
canonical applied URL. Option-only historical updates SHALL replace the current
entry; draft edits and failed/no-op requests SHALL NOT add entries. Back and
Forward SHALL restore the canonical state and corresponding results without
adding another entry.

On report creation, history restoration SHALL preserve title, document date,
EasyMDE content and the independently selected model. In-progress clinical data
SHALL NOT be replaced when a filter history entry is restored.

#### Scenario: Back undoes an applied filter

- **GIVEN** applied state A followed by successful Apply of state B
- **WHEN** the user invokes browser Back
- **THEN** the address, visible controls, result summary and results return to A
- **AND** navigating Forward restores B without duplicate history entries

#### Scenario: Draft and failure do not pollute history

- **GIVEN** a clean canonical state A
- **WHEN** the user edits draft B without Apply or attempts an Apply that fails
- **THEN** no successful applied-history entry for B is created
- **AND** the last-applied address remains A while any error/draft is visible

### Requirement: Filtered-empty template recovery

The catalogue SHALL distinguish no models matching effective name/tag
predicates from a genuinely unfiltered empty catalogue. The former SHALL
describe the filter mismatch and expose applicable tag-removal/default-restore
recovery; the latter MAY offer the existing authorized creation action.

Manual empty tag state with no name query SHALL be treated as unfiltered for
this distinction. Existing private/inactive eligibility and unavailable-default
warnings SHALL remain unchanged.

#### Scenario: Active filter yields no models

- **GIVEN** public-or-own models exist outside the applied predicate
- **WHEN** the applied name/tag combination returns zero
- **THEN** the empty state says no model corresponds to current filters
- **AND** recovery is offered instead of only Crie o primeiro template

#### Scenario: Actually empty unfiltered catalogue

- **WHEN** no model is visible and there is no effective name or tag predicate
- **THEN** the normal empty-catalogue explanation is used
- **AND** creation is offered only under existing management authorization

### Requirement: Accessible report discovery controls

Both report discovery surfaces SHALL provide a text-labelled `Aplicar filtros`
button, visible `Correspondência`, task-oriented ANY/ALL and historical wording,
specific accessible tag-removal names and the same neutral high-contrast chip
style as patient filtering. Remove targets SHALL be at least 24x24 CSS px and
44x44 CSS px in coarse-pointer/mobile presentation. Long names SHALL wrap
without introducing horizontal page overflow.

#### Scenario: Mobile selection and removal remain legible

- **WHEN** several long template tags are selected at 390 px width
- **THEN** labels wrap safely and the enhanced option panel stays viewport-bound
- **AND** every chip can be removed through at least a 44x44 CSS-pixel target

## MODIFIED Requirements

### Requirement: Dynamic report template name discovery

Both surfaces SHALL offer trimmed, case/accent-insensitive name substring search
combined with tags, paginated at 20 distinct models in stable order. Editing the
name SHALL remain a pending draft action until the user explicitly chooses
`Aplicar filtros`; typing alone SHALL NOT issue a model-result query or modify
the last-applied predicate. Enhanced Apply SHALL update results without a
full-page navigation. Loading, no-results and errors SHALL be distinguishable;
stale responses SHALL NOT replace newer results.

#### Scenario: Accent-insensitive dynamic search

- **WHEN** the user enters an unaccented portion of an accented model name and
  chooses Aplicar filtros
- **THEN** matching eligible models appear
- **AND** active applied tags and matching mode remain effective until replaced
  by the submitted draft

#### Scenario: Unapplied name does not alter results

- **GIVEN** results for applied name A
- **WHEN** the user replaces the input with name B without applying
- **THEN** results and canonical applied state remain for A
- **AND** a visible unapplied-change indication identifies pending name B

#### Scenario: Pagination searches beyond the initial page

- **GIVEN** more than 20 eligible models match
- **WHEN** the user navigates result pages or applies a changed name query
- **THEN** paging retains applied filters and the changed query restarts at the
  first page
- **AND** searching is not limited to models initially loaded in the browser

#### Scenario: Out-of-order response and failure are safe

- **WHEN** an earlier explicit request finishes after a later explicit request
  or a request fails
- **THEN** stale results are ignored and failure is announced without claiming
  successful empty or unfiltered results

#### Scenario: Oversized name query is rejected

- **WHEN** q exceeds 255 characters after trimming
- **THEN** the server returns HTTP 400 with a validation message
