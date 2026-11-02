# S2: Namespaced catalogue and principal-tag administration

## Identity and objective

Change: `add-specialty-team-tag-governance`; tasks 2.1-2.3 in
[../tasks.md](../tasks.md). Predecessor: accepted S1. Deliver administrator
creation/edit of classified namespaced tags and public principal mappings while
preserving existing identities and reserving names in every state.

## Read first

- [Shared execution/report contract](README.md), `AGENTS.md`,
  `PROJECT_CONTEXT.md`, repository coding standards.
- [Proposal](../proposal.md), [design D2, D4, migration plan](../design.md).
- [Governance spec](../specs/team-tag-governance/spec.md): classification,
  namespaces, principal configuration and administrator control.
- `apps/patients/models.py`, `admin.py`, `forms.py`, catalogue views in `views.py`;
  accounts models/admin and migrations; `apps/core/models/soft_delete.py`.
- Accepted S1 code; its report is supplementary, not a required `/tmp` dependency.

## Requirements and evidence

- **R1:** Admin creates/edits origin, visibility and namespace; existing rows retain
  IDs/authors/associations and become public/custom without inferred teams.
  Evidence: admin requests and PostgreSQL migration fixtures.
- **R2:** Case/space-normalized names are reserved within global/team namespaces,
  including inactive/archived rows and concurrent creates. Evidence: database
  constraint tests and read-only collision preflight.
- **R3:** Admin maps one public same-namespace principal tag per team; invalid
  reclassification/moves are rejected while referenced. Evidence: admin and domain
  validation tests; no automatic tag creation.
- **R4:** Creator is immutable and ordinary staff/clinical users cannot mutate the
  catalogue through known URLs or forged fields. Creation/edits are attributable.
  Evidence: actor/time history and negative route/admin cases.

## Expected blast radius

Allowed production paths:

- `apps/patients/models.py`, `admin.py`, `forms.py`, catalogue sections of `views.py`.
- New `apps/patients/services/tag_catalogue.py`, `tag_policy.py`.
- New `apps/patients/management/commands/preflight_team_tags.py`.
- `apps/accounts/models.py`, `admin.py` for principal mapping only.
- New sequential accounts/patients migrations; no existing migration rewrites.

Tests: new `apps/patients/tests/test_tag_catalogue_governance.py`,
`test_team_tag_migrations.py`; existing `test_tags.py`, `test_views.py`,
`test_history.py`, `apps/accounts/tests/test_medical_specialty_admin.py`.
Docs: `docs/patients/tags_management.md`,
`docs/admin_guide_medical_specialties.md`, `openspec/config.yaml` tag-engine claim.

Lifecycle actions, responsible ownership/transfer and their actor fields belong
to S3. Assignment policy belongs to S4; reader redaction to S5. This catalogue
checkpoint is not safe to deploy with restricted data. No Taggit import/removal,
patient permission change or unrelated soft-delete-base change.

## Failing-before plan

Capture RED for absent classification/namespace fields, global-name limitations,
archived-name reuse and invalid principal mappings. Include unchanged legacy-ID
fixtures and PostgreSQL concurrent uniqueness tests, not only form validation.

## Implementation constraints

Reuse catalogue IDs and ordinary admin conventions. Apply collision preflight
without guessing/merging data. Test the command against schema states before and
after these additive migrations; selecting not-yet-added fields before preflight
would defeat its purpose. Current public-tag behavior remains compatible.
Restrict legacy catalogue mutation routes to administrator authority without
building future leader pages. Do not implement the S3 lifecycle service early.

## Validation

Focused:

```bash
./scripts/test.sh apps.patients.tests.test_tag_catalogue_governance
./scripts/test.sh apps.patients.tests.test_team_tag_migrations
./scripts/test.sh apps.accounts.tests.test_medical_specialty_admin
```

Project gates: shared contract and `AGENTS.md`. Runtime evidence in fixtures:
admin creates same-named tags in two namespaces, rejects a third conflicting row
and configures a valid principal; ordinary staff cannot mutate these records.

## Acceptance criteria

- [ ] R1: admin classification and migration preservation pass.
- [ ] R2: global/team uniqueness, archived reservation and preflight pass.
- [ ] R3: principal configuration/invariant matrix passes without inferred tags.
- [ ] R4: creator/history/route authorization are proven.
- [ ] Current catalogue docs and project gates match this delivered boundary.

## Escalation and evidence report

Apply shared escalation conditions, especially legacy collisions, circular
migrations or new privacy/namespace choices. Report using the shared schema at
`/tmp/eqmd-team-tags-slice-002-report.md`, mapping R1-R4 to RED/GREEN, migration,
admin/runtime and command-exit evidence. Explicitly retain the S5 privacy gate.

## Worker handoff

Implement only approved S2 from canonical artifacts and accepted S1 code.
Follow repository policy and produce the report. Do not update `tasks.md`, commit,
push, merge, deploy, archive or start S3. Return `READY_FOR_REVIEW` with
`REPORT_PATH`, or `BLOCKED_NEEDS_DECISION` with evidence.
