# Reports

## Purpose

Define behavior for generic report templates and patient reports, including
creation, permissions, and PDF output.

## Requirements

### Requirement: Manage report templates

The system SHALL allow authorized users (admin/staff, doctors, residents) to
create, update, and view report templates.

#### Scenario: Authorized template creation

- **WHEN** an admin/staff, doctor, or resident submits a new report template
- **THEN** the system saves the template and attributes it to the creator

#### Scenario: Unauthorized template creation blocked

- **WHEN** a user who is not admin/staff, doctor, or resident attempts to create
  a report template
- **THEN** the system denies the action

### Requirement: Template visibility rules

The system SHALL show public templates to all authenticated users and private
templates only to their creator.

#### Scenario: Public template visible

- **WHEN** an authenticated user lists report templates
- **THEN** the system includes templates marked as public

#### Scenario: Private template hidden

- **WHEN** an authenticated user lists report templates
- **THEN** the system excludes private templates created by other users

### Requirement: Strict placeholder validation

The system SHALL validate template placeholders against an allowlist and require
the `patient_name` placeholder.

#### Scenario: Unknown placeholder rejected

- **WHEN** a template contains a placeholder not in the allowlist
- **THEN** the system rejects the template with a validation error

#### Scenario: Missing required placeholders rejected

- **WHEN** a template omits `patient_name`
- **THEN** the system rejects the template with a validation error

### Requirement: Create reports from templates

The system SHALL allow users to create reports from templates, render
placeholders server-side, and allow editing of the resulting markdown before
saving.

#### Scenario: Template-based report creation

- **WHEN** a user selects a template and submits report creation
- **THEN** the system renders placeholders into markdown and saves the report
  content

#### Scenario: Manual report creation without template

- **WHEN** a user submits report content without selecting a template
- **THEN** the system saves the report content as provided

### Requirement: Report event behavior

Reports SHALL be stored as Event subtypes with event type `REPORT_EVENT` and
follow the 24-hour edit/delete window by creator.

#### Scenario: Report edit within window

- **WHEN** the report creator edits a report within 24 hours of creation
- **THEN** the system allows the update

#### Scenario: Report edit after window denied

- **WHEN** the report creator attempts to edit a report after 24 hours
- **THEN** the system denies the update

### Requirement: PDF generation with letterhead and signature

The system SHALL generate report PDFs with hospital letterhead, support page
breaks, and include a signature section.

#### Scenario: PDF download available

- **WHEN** an authorized user requests a report PDF
- **THEN** the system returns a PDF with letterhead, page breaks, and signature
  section

### Requirement: No report attachments

The system SHALL NOT support attachments for reports.

#### Scenario: Attachments not available

- **WHEN** a user views a report
- **THEN** the system does not provide attachment upload or listing

### Requirement: Report duplication

The system SHALL provide a duplicate action that creates a new report
from an existing report of the same patient, pre-filling the editable
creation form with the source title and content.

#### Scenario: Duplicate form pre-filled from source

- **WHEN** an authorized user opens the duplicate action for a report
- **THEN** the system renders the report creation form with the source
  report's title and content, and today's document date

#### Scenario: Duplicate creates an independent copy

- **WHEN** an authorized user submits the duplicate form
- **THEN** the system creates a new report for the same patient,
  attributed to the submitting user, with a fresh event datetime
- **AND** the new report is editable within its own 24-hour window
- **AND** the system redirects to the patient timeline

#### Scenario: Source report unchanged

- **WHEN** a duplicate is created
- **THEN** the source report's content, title, author, and event
  datetime remain unchanged

#### Scenario: Template provenance not copied

- **WHEN** the source report was created from a template
- **AND** a duplicate is created from it
- **THEN** the duplicate is saved without a template association and
  its content is the source's stored content (no template re-render)

#### Scenario: Unauthorized duplication denied

- **WHEN** a user without `events.add_event` or without access to the
  patient opens or submits the duplicate action
- **THEN** the system denies the request

#### Scenario: Duplicate action on the timeline card

- **WHEN** a user with `events.add_event` views a report event on the
  patient timeline
- **THEN** the report card exposes a duplicate action linking to the
  duplicate form
- **AND** users without the permission do not see the action

### Requirement: Optional report template classification

The system SHALL let authorized report-template editors associate zero or more
existing catalogue tags during creation and editing. It SHALL NOT create or
modify catalogue tags, automatically classify templates from profile defaults,
or copy template tags to patients or generated reports.

With JavaScript enhancement, create and update SHALL support multiple choices
by ordinary click/tap and explicit removal of each selected chip, including
the last. Zero editable selections SHALL remain valid and SHALL be persisted
only on the existing explicit template-form submit.

#### Scenario: Creator classifies and later edits a model

- **WHEN** a permitted creator saves a model with two authorized tags
- **THEN** both associations are retained without duplicates
- **AND** the creator can later add or remove authorized associations.

#### Scenario: Existing templates remain unclassified

- **WHEN** the feature is deployed over existing report templates
- **THEN** those templates have no associations unless subsequently classified
- **AND** their content, visibility, author and generated reports are unchanged.

#### Scenario: Classification is optional and independent of filter defaults

- **GIVEN** the creator has saved default tags
- **WHEN** a new template is saved without classification tags
- **THEN** the template remains untagged.

#### Scenario: Editor removes its last editable classification

- **GIVEN** a model has one editable selected tag
- **WHEN** the enhanced editor removes that chip and chooses Salvar Modelo
- **THEN** the editable association is removed without selecting a replacement
- **AND** protected associations retain their existing policy and visibility

### Requirement: Per-tag report template mutation authority

The system SHALL retain current template editing gates and also validate
association authority. New links SHALL require active tags; restricted and
principal tags SHALL require current team membership or catalogue administrator
authority. Non-principal public tags SHALL be usable by permitted editors.
Leadership SHALL NOT be required and staff status alone SHALL NOT override
catalogue policy.

#### Scenario: Member classifies a template using a team tag

- **GIVEN** a creator has active membership in a tag's active team
- **WHEN** that creator associates the active team tag with their model
- **THEN** the association is saved without requiring team leadership
- **AND** another active membership need not be the selected specialty.

#### Scenario: Public principal tag still requires its team authority

- **WHEN** an editor outside a principal tag's team tries to associate it
- **THEN** the request is denied unless catalogue administrator authority applies.

#### Scenario: Forged or stale association request fails atomically

- **WHEN** an editor requests a new link to an unknown, inaccessible or newly
  ineligible tag
- **THEN** a generic validation error is returned without restricted metadata
- **AND** no template fields, associations or audit changes from that request save.

#### Scenario: Template editing does not follow tag membership

- **WHEN** a team member who does not own a model tries to edit its tags
- **THEN** existing ownership and administrative editing rules still apply.

### Requirement: Safe retention of report template associations

The system SHALL preserve links the editor cannot currently remove, including
hidden links. Existing inactive or archived links SHALL remain retainable and
removable by authorized actors, but SHALL NOT be newly assigned. Legacy edits
that omit classification controls SHALL preserve existing links.

#### Scenario: Creator loses a membership before editing text

- **GIVEN** a model retains a tag from a team its creator has left
- **WHEN** the creator edits model text with their remaining authorized tags
- **THEN** the protected association remains without being exposed in the editor.

#### Scenario: Historical tag can be retained or removed

- **GIVEN** an existing association has become inactive or archived
- **WHEN** an authorized editor retains it or explicitly removes it
- **THEN** the requested authorized change is saved
- **AND** adding that tag to another model remains denied.

#### Scenario: Empty selection is distinct from omitted controls

- **WHEN** an editor explicitly submits an empty classification selection
- **THEN** only associations they may remove are cleared
- **AND** a legacy submission omitting classification controls changes no links.

### Requirement: Audited report template association changes

The system SHALL record association additions and removals with actor, time
and reconstructible tag identities. Tag-only edits SHALL be attributable.
Failed changes SHALL leave no partial history; patient clinical events SHALL
NOT be created for template classification. Inspection SHALL use authorized
technical data access; this change SHALL NOT add an audit-history UI.

#### Scenario: Tag-only edit has an audit trail

- **WHEN** a creator replaces one authorized classification tag with another
- **THEN** history identifies the actor, time and removed/added identities
- **AND** no patient event is created.

#### Scenario: Audit is inspected technically without a new screen

- **WHEN** an authorized operator inspects stored association history through
  existing technical data access
- **THEN** actor, time and added/removed identities are reconstructible
- **AND** no new audit page, endpoint or application-user permission is required.

### Requirement: Template visibility independent of tag metadata

Classification SHALL NOT broaden or restrict template authorization.
All report discovery and editing surfaces SHALL expose tag metadata only to
current authorized readers. Restricted identifiers, labels, counts and history
details SHALL NOT leak through public templates or error responses.

#### Scenario: Outsider sees public model but not team metadata

- **GIVEN** a public model has only a restricted tag from another team
- **WHEN** an outsider opens discovery with no tag predicate
- **THEN** the public model is available without that tag's metadata or hidden count.

#### Scenario: Private model remains private despite shared tags

- **WHEN** another user filters for a tag on a private model they do not own
- **THEN** the private model is absent from results and counts.

#### Scenario: Membership revocation affects the next response

- **WHEN** a viewer's team membership is revoked
- **THEN** subsequent HTML, JSON and affected history views omit its restricted
  metadata even within an existing session.

### Requirement: Consistent report template tag matching

The system SHALL offer multi-tag ANY and ALL discovery on the model catalogue
and report-creation selector. ANY SHALL require one selected identity and ALL
every selected identity. Results SHALL be distinct and conjunctive with name
search and existing eligibility. Untagged models SHALL match no non-empty tag
predicate and remain discoverable after clearing it.

#### Scenario: Combined tags and name narrow results

- **GIVEN** model A has tags X and Y, B only X, and C no tags
- **WHEN** X and Y are selected with ANY
- **THEN** A and B match within name and eligibility constraints
- **AND** ALL matches only A, while C requires clearing the tag predicate.

#### Scenario: Management and creation retain different active eligibility

- **WHEN** identical valid filters are used on both surfaces
- **THEN** eligible active public-or-own models match consistently
- **AND** inactive models remain manageable in the catalogue but not selectable
  for a new report.

### Requirement: Shared report discovery specialty defaults

Both report discovery surfaces SHALL use the patient list/map's current
specialty defaults: explicit manual state first, saved preference second,
valid principal tag with ANY third, otherwise no tag predicate. Explicit saved
empty selections SHALL suppress principal fallback. Browsing SHALL NOT save
preferences or invent separate report defaults.

#### Scenario: First entry uses the existing saved preference

- **WHEN** a user opens either surface without manual tag state
- **THEN** the current valid specialty's saved tags and mode are visibly applied
- **AND** the same preference remains shared with patient list and map.

#### Scenario: Empty preference and absent specialty apply no tags

- **WHEN** a specialty preference is explicitly empty or no valid specialty exists
- **THEN** no tag predicate is applied and no principal tag is silently inserted.

#### Scenario: Invalid automatic defaults warn safely

- **WHEN** some saved default tags are inactive, archived or inaccessible
- **THEN** only valid defaults apply with a generic warning
- **AND** if none remain there is no tag predicate or silent preference rewrite.

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

### Requirement: Discovery preserves report creation state

With JavaScript enhancement, searching, filtering, clearing, reapplying and
paginating template results SHALL NOT submit, navigate or modify an in-progress
report or change its chosen model.
A still-authorized selected model outside filtered results SHALL remain selected
and visibly separate. Presentation filters SHALL NOT become submission
authorization. Existing explicit model application behavior SHALL remain.

#### Scenario: Filtering leaves edited report fields untouched

- **GIVEN** the user has entered title, document date and markdown
- **WHEN** the enhanced selector is searched, filtered, cleared or paginated,
  or its historical-options toggle is changed
- **THEN** every edited field and the selected model remain unchanged
- **AND** no clinical record is saved or placeholders re-rendered.

#### Scenario: Selected model falls outside results

- **WHEN** the user filters away a still-authorized selected model
- **THEN** it stays selected with an outside-results indication
- **AND** the matching result count excludes that pinned choice
- **AND** form validation still accepts it even if it is outside the current page.

#### Scenario: Revoked choice fails and manual creation remains available

- **WHEN** a submitted model is now inactive or private to someone else
- **THEN** server-side validation rejects it regardless of previous display
- **AND** subsequent lookup responses expose no unavailable model metadata
- **AND** explicitly clearing the choice permits manual creation.

#### Scenario: Unenhanced discovery is explicit and usable

- **WHEN** JavaScript is unavailable
- **THEN** separate GET controls provide filtering and pagination without nested
  forms, with a warning to filter before editing because navigation occurs
- **AND** report duplication and update forms retain their existing behavior.

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

### Requirement: Clean reliable report discovery presentation

Report catalogue and report-creation filters SHALL render without developer
comment delimiters or comment text. Their tag lookup SHALL expose clickable
matches on first entry with cache-safe assets and an input-anchored panel.
Responsive alignment SHALL preserve existing filter, explicit Apply and
clinical-content isolation behavior.

#### Scenario: Developer comments stay out of the page

- **WHEN** either report discovery surface renders
- **THEN** multiline template comments do not appear as visible page content.

#### Scenario: Independent report first entry

- **GIVEN** legacy static URLs were cached
- **WHEN** a report discovery surface is opened directly and a tag is searched
- **THEN** matching rows are visible without navigating to patient pages
- **AND** filtering does not alter in-progress clinical content.

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

### Requirement: Searchable report template classification editor

With JavaScript enhancement, template create/update SHALL offer searchable
authorized choices and selected chips. Ordinary click/tap SHALL add several
different offered identities without replacing earlier selections or requiring
Ctrl/Cmd. Already selected results SHALL be marked and inert; chips SHALL expose
explicit removal. Neither search nor selection SHALL create catalogue rows.

The offered universe SHALL be the existing server-approved editor choices, not
the broader discovery read lookup. Local search SHALL be case/accent-insensitive,
retain original labels and change neither authority nor pending selections.
No new tag lookup or permission SHALL be required.

#### Scenario: Creation accumulates two tags without modifiers

- **WHEN** an authorized creator clicks offered X then Y without modifiers
- **THEN** both chips are selected exactly once
- **AND** Criar Modelo persists both through existing validation

#### Scenario: Search does not alter selection or fetch other metadata

- **GIVEN** X is selected in the editor
- **WHEN** a label query is entered, changed or cleared
- **THEN** only already offered matching choices are shown without requests
- **AND** X stays selected and no broader readable-only tag becomes selectable

#### Scenario: Existing historical and protected links keep their boundaries

- **GIVEN** an editor may remove an existing historical link but not a hidden link
- **WHEN** the form renders and the historical chip is removed and saved
- **THEN** its visible state label and authorized removal work as before
- **AND** the hidden link is neither exposed nor removed
- **AND** a later GET does not offer the removed historical tag as a new choice

### Requirement: Deferred classification editor persistence

Tag search, additions and removals SHALL remain local draft changes until the
normal Criar/Salvar Modelo submit. They SHALL NOT submit/navigate, change
history, save preferences or modify name, markdown, active/public switches or
clinical data. Search-field Enter SHALL NOT submit the parent form.

The existing enabled tag_ids field and tags_present=1 marker SHALL remain the
single submission contract. Empty classification SHALL NOT become missing
legacy controls. Bound validation responses SHALL retain authorized submitted
selection, including empty, rather than reintroducing stored initial tags.
Current atomic validation, ownership, per-tag authority and audit SHALL remain.

#### Scenario: Last-chip removal stays unsaved until explicit Save

- **GIVEN** edited markdown/name and one selected editable tag
- **WHEN** the chip is removed without saving
- **THEN** the other inputs and database remain unchanged
- **AND** explicit Save can then persist the empty editable selection

#### Scenario: Another field fails validation

- **WHEN** Save fails placeholder/name validation after changing tags
- **THEN** authorized submitted selections or explicit empty remain represented
- **AND** edited fields/errors remain available for correction and retry
- **AND** forged or revoked identities do not become labels or client options

#### Scenario: Current authority is enforced again on Save

- **GIVEN** a tag was offered before authority changed
- **WHEN** an invalid new association is submitted
- **THEN** the current generic validation and atomic rollback still apply
- **AND** no template fields, tag links or history partially save

### Requirement: Accessible progressive classification controls

Enhanced controls SHALL provide a visible associated search label, keyboard
operability, predictable focus after chip removal and polite selection status.
Removal names SHALL identify the tag and targets SHALL be at least 24x24 CSS px,
or 44x44 for coarse pointers. Long labels and results SHALL remain contained at
1440, 390 and 320 CSS pixels without introducing page overflow.

The native field SHALL remain usable when JavaScript is absent or initialization
fails, with explicit desktop Ctrl/Cmd guidance. Its enabled selected values and
the existing marker SHALL post multiple or zero tags without duplication.
Generic no-options/no-match messages SHALL NOT reveal protected identities or
counts. Dynamic text SHALL be escaped/text-only.

#### Scenario: Keyboard and touch remove the final chip

- **WHEN** keyboard or touch activates the final chip's named removal control
- **THEN** no replacement selection is required and a sensible focus remains
- **AND** no parent-form submit or unrelated field change occurs

#### Scenario: Native fallback and blocked script remain usable

- **WHEN** JavaScript is disabled or the editor asset cannot initialize
- **THEN** the native select, label, guidance and errors remain visible
- **AND** multiple selection and explicit empty POST retain existing semantics

#### Scenario: No offered choices does not expose hidden associations

- **WHEN** the editor has no authorized choices or no local label matches
- **THEN** a generic field-level explanation is shown
- **AND** no hidden tag identity/count, default tag or creation action appears
