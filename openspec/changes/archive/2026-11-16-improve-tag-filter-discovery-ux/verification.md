# Runtime Verification Contract

## Purpose and Authority

Provide reproducible browser and executable evidence for TFUX S1–S4. Automated
Django tests run normally in their isolated test database. Browser checks use
the already-running development stack, not a server started, restarted,
remounted or migrated by a worker. Workers do not create shared-stack users,
patients, teams, memberships, tags, preferences or templates merely to enable
verification.

No production application implementation is authorized by this file. Evidence
scripts and artifacts live outside the repository as named below.

## Evidence Location and Tooling

Use system Chrome and the already-installed Playwright package under
`.pi/skills/verify-eqmd/harness/node_modules/` without inventing a new project
harness or dependency. A standalone slice evidence script imports that package
explicitly. If tooling or Chrome is unavailable, stop and report the blocker.

```text
/tmp/eqmd-tag-filter-ux/<run-id>/
  manifest.json
  verify-TFUX-S<1..4>.mjs
  assertions.json
  requests.jsonl
  screenshots/
  probes/
  run-instructions.txt
```

The slice report is `/tmp/sirhosp-slice-TFUX-S<n>-report.md`. Every assertion
records status, role, viewport, action and observed expectation. Preserve both
failing-before and passing-after evidence. Do not persist passwords, storage
states, authenticated traces or unredacted request headers/cookies.

## Served Checkout Gate

Before trusting a run:

1. Confirm `eqmd_dev` is already running and login responds successfully.
2. Record `/app` checkout path and revision plus workspace revision.
3. Compare every implementation and built asset file touched by the slice
   between workspace and `/app`; matching hashes are required. Do not restart,
   remount or edit the served tree to obtain agreement.
4. Run read-only database connectivity/migration checks as appropriate; this
   change approves no migration.

A mismatch marks runtime evidence `BLOCKED_NEEDS_DECISION`, not passed. Record
console errors and treat a relevant new error as a failed scenario.

## Operator-Owned Fixture Manifest

The operator supplies or explicitly approves disposable fixtures and their
credentials as environment-variable names. The manifest records exact IDs,
owners, intended initial states and cleanup responsibility. Browser setup must
not infer ownership from a name prefix alone. Existing real records are never
repurposed for lifecycle/revocation tests.

Required logical scenarios, realized using the smallest approved fixture set:

- Viewer with a valid active specialty/saved ANY tag preference and a colleague
  outside that restricted tag's team.
- Active X/Y tags, a patient with both, a patient with only X and an otherwise
  eligible untagged patient; enough tags beyond 20 to prove internal scrolling.
- A long tag name and readable inactive/archived tags. Model-only active tags,
  historical template associations and restricted tags hidden from an outsider.
- Ward tree with matching/nonmatching occupancy and an independently
  controllable empty-ward display scenario.
- More than 20 public/own models for pagination/history, tagged X/Y/XY,
  untagged, accented names and at least one filter combination with zero match.
- Report-creation user, disposable patient and authorized selected model,
  including a case where filtering moves the selected model outside results.

Cleanup/restoration is operator-owned and exact-ID scoped. Worker journeys that
only browse/filter must not POST clinical or preference data. Any fixture
transition needed for revocation is performed by the operator with before/after
records; it is not improvised in a worker shell.

## Browser Matrix

Use real login forms and isolated browser contexts per role.

- Desktop: 1440x900.
- Mobile: 390x844 and 320 px width, with touch/coarse presentation where target
  size is asserted.
- JavaScript enabled for enhancement and a separate `javaScriptEnabled: false`
  context for native fallback.
- Keyboard-only sequences for lookup, selection/removal and Apply.
- Screenshots supplement executable DOM/text/network assertions; they do not
  replace them.

Every run includes the served-checkout gate and asserts no relevant new console
errors. Requests logs redact authentication and contain URLs/status/timing only.

## Deterministic Network and State Scenarios

Use `page.route` with `route.fetch` to delay real backend responses and prove
only the latest explicit result/option request renders. Use `route.fulfill`
only to induce 503/network failures. Never fabricate successful tags, models,
patients or permission payloads. Remove routes after each scenario.

For draft/applied checks:

1. Record server-derived initial applied state and results.
2. Change q, status/ward as applicable, tags, mode and empty-ward visibility;
   verify results and canonical applied URL stay unchanged and dirty appears.
3. Revert values one by one and prove dirty tracks normalized equality.
4. Apply once and assert resulting patient/model IDs, count, summary, controls
   and URL agree. Apply must not issue a clinical or preference POST.
5. With another pending draft, invoke each supported clear/reapply/badge/page
   action and prove that unrelated pending values are not silently committed.
6. In asynchronous report flows, induce failure and prove last results/URL,
   draft and error/dirty indication remain honest and retryable. Patient/map
   retains its normal full-page GET transport and option-request recovery.

For report history, record `history.length`, perform a no-op Apply, draft edit,
option-only historical toggle and successful Apply A→B. Only meaningful
successful result-state transitions may increment appropriately. Browser Back
must restore A and Forward B without a duplicate request loop or another pushed
entry. Failed requests never commit a new canonical URL.

## Per-Slice Obligations

### S1 — Language and recovery

- Capture old icon-only/ambiguous labels and filtered-empty CTA as reproducible
  failing-before evidence.
- After implementation, verify exact task wording and accessible names across
  patient list, map and report catalogue.
- Exercise filtered-zero and genuinely unfiltered empty contexts. The latter
  may be covered by isolated view tests if the shared browser stack cannot
  provide a safe genuinely empty account; filtered-zero requires browser proof.
- Assert filtering results, query parameters and existing application timing
  are unchanged in this slice.

### S2 — Stable patient/map selector

- Record old unbounded card-height growth and Escape/reopen behavior before
  implementation. Measure the same panel and card after opening and loading a
  second page of real approved options.
- Prove click-outside/Escape closure, focus return, click/focus reopen,
  Arrow/Home/End/Enter/Space, selected-row state and chip removal.
- Measure chip text/target rectangles at desktop/mobile and inspect horizontal
  overflow with long tags at 320 px. Assert contrast using computed colors and
  a recorded WCAG calculation when possible.
- Cover list q/status/tags/mode and map q/ward/tags/mode/empty-wards. Empty
  wards cannot trigger a form submission or apply an unrelated draft.
- Exercise native no-JS GET repeated tags, pagination and explicit preference
  state regression without saving preferences during the journey.

### S3 — Report catalogue parity

- Failing-before browser evidence: native multiple is still used, typing q
  updates results before Apply, no normalized dirty indication exists and Back
  after a pushed filter does not restore matching results.
- Prove the enhanced selector accepts active, template-only, long and
  historical tags, remains viewport-bound and reads repeated/selected safe IDs.
- Prove the generic report lookup boundary for reader/outsider independently of
  patient-record permission. Never sample a restricted hidden tag payload.
- Verify explicit Apply, scoped pending actions, stale/failing responses,
  20-model pagination, filtered-empty recovery, native no-JS and Back/Forward.
- Confirm report creation remains on one functioning controller with no
  duplicate listeners; this is a regression guard, not the S4 completion proof.

### S4 — Report creation parity

- Start with real sentinel values in title, document date, EasyMDE content and
  selected model; record model-in-results and model-outside-results variants.
- Run pending edit/Apply, ANY/ALL, historical on/off, clear/reapply, applied
  badge removal, pagination, failure and Back/Forward. After every interaction,
  assert exact sentinel equality, zero clinical POSTs and zero unexpected main
  document navigation.
- Prove no duplicate event handlers or duplicate repeated-tag values. Explicit
  model application/selection must still navigate/prefill only through the
  pre-existing workflow when intentionally chosen.
- Repeat keyboard/mobile checks and validate retained outside-results,
  revoked-choice and manual-creation behavior with operator-managed states.
- In no-JS mode, prove separate GET form, no nested clinical form and visible
  pre-edit warning. Duplicate/update forms remain without discovery controls.

## Report and Handoff

Each report includes requirement-to-evidence mapping, changed files, RED and
GREEN artifacts, commands/exit statuses, runtime run ID/manifest, served code
identity, screenshots/probes, console/network status and unexpected scope with
justification. State genuine limitations instead of relaxing assertions.

S2–S4 handoffs name actual implemented selector attributes/events, state and
URL helpers, lookup/view response shapes and consuming assets. An optional path
mentioned in planning is not a dependency unless its delivered interface is
named in the accepted prior report. No credential or patient-identifying
fixture content is copied into the repository.

## Verification Record (executed, 2026-11-16)

Contract realized per slice under operator-authorized served-stack runs with
hash-verified overlays and exact-ID disposable fixtures; full restoration
verified after every run (code by hash, fixtures by ID, served tree clean,
server HTTP 200).

### S1 — committed ea546d7

- Review: independent reviewer verdict OK after fixes.
- Suite: full fresh-DB run green; focused apps green.
- Browser `tfux-s1-runtime-01`: 44/44 assertions (patient list, map,
  catalogue language; filtered-zero recovery; no timing changes).

### S2 — committed 7a3f6d8

- Review: independent reviewer verdict OK after fixes.
- Suite: full fresh-DB run green.
- Browser `tfux-s2-runtime-01`: 72/72 assertions (explicit Apply on
  patients/map, stable bounded selector, chips, keyboard/mobile, ward cache
  restored from exact payload snapshot).

### S3 — committed 31bfe44

- Loop: 5 review rounds (BLOCK→OK trajectory), 4 fix rounds incl. the
  operator-approved simplification mandate (controls user-owned; async
  hydration removed; controller 921→704 lines).
- Suite: final fresh-DB 4086 OK (43 skipped).
- Browser `tfux-s3-runtime-01` (operator Option B): 58/58 assertions incl.
  live arbitration of the review-4 fix (pagination-preserving toggle) and the
  review-5 race (reproduced, coherent end state, sub-second triple-action
  window).
- Operator acceptance override: review-5 P1 (scoped action during in-flight
  popstate derives from popped predicate) and P2 (`__reconcile_q` marker
  strip) recorded as DEFERRED in
  `s3-loop-20261115-154045/slices/tfux-s3/acceptance-record.md`; not fixed,
  not regressed by S4.

### S4 — committed 37c1172

- Reviews: R1 BLOCK (1xP0+2xP1+1xP2) → fix-1 (harness browser-faithful
  select stub; stale-selection reconciliation vs current clinical select
  value; native no-JS historical control restored and honored; non-vacuous
  failed-Apply results) → R2 OK-with-notes (3xP2) → fix-2 (wrapper hidden,
  placement assertion, real revoked payload) → R3 OK clean.
- Suite: final fresh-DB 4104 OK (56 skipped); documented pre-existing
  probabilistic substring flakes in `test_template_selection` proven on
  pristine BASE by contraprova and left untouched.
- Browser `s4-runtime-01`: 59/59 assertions (automatic-origin default, clean
  Apply no-op, ANY/ALL, scoped badge/reapply preserving user draft, legacy
  prefill navigation, outside-results pinned with count excluded,
  clear-during-in-flight with no phantom notices (review-2 P1 live), 503
  retention, Back/Forward without new entries, pagination page=2, mobile
  390 geometry, no-JS native fallback incl. historical checkbox honored,
  catalogue+patients regression, zero clinical POSTs, zero console errors).

Evidence roots: `/tmp/eqmd-tag-filter-ux/improve-tag-filter-discovery-ux/`
(s1/s2 runs, s3 loop incl. acceptance record, s4 review bundle and runtime),
slice reports `/tmp/sirhosp-slice-TFUX-S{1..4}-report.md`.
