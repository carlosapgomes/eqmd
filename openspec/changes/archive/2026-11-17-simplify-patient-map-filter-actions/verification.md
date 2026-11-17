# Verification: Patient-map filter corrections

## Runtime and fixture boundary

The operator excluded shared cache generation from this delivery. An expired
dev cache is not authorization to run the generator, schedule jobs, rewrite
WardMappingCache rows or change fallback behavior.

Use the standard isolated PostgreSQL test database for automated fixtures.
For browser proof, a TestCase-backed workspace preview with genuine ORM rows,
real permission/default resolution and a healthy fixture cache is acceptable.
Label routed preview versus deployed evidence explicitly. Do not substitute
static screenshots or an empty/updating cache for the required cases.

A live-dev journey is optional and requires operator-supplied/approved
disposable fixtures plus an already usable cache. Missing live fixtures must
not be worked around by changing shared accounts, preferences or cache.

Use installed Playwright/system Chrome under the verify-eqmd skill's safety
rules. No package/browser install, supervision journey/scaffold execution,
server restart/remount, shared generator or migration is authorized here.

## Required primary fixture

Use a normal non-superuser clinical account with view-patient permission:

- Valid active specialty A and a genuine saved non-empty default X/ALL.
- Another readable active tag Y and an inaccessible tag for privacy regression.
- Ward A: eligible Ana X, Ana Y and Ana XY.
- Ward B: eligible Bruno Y and an eligible untagged inpatient.
- Ward C: genuinely empty.
- An outpatient carrying X that must never enter the map result.
- A fresh valid cache referencing those wards/patients, with associations
  reprojected by the real requester-aware service.

The primary actor must not be an empty-profile substitute. Secondary cases
(saved-empty with no principal, principal-only, no specialty/default, partial
or fully unavailable defaults, invalid input) may use isolated integration
tests rather than operator-controlled live lifecycle transitions.

Record exact owned IDs, expected patient/ward IDs, initial specialty/preference
IDs/tags/mode, role, viewport, source hashes and cleanup owner. Record credential
environment-variable names only; never save passwords, cookies, storage state,
authenticated traces or real clinical records in evidence.

## Evidence location

Keep standalone scripts, assertions, sanitized request logs and screenshots in:

```text
/tmp/eqmd-patient-map-filter-actions/<run-id>/
  manifest.json
  verify-S1.mjs
  run-instructions.txt
  assertions.json
  requests.jsonl
  screenshots/
  probes/
```

Use TestCase rollback and exact-owner read-only post-checks for isolated preview
cleanup. Live fixture lifecycle/cleanup remains operator controlled. Do not
delete or restore rows generally. No filter/draft journey may send a clinical
or preference POST; login is the only necessary authentication POST.

## Mandatory journey

1. Parameter-free map uses saved X/ALL with a truthful saved-default label,
   correct eligible result and no redundant restore action.
2. Apply Ana, ward A, Y and show-empty enabled. Show one action bar, a read-only
   applied summary, personalized context and totals matching rendered rows.
3. Type pending Bruno, ward B, different tags and show-empty disabled.
   Clear-all: URL contains only manual/ANY; search/ward/tags are empty,
   show-empty is false, eligible untagged inpatients match and outpatients do
   not. Reload retains this state; separate initial entry still uses X/ALL.
4. Reapply Ana/ward A/Y/show-empty enabled. Enter different pending controls.
   Restore: applied Ana/ward A/show-empty enabled remain, X/ALL returns and
   pending values are discarded. Preferences/membership rows are unchanged.
5. Draft × preserves other pending fields and leaves results/URL/summary
   unchanged. Dirty indication clears on normalized restoration. Clean
   enhanced Apply produces no patient-result request/history change.
6. With JavaScript disabled, initial default tags are present. Deselect all
   native options and Apply: explicit manual-empty, no automatic fallback,
   with the other submitted visible fields applied.
7. Manual-empty with no q/ward omits "resultado filtrado" in full and AJAX
   totals. Mode alone and show-empty alone do not trigger the label.
   Applied q, ward or effective default/manual tags do trigger it.
8. With show-empty and an applied tag/search hiding patients in a populated
   ward, the ward says no patients match the filters. Without patient-narrowing
   predicates, a genuinely empty ward keeps the no-inpatients wording.
   A ward-only selection must not be mistaken for patient narrowing.
9. With valid cache, no-match search and show-empty enabled, wards remain
   visible with zero patients. One visible notice before the tree explains
   both facts, without requiring expansion or repeating recovery buttons.
   Full HTML and AJAX fragment agree.
10. With show-empty disabled and zero matches, show one filtered-empty
    explanation referring to the main action bar. Without effective filters,
    do not claim filtering hid patients. Invalid and unavailable-cache cases
    remain distinct and are not counted as successful empty-result evidence.
11. Check 1440, 390 and 320px, named keyboard controls, readable long labels and
    no added overflow versus the baseline shell. Keep tree controls distinct
    from filter actions. Smoke-check unchanged list and both report surfaces,
    including their lookup/Apply behavior.

Always capture links from the rendered applied state, not values invented by
the driver. Browser actions must use real controls, not internal JS setters.
Do not click the preference-save action during these no-write journeys.

## Automated and project gates

Run the slice's focused command and project-required scoped checks. New
deterministic behavior requires meaningful failing-before tests. Browser RED
must reproduce behavior, not a login/fixture/tooling failure.

If /app serves a different checkout, use an isolated container /tmp copy through
docker exec eqmd_dev, record its identity and compare changed-source hashes.
Do not overwrite /projects/dev/eqmd or modify mounts to unblock verification.
No asset changes are planned; adding one requires scope approval and a build.

Report skips and pre-existing lint/type/spec baselines separately. Do not claim
a monolithic run passed if only batches completed. Fresh batch inventory must
include the new tests, not reuse the previous change's fixed test count.

## Recorded Completion

The operator accepted both the map contract and visual homologation amendment
before authorizing synchronization and archive on 2026-11-17.

Final focused evidence is in /tmp/eqmd-pmfa-layout.g6En43/focused-final.log:
235 tests, 31 skips, no failures/errors. This includes the new layout module.
Chrome evidence there records 30 passing groups, exact-owner cleanup and
unchanged preference/clinical/cache snapshots. The 1440/390/320px list/map
screenshots confirm left alignment and separate bordered display options.
The standalone checklist/report is /tmp/sirhosp-slice-PMFA-S1-layout-report.md.

Historical full-suite evidence is under
/tmp/eqmd-patient-map-filter-actions/20261117-s1/batches/: 4,140 unique IDs
across 298 modules and 32 sequential batches, 4,084 passed and 56 skipped.
It predates visual polish; no post-polish full-suite execution is claimed.

A separately authorized temporary dev binding serves the worktree for manual
homologation. Its read-only readiness, service identity and preserved shared
cache evidence is under /tmp/eqmd-pmfa-env.W5Hza2/. That operation did not run
migrations, the shared generator or shared fixture provisioning.
Git stage/commit/merge and returning dev to integrated main remain operator
steps after this documentation closure.
