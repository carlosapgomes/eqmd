# Verification: Report catalogue actions and loading

## Baseline and evidence boundary

The diagnostic report /tmp/reports-template-tag-filter-analysis.md and
/tmp/eqmd-report-filter-audit.1FqPBq/ describe 6fd95d6, not passing-after proof.
Baseline diagnosis: 17 real-Chrome probes, successful roughly 30-40ms backend
responses, about 15.5s overlays, stale controls after restore, duplicated
recovery links and overlay IDs. Existing Django discovery tests passed with
container Node skips; the host harness does not load page-loading.js.

Use PostgreSQL TestCase fixtures and real system Chrome/installed Playwright.
A TestClient bridge with CSRF enforcement is acceptable if clearly labelled.
Do not use the operator's profile, shared data, migrations, generators,
server restart/remount, package installs or real clinical submissions.
Login is the only necessary authentication POST. Store no credentials,
cookies, authenticated traces or real clinical content.

## Fixture

Use a non-superuser reader with a valid specialty and genuine saved X/ALL:

- Models with X, Y and no tags, including nonempty Ana matches and other
  names outside Ana, plus enough visible models to paginate.
- A private foreign model that must never become eligible.
- Readable historical and foreign restricted metadata for regression.
- Secondary isolated saved-empty/no-principal, principal-only, no specialty,
  unavailable-default and membership-revocation cases.
- A disposable patient/model selection and nonempty title/date/markdown for
  creation regression, with no report save during the browser journey.

Record exact owned IDs, role, source/built-asset hashes, viewport and expected
result IDs/counts. Verify preference/membership/association/report snapshots
and TestCase rollback with exact-owner post-checks. No shared cache writes.

## RTFA-S1 browser matrix

1. Reproduce legacy clear/reapply, applied × and pagination with current scripts
   plus the global bundle. Observe successful response under a 15-second mask.
2. After correction, each intercepted action completes with inline status/error
   and no global mask, including after the delayed-show window.
3. Reject a fragment request: previous results/URL remain usable and retryable.
4. Clean enhanced Apply and lookup/historical changes produce no page mask.
5. Ordinary navigation still follows its link, shows feedback when pending and
   clears it on document load/pageshow. Verify normal native form navigation
   with disposable login or a harness, not clinical POSTs.
6. Confirm one overlay ID on catalogue, creation, list and map. Test no-overlay
   documents safely in the unit harness.
7. Verify cached-unversioned bundle versus current HTML/versioned URL without
   changing service-worker strategy; prove actual built bytes were loaded.

Use deterministic fake timers/event propagation in the Node harness to cover
late preventDefault and delayed callbacks. Chrome must integrate the real
global script and page controllers. Do not declare success from a standalone
catalogue stub or hide the overlay manually in a test.

## RTFA-S2 browser matrix

1. Initial automatic X/ALL: correct results and no visible/focusable restore.
2. Apply name Ana and manual Y through AJAX. Restore becomes available in the
   unchanged form; its href reflects applied Ana, not the initial query.
3. Enter pending Bruno/tags/mode/historical choice. Clear-all follows its real
   link by document GET to manual/ANY only. Name/tags are empty, historical
   choice is reset, eligible untagged models appear and private models do not.
   Reload stays empty; separate parameter-free entry returns X/ALL.
4. With applied Ana/Y and pending Bruno/different tags/mode, restore navigates
   by GET, preserves applied Ana/historical option, resets page/fragment,
   renders X/ALL and a clean editor, without saving preferences.
5. Immediately Apply: no request/history or reintroduction of the old draft.
6. Delay an Apply response, then choose canonical clear/restore. Releasing the
   old response cannot rewrite the new page, URL, controls or history.
7. Exercise Back/Forward across AJAX Apply and native canonical actions.
8. Check AJAX pagination, lookup-only historical flag, late edits during Apply,
   input errors and generic retry. Reconciled action hrefs must stay current.
9. Repeat with JS disabled and native empty selection. Cover the default matrix
   and restore visibility after initial/AJAX/popstate changes.
10. Verify exactly one action bar and no empty-state or applied-summary action
    duplicates. Draft × requires Apply and has accessible 24/44px targets.
    Check 1440/390/320px, coarse pointer, keyboard and long names; compare shell
    overflow to baseline rather than accepting any newly introduced overflow.
11. Exercise legacy tag-only URLs: they preserve applied name as before.
12. Creation regression: type title/date/EasyMDE text, choose a model and use
    lookup, Apply, legacy clear/reapply, pagination and Back/Forward. These
    remain in-place; all clinical fields and the chosen model persist, including
    the authorized outside-results case. No catalogue navigation flag appears.
13. Smoke-test accepted Lista/Mapa actions and their independent preference POST
    boundaries without sending a preference mutation.

## Gates and report

Run the exact slice command, host Node harness, scoped project lint/type/format,
npm run build, strict change validation, Prettier 3.6.2 and markdownlint-cli2
0.22.1. Log exit statuses and describe real browser versus routed TestCase proof.
Container Node skips require explicit host execution, not a green-by-skip claim.

Keep evidence under /tmp/eqmd-report-filter-actions/<run-id>/<slice-id>/.
Report R-to-evidence mapping, RED/GREEN, actual code/asset identity, ownership,
cleanup and limitations at /tmp/sirhosp-slice-<ID>-report.md.
If a full-suite claim is made, discover a fresh inventory including new tests;
label batches and pre-existing baselines honestly.

## Execution record — 2026-11-18

Both slices are implemented and integrated into main at `0a2a560`.
The operator requested canonical synchronization and archival on 2026-11-18.
This section records execution; the preceding sections retain the original
verification contract.

### RTFA-S1

- Final focused Django command: 88 collected, 56 passed, 32 Node-unavailable
  skips. Additional regressions: 121 passed, no skips.
- Host execution: 38 loader cases and 30 legacy discovery scenarios passed.
- Chrome: 28 integrated groups passed with current compiled page/global scripts.
- Scoped Ruff/format/mypy, build, static identity, OpenSpec and Markdown passed.
- Independent final review: APPROVE, no findings; `meta/muse-wonder-1.0:high`.
- Report: /tmp/sirhosp-slice-RTFA-S1-report.md.
- Evidence: /tmp/eqmd-report-filter-actions/20261117/RTFA-S1/.
- Review run: `a5ca7bd1-fc26-419c-a57b-34e6af21b390`.

### RTFA-S2

- Final focused Django command: 237 collected, 204 passed, 33 Node-unavailable
  skips. Additional static/layout regressions: 10 passed, no skips.
- Host execution: 17 canonical actions, 30 legacy discovery and 38 loader cases
  passed. Modified/cancelled click regressions preserve source-tab Apply.
- Chrome: 33 report groups and six patient-smoke groups passed.
- Initial P2 concerning modified clicks was corrected and independently closed.
  Final review: APPROVE, no remaining findings; `meta/muse-wonder-1.0:high`.
- Scoped Ruff/format/mypy, build, OpenSpec and Markdown passed. The build retains
  nineteen existing warnings; no dependency update was performed.
- Report: /tmp/sirhosp-slice-RTFA-S2-report.md.
- Evidence: /tmp/eqmd-report-filter-actions/20261117/RTFA-S2/.
- Final review run: `eac7d1be-0f13-4455-a103-cf61a37033d4`.

### Evidence boundaries and archival checks

Chrome used isolated synthetic fixtures and current compiled assets, routing
through a real CSRF-enforcing Django TestClient/PostgreSQL TestCase. This is not
an authenticated live HTTP-server journey. An attempted real Ctrl-new-tab
probe could not route its initial popup and was not counted as passing browser
proof; deterministic modifier tests provide the positive evidence.

All browser fixture snapshots remained unchanged outside intended fixture
operations and exact-owner post-rollback checks found zero rows. No shared ward
cache generator, clinical save or profile/preference mutation was performed.
Container Node skips were explicitly covered on the host, not claimed as
executed Django tests. No full-repository test result is claimed.

Closure compared all nineteen source/test/generated files against the validated
manifests and committed main blobs. Canonical reports sync changes five existing
requirements and adds three; page-navigation-feedback adds three requirements.
Unrelated requirements and existing archives are preserved. The editor change
is synchronized separately and does not redefine these filter requirements.
