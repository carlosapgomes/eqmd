# Reports: Template classification and discovery delta

## ADDED Requirements

### Requirement: Optional report template classification

The system SHALL let authorized report-template editors associate zero or more
existing catalogue tags during creation and editing. It SHALL NOT create or
modify catalogue tags, automatically classify templates from profile defaults,
or copy template tags to patients or generated reports.

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

#### Scenario: Clear and reapply have different effects

- **WHEN** the user clears tags while a name query is active
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
combined with tags, paginated at 20 distinct models in stable order. Typing SHALL
update results without full-page navigation. Loading, no-results and errors SHALL
be distinguishable; stale responses SHALL NOT replace newer results.

#### Scenario: Accent-insensitive dynamic search

- **WHEN** the user types an unaccented portion of an accented model name
- **THEN** matching eligible models appear after a short debounce
- **AND** active tags and matching mode remain effective.

#### Scenario: Pagination searches beyond the initial page

- **GIVEN** more than 20 eligible models match
- **WHEN** the user navigates result pages or changes the name query
- **THEN** paging retains filters and the changed query restarts at the first page
- **AND** searching is not limited to models initially loaded in the browser.

#### Scenario: Out-of-order response and failure are safe

- **WHEN** an earlier request finishes after a later search or a request fails
- **THEN** stale results are ignored and failure is announced without claiming
  successful empty or unfiltered results.

#### Scenario: Oversized name query is rejected

- **WHEN** q exceeds 255 characters after trimming
- **THEN** the server returns HTTP 400 with a validation message.

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
