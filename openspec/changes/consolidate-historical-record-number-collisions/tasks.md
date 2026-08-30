# Tasks: consolidate-historical-record-number-collisions

## 1. Slice 01 - Audited consolidation tooling

- [x] 1.1 Add collision-group discovery to the identity service
      (aggregate counts; canonical `Lower(Trim(record_number))` reused)
- [x] 1.2 Add the audited consolidation service (append-flow renumbering
      for current numbers; `::voided::<ref>` markers preserving the
      original value and unique per row; rationale and operator on every
      touched row)
- [x] 1.3 Add the `consolidate_record_numbers` management command
      (aggregate audit, plan validation, `--dry-run` default with atomic
      rollback, `--execute` with single-transaction zero-collision
      post-check)
- [x] 1.4 Add RED/GREEN tests on synthetic data covering discovery,
      dry-run immutability, void/renumber semantics, stale-plan refusal,
      and post-check rollback (including a 3-row group with distinct
      per-row markers)
- [x] 1.5 Run every slice gate and create
      `/tmp/consolidate-historical-record-number-collisions-slice-01-report.md`
      (kept marked via correction addendum 2, report section 15,
      2026-08-30)
- [x] 1.6 Widen `record_number` to 120 through renumbered migrations
      (new `0002` widen; the verified constraint migration becomes
      `0003` depending on it), with a RED capacity test proving an
      18-char erroneous original can be voided end-to-end
- [x] 1.7 Re-run every slice gate and append correction addendum 2 to
      the report (capacity root cause, RED, migration evidence,
      `showmigrations`/`sqlmigrate` outputs; see report section 15)

## 2. Slice 02 - Module split and operator runbook

- [x] 2.1 Extract the five slice-004 constraint test classes into
      `apps/patients/tests/test_patient_record_constraint_database.py`
      leaving both modules under the 450-line hard limit with identical
      test discovery counts
- [x] 2.2 Add the operator runbook (docs) covering: aggregate audit,
      plan authoring rules, dry-run review, execution by the project
      owner only, zero-collision confirmation, and `0002` application
      order
- [x] 2.3 Run every slice gate and create
      `/tmp/consolidate-historical-record-number-collisions-slice-02-report.md`

## 4. Slice 03 - Operator clinical review helper (planner-implemented

Implemented at the owner's direct request; gates below.

- [x] 4.1 Add `build_collision_review` (name, birthday, current flag,
      likely-same-person marker per row) and the plan-scaffold builder
      to the consolidation service *(planner-implemented 2026-08-30 at
      the owner's request; see slice-03 report)*
- [x] 4.2 Add `--show-patients` and `--emit-skeleton <path>` to the
      command (operator console only; CPF/CNS never printed)
- [x] 4.3 Add `apps/patients/tests/test_consolidation_review.py`
      (RED->GREEN) and run every gate with a
      `/tmp/consolidate-historical-record-number-collisions-slice-03-report.md`
- [x] 4.4 Add `services/consolidation_prefill.py` (same-person
      criterion drafting: keep rule, `DUP-####` series with database
      uniqueness, void/renumber routing) *(planner-implemented
      2026-08-30 under the owner's authorized criterion)*
- [x] 4.5 Add `--prefill` to `--emit-skeleton` (decided-group count in
      output; `--prefill` without `--emit-skeleton` fails closed) and
      document it in the runbook step 3
- [x] 4.6 RED->GREEN for the prefill (6 new tests) and every gate
      green (suite 2746); addendum appended to the slice-03 report

## Closure (project owner + third LLM; not an implementer slice)

- [ ] 3.1 Operator executes the reviewed plan against the restored dev
      database and applies `0002` only after the aggregate count is zero
      *(deferred by owner decision 2026-08-30, ADR-0002: deploy ships with
      patients migrations held at `0001_initial`; 35/40 groups decided in
      `~/consolidacao/plan-completo.json`, 5 mixed groups pending in
      `decidir-grupos.json`; re-audit and plan regeneration required if the
      database changes meanwhile)*
- [ ] 3.2 Third LLM re-verifies the aggregate audit (zero), migration
      state (`0002` applied on dev), and the full suite, then marks
      `harden-patient-identity-and-duplicate-prevention` tasks 5.1-5.5
      *(awaits 3.1; identity tasks 5.3-5.5 verified and closed 2026-08-30)*
