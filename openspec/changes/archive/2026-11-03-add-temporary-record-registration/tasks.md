# Tasks: add temporary record registration

## 1. Slice 001 — temporary record creation

- [x] 1.1 Implement `apps/patients/services/temporary_record.py`
      (`generate_temporary_record_number`, `is_temporary_record_number`,
      prefix constant re-export) per
      `slices/slice-001-temporary-record-creation.md`.
- [x] 1.2 Extend `PatientForm` with `use_temporary_record` and
      `temporary_record_reason`; generate the number in `save()` and store
      the reason in `change_reason`.
- [x] 1.3 Add the UI toggle to `patients/patient_create.html`.
- [x] 1.4 TDD: `apps/patients/tests/test_temporary_record_creation.py`
      RED → GREEN → REFACTOR; full suite green; no new findings.

## 2. Slice 002 — prefix protection and regularization

- [x] 2.1 Add `validate_permanent_record_number` to
      `apps/patients/validators.py` and enforce it at the four manual doors
      (creation form, both update forms, managed model method).
- [x] 2.2 Add `Patient.is_temporary_record` property and the temporary
      banner linking to the existing quick-update flow in
      `patients/patient_detail.html`.
- [x] 2.3 TDD: `apps/patients/tests/test_temporary_record_prefix_protection.py`
      RED → GREEN → REFACTOR; regularization regression covered; full suite
      green; no new findings.

## 3. Slice 003 — pending dashboard

- [x] 3.1 Implement staff-only `TemporaryRecordListView` + URL
      `temporary-records/` + `patients/temporary_record_list.html` with
      pending age, reason and aggregate by creator.
- [x] 3.2 TDD: `apps/patients/tests/test_temporary_record_list.py`
      RED → GREEN → REFACTOR; full suite green; no new findings.
