# Proposal: consolidate-historical-record-number-collisions

## Why

The lifetime record-number constraint
(`0002_patient_record_number_lifetime_unique`) is implemented and tested
but cannot be applied to any database derived from production data: the
PII-free audit found canonical collision groups (37 across different
patients plus 3 same-patient repeats at audit time, 2026-08-29). The
migration preflight fails closed on them, so the database-level guarantee
stays unavailable until every collision is resolved by an audited,
human-decided consolidation.

Record numbers must never be reused, and no clinical consolidation may
happen automatically: each colliding group needs a clinical decision about
which assignment rightfully owns the number.

## What Changes

- Add a collision-group discovery service that reuses the canonical
  `Lower(Trim(record_number))` comparison and reports aggregate counts by
  default.
- Add an audited consolidation service: for each decided group, the
  rightful row keeps the number; erroneous rows are either renumbered
  through the existing append flow (when they are the patient's current
  number) or voided in place with a derived unique marker that preserves
  the original value verbatim plus a decision reference; the clinical
  rationale and operator are recorded on every touched row.
- Add a management command `consolidate_record_numbers` that emits the
  aggregate audit, validates an operator-provided JSON decision plan,
  defaults to `--dry-run` (atomic rollback), and executes only the decided
  groups inside one transaction with a zero-collision post-check.
- Split the oversized `test_patient_identity_record_numbers.py` module
  (639 lines; the 450-line hard limit) by extracting the five slice-004
  constraint classes into a dedicated module.
- Provide the operator runbook so the project owner (never an implementer
  LLM) executes the plan against the restored dev database and applies
  `0002` only after the aggregate count is zero.

## Impact

- Affected apps: `patients` (service, management command, tests).
- No model, migration, form, view, template, admin, signal, or URL
  changes in this change; ordinary interfaces keep their slice-003
  immutability guarantees.
- The restored production copy is never mutated by implementers; the
  operator executes the plan and the migration, and third-LLM
  verification re-checks the aggregate outcome.
