# Slice 01 — Clinical delete route becomes superuser-only

- Slice ID: S1
- Change ID: `restrict-patient-delete-to-admin`
- Task: `tasks.md` item 2 (Slice 1).

## Objective

One sentence: `POST /patients/<uuid>/delete/` rejects every non-superuser
with `403` and still soft-deletes on a superuser `POST` with a reason.

## Read first

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `openspec/changes/restrict-patient-delete-to-admin/proposal.md`
- `openspec/changes/restrict-patient-delete-to-admin/design.md` (Route/Behavior
  Design, Test Design)
- `openspec/changes/restrict-patient-delete-to-admin/specs/patient-delete/spec.md`
  (Requirement: superuser-only)
- `apps/patients/views.py` (`PatientDeleteView`, `PatientRestoreView`)
- `apps/core/permissions/decorators.py` (`doctor_required`)
- `apps/patients/tests/test_views.py` (`test_patient_delete_view`,
  `test_permission_required`)

Follow the repository engineering policy in `AGENTS.md` and preserve existing
conventions. Prefer the smallest correct change; avoid speculative abstraction
and unrelated refactoring.

## Requirements

- R1: Authenticated non-superuser (doctor and staff non-superuser) `POST`
  with `deletion_reason` → `403`, patient stays active and unchanged.
- R2: Superuser `POST` with non-empty reason → existing soft-delete behavior
  (`is_deleted=True`, `deleted_by`/`deletion_reason` recorded, `302` to the
  patient list).
- R3: Superuser `POST` with empty or whitespace-only reason → no deletion,
  redirect to detail with the existing error message (behavior preserved).
- R4: Anonymous `POST` → login redirect (behavior preserved).
- R5: `GET` on the route keeps returning `405` for every caller (no
  confirmation page introduced, gate lives in `post()`, not dispatch).

## Expected blast radius

- Likely: `apps/patients/views.py` (`PatientDeleteView` gate only),
  focused tests in `apps/patients/tests/test_views.py` (update/add).
- Sensitive / out of scope without escalation: `Patient` model and
  soft-delete semantics, `PatientRestoreView`, `PatientAdmin` actions,
  `PatientUpdateView`/record-number/admission/event permissions, URL routes and
  namespaces, any template (belongs to S2).

## Failing-before plan

Failing-before evidence (run before changing `views.py`):

- targeted test: `test_patient_delete_view` in
  `apps/patients/tests/test_views.py` (doctor `POST` → today `302` + deleted).
- expected failure: after adding the new expectation (doctor `POST` →
  `403`, patient still active), the new assertion fails on current code,
  proving the crafted-POST path is open.

## Implementation constraints

- Replace the `doctor_required` gate with an explicit superuser check inside
  `post()` that raises `PermissionDenied` for authenticated non-superusers.
  Do NOT use `user_passes_test` here: it redirects failures to login instead
  of returning `403`, and at dispatch level it would also swallow the `405`
  for `GET`. Predicate matches `PatientRestoreView` (superuser), failure
  behavior differs by design; do not introduce a new permission codename,
  group, or staff-based rule without escalation.
- Keep the route POST-only; do not add a `get()` handler or confirmation
  page in this slice.
- Do not touch templates, the orphan confirmation template, admin, or any
  other view in this slice (S2 owns templates).
- Do not implement S2 early.

## Validation

Focused validation (worker runs during the slice):

- `./scripts/test.sh apps.patients.tests.test_views`
- `./scripts/test.sh apps.patients.tests.test_soft_delete`

Project-required gates: reference `AGENTS.md`; run the repo's required checks
for touched files before handoff.

Runtime/verification evidence: not a browser slice; test evidence plus a
`POST` matrix spot-check (anonymous/doctor/superuser, with/without reason) is
sufficient.

## Acceptance criteria

- [ ] R1 verified: doctor and staff-non-superuser `POST` → `403`, patient active.
- [ ] R2 verified: superuser `POST` with reason → soft-deleted (`deleted_by`/
      reason recorded) + `302` to list.
- [ ] R3 verified: superuser empty/whitespace-reason `POST` deletes nothing
      (redirect to detail with error).
- [ ] R4 verified: anonymous `POST` redirects to login.
- [ ] R5 verified: `GET` → `405` for every caller.
- [ ] Focused suites above pass.
- [ ] No file outside the blast radius changed without written justification.

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` if any of these appears: contradiction
between proposal/design/spec; a request to allow staff non-superusers or any
clinical role; a required migration, permission, group, or model change;
a new security/privacy/clinical implication; impossibility of meeting R1
without altering an out-of-scope surface.

## Evidence report

Path: `/tmp/sirhosp-slice-restrict-delete-s1-report.md`

Include: status (`READY_FOR_REVIEW` or `BLOCKED_NEEDS_DECISION`);
requirements → evidence; files changed; failing-before evidence; passing-after
evidence; commands with exit status; unexpected blast-radius expansion with
justification; risks/limitations; decisions needing a human, if any.

## Worker handoff

Implement only this approved slice. Treat the slice and referenced OpenSpec
artifacts as the implementation contract. Reconstruct context from the listed
files; do not rely on prior conversation. Follow the repository engineering
policy. Produce failing-before evidence, implement the smallest correct change,
run focused validation, and produce the required evidence report. Do not update
`tasks.md`, commit, push, merge, archive, or start another slice. If a new
decision is required, stop with `BLOCKED_NEEDS_DECISION` and evidence.
Otherwise finish with `READY_FOR_REVIEW` and
`REPORT_PATH=/tmp/sirhosp-slice-restrict-delete-s1-report.md`.
