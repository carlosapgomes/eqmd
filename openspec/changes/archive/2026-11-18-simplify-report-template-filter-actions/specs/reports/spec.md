# Report catalogue filter actions delta

## MODIFIED Requirements

### Requirement: Explicit report discovery override and validation

Both surfaces SHALL distinguish clear from reapply, preserve effective repeated
tag identities and ANY/ALL state across search and pagination, and allow readable
historical tags for explicit manual filtering. Malformed, unknown or inaccessible
explicit filters SHALL fail generically rather than silently widening results.
Enhanced historical choices SHALL load without navigation or lost selections.

The catalogue's new clear-all action follows the canonical catalogue contract;
report creation and legacy tag-only query URLs retain their existing scopes.

#### Scenario: Clear and reapply have different effects

- **WHEN** report creation clears tags, or a legacy tag-only query is opened,
  while a name query is active
- **THEN** the name query remains with explicit manual-empty tag state
- **AND** refresh does not reapply defaults until the user requests reapply.

#### Scenario: Explicit invalid tag does not reveal an unfiltered list

- **WHEN** either surface receives an unknown, unreadable tag or invalid mode
- **THEN** it returns HTTP 400 with a generic message and no successful results.

#### Scenario: Historical identity remains useful for manual discovery

- **WHEN** an authorized reader explicitly filters by an inactive or archived tag
- **THEN** retained associations can match with their state visibly labelled
- **AND** the historical tag is not newly assignable or automatically applied.

#### Scenario: Historical choices load without navigation

- **GIVEN** JavaScript enhancement is active on either discovery surface
- **WHEN** the user enables historical choices
- **THEN** readable inactive/archived tags become selectable without navigation
- **AND** q, mode, current selections and default/manual origin remain unchanged
- **AND** disabling the option retains already-selected readable historical tags.

### Requirement: Explicit report discovery draft state

Both report discovery surfaces SHALL separate the last-applied result predicate
from draft name, tags and correspondence controls. Ordinary edits SHALL expose
`Alterações não aplicadas` without changing result predicates. `Aplicar filtros`
SHALL apply the complete normalized draft and reconcile applied state, result
summary and controls only after success. The tag-option search field SHALL NOT
be treated as the model-name predicate.

On report creation, clear/reapply, applied-badge removal and pagination SHALL
retain their current last-applied scopes and preserve unrelated pending edits.
Catalogue pagination and ordinary AJAX Apply SHALL retain their existing draft
and late-edit protection. Historical-option lookup MAY update choices
independently, but SHALL NOT alter result predicates or discard pending choices.

The catalogue's canonical clear-all and specialty-restore actions SHALL instead
perform explicit full GET navigation from applied state, discard pending drafts
and render controls matching the resulting applied state. Legacy tag-only query
URLs SHALL retain their existing scopes. These exceptions SHALL NOT reach
report-creation discovery or its clinical editor.

#### Scenario: Pending correspondence does not describe current results

- **GIVEN** models filtered with ANY and two selected tags
- **WHEN** the user changes the visible correspondence to ALL without Apply
- **THEN** the existing models and their applied summary remain ANY
- **AND** the page visibly reports unapplied changes rather than presenting ALL
  as the source of the current results

#### Scenario: Apply succeeds atomically in the UI

- **GIVEN** a draft name query, selected tags and ALL correspondence
- **AND** no further edit is made while Apply is pending
- **WHEN** Apply returns a successful matching response
- **THEN** results, applied tags/mode, canonical URL and draft reflect that same
  state and the unapplied-change indication clears

#### Scenario: Failure does not masquerade as empty results

- **WHEN** an Apply or scoped discovery request fails
- **THEN** last-applied results and URL remain associated with the previous state
- **AND** the draft and unapplied/error indications remain available for retry

#### Scenario: Scoped navigation does not commit pending edits

- **GIVEN** pending changes that differ from the applied predicate
- **WHEN** the catalogue paginates, or report creation performs a scoped
  pagination, badge-removal, tag-clear or specialty-reapply action
- **THEN** only the named change is applied to the previous applied predicate
- **AND** the unrelated pending controls remain draft and visibly dirty

#### Scenario: Late edits survive ordinary AJAX Apply

- **GIVEN** Apply submitted draft B and a newer draft C is entered before success
- **WHEN** the successful B response arrives
- **THEN** results and applied baseline describe B
- **AND** C stays visible and pending rather than being overwritten

#### Scenario: Canonical catalogue action reconstructs controls

- **GIVEN** an applied catalogue predicate and different pending controls
- **WHEN** canonical clear-all or specialty restore succeeds
- **THEN** the full GET renders the resulting applied tags, mode and name
- **AND** the editor is clean and Apply cannot undo the action with old controls
- **AND** an older fragment response cannot override that navigation

### Requirement: Filtered-empty template recovery

The catalogue SHALL distinguish no models matching effective name/tag
predicates from a genuinely unfiltered empty catalogue. The former SHALL
describe the filter mismatch and refer to the single catalogue filter action
bar without duplicating clear/restore controls; the latter MAY offer the
existing authorized creation action.

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

#### Scenario: Filtered-empty recovery does not duplicate the action bar

- **WHEN** a valid name/tag predicate returns no models
- **THEN** one explanation refers to the canonical filter actions above
- **AND** no old tag-clear/restore links or applied-badge removal controls repeat

### Requirement: Accessible report discovery controls

Both report discovery surfaces SHALL provide a text-labelled `Aplicar filtros`
button, visible `Correspondência`, task-oriented ANY/ALL and historical wording,
specific accessible tag-removal names and the same neutral high-contrast chip
style as patient filtering. Remove targets SHALL be at least 24x24 CSS px and
44x44 CSS px in coarse-pointer/mobile presentation. Long names SHALL wrap
without introducing horizontal page overflow.

The catalogue SHALL order Apply, clear-all and conditional specialty restore
in one left-aligned wrapping bar matching the patient surfaces. Its applied
summary SHALL be informational. Only draft chips expose individual removal,
with tag-specific accessible names and the existing minimum target sizes.
Report creation's existing controls and behavior SHALL remain unchanged.

#### Scenario: Mobile selection and removal remain legible

- **WHEN** several long template tags are selected at 390 px width
- **THEN** labels wrap safely and the enhanced option panel stays viewport-bound
- **AND** every chip can be removed through at least a 44x44 CSS-pixel target

#### Scenario: Catalogue summary does not compete with draft editing

- **WHEN** the catalogue renders at 1440, 390 or 320 CSS pixels
- **THEN** the action bar stays left-aligned and long labels wrap safely
- **AND** the applied summary has no removal actions
- **AND** draft chips remain keyboard operable with their accessible targets

### Requirement: Restorable report discovery history

Enhanced catalogue Apply/pagination and creation discovery SHALL add a history
entry only when
a successful explicit application or deliberate scoped navigation changes the
canonical applied URL. Option-only historical updates SHALL replace the current
entry; draft edits and failed/no-op requests SHALL NOT add entries. Back and
Forward SHALL restore the canonical state and corresponding results without
adding another entry.

On report creation, history restoration SHALL preserve title, document date,
EasyMDE content and the independently selected model. In-progress clinical data
SHALL NOT be replaced when a filter history entry is restored.

Canonical catalogue clear-all/restore SHALL use ordinary browser full-GET
history without an additional AJAX pushState entry for the same transition.
Their action links SHALL omit fragment and reset pagination. Existing no-op,
failed-request and popstate rules for enhanced Apply/pagination remain intact.

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

#### Scenario: Browser history spans native catalogue actions

- **GIVEN** applied catalogue state A followed by a canonical full-GET action B
- **WHEN** Back and then Forward are used
- **THEN** address, controls, source summary and results correspond to A then B
- **AND** no duplicate application-created history entry or stale in-flight
  response changes those states

## ADDED Requirements

### Requirement: Canonical report catalogue filter actions

The catalogue SHALL offer one bar with Aplicar filtros, Limpar todos os filtros
and conditional Usar padrão de tags da especialidade. Restore SHALL be offered
only for manual state, a valid active specialty and a configured saved or
principal default; a saved-empty preference counts as configured.
Hidden actions SHALL NOT be visually offered, focusable or exposed as actions
to assistive technology. Availability SHALL follow server-resolved state after
initial rendering and every successful catalogue fragment/history update.

Apply SHALL retain its enhanced AJAX/no-request-clean behavior. Canonical
clear-all and restore SHALL perform native full GET navigation with or without
JavaScript, discard pending drafts and cancel/invalidate older catalogue
requests. Server and reconciled hrefs SHALL describe applied state, not draft
controls. The selector, summary and empty state SHALL NOT repeat global actions.

#### Scenario: Conditional restore updates after AJAX Apply

- **GIVEN** automatic saved X/ALL with no offered restore action
- **WHEN** manual Y is successfully applied through AJAX
- **THEN** the canonical restore action becomes available exactly once
- **AND** its href preserves the newly applied name, not an older rendered name

#### Scenario: Missing or already applied default has no redundant restore

- **WHEN** state is automatic, specialty is invalid or no default is configured
- **THEN** restore is not offered
- **AND** Apply and clear-all remain available
- **AND** a manual state with a configured saved-empty default may offer restore

### Requirement: Report catalogue clear-all suppresses automatic defaults

Catalogue clear-all SHALL immediately navigate to a fresh explicit manual-empty
ANY state without name, tag aliases, historical option, page, fragment or other
stale parameters. Refresh SHALL retain that state; separate parameter-free
entry SHALL still use shared defaults. Public-or-own visibility and inactive
catalogue eligibility SHALL remain unchanged. No preference is saved.

#### Scenario: True clear-all differs from legacy tag-only clear

- **GIVEN** saved X/ALL, applied name/tags Y and different pending edits
- **WHEN** canonical clear-all is chosen
- **THEN** name and tags are empty, mode is ANY and results start on page one
- **AND** untagged eligible models can match without exposing private models
- **AND** reload does not reinsert X and the rendered controls are clean
- **AND** legacy tag-only URLs can still preserve an existing name query

### Requirement: Report catalogue specialty restore is tag-scoped

Canonical restore SHALL recompute the active specialty's existing tags/mode,
preserving applied name and the applied historical lookup option while removing
tag overrides, page and fragment. It SHALL discard all pending drafts and render
the resolved controls clean. Saved-empty, principal fallback, unavailable-default
warnings and requester visibility SHALL retain existing semantics.
Browsing SHALL NOT change preferences, memberships, associations or reports.

#### Scenario: Restore preserves applied name rather than pending name

- **GIVEN** applied name Ana, manual Y and saved X/ALL
- **AND** pending name Bruno, different draft tags and correspondence
- **WHEN** canonical restore is chosen
- **THEN** Ana and X/ALL are applied and visibly selected on the resulting page
- **AND** Bruno and the old draft are discarded without preference writes
- **AND** immediate enhanced Apply sends no request and cannot undo restore

#### Scenario: In-flight Apply cannot override canonical navigation

- **GIVEN** an older catalogue fragment request is still pending
- **WHEN** clear-all or restore is chosen and that response later finishes
- **THEN** the native action's URL, controls, results and history remain authoritative
- **AND** report creation's controller is unaffected
