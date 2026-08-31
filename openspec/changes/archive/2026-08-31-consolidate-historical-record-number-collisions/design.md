# Design: consolidate-historical-record-number-collisions

## Context

- `0002_patient_record_number_lifetime_unique` adds an unconditional
  functional unique constraint over `Lower(Trim(record_number))`; its
  `RunPython` preflight aborts while any canonical collision group exists.
- The restored dev database (mirror of production data) has collision
  groups: 37 cross-patient plus 3 same-patient at audit time. Interactive
  flows are already protected (slices 001-003); imports/direct ORM are not
  (until `0002` applies).
- `PatientRecordNumber` is NOT simple-history tracked (only `Patient` and
  other models carry `HistoricalRecords`), so the audit trail for this
  operation must be explicit.
- Slice 003 keeps persisted assignments immutable and non-deletable in
  ordinary interfaces; its contract explicitly defers out-of-band trusted
  operations ("Direct SQL and QuerySet.delete() are trusted/out-of-band").
  This change is that audited out-of-band path.

## Goals

- Resolve every collision group through recorded clinical decisions, with
  zero automatic clinical merging.
- Keep every row (no deletion), keep the original value recoverable, and
  record who decided, when, and why.
- End state: aggregate collision count zero on the consolidated database,
  so `0002` applies cleanly (dev rehearsal, then production rollout).

## Non-Goals

- Automatic duplicate-patient merging or any clinical decision made by
  code.
- Changing slice-003 immutability in forms/views/admin.
- Adding simple-history to `PatientRecordNumber` (separate hygiene
  backlog item; in-row markers already preserve the audit).
- Merging patients, CNS/CPF handling, or duplicate-name review changes.

## Decisions

- **D1 - Human decision artifact.** The command emits the aggregate audit;
  the operator produces a JSON plan (kept outside the repository, never
  committed) listing, per collision group: the canonical number, the
  assignment that keeps it, and for each other assignment either
  `renumber` (with the new number) or `void`, each with a rationale
  string. Execution validates the plan against live discovery and refuses
  unknown or stale groups. The operator may delegate DRAFTING to the
  tool under a criterion they state and authorize (2026-08-30: every
  row of a group matching normalized name plus birthday): pre-drafted
  groups carry the criterion's rationale; the operator reviews, edits,
  and remains the decision-maker via dry-run and `--execute`.
- **D2 - Voiding marker, not deletion.** An erroneous historical row gets
  `record_number` rewritten to
  `<original>::voided::<plan-ref>:<assignment-id>` where `<plan-ref>` is a
  short per-execution reference and `<assignment-id>` is the row's own
  primary key. The original value stays verbatim and recoverable; the
  assignment id makes every marker unique per row (live data has groups
  of 3 and 7 rows whose voided rows would otherwise collide with each
  other and fail the post-check); `change_reason` records the rationale
  plus the plan reference; `updated_by` records the operator.
  `effective_date` is untouched; the row itself is never deleted.
- **D3 - Current numbers go through the append flow.** When the erroneous
  assignment is the patient's current number, the service calls the
  existing audited `update_current_record_number(new_number, user,
reason)` first (new current row, old row deactivated), then voids the
  deactivated old row with the D2 marker. Purely historical erroneous
  rows are voided directly.
- **D4 - One transaction, post-verified.** `--execute` wraps the whole
  plan in `transaction.atomic()`; any error rolls back everything. After
  the writes, the service re-runs discovery and raises unless the
  aggregate group count is zero. `--dry-run` is the default and uses
  `set_rollback(True)` inside the same atomic block (precedent:
  `refresh_patient_data` slice 005a).
- **D5 - Privacy discipline.** Default command output is aggregate-only
  (counts); `--show-records` prints per-group detail (canonical number,
  assignment ids, patient ids) solely for the operator console; the
  operator-console clinical flag `--show-patients` additionally prints
  patient names and birthdays with a likely-same-person marker
  (normalized name plus birthday), because the owner needs clinical
  context to decide ownership; `--emit-skeleton` writes an operator-only
  decision scaffold with the same clinical context. CPF and CNS never
  appear anywhere; logs, reports, and the `/tmp` slice report contain
  only aggregate numbers and synthetic examples.
- **D6 - Reuse without new coupling.** Discovery reuses the service-level
  canonical helpers already in `services/patient_identity.py`; the
  command stays a thin transport. No model changes; the migration's own
  preflight copy remains the authoritative fail-closed gate.

## Risks / Trade-offs

- **D7 - Column capacity (2026-08-30, correction 2).** Live data has one
  collision group with two 18-char numbers: only one row can be the
  keeper, so the other's marker needs at least 18+33 = 51 characters
  and cannot fit `VarChar(50)`. Planner decision: widen
  `PatientRecordNumber.record_number` to 120 (metadata-only on
  PostgreSQL) instead of weakening the marker contract again. Since no
  environment has applied the lifetime-constraint migration, the clean
  order is renumbered migrations: `0002` widens the column; the
  constraint becomes `0003` depending on it. Human input stays capped
  at 50 by the explicit form fields (`PatientForm`,
  `QuickRecordNumberUpdateForm`) and the service validator (minimum
  length only); markers remain out-of-band values.

- Voiding rewrites a persisted assignment's `record_number`, which
  contradicts the letter of slice-003 R6 inside ordinary interfaces; this
  is the explicitly designed out-of-band exception, recorded and
  reviewable. Ordinary interfaces remain strict.
- A marker colliding with a real number of the same shape is impossible:
  the marker embeds the `::voided::` separator plus the per-execution
  reference; markers of two voided rows never collide with each other
  because each embeds its unique assignment id.
- The operator plan file contains clinical identifiers; it must never be
  committed. The runbook states this.
- Same-patient repeats: the operator picks the surviving row (usually the
  earliest or the currently referenced one); the other is voided with the
  same mechanism.

## Migration Plan

`0002_widen_record_number_column` (new): AlterField
`record_number` max_length 50 -> 120, depends on `0001_initial`.
`0003_patient_record_number_lifetime_unique` (renamed from the verified
slice-004 `0002`): same preflight and constraint, now depending on the
widen migration. Safe renumber: no environment has the constraint
migration applied (dev-restored shows it unapplied; test databases are
ephemeral; production mirrors dev). Application order on any database:
the widen may apply before consolidation; the constraint's preflight
still fails closed until the aggregate collision count is zero.

## Open Questions

None - the marker format may be tuned by the implementer as long as it
preserves the original value verbatim and contains the plan reference.
