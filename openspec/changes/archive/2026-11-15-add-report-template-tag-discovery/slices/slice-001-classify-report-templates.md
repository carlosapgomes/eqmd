# S1 — Classify report templates

## Identity

- Change: `add-report-template-tag-discovery`.
- Task: [tasks.md §1 / 1.1](../tasks.md#1-s1--classify-a-report-template-end-to-end).
- Dependency: approved change and explicit operator approval to generate the
  schema migration; live schema application remains operator-controlled.

## Objective

A creator can save and later revise optional report-template classifications,
with safe visibility, retained protected links and attributable history.

## Read First

- `AGENTS.md`, `PROJECT_CONTEXT.md`, `openspec/config.yaml`.
- `docs/workflows/coding-standards.md`.
- This change's `proposal.md`, `design.md` D1–D3, D7–D8 and Migration Plan.
- This change's `verification.md` for tooling, fixture ownership and handoff.
- This change's `specs/reports/spec.md`: first five requirements.
- `openspec/specs/reports/spec.md` and
  `openspec/specs/team-tag-governance/spec.md`.
- `apps/reports/models.py`, `forms.py`, `admin.py`,
  `views/template_views.py`, `services/permissions.py`.
- `apps/patients/services/tag_policy.py`, `tag_projection.py`,
  `tag_catalogue.py`; `apps/accounts/services/team_membership.py`.
- `apps/reports/tests/test_models_template.py`,
  `test_template_views.py`, `test_template_permissions.py`.
- `.pi/skills/verify-eqmd/SKILL.md` for served-checkout and runtime safety.

## Requirements and Planned Evidence

- **R1:** Create and edit zero/multiple distinct AllowedTag links without profile
  auto-fill or backfill. Evidence: CRUD tests, migration inspection and browser.
- **R2:** Enforce template gates plus D2 tag authority, active memberships and
  lifecycle on writes, including ordinary staff versus catalogue administrators.
  Evidence: success/denial and stale-authorization tests.
- **R3:** Preserve hidden/non-removable links; retain/remove authorized historical
  links; distinguish explicit clear from legacy omission. Evidence: bound-form
  and service tests with mixed protected/editable associations.
- **R4:** Persist fields and links atomically with actor/time/M2M history; no
  patient events or new history UI. Evidence: data-layer tag-only delta, no-op,
  failure/rollback and actor tests; authorized technical inspection suffices.
- **R5:** Display only currently readable badges and editor choices, including
  safe admin history. Evidence: member/outsider HTML and admin-history tests,
  plus same-session membership revocation.
- **R6:** Existing report rendering, manual creation, private visibility,
  placeholder validation and administrative update exceptions remain unchanged.
  Evidence: existing reports suite and targeted assertions where touched.

## Expected Blast Radius

Approved existing paths:

- `apps/reports/models.py`, `apps/reports/forms.py`,
  `apps/reports/admin.py`, `apps/reports/views/template_views.py`.
- `apps/reports/templates/reports/reporttemplate_form.html`.
- `apps/reports/templates/reports/reporttemplate_list.html`.
- `apps/reports/tests/test_models_template.py`,
  `apps/reports/tests/test_template_views.py`.

Required new paths for R1–R5:

- `apps/reports/services/template_tags.py`.
- `apps/reports/services/template_tag_projection.py`.
- `apps/reports/templates/components/_report_template_tags.html`.
- `apps/reports/tests/test_template_tags.py`.
- `apps/reports/tests/test_template_tag_history.py`.
- `apps/reports/migrations/0004_reporttemplate_tags.py`; verify the unchanged
  graph before generating, and escalate if a different migration leaf is present.

Optional preapproved helpers, never prerequisites for the next slice:

- `apps/reports/forms_template_tags.py` for a bounded form/field helper.
- `apps/reports/tests/tag_fixtures.py` for coherent test fixtures.

The only additional non-repo write area is the run-specific verification
deliverable directory named in `verification.md`; no repository harness changes.

Sensitive/outside scope: no patient/account policy or schema changes, no tag
catalogue mutation, no clinical event/PDF/renderer/duplication changes, no
discovery filters or frontend infrastructure for S2/S3.

## Failing-Before Plan

Use RED → GREEN → REFACTOR:

1. Add a create/update request test submitting two authorized tag identities.
2. Run the focused command below against baseline implementation. Record the
   expected missing-association/model-field failure, not an unrelated setup error.
3. Add protected-retention, history and denial regressions before their fixes.
   Record an audit-inspection/browser reproduction before any admin masking fix.

Do not generate migrations before the operator's required approval.

## Implementation Constraints

Follow repository engineering policy in `AGENTS.md` and preserve existing
conventions. Prefer the smallest correct change, without speculative abstraction
or unrelated refactoring.

D1–D3 are authoritative: transaction-aware service writes, no unrestricted
ModelForm M2M replacement, current membership checks and explicit M2M audit.
Keep Django admin tag controls absent; its existing text saves must preserve
links and never expose restricted M2M history deltas. Do not rewrite old audit
rows or classify existing data. Do not introduce new tag administration rights.

## Validation

### Focused Validation

```bash
./scripts/test.sh apps.reports.tests.test_template_tags \
  apps.reports.tests.test_template_tag_history \
  apps.reports.tests.test_template_views
./scripts/test.sh apps.reports
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
```

Inspect the generated migration for only D1's additive schema and dependencies;
it must contain no RunPython backfill. Record approved generation separately
from read-only drift checks and operator-controlled schema application.

### Project-Required Gates

Run the gates in `AGENTS.md` and `docs/workflows/coding-standards.md` for the
changed paths. Do not turn missing infrastructure or existing failures into an
unqualified pass.

### Runtime / Verification Evidence

Follow `verification.md`: the operator supplies the fixture manifest and owns
membership/catalogue transitions, restoration and cleanup. The worker uses a
standalone Playwright evidence script under the approved non-repo run directory.
No fixture manifest/tooling means blocked, not permission to scaffold shared data.

On the verified served checkout with those approved disposable fixtures:

1. Creator with membership A creates a public model tagged public X and team A.
2. Creator edits the selection; reload proves the saved association changes.
3. Outsider can see the public model but not team A's metadata or hidden count.
4. Revoke creator's membership, edit text and verify team A's protected link
   remains without exposing it. Use approved fixtures only; never real users.
5. Record URLs, roles, fixture identities, screenshots/assertions and read-only
   association/history probes. Do not reuse the supervision journeys as proof.

If schema/runtime prerequisites are unavailable, report the blocker rather than
claiming runtime acceptance.

## Acceptance Criteria

- [ ] R1: Optional multiple classification persists with no backfill/default fill.
- [ ] R2: Every authority/lifecycle test passes without widening staff rights.
- [ ] R3: Protected links survive and clear/omission/historical cases pass.
- [ ] R4: Technical audit is attributable and atomic, with no new audit UI.
- [ ] R5: Member/outsider/admin surfaces do not leak restricted metadata.
- [ ] R6: Existing reports behavior passes regression checks.
- [ ] Focused/project gates and runtime proof are recorded with exit statuses.
- [ ] D7 handoff lists actual module exports/signatures and optional helpers.

## Escalation Conditions

Stop with `BLOCKED_NEEDS_DECISION` for conflicting spec/design, a new
product/architecture decision, material scope expansion, unapproved public
compatibility or persistence/FSM change, a new security/privacy/integrity/clinical
implication, or inability to satisfy the contract. Additional unlisted paths
require a concrete justification and approval before editing. Missing runtime
or command prerequisites are blockers, not passing evidence.
Missing migration-generation approval is an explicit pre-implementation blocker.
Never apply the migration to shared dev to unblock your own browser evidence.

## Evidence Report

Path: `/tmp/sirhosp-slice-S1-report.md`.

The report must contain status (`READY_FOR_REVIEW` or
`BLOCKED_NEEDS_DECISION`), R-to-evidence mapping, changed paths, failing-before
and passing-after evidence, commands with exit statuses, runtime evidence,
unexpected blast radius with justification, limitations and human decisions.
Include the runtime artifacts and actual implementation-interface manifest
required by `verification.md` and design D7. Name projection/mutation exports,
typed signatures, return shapes, consumers and tests. Explicitly list optional
helpers created or record that none were needed. No next slice may assume an
optional module exists. Do not duplicate the diff as before/after snippets.

## Worker Handoff

```text
Implement only this approved slice. Treat this contract and the referenced
OpenSpec artifacts as authority; reconstruct fresh context from the listed files.
Follow repository engineering policy. Produce failing-before evidence, implement
the smallest correct change, validate and write the evidence report. Do not
update tasks.md, commit, push, merge, archive or start another slice. If a new
decision is required, stop with BLOCKED_NEEDS_DECISION and evidence. Otherwise
finish READY_FOR_REVIEW with REPORT_PATH=/tmp/sirhosp-slice-S1-report.md.
```
