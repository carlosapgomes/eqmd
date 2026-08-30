# Tasks: Patient Identity and Duplicate Prevention

## 0. Mandatory Preconditions

- [ ] 0.1 Record a clean `BASE_REF` and obtain exit code 0 with zero
      failures/errors from `./scripts/test.sh` before any feature edit
      (WAIVED by user: baseline is pre-existing red; gate is zero NEW
      failures in `apps/patients` and in changed modules - met)
- [x] 0.2 Confirm `ruff` and `mypy` are available inside `eqmd_dev` without an
      ad hoc package installation during a slice
      (`mypy` provisioned via project `install-dev-deps.sh`; `ruff 0.16.4`
      installed by the user on the host - gates now runnable)
- [x] 0.3 Confirm PostgreSQL `pg_trgm` and `unaccent` extensions in the target
      test environment

## 1. Slice 001 - Name and Birthday Review

- [x] 1.1 Create the typed patient-identity service and candidate DTO
      (gates re-verified green 2026-08-29 via restore-green slice 018C;
      marked by third LLM)
- [x] 1.2 Add exact and `pg_trgm >= 0.80` matching constrained by birthday,
      including soft-deleted patients
      (gates re-verified green 2026-08-29 via restore-green slice 018C;
      marked by third LLM)
- [x] 1.3 Add server-side two-step review to the patient creation form and UI
      (gates re-verified green 2026-08-29 via restore-green slice 018C;
      marked by third LLM)
- [x] 1.4 Add RED/GREEN tests for warning, confirmation, no-match regression,
      soft delete, permissions, and minimal disclosure
      (gates re-verified green 2026-08-29 via restore-green slice 018C;
      marked by third LLM)
- [x] 1.5 Run all slice gates and create
      `/tmp/harden-patient-identity-and-duplicate-prevention-slice-001-report.md`
      (report created; gates re-verified green 2026-08-29 via restore-green
      slice 018C; marked by third LLM)

## 2. Slice 002 - Strong CPF/CNS Evidence

- [x] 2.1 Add CPF/CNS normalization and checksum validation for new or changed
      interactive values
      (official CNS rule — Portaria SAS/MS 174/2000 — verified 2026-08-29
      after correction 002-fix1; third-LLM marked)
- [x] 2.2 Block create/update when another active or soft-deleted patient has
      the same valid normalized CPF or CNS
- [x] 2.3 Preserve unchanged invalid legacy identifiers during unrelated
      profile edits
- [x] 2.4 Replace private-plan wording with CNS terminology in create/update
      forms
- [x] 2.5 Add RED/GREEN tests and create
      `/tmp/harden-patient-identity-and-duplicate-prevention-slice-002-report.md`

## 3. Slice 003 - Managed Record-Number Reservation

- [x] 3.1 Reject current, historical, same-patient, and soft-deleted record
      reuse in all interactive creation/change forms
- [x] 3.2 Make record changes atomic and preserve current/denormalized values on
      conflict
- [x] 3.3 Reject ordinary edit/delete of persisted record assignments in user
      and admin flows
- [x] 3.4 Map known record conflicts to field/domain errors instead of HTTP 500
- [x] 3.5 Add RED/GREEN tests and create
      `/tmp/harden-patient-identity-and-duplicate-prevention-slice-003-report.md`

Verifier note (2026-08-29, third LLM): implementation verified COMPLETE.
Formal INCOMPLETE in the report rested solely on pre-existing admin.py
frozen debt (ruff 18 / format / mypy 5), proven HEAD-identical via targeted
stash and zero-NEW vs /tmp/ruff_patients_full.txt; per the frozen-debt
gate policy (restore-green 018A/018C precedent) those scoped gates are
satisfied. Full suite 2699 OK (skipped=25), exit 0. Extra file
apps/patients/tests/test_record_tracking_views.py approved by planner
(spec-driven rewrite of tests asserting R6/R7-forbidden behavior).

## 4. Slice 004 - PostgreSQL Concurrency Constraint

- [x] 4.1 Add aggregate-only migration preflight with no data mutation
      (`0002_patient_record_number_lifetime_unique.py` RunPython before
      AddConstraint; verified by third LLM)
- [x] 4.2 Add functional global uniqueness over canonical record number without
      modifying `0001_initial.py` (zero diff; verified by third LLM)
- [x] 4.3 Add PostgreSQL tests for direct ORM conflict, same-patient repeat,
      canonical equivalence, concurrency, and dirty-migration refusal
      (11 new tests; RED 8 failures/2 errors captured; verified by third LLM)
- [x] 4.4 Verify migration state and SQL only against clean test databases; do
      not apply the migration to the restored production copy
      (`eqmd_dev` shows 0002 unapplied; verified by third LLM)
- [x] 4.5 Run all slice gates and create
      `/tmp/harden-patient-identity-and-duplicate-prevention-slice-004-report.md`
      (full suite 2710 OK exit 0; verified by third LLM)

## 5. Consolidated Release Gate

- [ ] 5.1 Complete and approve the separate audited consolidation change
      *(deferred by owner decision 2026-08-30, ADR-0002: tooling complete
      and verified — slices 01-03 — with 35/40 groups decided in the
      operator plan; the 5 mixed groups await clinical decisions;
      execution and `0003` application tracked by the consolidation
      change tasks 3.1/3.2)*
- [ ] 5.2 Confirm aggregate count zero for cross-patient and same-patient
      canonical record collisions
      *(deferred with 5.1 per ADR-0002; last audited state: 40 groups /
      86 rows)*
- [x] 5.3 Run `./scripts/test.sh` with exit code 0 and zero failures/errors
      *(verified 2026-08-30: 2746 tests, 0F/0E, 25 skipped, exit 0)*
- [x] 5.4 Run scoped typecheck, Ruff checks, migration drift check, OpenSpec
      validation, and Markdown lint with no errors
      *(verified 2026-08-30 across slices 01-03: strict combined typecheck
      clean on 7 files, ruff/format clean, makemigrations --check clean,
      openspec strict valid, markdownlint 0 errors)*
- [x] 5.5 Obtain third-LLM verification of all four temporary slice reports
      *(verified 2026-08-30: slices 001, 002 (2 corrections), 003, 004 all
      COMPLETE with independent gate reruns; consolidation change slices
      01, 02, 03 + addenda likewise verified)*
