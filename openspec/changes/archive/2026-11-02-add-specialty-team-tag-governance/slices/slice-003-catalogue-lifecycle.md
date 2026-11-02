# S3: Administrative lifecycle and responsibility transfer

## Identity and objective

Change: `add-specialty-team-tag-governance`; tasks 3.1-3.3 in
[../tasks.md](../tasks.md). Predecessor: accepted S2. Deliver administrator
archive/restore/reactivation and responsibility transfer on the same catalogue
identity, with complete actor/time history.

## Read first

- [Shared execution/report contract](README.md), `AGENTS.md`,
  `PROJECT_CONTEXT.md`, repository coding standards.
- [Design D2-D4](../design.md),
  [governance lifecycle/transfer requirements](../specs/team-tag-governance/spec.md),
  [catalogue audit requirement](../specs/patient-tag-audit/spec.md).
- Accepted S1/S2 code; `apps/patients/models.py`, `admin.py`, `forms.py`, catalogue
  views/services; `apps/core/models/soft_delete.py` bulk/restore behavior.

## Requirements and evidence

- **R1:** Active/inactive/archived transitions preserve names, identity,
  associations and principal mapping; administrator restore returns inactive.
  Evidence: admin lifecycle sequence and PostgreSQL state-preservation cases.
- **R2:** Latest action actors/times supplement full immutable history without
  required reasons, including bulk routes. Evidence: multi-actor transition
  history, failed-action rollback and admin bulk-bypass tests.
- **R3:** Administrator transfers responsibility only to an eligible same-team
  leader without changing creator; former responsibility confers no authority.
  Evidence: transfer/revoked/ineligible-recipient policy matrix.
- **R4:** Staff status alone cannot archive/restore/transfer, and a responsible
  leader's policy is limited to own custom restricted edits/deactivate/reactivate.
  Evidence: direct administrative requests and domain negative cases; S6 owns
  delivery of the separate leader UI.

## Expected blast radius

Allowed production paths:

- `apps/patients/models.py`, `admin.py`, `forms.py`, catalogue sections of `views.py`.
- S2 `apps/patients/services/tag_catalogue.py`, `tag_policy.py`.
- New sequential patients migrations for responsibility/action fields, history
  and canonical archived-state checks; never rewrite S2 migrations.

Tests: new `apps/patients/tests/test_tag_catalogue_lifecycle.py`,
`test_tag_responsibility.py`; existing `test_tag_catalogue_governance.py`,
`test_team_tag_migrations.py`, `test_history.py`, `test_soft_delete.py`.
Docs: `docs/patients/tags_management.md`, `docs/security/audit-history.md` for
catalogue transitions only.

No assignment/event migration, patient presentation, membership administration,
leader page or preference implementation. Do not alter unrelated soft-delete
models or physically delete catalogue/history records. S5 privacy remains required.

## Failing-before plan

Capture RED when restored tags retain active state, action actors are absent,
creator is changed by transfer, and bulk operations bypass transition checks.
S2 classification/identity suites must remain green; do not rewrite them to hide
migration regressions.

## Implementation constraints

Use catalogue services and transactions for administrative form and bulk actions.
Handle queryset/bulk bypasses explicitly; inheriting the generic restore unchanged
is insufficient. Preserve stale responsible references after membership loss for
history, but grant no management rights until an explicit valid transfer.
Normalize legacy archived state without fabricating historical actors. Keep all
identities and associations; migration tests run only in the isolated test DB.

## Validation

Focused:

```bash
./scripts/test.sh apps.patients.tests.test_tag_catalogue_lifecycle
./scripts/test.sh apps.patients.tests.test_tag_responsibility
./scripts/test.sh apps.patients.tests.test_team_tag_migrations
./scripts/test.sh apps.patients.tests.test_tag_catalogue_governance
```

Project gates: shared contract and `AGENTS.md`. Runtime evidence in admin fixtures:
archive -> restore inactive -> activate, and transfer A -> B while creator stays
A. Demonstrate forbidden ordinary-staff/leader administrative requests.

## Acceptance criteria

- [ ] R1: canonical states and restore-inactive preserve identity/associations.
- [ ] R2: every successful transition is attributed and failed writes roll back.
- [ ] R3: eligible transfer preserves creator and changes management authority.
- [ ] R4: server-side administrator/responsible-leader boundaries pass.
- [ ] Lifecycle docs, additive migrations and project gates are evidenced.

## Escalation and evidence report

Apply shared conditions, especially ambiguous historical attribution, destructive
migration or proposed responsibility rules outside design. Report
`/tmp/eqmd-team-tags-slice-003-report.md` using the shared schema with R1-R4
migration/admin/RED-GREEN evidence and the still-open S5 reader gate.

## Worker handoff

Implement only approved S3 using fresh canonical context and accepted S2 code.
Follow repository policy. Do not update `tasks.md`, commit, push, merge, deploy,
archive or start S4. Return `READY_FOR_REVIEW` with `REPORT_PATH`, or
`BLOCKED_NEEDS_DECISION` with evidence.
