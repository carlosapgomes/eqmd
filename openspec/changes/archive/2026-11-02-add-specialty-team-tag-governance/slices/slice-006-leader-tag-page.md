# S6: Responsible leader team tag page

## Identity and objective

Change: `add-specialty-team-tag-governance`. Tasks: 6.1-6.2 in
[../tasks.md](../tasks.md). Depends on accepted S5. Deliver a team tag page where
eligible responsible leaders create and maintain their custom restricted
labels without catalogue-admin privileges.

## Read first

- [Shared execution/report contract](README.md), `AGENTS.md`,
  `PROJECT_CONTEXT.md`, repository coding standards.
- [Proposal](../proposal.md), [design D1-D4](../design.md),
  [governance spec](../specs/team-tag-governance/spec.md).
- Accepted S1-S5 code; reports are supplementary, not required `/tmp` inputs.
- `apps/patients/urls.py`, `views.py` catalogue paths, `forms.py`;
  services `tag_catalogue.py`, `tag_policy.py`; `templates/base_app.html`.

## Requirements and evidence

- **R1:** An eligible leader can create a custom restricted tag only in a team
  they lead. Evidence: create GET/POST, team namespace and server-derived fields.
- **R2:** Management follows responsible leader rather than creator; other leaders,
  former leaders and members cannot edit. Evidence: transfer/revoke/forged-ID matrix.
- **R3:** Leader actions are limited to editing allowed fields and deactivation/
  reactivation; no public/system tag, transfer, archive or membership controls.
  Evidence: negative direct POSTs as well as rendered controls.
- **R4:** Mobile-usable navigation, team context, lifecycle labels and success/error
  feedback are clear. Evidence: browser flow and focused template assertions.

## Allowed blast radius

- `apps/patients/urls.py`; new `views_team_tags.py`, `forms_team_tags.py`;
  existing `tag_catalogue.py`, `tag_policy.py` for the delivered workflow only.
- New `apps/patients/templates/patients/team_tags.html`, `team_tag_form.html`.
- `templates/base_app.html` for a permission-checked navigation entry only.
- New `apps/patients/tests/test_team_tag_views.py`.
- `docs/patients/tags_management.md` leader section.

No schema migration, ordinary member tag creation, team roster management,
preference UI, general Django Admin access or new frontend dependency.

## Failing-before plan

Write RED request tests for absent team routes and forbidden cross-team/
non-responsible edits. Do not count hidden buttons as authorization evidence.
Use fixtures for two leaders, one transferred tag, a revoked leader and a member.

## Implementation constraints

The team URL is explicit and does not change the user's active specialty.
Leadership eligibility is evaluated per request; membership in another team is
not sufficient. Invoke existing services, do not duplicate policy in controllers.
Origin/visibility/team/responsibility/archival fields are server-controlled.
Keep user-facing Portuguese Bootstrap UI separate from the Django Admin.

## Validation

Focused:

```bash
./scripts/test.sh apps.patients.tests.test_team_tag_views
./scripts/test.sh apps.patients.tests.test_tag_catalogue_governance
./scripts/test.sh apps.accounts.tests.test_team_membership
npm run build
```

Apply project gates from `AGENTS.md`, including full suite, scoped Ruff/types and
changed Markdown lint. Browser evidence: leader creates, edits, deactivates and
reactivates own tag; second leader cannot edit until admin transfer; revoked
leader loses access without logout. Capture desktop/mobile test-fixture evidence.

## Acceptance criteria

- [ ] R1: only valid led-team custom restricted tags can be created.
- [ ] R2: responsibility transfer and revocation alter effective rights immediately.
- [ ] R3: every forged administrative operation is denied without side effects.
- [ ] R4: navigation and mobile workflow are demonstrated without admin escalation.
- [ ] Documentation, build and required gates pass.

## Escalation and report

Stop `BLOCKED_NEEDS_DECISION` if administration of memberships, new schema or a
policy change becomes necessary. Report
`/tmp/eqmd-team-tags-slice-006-report.md` using the shared report schema with
R1-R4 evidence, files, RED/GREEN, command statuses and browser observations.

## Worker handoff

Implement only approved S6 with fresh canonical context and accepted S5 code.
Follow the shared contract. Do not update `tasks.md`, commit, push, merge, deploy,
archive or start S7. Mark this slice's checklist only after verification. Return
`READY_FOR_REVIEW` with `REPORT_PATH` or `BLOCKED_NEEDS_DECISION` with evidence.
