# Report-template classification editor delta

## MODIFIED Requirements

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

## ADDED Requirements

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
