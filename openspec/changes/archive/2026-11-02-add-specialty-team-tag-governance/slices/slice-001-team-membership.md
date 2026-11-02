# S1: Durable team membership and leadership

## Identity and objective

Change: `add-specialty-team-tag-governance`. Tasks: 1.1-1.3 in
[../tasks.md](../tasks.md). Deliver administrator-managed team membership and
multiple leaders with request-time specialty eligibility and revocation.

## Read first

- [Shared execution/report contract](README.md), `AGENTS.md`,
  `PROJECT_CONTEXT.md`, `docs/workflows/coding-standards.md`.
- [Proposal](../proposal.md), [design D1](../design.md),
  [accounts delta](../specs/accounts/spec.md), `openspec/specs/accounts/spec.md`.
- `apps/accounts/models.py`, `admin.py`, `forms.py`, `views.py`, `signals.py`;
  `apps/accounts/migrations/0004_add_medical_specialty_models.py`.
- Existing `apps/accounts/tests/test_medical_specialty_*.py` and
  `templates/base_app.html` specialty menu.

## Requirements and evidence

- **R1:** Admin can retain/deactivate membership and grant multiple leaders.
  Evidence: new `test_team_membership` admin/domain/migration cases.
- **R2:** Properties, profile form and switching API require both active
  membership and active specialty. Evidence: existing specialty regressions and
  revoked-membership request tests.
- **R3:** Revocation invalidates selected context and leadership immediately;
  return retains the membership identity without restoring leadership.
  Evidence: same-session revoke/rejoin integration cases.
- **R4:** Leadership never grants staff permissions or membership administration.
  Evidence: negative admin access and permission-escalation tests.

## Allowed blast radius

- `apps/accounts/models.py`, `admin.py`, `forms.py`, `views.py`, `signals.py`.
- New `apps/accounts/services/__init__.py` and `team_membership.py`.
- New sequential accounts migration files; never edit existing migrations.
- `apps/accounts/tests/test_team_membership.py` (new),
  `test_medical_specialty_models.py`, `test_medical_specialty_properties.py`,
  `test_medical_specialty_admin.py`, `test_medical_specialty_profile.py`,
  `test_medical_specialty_ajax.py`.
- `templates/base_app.html` and `apps/accounts/templates/accounts/profile.html`
  only where eligibility display needs to match the backend.
- `docs/admin_guide_medical_specialties.md` for the delivered membership behavior.
- Operator-approved test-only amendment:
  `apps/outpatientprescriptions/tests/test_integration.py`, only the query-count
  expectation and matching comment in `test_list_view_query_count` (23 -> 19).
  Preserve strict equality; this reflects the shared-template query reduction,
  not permission to weaken performance coverage or change prescription behavior.

No tag schema, preferences, tag management UI, patient authorization or lifecycle
expiration changes. Any additional production file requires a justified,
planner-approved scope amendment under the shared contract.

## Failing-before plan

Add tests demonstrating absent active/leader membership state and continued
specialty eligibility after membership revocation. Capture RED from the focused
module before implementation. Migration tests run only in the isolated test DB.

## Implementation constraints

Follow repository engineering policy; implement only this slice. Additive
migration/backfill preserves assigned actor/time and user-specialty uniqueness.
Keep service decisions out of views/templates. Ordinary admin removal deactivates
the retained row. Do not reuse account-renewal supervisors or profession groups.
Do not apply migrations to development/production databases without approval.

## Validation

Focused:

```bash
./scripts/test.sh apps.accounts.tests.test_team_membership
./scripts/test.sh apps.accounts
```

Project-required gates: `AGENTS.md` and coding standards (full suite immediately
following code changes, scoped Ruff/type checking, changed Markdown lint).

Runtime evidence: admin grants two leaders; ordinary member cannot use admin;
revoked current membership disappears on the next page/API request without logout.
Do not use production accounts/data for this evidence.

## Acceptance criteria

- [ ] R1: multiple leaders and retained membership transitions pass tests.
- [ ] R2: every specialty selection path agrees on eligibility.
- [ ] R3: same-session revocation/rejoin preserves identity without privilege return.
- [ ] R4: no staff/user-management privilege is conferred by leadership.
- [ ] Additive migration, documentation and project gates are evidenced.

## Escalation and report

Stop with `BLOCKED_NEEDS_DECISION` for spec conflict, new product/security choice,
material scope expansion, destructive migration need or unexplained regression.
Write `/tmp/eqmd-team-tags-slice-001-report.md` with status, R1-R4 evidence,
files, RED/GREEN output, commands/exit statuses, runtime evidence, scope
amendments and limitations. No sensitive patient data belong in reports.

## Worker handoff

Implement only approved S1 from the referenced artifacts with fresh context.
Produce failing-before evidence, the smallest correct change and all gates.
Do not update `tasks.md`, commit, push, archive or begin S2. Mark only this slice's
acceptance checklist after verification. Finish `READY_FOR_REVIEW` with the report
`REPORT_PATH`, or stop `BLOCKED_NEEDS_DECISION` with evidence.
