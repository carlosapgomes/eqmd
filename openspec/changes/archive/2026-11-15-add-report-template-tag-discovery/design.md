# Design: Report template tag discovery

## Context

See `proposal.md` for motivation and `specs/reports/spec.md` for behavior.
Current seams:

- `apps/reports/models.py`: ReportTemplate has no tags and uses simple-history.
- `apps/reports/forms.py`: ReportTemplateForm receives the actor;
  ReportCreateForm validates active public-or-own template choices.
- `apps/reports/views/template_views.py`: public-or-own catalogue, 20 per page,
  with no search; inactive models are still listed for management.
- `apps/reports/templates/reports/report_create_form.html`: explicit template
  selection navigates to the existing GET prefill flow.
- `apps/accounts/services/tag_preferences.py`: manual > saved > principal >
  none, resolved for the valid current specialty on each request.
- `apps/patients/services/tag_policy.py`, `tag_projection.py`,
  `tag_filters.py` and `tag_lookup.py`: catalogue authority, metadata
  visibility, identities, ANY/ALL and explicit manual-empty behavior.

## Goals / Non-Goals

Deliver discovery without changing document content or access decisions.
Keep report-specific queries and transport in reports; reuse catalogue policy
and preference resolution rather than patient association mutation services.
Do not generalize other template families, rewrite patient services or replace
the report renderer/application workflow.

## Decisions

### D1. Catalogue identity and additive schema

Add optional `ReportTemplate.tags`, a many-to-many relation to
`patients.AllowedTag` with reverse name `report_templates`. Use the existing
integer tag identity, not patient `Tag`, Taggit, strings or a copied catalogue.
Enforce unique template/tag pairs through the association table.

Enable native simple-history M2M tracking for `tags`; include its generated
historical association model in the same reports schema migration. Depend on
the current patients migration leaf when generating it, rather than guessing a
future filename. Do not backfill live associations or invent pre-feature audit
records for existing templates.

Alternative rejected: new generic tagging infrastructure. Only reports needs
the relation now; a future family can reuse the proven behavior later.

### D2. Editor authority is separate from catalogue administration

Keep existing template create/update/delete gates, including staff/superuser
update exceptions. Template editing authority alone never grants tag authority.

Use existing catalogue policy for each association:

- Active non-principal public tags: assignable by an authorized template editor.
- Principal public tags and restricted team tags: require active membership in
  their team, or the existing catalogue-administrator override.
- Membership is the union of active memberships in active teams, not only the
  selected specialty; leadership is unnecessary.
- Staff status alone is not a catalogue-administrator override.
- Only active tags may be added. Existing inactive/archived associations can be
  retained, or removed with current per-tag authority.

Provide a reports-owned association service, proposed
`apps/reports/services/template_tags.py`. Save template fields and tag deltas
in one transaction, locking the template, affected catalogue rows and relevant
memberships before revalidating authorization. A rejected request must not save
partial text, visibility, associations or audit changes.

Do not delegate association writes to ModelForm's unrestricted M2M `set()`.
From the current persisted set E, compute removable-by-actor set R and submitted
editable set S, then persist `(E - R) union S`. Read E through the association
table or AllowedTag.all_objects so archived links are not lost through the
soft-delete default manager. Validate every new identity
using assignment policy; existing editable historical identities may be kept.
Hidden or otherwise non-removable links stay outside editable controls and are
preserved. Explicit forged protected IDs get the same generic validation error
as unknown IDs, without echoing their metadata.

New forms send a hidden `tags_present=1` marker. A missing marker in legacy
create/update submissions means no association edit, not clear-all. With the
marker present, an empty selection removes only authorized editable links.
Filter defaults must never populate a new template's classification.

Record the actor and time through template history, including tag-only edits
and association snapshots; a no-op association save must not invent a tag
change. Do not generate patient TagEventReference/Event records. Django admin
must not become an alternative unvalidated tag-write surface.

### D3. Metadata projections and lifecycle

Reuse request-time `tag_projection.Visibility` and `tag_badge` after
visibility checks. A public template may contain restricted associations; an
outsider can still discover/use the template after clearing filters but sees
neither those tags nor hidden association counts.

All new HTML, JSON, validation messages, DOM attributes and any affected admin
history diffs must respect this projection. Native M2M history must not leak
restricted tag names/IDs through the existing SimpleHistoryAdmin. Keep admin
tag controls absent; omit the tags M2M delta field from the built-in admin
history display rather than introducing a new restricted-history viewer.
Audit inspection in this change is technical data-layer inspection only: trusted
operators with existing database/ORM access can reconstruct actor, time and tag
deltas, and automated tests prove those records. This does not grant application
users database access or create a report-author audit-reading role. Store the
full snapshots, but do not register generated historical association models for
browsing. No new audit screen, history endpoint or shared result cache. This
boundary was explicitly accepted by the operator.

Inactive/archived associations persist. Resolve existing links with the
all-objects catalogue before applying visibility, not an active-only/default
manager. New editor choices are active authorized tags plus existing editable
historical tags labelled with lifecycle state.
Discovery's normal choices are active readable catalogue tags plus selected
readable historical identities. An explicit historical-options toggle can expose
readable inactive/archived choices for manual filtering only.

Do not use `filter_tag_options()` unchanged: it currently requires usage by
a patient and would hide tags used only by report templates.

### D4. One discovery contract, two eligibility scopes

Add a typed reports query service, proposed
`apps/reports/services/template_discovery.py`. Keep explicit catalogue and
selectable base query builders rather than a client-controlled permission scope.

- Catalogue base: public or actor-created, including inactive templates as today.
- Report selector base: the same visibility plus active templates only.
- Apply the same resolved tag state and name predicate to either base.
- ANY matches one identity; ALL matches every identity; always deduplicate.
- Name query `q`: trimmed, case/accent-insensitive substring on name only,
  using existing PostgreSQL unaccent support. Empty q means no name predicate;
  over 255 characters produces HTTP 400 with a generic validation message.
- Stable order: name, then primary key. Page size is 20; use the existing
  paginator's forgiving page normalization. Reset page when filters change.
- Prefetch only bounded page associations and project before display.

Reuse `resolve_request_state()` for defaults and existing query-state helpers
for repeated `tags`, `tag_mode=any|all`, `tag_filter=manual` and legacy
`tag`. Do not call patient-specific `apply_tag_selection()`, whose relation
path is `patient_tags`.

Explicit invalid/inaccessible tags or modes return HTTP 400 with a generic
message and no successful unfiltered result. The preference resolver records
some invalid inputs as an error with an empty selection: reports must detect
that error before querying results. Unavailable automatic defaults instead omit
invalid tags, warn generically and apply the remaining defaults, or none.

Clear preserves q and explicitly removes the tag predicate. Reapply preserves q,
drops manual tag state and recomputes defaults. Neither action saves profile
preferences; preference editing stays on the existing profile surface. Automatic
state must not be converted into manual state just by typing q or paginating.

### D5. Catalogue transport and progressive enhancement

Keep the existing catalogue URL and add an optional `fragment=results` response
at that URL. Normal GET renders the page; fragment GET renders a reports-owned
results partial containing table/empty state, effective-filter summary,
pagination and an inert `<template data-template-tag-options>` carrying the
current readable native-select options with selected states. Both use D4 and
identical auth/error handling.

Use a reports-owned filter component with q, native multi-select tag choices,
ANY/ALL, apply, clear and reapply controls. Preserve the established pt-BR
semantics; do not couple it to patient-only context or require changes to the
shared patient tag selector. Include historical choices only on explicit
request, using `include_historical=1`; this controls options, not matching.

With enhancement, toggling historical options fetches this same fragment without
navigation. The client replaces only the native select's options from the inert
block, preserving focus, chosen identities, q, mode and automatic/manual origin.
Readable historical tags already selected remain available even when the toggle
is off; toggling alone neither selects tags nor changes the tag predicate.
Reuse the same option builder for the full page, fragment and D6 JSON response.
Missing/failed/stale option responses must not erase current selections; show
an error and ignore stale responses. Never inject unprojected catalogue rows.

Enhance through `assets/js/report-template-discovery.js`, copied by Webpack:
debounce q by 250 ms, submit tag/mode changes through Apply, cancel or ignore
obsolete requests, and announce loading/empty/error states politely. Pagination
and clear/reapply fetch without full navigation when enhanced. Update canonical
query state without dropping repeated tags or changing automatic/manual source.
Apply returned effective state to controls and summary. An explicit Apply is
a manual override; typing q alone or following pagination is not. A failed
request must not masquerade as an empty or successful unfiltered search.

Without JS, normal GET filtering/pagination remains usable. Render untrusted
labels through Django escaping or textContent, never raw string HTML assembly.

### D6. Report creation integration without content loss

Add authenticated `GET /reports/templates/select/`, named
`reports:template_select`, for selectable-model discovery using D4. It is not
a content-rendering endpoint and takes no patient identifier.

Response fields: `results` (id, name, projected tags), `count`, `page`,
`num_pages`, `has_next`, `has_previous`, and `filter` (source, mode,
projected selected tags, generic warning), and `tag_options` containing the
same readable choices and selected states as D5's inert options block.
The historical toggle fetches these choices without navigation, changing
clinical fields or implicitly applying tags. An optional `selected_template`
UUID is resolved separately against current selectable eligibility and returned
as `selected` (id, name, projected tags), or null with a generic
`selection_unavailable` flag for unknown/ineligible choices. It never broadens
results or their count. Malformed UUIDs and invalid explicit filters return
HTTP 400 and `error` only. Do not serialize markdown, private foreign models
or restricted metadata; avoid shared caching.

The report page shares D5's filter component and enhancement module, but renders
bounded native choices from the selectable result page. Keep
ReportCreateForm.template's validation queryset as the complete active
public-or-own set; presentation filters are not permission checks. Its widget
must render only the current result page plus one currently selected authorized
template, not enumerate that complete queryset.

If the current template stops matching q/tags, keep it selected separately and
label it as outside the current results. Do not silently clear or replace it,
dispatch its change handler, or count it as a matching result. Revalidate its
eligibility through the separate `selected` projection on every lookup, and on
submission. If unavailable, replace stale option metadata with a generic
unavailable label, keep the submitted identity for validation, and explain that
manual creation requires explicitly clearing it. An inactive/private-foreign
choice must still be rejected on submission.

q/tag/mode/clear/reapply/pagination interactions must not submit the clinical
POST form, navigate the document, re-render placeholders or modify title,
document_date, content or the selected template. Keep GET filter controls
outside the clinical form and scoped JS listeners; preserve state on validation
errors.

Explicitly choosing another model continues to use the existing GET prefill
workflow. This change does not introduce asynchronous template application or
change the existing replacement semantics. Only discovery interactions have the
new no-navigation/no-content-loss guarantee.

Without JS, provide a separate GET filter form and paginated bounded choices,
with a visible warning to filter before editing because this fallback navigates.
Do not nest forms. Manual report creation remains possible with no template.
Duplicate/update report forms do not gain template selection.

### D7. Small vertical implementation sequence

S1 delivers create/edit classification, safe visible badges and audit end to end.
S2 delivers searchable, default-filtered catalogue browsing including runtime UX.
S3 reuses S2's query contract and UI behavior in the clinical creation selector.
No separate schema-only, backend-only or testing-only slice is necessary.

S1 must deliver `services/template_tags.py` and
`services/template_tag_projection.py`; S2 must deliver
`services/template_discovery.py` and the shared filter component/discovery asset.
Their accepted evidence reports are the inter-slice handoff: name actual exported
functions, typed signatures, return shapes, callers and relevant tests. Also
identify optional form/test helpers that were created, or explicitly record that
none were needed. A candidate path marked optional is never a prerequisite.
Workers must read the preceding accepted handoff and its actual source before
editing; a missing handoff is a blocker, not permission to invent an interface.
Keep named paths stable; moves outside a later slice's approved paths require
approval. This does not require speculative helpers or implementation ahead.

### D8. Reproducible runtime verification

`verification.md` is the shared runtime contract for all three slices: named
Playwright mechanism, externally stored reproducible evidence, operator-owned
fixture provisioning/restoration/cleanup and explicit blocked behavior when
prerequisites are missing. These proof artifacts are separate from application
implementation and do not authorize a new repository harness or dependency.

## Risks / Trade-offs

- Restricted links on public models -> project metadata per request and preserve
  protected associations on edit; verify outsider HTML, JSON and admin history.
- Membership/lifecycle changes after form load -> lock and revalidate writes;
  resolve read visibility and defaults again on every request.
- Initially untagged catalogue looks empty under defaults -> explain the active
  filter and provide clear/reapply; no automatic backfill.
- M2M auditing is not enabled by ordinary model history -> enable explicit native
  M2M tracking and verify actor, snapshots and transactional rollback.
- Shared dev container can serve another checkout -> record served revision/path
  before accepting runtime evidence; never restart or remount it silently.
- Name scans may grow -> bounded pagination first; no speculative new index.
  Escalate measured performance issues rather than broadening this change.

## Migration Plan

1. Obtain the operator's required migration approval before generation/application
   under repository workflow; planning this change does not authorize either.
2. S1 generates a schema-only additive reports migration for the relation and
   historical relation; inspect the graph and confirm no data migration.
3. Apply only through the operator-approved deployment procedure. Browser checks
   require the served checkout to have that schema; do not migrate shared dev
   merely to unblock verification.
4. Existing templates and clinical reports retain their fields and identities;
   all existing live tag association sets start empty.
5. Deploy built assets with the corresponding backend, then verify a tagged model
   across catalogue and report creation with two team identities.

Rollback: deploy the previous application/assets while retaining additive tables
and accumulated associations/history. Do not unapply/drop tables or discard data
as a routine rollback. A later schema rollback requires explicit approval and
an export/retention plan.

## Planning Status

No unresolved product decision is needed for decomposition. Implementation is
not started. Migration execution and runtime fixture authorization remain
operator-controlled gates, not inferred from artifact completeness.
