# Verification: Report-template classification editor

## Baseline

Diagnostic evidence: /tmp/eqmd-report-template-editor-audit/.

- report.md distinguishes native-control UX from a persistence failure.
- Nine Chrome groups proved ordinary second click replaces selection, while
  Ctrl/Cmd adds/removes choices and real form POST saves authorized changes.
- Forty-nine classification/history/view tests passed without skips.
- Create/update still render forms.SelectMultiple with no search/chips.
- Protected and historical links already have deliberate backend semantics.

Those results are diagnosis, not passing-after proof for the new editor.
Before implementation, record current app/asset hashes and the accepted
RTFA-S1/S2 state. Do not reset the uncommitted working tree or regenerate
shared cache to obtain a cleaner baseline.

## Safe Runtime

Use existing system Chrome/installed Playwright and the real rendered pages.
A CSRF-enforcing TestClient/PostgreSQL TestCase bridge is acceptable when
explicitly labelled; it is not a live authenticated-server journey.
Use isolated fixtures only, never the operator's account, real templates or
clinical data. Do not install dependencies, migrate, restart/remount services
or run cache generators.

An editor POST to disposable TestCase-owned templates is required to verify
classification persistence. No patient report may be saved. Login and the
explicit create/update submissions are the only expected POSTs.
Snapshots must distinguish intended template/M2M/history writes from forbidden
profile/membership/preference/catalogue/patient/report/cache mutations.
Rollback and exact-owned-ID post-checks must show zero owned rows remain.
Do not export passwords, cookies, authenticated traces or real clinical content.

## Fixture Matrix

- Non-superuser doctor/resident with a current active team membership.
- Active non-principal public tag and active own-team restricted/principal tags.
- A readable but non-assignable public principal tag owned by another team.
- An inaccessible foreign restricted tag that must never reach the editor DOM.
- Existing editable inactive/archived associations and protected retained links.
- Other creator, plain staff and catalogue administrator negative/positive gates.
- Empty offered-choice context, repeated identities, Unicode/HTML-like labels,
  long labels and case/accent-insensitive search.
- Genuine saved specialty defaults to prove new classification stays empty.
- Valid patient_name placeholder, plus invalid-placeholder/name retry cases.

An additional active membership need not be the selected specialty.
Visibility alone must never grant mutation authority.
Do not simulate an empty choice context by filtering only in JavaScript.

## RED

Use automated failing tests for missing enhancement/submission wiring and a
real browser before journey for the reported interaction:

1. Create: ordinary X click then Y leaves only Y, contrary to the new outcome.
2. Update: there is no named × action for removing the last selected chip.
3. Show native-only UI, no local search and required modifier behavior.
4. Pin the current successful empty/multiple POST semantics, protected retention,
   historical handling and form validation as regression positives.

Missing fixtures/auth, unavailable assets and backend-empty-save assertions
that already pass are not valid RED evidence for this change.

## Passing-After Matrix

1. Direct first entry to create renders a working search/selection UI, seeded
   empty despite saved specialty defaults. No patient-page visit is needed.
2. Click/tap X then Y without modifiers: both chips remain. Click an already
   selected result: no duplicate. Search/clear query: choices update but chips
   and native selected values stay unchanged.
3. Type unaccented/case-varied portions of accented labels. Mark selected rows.
   A no-match term gives generic feedback and never creates a catalogue tag.
4. Remove individual chips, including the final chip, without modifiers.
   Zero state has no replacement/default tag and no form submit/navigation.
5. Fill name/markdown and toggle active/public. Perform search/add/remove using
   mouse and keyboard. Values and database stay unchanged until explicit submit.
   Search Enter/Escape must not submit or clear other form fields.
6. Create with two tags, create with zero, update to different tags and update
   to zero editable tags. Check actual browser POST values, persisted IDs and
   expected audit; preserve protected associations.
7. Keep/remove an existing inactive/archived choice. Preserve its state label;
   after saved removal a fresh GET does not offer it as a new association.
8. Save with another invalid field, once with changed tags and once with zero.
   Re-render preserves authorized submitted state and edited values, shows
   errors and permits retry. A forged/revoked identity is never hydrated as
   an option/chip; rejected changes save no fields/M2M/history.
9. Verify native field remains enabled/named; no duplicated tag_ids inputs.
   Empty enhanced POST retains tags_present=1. Legacy marker omission remains
   untouched. A native form reset, if invoked, resynchronizes only tag display.
10. At 1440/390/320px, use long labels, keyboard focus and coarse pointer.
    Chips/scrollable results stay contained; removal targets are 24/44px.
    Compare shell overflow with the same baseline rather than demanding an
    unrelated pre-existing shell fix.
11. With JS disabled and with the asset blocked, native label/select/help/errors
    remain visible. Test multiple, removal of last selection and actual empty
    POST through the existing marker contract. Desktop modifier guidance is
    expected here; enhanced users do not need it.
12. No-choice state explains the current editor field generically; no protected
    identifiers/counts or read-only-only options enter choices or messages.
13. Smoke accepted catalogue actions and patient list/map filters; assert this
    script loads only in template create/update. Report-creation discovery,
    chosen patient-report model and clinical editor remain unchanged.

## Gates and Handoff

Run the exact slice command, host harness, build, scoped project checks and
strict change validation. Container Node skips require actual host execution,
not a green-by-skip claim. This feature adds no lookup/pagination backend.

Capture source/container/built-asset identity, viewport, action/result evidence,
GET/POST log, intended M2M/history writes and forbidden-write snapshots.
Use /tmp/eqmd-report-template-tag-editor/<run-id>/RTTE-S1/.
Report at /tmp/sirhosp-slice-RTTE-S1-report.md with R-to-evidence mapping,
RED/GREEN, exit statuses, baseline comparison, cleanup, scope decisions and
limitations. Do not make a full-suite claim from focused tests alone.

## Execution record — 2026-11-18

RTTE-S1 is implemented and integrated into main at `0a2a560`.
The operator requested canonical synchronization and archival on 2026-11-18.
This section records execution; the preceding sections retain the original
verification contract.

### Results and identity

- Exact slice Django command: 193 collected, 161 passed, 32 Node-unavailable
  skips. Additional catalogue/loader/layout command: 21 collected, 19 passed,
  two Node-unavailable skips.
- Combined distinct modules: 214 collected, 180 passed, 34 skipped, no failures.
  This is not a full-repository run.
- Host execution: 17 editor, 30 legacy discovery, 17 canonical catalogue and
  38 loader cases passed: 102 total, zero failures.
- Chrome: 22 editor, 33 protected report and six patient-smoke groups passed:
  61 groups, including multiple/zero actual editor POSTs and validation retry.
- Scoped Ruff/format/mypy, syntax/helper bounds, build, OpenSpec and Markdown
  passed. Nineteen existing build warnings remain.
- All nine source/test/generated files match the validated manifests, active
  container and committed main content; the public dev asset hash also matched.
- All nineteen accepted RTFA files and the four classification-backend files
  remained byte-identical.

### Independent review and retained notes

Final fresh-context review by `meta/muse-wonder-1.0:high`: APPROVE_WITH_NITS,
no blocking findings. The reviewer inspected source/evidence but had no shell
tool; reported tests are parent-executed, not reviewer re-executions.

Two non-blocking accessibility notes remain explicitly outside this closure:

- Selected inert result labels still retain the action prefix Adicionar.
- Expanded/collapsed result-panel state is not announced by the search control.
  A future adjustment should respect the current native-button search pattern
  rather than impose an incomplete combobox contract.

These are retained review observations, not claims of corrections or additional
requirements. R1–R7 remain approved with these notes.

### Evidence boundaries and archival checks

Browser proof uses isolated Chrome contexts/current compiled scripts and a
synthetic-origin route through a real CSRF-enforcing TestClient/PostgreSQL
TestCase, not an authenticated live HTTP-server journey. Native routed 302
escapes interception; a disclosed meta-refresh shim follows redirects while
the actual backend 302 and tag-field POST metadata are recorded. No-JS control
and persistence proof is not a live-server redirect claim.

Only intended owned-template/M2M/history writes occurred. Forbidden snapshots
were unchanged and exact-owned-ID rollback checks found zero rows. No operator
account/browser profile, shared clinical/profile data or shared cache was
modified; no secrets or authenticated browser traces were exported.

Report: /tmp/sirhosp-slice-RTTE-S1-report.md.
Evidence: /tmp/eqmd-report-template-tag-editor/20261117/RTTE-S1/.
Review: `388e84af-44a3-4653-b220-5d326f8c6653`, with
`independent-review.md` and `review-reference.txt` in that evidence directory.

Canonical reports sync modifies Optional report template classification and
adds three editor requirements. The RTFA synchronization is separate; protected
authority/history/defaults and the other report requirements remain intact.
