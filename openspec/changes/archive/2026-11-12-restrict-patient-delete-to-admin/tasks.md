# Tasks: restrict-patient-delete-to-admin

## 1. Preparation

- [ ] 1.1 Confirm scope: superuser-only clinical delete, no clinical
      confirmation page, orphan template deleted (see `proposal.md`, `design.md`).
- [ ] 1.2 Confirm Django admin bulk delete/restore stays the supported path.

## 2. Slice 1 — Clinical delete route becomes superuser-only

- [x] 2.1 Produce failing-before evidence: new doctor-`POST`-rejected
      expectation fails on current code.
- [x] 2.2 Replace the `doctor_required` gate on `PatientDeleteView` with the
      superuser gate (R1–R4 in the slice).
- [x] 2.3 Update/extend focused tests (doctor `403`, superuser success,
      empty-reason and anonymous behavior).
- [x] 2.4 Validate `./scripts/test.sh apps.patients.tests.test_views` and
      `./scripts/test.sh apps.patients.tests.test_soft_delete`.
      Contract: `slices/slice-001-delete-route-superuser-only.md`

## 3. Slice 2 — Remove clinical Excluir affordances and dead template

- [x] 3.1 Produce failing-before evidence: non-superuser detail/list HTML
      contains the delete control; orphan template exists unreferenced.
- [x] 3.2 Remove (or explicitly gate) the `Excluir` anchors in
      `patient_detail.html` and `patient_list.html` per the slice decision.
- [x] 3.3 Delete `patient_confirm_delete.html` and verify zero references
      in runtime code and templates (planning/history docs excluded).
- [x] 3.4 Validate focused suites plus rendered-HTML/`grep` evidence.
      Contract: `slices/slice-002-remove-excluir-ui-and-orphan-template.md`

## 4. Final verification

- [x] 4.1 Run `./scripts/test.sh apps.patients`
- [x] 4.2 Consolidate S1/S2 evidence in the handoff
- [ ] 4.3 Prepare change archival on completion (no commit/push by workers)
