# Runtime Verification Contract

## Purpose and Authority

This is the shared runtime evidence contract for S1–S3, not a fourth slice or a
new application harness. Each worker owns its feature verification script and
assertions. The operator owns shared-stack fixture provisioning, membership and
catalogue transitions, schema application, restoration and cleanup.

At slice start, check that the operator has supplied the fixture manifest,
required browser tooling and a plan to serve this checkout with its schema.
Missing prerequisites mean `BLOCKED_NEEDS_DECISION`; focused unit tests alone
do not satisfy mandatory runtime acceptance. Never create shared-stack users,
teams, catalogue tags or memberships merely to unblock verification.

## Mechanism and Allowed Evidence Paths

Use a standalone Node/Playwright script with system Chrome and the existing
Playwright dependency under `.pi/skills/verify-eqmd/harness/node_modules/`.
Resolve that installed package explicitly from the script; do not import the
supervision harness's journey runner or invoke its fixed scaffold/cleanup.
If the package or Chrome is unavailable, stop for the operator: no new package,
browser install or repository harness change is authorized by this contract.

Write the reproducible script and final run evidence under:

```text
/tmp/eqmd-report-template-verification/<run-id>/
  manifest.json
  verify-S1.mjs | verify-S2.mjs | verify-S3.mjs
  run-instructions.txt
  assertions.json
  requests.jsonl
  screenshots/
  traces/
  probes/
```

The worker may create these named evidence deliverables outside the repo. Keep
script, invocation/environment requirements, assertions and traces as final
verification deliverables. Remove unrelated temporary scratch files; do not
copy credentials into the manifest, logs, reports or repository. This path is
not authorization to create unrelated tools or application code.

Real interaction is required: login, controls, native choices, EasyMDE typing
and submit where the scenario calls for it. Read-only DOM/ORM probes supplement
rather than replace the user journey. All Python/manage.py probes run through
`docker exec eqmd_dev` and may not mutate the shared database.

Before trusting UI proof, record the served checkout path/revision and compare
the relevant served file contents with the edited worktree; matching HEAD alone
does not prove uncommitted changes are served. Do not restart, remount or migrate
the shared stack to fix a mismatch.

## Operator-Owned Fixture Manifest

The operator supplies or explicitly approves the run's disposable fixtures,
recording exact identities, ownership/run ID and intended initial state. The
manifest names credential environment variables, never passwords. Supply only
fixtures required by the current slice:

| Slice | Required identities and states                                    |
| ----- | ----------------------------------------------------------------- |
| S1    | Creator in active team A; outsider; public and team tags          |
| S2    | Profile defaults; X/Y, template-only, historical tags; 21+ models |
| S3    | S2 fixtures, disposable patient and revocable selected model      |

For S1, include any ordinary-staff/catalogue-administrator roles needed by live
checks. For S2, include inactive and archived readable tags, an unreadable team
tag, duplicate/accented model names, inactive models, an untagged model and a
foreign private model. Record which profile has saved tags/mode and the expected
result IDs; do not infer fixture ownership from a name prefix alone.

Workers may create or edit report templates/reports through the real UI only
with manifest-listed disposable actors and patient, as required by the slice.
Record exact newly created IDs for the operator's cleanup. Other shared-state
changes, including memberships, tag lifecycle and profile defaults, are performed
by the operator at documented checkpoints, not improvised in a worker shell.
Automated Django tests retain their normal isolated test-database fixture flow.

For revocation/lifecycle scenarios, name the checkpoint, exact owned record,
operator action, before/after state and restoration responsibility in the run
instructions. The operator performs the transition between recorded requests.
If that coordination is unavailable, stop as blocked; do not mutate real users
or silently replace the scenario with a mock.

The operator restores and cleans up exactly the owned fixture IDs after both
successful and failed runs. The worker records created IDs and cleanup handoff
in its evidence report; no broad prefix deletion, drop/truncate or unrelated
fixture cleanup is authorized. Evidence survives data cleanup.

## Deterministic Network and Browser Scenarios

Use Playwright's request routing in the isolated verification context:

- Out-of-order responses: intercept discovery requests with `page.route`, fetch
  real backend responses using `route.fetch`, hold the older response, deliver
  the newer query response first and release the older one with `route.fulfill`.
  Assert the rendered q/results/options still describe the newer request.
- HTTP failure: fulfill one discovery request with a controlled 503; optionally
  use `route.abort` for the transport-failure case. Assert visible error, no
  successful empty/unfiltered replacement and no cleared selections.
- No-JS: create a separate context with `javaScriptEnabled: false` and exercise
  the real GET fallback. Capture the warning and form structure.
- Content preservation: record exact title/date/selected ID and EasyMDE value,
  observe main-frame navigation and clinical POST requests, operate each
  discovery control including the historical toggle, and assert no changes.

Never fabricate successful model/tag payloads as feature evidence. Routing may
control delivery order or induce failure; permission, projection and matching
checks must use actual backend responses for the signed-in fixture actor.
Remove route handlers between scenarios so fault injection cannot contaminate
subsequent observations. Redact authentication material from request logs.

## Evidence and Cross-Slice Handoff

Every slice report references its manifest, script, exact invocation, assertions,
served-code verification and artifacts. It records prerequisites, exit statuses,
created record IDs, operator checkpoints and cleanup handoff. A reviewer must be
able to rerun the same scenario with newly approved equivalent fixtures.

Also include the implementation-interface handoff required by design D7: actual
module paths, exported function signatures/return shapes, consumers and tests,
plus a list of optional helpers that exist or were not needed. The next worker
must read the preceding accepted report and referenced source; a missing handoff
or required runtime prerequisite is a blocker, not an assumed pass.
