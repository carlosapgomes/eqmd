# S4: Authorized patient assignments with atomic audit writes

## Identity and objective

Change: `add-specialty-team-tag-governance`; tasks 4.1-4.3 in
[../tasks.md](../tasks.md). Predecessor: accepted S3. Deliver patient/admin
assignment and removal as policy-checked transactions with stable audit events.
This is a write-path checkpoint, not the S5 read-privacy checkpoint.

## Read first

- [Shared execution/report contract](README.md), `AGENTS.md`,
  `PROJECT_CONTEXT.md`, repository coding standards.
- [Design D4-D5](../design.md),
  [assignment requirements](../specs/team-tag-governance/spec.md),
  [atomicity/identity/immutability requirements](../specs/patient-tag-audit/spec.md).
- `apps/patients/views.py` add/remove/bulk POSTs, `admin.py`, catalogue/policy
  services; `apps/events/models.py`, `admin.py`; existing assignment tests.
- Accepted S1-S3 code; prior reports are supplementary.

## Requirements and evidence

- **R1:** Clinical gates plus per-tag policy apply to patient/admin/bulk writes;
  principal tags require membership/admin even when public. Evidence: member,
  outsider, revoked, staff, leader and administrator request matrix.
- **R2:** Association and event/reference writes commit atomically; duplicate races
  cannot create duplicate associations or misleading events. Evidence: event-write
  and bulk failure injection plus PostgreSQL concurrency tests.
- **R3:** New events carry stable catalogue references and snapshots; conservative
  legacy backfill retains unresolved originals. Evidence: historical-rename,
  mixed-bulk and migration fixtures with known/ambiguous/unresolved identities.
- **R4:** Ordinary audit-event edit/delete is denied; correcting an assignment
  appends an opposing event. Discharge/specialty changes do not clear tags.
  Evidence: direct-action, correction and clinical-transition regression tests.

## Expected blast radius

Allowed production paths:

- `apps/patients/views.py` tag mutation portions, `admin.py` assignment paths;
  new `services/tag_assignments.py`; existing `services/tag_policy.py`.
- `apps/events/models.py`, `admin.py`; new `tag_event_reference.py`,
  `services/__init__.py`, `services/tag_audit.py`.
- New sequential events migrations only; extend
  `apps/patients/management/commands/preflight_team_tags.py` for legacy references.
- `apps/core/permissions/utils.py` tag-assignment and tag-audit-event mutation
  checks; `apps/patients/templates/patients/partials/tag_management.html` bulk label.

Tests: new `apps/patients/tests/test_tag_assignment_policy.py`,
`apps/events/tests/test_tag_audit_writes.py`; existing patients `test_tags.py`,
`test_tag_architecture_refactor.py`, events `test_record_tracking_events.py`,
`test_history.py` and patient transition tests only for tag-preservation assertions.
Docs: `docs/patients/tags_management.md`, `docs/security/audit-history.md`,
`docs/apps/patients.md` current patient-association description.

No read projection/template inventory, current timeline header, ANY/ALL filters,
leader page or preferences. S5 owns metadata redaction. Do not refactor unrelated
clinical-event permissions, admission behavior or catalogue lifecycle.

## Failing-before plan

Capture RED from an event-write failure leaving a changed association, an outsider
mutating a public principal tag, and admin/bulk writes lacking timeline events.
Exercise real transactions and constraints, not only mocked service return values.
Add a legacy event with ambiguous historical names; it must not be guessed.

## Implementation constraints

Call one service from each administrative/user mutation path. Preserve unknown or
unauthorized associations in bulk removal; make its UI label match the authorized
set semantics. Lock/revalidate catalogue and membership/authority as defined in
D5; record conflict behavior without widening permissions. Keep raw legacy event
snapshots intact and preserve current event types/IDs. S5 will handle unresolved
legacy redaction; do not claim it is already safe for non-admin readers here.

## Validation

Focused:

```bash
./scripts/test.sh apps.patients.tests.test_tag_assignment_policy
./scripts/test.sh apps.events.tests.test_tag_audit_writes
./scripts/test.sh apps.patients.tests.test_tags
./scripts/test.sh apps.events.tests.test_record_tracking_events
```

Project gates: shared contract and `AGENTS.md`. Runtime evidence: member/admin
add/remove and authorized bulk removal produce paired events; outsider principal
POST fails; injected event failure leaves no changed association. Use test data.

## Acceptance criteria

- [ ] R1: every patient/admin/bulk mutation entry point enforces per-tag policy.
- [ ] R2: failure/concurrency cases preserve association/event consistency.
- [ ] R3: new references are stable and ambiguous legacy history is unchanged.
- [ ] R4: audit correction/immutability and clinical-transition preservation pass.
- [ ] Write-path documentation, migrations and project gates are evidenced.

## Escalation and evidence report

Apply shared conditions, especially an unlisted write door, undefined concurrency
result or ambiguous clinical mapping requiring a human. Report
`/tmp/eqmd-team-tags-slice-004-report.md` with R1-R4 evidence, migration and
transaction results. Explicitly identify S5 privacy as not yet delivered.

## Worker handoff

Implement only approved S4 from canonical artifacts and accepted S3 code.
Do not update `tasks.md`, commit, push, merge, deploy, archive or start S5.
Return `READY_FOR_REVIEW` with `REPORT_PATH`, or `BLOCKED_NEEDS_DECISION` with
failing evidence and the required decision.
