# Design: Truthful loading and canonical catalogue actions

## D1. Evidence and accepted behavior

Baseline: 6fd95d6. Chrome diagnosis used real Django/PostgreSQL TestCase data,
saved X/ALL, tagged X/Y models and 21 untagged models. Clear changed 1 to 23
and restore returned 1 in roughly 30-40ms backend time, but a global overlay
remained about 15.5 seconds. The page contains two pageLoadingOverlay IDs.

The current catalogue controller deliberately preserves controls except on
popstate. Thus a restored X/ALL result may coexist with empty ANY controls;
Apply can undo that restore. Existing tests enforce this older behavior.
This change supersedes it only for the new catalogue clear-all/restore actions.

## D2. Correct navigation feedback, not a shorter timeout

The global loader must decide after cancellable event dispatch has completed
whether navigation is still intended. Respect defaultPrevented both before
scheduling and before delayed display. Do not mask intercepted links/forms,
lookup, AJAX completion/failure or clean/no-op Apply.

Keep genuine document navigation, current opt-outs, pageshow/load cleanup and
the defensive timeout. Preserve external/hash/download/new-window handling.
Do not hide the bug by shortening the timeout or disabling loading globally.
The requests themselves, history and application handlers must be unaffected.

Retain the existing overlay in templates/base.html and remove the duplicate
from base_app.html. Pages not using the overlay remain safe.
Use existing versioned_static for main-bundle.js in base.html so cached
unversioned bundles cannot retain the old listener after a rebuild.
No service-worker strategy or clinical caching change is needed.

## D3. Catalogue actions and transport choice

Use one left-aligned wrapping bar in the same order/styles as Lista/Mapa:

- Aplicar filtros submits the complete visible draft. Enhanced Apply remains
  AJAX; clean enhanced Apply stays no-request/no-history.
- Limpar todos os filtros is an immediate full GET. Its canonical URL is a
  fresh QueryDict with only tag_filter=manual and tag_mode=any.
- Usar padrão de tags da especialidade is an immediate full GET. Preserve
  applied q and the applied include_historical lookup option, remove tag
  aliases/mode/manual marker, page and fragment, and recompute defaults.

Clear-all removes q, tags, historical option, pagination, fragment and unrelated
parameters. Mode becomes ANY. Reload remains manual-empty; parameter-free
entry still uses shared specialty defaults. Both actions discard every pending
draft, including edits made during an unfinished Apply. Eligibility is unchanged.

Full GET is intentional: it reconstructs chips, mode, markers and dirty state
from server-resolved data without a second client state model. No-JS follows
the same links. Ordinary draft edits, AJAX Apply/pagination, historical lookup
and popstate retain their existing contract.

Do not reuse the old tag-only clear branch for the new clear-all action.
Legacy tag-only query URLs retain their old scopes, including q preservation.
Report creation retains its current links, AJAX/JSON actions and draft rules.

## D4. Server-owned visibility and refreshed links

Restore is available only for manual state, valid active specialty and a
configured saved preference or principal tag. Saved-empty counts as configured;
automatic entry, absent/invalid specialty and absent defaults do not offer it.

Consume the existing resolved DiscoveryState; do not resolve preferences again
or trust raw tag identities. A typed catalogue-owned action service derives
URLs and visibility. A small TemplateListView subclass adds context and wires
only the existing reports:template_list route. The legacy view/parser stays
unchanged; no business branching belongs in the adapter.

Initial HTML and every results fragment carry server-derived restore visibility.
A catalogue-only restore anchor may exist with the native hidden attribute
when unavailable; it must be absent from visual/keyboard/accessibility actions.
After AJAX Apply, pagination and popstate, refresh that visibility from the
fresh fragment so automatic-to-manual transitions do not leave a stale bar.
Reconcile canonical hrefs from the last applied state, never pending controls,
including after lookup-only historical changes.

Mark the new anchors with an explicit catalogue-only opt-in while retaining
compatible discovery hooks as needed. In initializeDiscovery only:

- Derive clear-all from fresh manual/ANY state, not applied q.
- Let canonical anchors perform native GET; do not preventDefault or fetch a
  competing fragment. Abort/invalidate an older catalogue request first.
- Hydrate restore availability from the new server flag after fragment updates.
  Keep focus sensible if a currently focused restore action becomes hidden.

## D5. Shared templates and bounded legacy edits

The catalogue adapter sets an explicit catalogue_filter_actions flag. Shared
filters branch on that flag; creation/default branches keep their markup and
behavior. Add no report preference-save POST or report-specific default store.

The catalogue results summary is informational, with no applied ×. Filtered
empty results refer to the single bar rather than repeating links. Draft chips
keep accessible tag-specific names and existing 24/44px targets; no bulk
Limpar seleção is introduced.

Do not grow the 1,575-line discovery controller into another workflow.
Allow only a bounded bridge inside initializeDiscovery and its local helpers:
at most 40 added non-comment executable lines, no edits to initializeSelection.
New URL/default logic belongs in the typed service. New tests/harnesses stay
bounded instead of expanding the 619-line S3 test or 1,540-line old harness.
If the bound cannot deliver the contract, stop with an explicit split proposal,
not a silent controller extraction or a second competing catalogue controller.

## D6. Creation and privacy boundary

Report creation's chosen model, pinned outside-results selection, clinical
fields, EasyMDE content, validation and history remain unchanged. Shared global
feedback becomes truthful there too, but no catalogue navigation flag may
reach its controls. Creation stays enhanced in-place, with existing no-JS
warning/separate GET behavior.

Retain public-or-own catalogue eligibility, inactive-model management,
creation's active-only eligibility, requester-visible tags, invalid-input 400
responses, unavailable-default warnings and legacy bookmarks. GET/draft
actions cannot save preferences, memberships, template associations or reports.

## D7. Slices, build and rollback

RTFA-S1 is independently useful: legacy catalogue AJAX stops producing the
false global mask and base-page IDs become unique. RTFA-S2 depends on S1 and
delivers the complete catalogue user outcome. Do not run both in one worker turn.

Each changed source asset requires npm run build. Test real compiled/global
scripts together with the page controllers; the old stub harness alone misses
the defect. Use existing tools/dependencies; no install is authorized.

Rollback restores the affected source/templates/route and rebuilds matching
assets. No data rollback is needed. Do not edit generated static files by hand,
run migrations/generators or restart/remount shared services for verification.
