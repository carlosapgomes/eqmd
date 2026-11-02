# Slice 002: clinical identity guardrails

## Identity

- Slice: S2
  (`slice-002-clinical-identity-guardrails.md`).
- Change: `harden-discharge-report-collaborative-draft`.
- Task: `tasks.md` section 2.
- Depends on: nothing (independent of S1/S3).

## Objective

Clinical users cannot silently lack
`profession_type`, and existing identity gaps are
auditable read-only.

## Read first

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `openspec/changes/harden-discharge-report-collaborative-draft/proposal.md`
- `openspec/changes/harden-discharge-report-collaborative-draft/design.md`
  (decisions D3, D4, D5 are binding for this slice)
- `openspec/changes/harden-discharge-report-collaborative-draft/specs/accounts/spec.md`
- `apps/accounts/models.py`
  (`EqmdCustomUser.profession_type`)
- `apps/accounts/admin.py` (user forms)
- `apps/accounts/signals.py`
  (`assign_user_to_profession_group`)
- `apps/core/management/commands/setup_groups.py`
- `apps/core/tests/test_new_permissions.py`
  (`setup_groups` usage pattern)

Follow the repository engineering policy in `AGENTS.md`
and preserve existing conventions. Prefer the smallest
correct change; avoid speculative abstraction and
unrelated refactoring.

## Requirements

- R1: Admin user forms reject a missing
  `profession_type` for regular users; superusers
  and `User Managers` members stay exempt.
  Evidence: admin form tests for blocked and
  exempt saves.
- R2: A read-only `audit_clinical_identity`
  management command lists active `NULL`
  `profession_type` users (excluding superusers
  and `User Managers` members), profession groups
  missing expected permissions, and non-exempt
  users in no profession group. Evidence:
  command test asserting grouped output with
  exempt users absent from the findings.
- R3: The audit command modifies zero database
  rows. Evidence: test comparing row counts or
  asserting `queries` contain no writes.
- R4: `setup_groups` reconciles an existing empty
  profession group to its full specified set
  (signal-created group scenario). Evidence:
  regression test creating the empty group via
  the signal path, then running the command.
- R5: The field stays nullable; no migration is
  created. Evidence: `git status` shows no new
  migration files.

## Expected blast radius

- Likely: `apps/accounts/admin.py`, new
  `apps/accounts/management/commands/audit_clinical_identity.py`,
  accounts/core tests.
- Sensitive, do not change without escalation:
  field nullability, signal group-assignment
  semantics, `setup_groups` permission sets,
  authentication flows, non-admin user creation
  paths.
- Previous behavior that must hold: superuser
  creation, User Managers workflows, existing
  group permissions after `setup_groups`.

## Failing-before plan

Failing-before evidence (run before implementing):

- targeted test: admin saves a regular user
  without `profession_type` → today succeeds,
  after fix fails validation.
- targeted test: audit command on a fixture with
  gaps → today command missing, after fix lists
  all three gap kinds.
- targeted test: empty signal-created group plus
  `setup_groups` → document today (expected
  pass already) as lock-in baseline.

Record commands, exit codes, and failure output in
the evidence report.

## Implementation constraints

- Read-only audit: no `create/update/delete/set`
  calls on any model in the command path.
- Keep the model field nullable; do not add a
  default or a migration.
- Do not change `setup_groups` permission sets;
  only lock reconciliation with tests unless a
  genuine gap forces a minimal fix (justify).
- Do not implement S1 (predicate) or S3
  (finalization anchoring) in this slice.

## Validation

Focused validation (worker runs during the slice):

- `./scripts/test.sh apps.accounts`
- `./scripts/test.sh apps.core.tests.test_new_permissions`

Project-required gates: see `AGENTS.md` (full suite
via `./scripts/test.sh` before handoff; markdown
lint for touched docs). Do not replicate global
gates here beyond referencing them.

Runtime/verification evidence: audit command
output on a seeded database, plus an admin-form
rejection screenshot or POST transcript.

TDD is required: RED → GREEN → REFACTOR for R1..R4.

## Acceptance criteria

- [ ] Admin blocks profession-less clinical users
      and allows exempt ones.
- [ ] Audit lists all three gap kinds grouped and
      readable.
- [ ] Audit writes nothing (proven by test).
- [ ] Empty-group reconciliation locked by test.
- [ ] No migration files created or modified.
- [ ] Focused suites pass; full suite green; no
      new ruff/mypy findings vs baseline.
- [ ] Evidence report written with failing-before
      and passing-after proof.

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` and evidence if
any of these appear: contradiction in
proposal/design/spec, the User-Manager exemption
check proves brittle (fall back to warning-only
per D3 and escalate), a schema change looks
required, unknown service-account patterns break
under the new validation, or inability to satisfy
R1..R5 without scope expansion.

## Evidence report

Path: `/tmp/eqmd-slice-S2-report.md`.

Include: status (`READY_FOR_REVIEW` or
`BLOCKED_NEEDS_DECISION`), requirements →
evidence, changed files, failing-before evidence,
passing-after evidence, commands with exit status,
runtime evidence, blast-radius expansion with
justification, risks, and open decisions for
humans.

## Worker handoff

Implement only this approved slice. Treat the slice
and referenced OpenSpec artifacts as the
implementation contract. Reconstruct context from
the listed files; do not rely on prior
conversation. Follow the repository engineering
policy. Produce failing-before evidence, implement
the smallest correct change, run focused
validation, and produce the required evidence
report. Do not update `tasks.md`, commit, push,
merge, archive, or start another slice. If a new
decision is required, stop with
`BLOCKED_NEEDS_DECISION` and evidence. Otherwise
finish with `READY_FOR_REVIEW` and
`REPORT_PATH=<path>`.
