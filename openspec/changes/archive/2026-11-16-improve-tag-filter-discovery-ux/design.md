# Design: Improve tag filter discovery UX

## Context

`apps.patients/templates/components/_tag_selector.html` and
`assets/js/tag-selector.js` provide an enhanced lookup on patient list and ward
map. Reports uses `components/_report_template_filters.html` plus
`assets/js/report-template-discovery.js`; the latter has separate catalogue
(fragment HTML) and creation (JSON) controllers. The shared filter component
also appears in report creation, while clinical edits live in a separate POST
form. Existing backend filters and preference resolution already preserve
manual/saved/principal/none states and requester-safe tag projections.

The change is presentation and interaction orchestration, not new filtering or
persistence. Its main design constraint is avoiding two independent sources of
truth while pending controls differ from the results on screen.

## Decisions

### D1. Three explicit states and one Apply transaction

Use these concepts in code and documentation:

1. **Applied**: the canonical effective predicate that produced the visible
   results, including non-tag predicates and its manual/automatic origin.
2. **Draft**: normalized values currently visible in the filter controls.
3. **Saved preference**: the separately persisted user-specialty setting,
   changed only by the existing explicit preference-save mutation.

The server response initializes applied and draft to the same values. The
client computes equality from normalized values, not just event occurrence:
trim name queries, deduplicate tag identities and compare mode and applicable
non-tag predicates. Returning a control to its applied value clears the dirty
state. Selector option-search text is excluded because it is not a predicate.

For enhanced forms, ordinary edits only change draft and expose the persistent
text **Alterações não aplicadas** near Apply. Apply sends all draft predicates
as one transaction. Applied results, canonical URL and origin are reconciled
only after a successful response; dirty clears only after those representations
agree. Before success, the existing results remain identified by their original
applied summary. On failure, retain results, draft and dirty status and show a
retryable error.

Apply is a text-labelled button in every surface. It need not be disabled when
clean. With enhancement, clean Apply returns without issuing a result request,
converting automatic origin to manual or adding a history entry. An ordinary
form Enter that invokes Apply has the same semantics as clicking it. Apply never
writes saved preferences. Native no-JavaScript forms retain their normal GET.

Patient list/map may keep full-page GET as transport. Report catalogue uses
its results fragment and report creation uses template-selection JSON when
enhanced; neither enters a clinical POST.

### D2. Shortcut, option and navigation actions are scoped

Name-based actions are explicit but are not permission to commit unrelated
draft edits:

- **Remover filtro de tags** creates manual-empty tag state in the applied
  predicate, preserving other last-applied predicates.
- **Restaurar padrão da especialidade** drops manual tag state and recomputes
  the existing defaults, preserving other last-applied predicates.
- Applied-badge removal applies only the named removal to the last-applied
  predicate. Pagination applies only a page change to that predicate.
- In non-navigating report controllers, these actions preserve pending draft
  controls visibly. If their resulting applied state differs from that draft,
  the dirty indication remains; no automatic replay silently applies the rest
  of the draft. Full-page patient/map links instead rebuild controls from the
  newly applied server state; pending form B never enters that request URL.
- Historical-option lookup changes presentation choices only. It may update
  options and its canonical flag immediately, but cannot change result
  predicates or clear the draft. An already-selected readable historical tag
  remains represented when unselected historical options are hidden.
- **Mostrar alas vazias** is a result predicate, not an option-only control;
  changing it becomes pending until Apply and cannot submit q/status/ward/tags.
- Existing clear and reapply query semantics, manual-empty and preference
  precedence do not change. Reworking a global clear-all or the location of
  preference editing is outside this change.

If a shortcut fails, it does not partially reconcile applied state or erase
the draft. Canonical non-JavaScript links retain their existing GET behavior;
the scoped draft requirement applies only where a live draft exists.

### D3. Task-oriented wording and recovery

Use the following canonical Portuguese labels, allowing layout punctuation but
not a return to implementation-oriented terms:

| Concept                  | Required wording                           |
| ------------------------ | ------------------------------------------ |
| ANY                      | `Pelo menos uma selecionada (OU)`          |
| ALL                      | `Todas as selecionadas (E)`                |
| Manual origin            | `Filtro personalizado`                     |
| Manual empty             | `Sem filtro de tags (personalizado)`       |
| Saved empty              | `Sem filtro de tags (preferência salva)`   |
| Apply                    | `Aplicar filtros`                          |
| Clear tag predicate      | `Remover filtro de tags`                   |
| Reapply defaults         | `Restaurar padrão da especialidade`        |
| Historical option toggle | `Mostrar inativas e arquivadas no seletor` |

Give matching mode a visible `Correspondência` label on every surface. Keep the
specialty name adjacent to automatic preference context where available.

A no-result response with an effective name/status/ward/tag predicate says
that no record **corresponds to the current filters**, offers the applicable
remove-tag/restore-default actions and does not call the collection empty of
records globally. Creation CTAs appear only in a genuinely unfiltered empty
collection and only under the existing authorization. Zero-tag manual state
with no other effective predicate is unfiltered, not a request for records
without tags. Unavailable defaults and stale-map feedback remain distinct from
ordinary no-match states.

This slice does not invent a new global clear-all semantic. Existing individual
search/status/ward removal links are retained with specific accessible names.

### D4. Stable and accessible selector presentation

The enhanced option panel is anchored to its selector, overlays following
content and has `width: 100%`, `max-height: min(18rem, 50vh)` and internal
vertical scrolling. Opening, loading more rows or changing result count cannot
change the host filter card's height merely because the option panel opened.
Selected chips and explicit status messages may still occupy their normal
space.

Opening and closing are predictable:

- Focus/pointer entry opens the current loaded list or starts the initial
  lookup. After Escape, focusing/clicking the search field reopens loaded
  results instead of requiring another query.
- Clicking outside and Escape close without removing selected tags. Escape
  returns focus to the search input and preserves its option-search term.
- ArrowUp/ArrowDown/Home/End, native Enter/Space activation, inert selected
  rows, `Carregar mais` and polite status messages retain their current action
  list contract. Do not add a focus trap or replace the established semantics
  with an untested ARIA listbox.
- Lookup failure clears neither selected chips nor a previously usable applied
  predicate and offers a direct retry path by focusing/searching again.

Names wrap at word boundaries and long unbroken values can break safely. All
remove buttons/links have names such as `Remover <tag> da seleção` or
`Remover <tag> dos filtros aplicados`, as appropriate to draft versus applied.
Their hit areas are at least 24x24 CSS px, with at least 44x44 under coarse
pointer/mobile presentation. Result rows retain approximately 44 px targets.

Filter-editor chips use one consistent neutral light surface and dark text on
all surfaces. A tag's custom color may be a decorative swatch, but arbitrary
custom colors never determine text contrast in filter controls. This avoids
the current white-on-teal and white-on-arbitrary-color combinations. Tag
badges inside patient/model result rows are outside scope.

### D5. Reuse selector behavior, not patient permissions or report transport

The existing `data-tag-*` selector contract remains the low-level enhanced
interaction surface. Extend it only as needed for stable panel behavior,
normalized change notifications and configurable URLs/IDs. The host controller
owns applied/draft reconciliation and transport.

For reports:

- Reuse `tag_lookup.search_visible_tags` and its visibility/lifecycle
  projection; do not call patient association queries.
- Add a reports-owned, read-only lookup view/URL with the same authentication
  and read boundary as report-template discovery. Return the established
  paginated badge shape, including selected readable historical identities.
- Do not weaken `TagLookupView.permission_required = patients.view_patient`
  and do not require patient-record permission to discover report templates.
  Do not expose hidden names, IDs, counts or team metadata.
- Keep the native `<select name="tags" multiple>` and repeated GET parameters
  as no-JavaScript fallback, with options from `discovery_tag_options`.
- Reports controllers consume selected IDs and change notices from the shared
  selector; they continue to own fragment/JSON request generation, results,
  loading/errors and URL state. Do not duplicate tag-result rendering in the
  report controller.
- The shared selector's historical control performs lookup-only updates. The
  old reports control must not issue a second competing options request.

Opt enhanced behavior into the catalogue in S3 and report creation in S4.
Before the respective slice, the other surface retains its established working
controller; activation must not produce duplicate submit/change handlers or a
partially initialized selector. No speculative generic lookup framework or
schema is needed.

### D6. Deliberate URL history in enhanced report discovery

Replace automatic per-keystroke history with result-state history:

- Successful Apply, explicit clear/reapply, badge removal and pagination use
  `pushState` only when the canonical applied URL actually changed.
- Option-only historical updates use `replaceState`.
- Draft edits update neither URL nor history entry count.
- A failed request leaves the last-applied URL intact.
- Back/Forward (`popstate`) requests the canonical URL's results without
  pushing a replacement entry, then reconciles controls, applied and draft to
  that state. No duplicate endless Back/Forward refresh is allowed.
- In report creation, history reconciliation also preserves clinical fields,
  EasyMDE content and the current independently authorized model selection.

Name searches no longer debounce into result requests. Debounce remains only
where useful for tag-option lookup (250 ms). Stale-response generation/abort
protection remains mandatory for explicit result requests and option lookups.

### D7. Preserve compatibility and clinical-state guarantees

Existing full/fragment/JSON query validation, 400 responses, stable
20-model pagination, active/public-or-own eligibility, ANY/ALL matching,
manual-empty and historical matching remain unchanged. Full-page and fragment
responses for the same canonical request expose the same effective state.

Without JavaScript, separate GET filter forms remain usable and Apply submits
the visible native fields. Report creation retains its pre-edit navigation
warning, has no nested clinical form and never silently saves clinical data.
Its selected model is projected separately and remains visibly available when
outside current results. Existing explicit navigation that applies a model
continues unchanged; duplicate/update forms do not acquire discovery controls.

Preference saves remain explicit and work with the visible draft selection as
before, but they neither submit the patient/map filter nor register a clinical
POST. This change does not reinterpret the saved-empty or principal fallback.

### D8. Verification-first implementation and independent handoff

Each slice uses RED → GREEN → REFACTOR for deterministic DOM/view behavior.
Browser reproduction supplies failing-before evidence where no lightweight DOM
runner exists; no new frontend test dependency is authorized.

Every browser run follows `verification.md` and records served checkout/file
identity, role, action, expected before failure, actual after behavior,
assertions and screenshots. DOM measurements prove panel containment and target
sizes rather than relying only on visual review. Patient/map checks run at
1440x900, 390x844 and 320px width with long names and 20+ options. Reports adds
explicit Apply, failure and Back/Forward checks. Creation repeats all relevant
checks with title/date/EasyMDE/model sentinels and a prohibition on clinical
POST/navigation.

The accepted handoff at each boundary names actual shared selector hooks,
events, context keys, lookup responses and transport consumers. Later slices
use only delivered interfaces; they do not require hypothetical filenames.
Unlisted but necessary files require concrete justification in the report.

### D9. Small rollout and reversible slices

S1 can ship independently as language and recovery improvements. S2 changes
only patient/map selection and filter-form orchestration. S3 opts catalogue
into the shared selector and history contract after S2 is accepted. S4 extends
the same behavior to creation after S3 is accepted.

Rollback is source/template/frontend deployment in reverse slice order; there
is no database or persisted-data rollback. If S4 is delayed, the catalogue
remains a complete accepted S3 state and creation retains its last accepted
controller without duplicate activation. Any need to weaken authorization,
alter matching results, change preferences or persist schema stops the slice
for a new decision.

## Risks / Trade-offs

- Two report controllers share templates: use explicit opt-in and prove no
  duplicate listeners. Missing coverage can break report creation, so S4 has
  mandatory browser proof even though S3 owns initial integration.
- Overlay clipping inside cards: verify z-index, overflow and mobile viewport;
  do not fix by globally changing every card's overflow.
- Dirty normalization can drift from server state: centralize canonical state
  per host and test typed-then-reverted, duplicate tags and failed Apply.
- Report shortcuts preserve drafts rather than replay them, while full-page
  patient links rebuild from server state: both UIs must identify what actually
  produced results so two states never masquerade as one.
- More frontend behavior increases review surface: preserve current tests and
  use existing scripts/dependencies; no broad JS framework or style rewrite.
