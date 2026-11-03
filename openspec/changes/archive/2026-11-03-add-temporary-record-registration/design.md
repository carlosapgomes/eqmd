# Design: add temporary record registration

## Context

The record-number subsystem already provides everything this change needs:

- `PatientRecordNumber` rows are immutable history with `created_by`,
  `updated_by`, `change_reason` and a lifetime unique constraint on
  `Lower(Trim(record_number))`.
- `PatientForm.save()` creates the initial `PatientRecordNumber` inside a
  transaction and denormalizes `Patient.current_record_number`.
- `Patient.update_current_record_number()` is the managed change door
  (format validation, conflict rejection, history row preservation).
- `find_record_number_conflict()` mirrors the database constraint and is
  used by all forms as the early conflict check.

The gap: a doctor without the definitive number has no sanctioned path.

## Decisions

### D1. Generated format: `TMP-` + 8 uppercase hex chars

`generate_temporary_record_number()` returns `TMP-` plus the first 8 hex
chars of a `uuid4`, uppercase (regex `^TMP-[0-9A-F]{8}$`).

- Rejected alternative: monotonic counter (`TMP-000042`). Deriving
  `MAX+1` has a race without a lockable sequence row; a dedicated sequence
  table would add a migration and maintenance for cosmetic value. The
  hospital does not require sequential temporary numbers; traceability is
  served by the audit trail, not by the number itself.
- Uniqueness: 8 hex chars give ~4.3 billion values; the generator rejects
  any candidate already taken (checked with `find_record_number_conflict`,
  retry limit 5) and the database lifetime constraint remains the final
  guarantee, exactly as for typed numbers.

### D2. Prefix constant lives in `apps/patients/validators.py`

`TEMPORARY_RECORD_PREFIX = "TMP-"` is defined in the base validators module
(no imports) so that `services/temporary_record.py`, forms, models and the
dashboard all import one constant without import cycles (validators must
not import services; services may import validators).

### D3. Temporary state is derived from the number prefix — no new fields

A patient is "temporary" when its current record number starts with
`TMP-` (`Patient.is_temporary_record` property). No boolean column, no
migration: the state is self-describing in every report and list, and
regularization flips it automatically when the current number changes.

### D4. The reason is stored in the existing `change_reason` audit field

Temporary creation writes `change_reason="Registro temporário: <motivo>"`.
This reuses the audit column that already exists on every
`PatientRecordNumber` row, keeps the reason adjacent to the number it
explains, and requires zero migrations. The dashboard reads it from the
current row.

### D5. Prefix protection at every manual write door

`validate_permanent_record_number()` rejects values starting with `TMP-`
(case-insensitive) and is applied at the four doors where a human types a
number: `PatientForm` (creation), `PatientRecordNumberForm`,
`QuickRecordNumberUpdateForm`, and `Patient.update_current_record_number`
(the managed service door used by the quick-update view). Generated numbers
never pass through these doors, so the generator is unaffected. Import and
refresh commands are out of scope (hospital-side numbers do not start with
`TMP-`; documented as an operational invariant, not enforced there).

### D6. Regularization reuses the existing change flow — no new door

When the definitive number arrives, the operator uses the existing
quick-update flow (`Patient.update_current_record_number`): the old `TMP-`
row is kept with `is_current=false`, `previous_record_number` records the
transition, and the lifetime constraint guards the new value. A banner on
the patient detail page links temporary patients to that flow. No dedicated
"regularize" endpoint is created (YAGNI).

### D7. Dashboard gated by `is_staff`, aggregation by creator username

The pending dashboard is a management view, not a clinical one; gating by
`is_staff` (via `UserPassesTestMixin`) avoids a permission-object migration
for a single view. Aggregation counts pending temporaries per creator
username (process metric). Revisit path: if coordination needs delegated
access without staff flag, add a dedicated permission in a follow-up change.

## Risks and mitigations

- Normalization of the easy path: mitigated by the mandatory reason, the
  unmistakable `TMP-` prefix, and the dashboard that keeps the debt visible.
- UUID-style number looks odd to staff: acceptable trade-off versus the
  collision-safety it buys; documented in D1.

## Slices

1. `slice-001-temporary-record-creation.md` — generation service, creation
   form flow, UI toggle, tests.
2. `slice-002-prefix-protection-and-regularization.md` — reserved prefix at
   every manual door, `is_temporary_record` property, detail-page banner,
   regularization regression tests.
3. `slice-003-pending-dashboard.md` — staff-only list view with age,
   reason and creator aggregate.

Each slice is vertical, testable, and touches the minimum files listed in
its own "Arquivos esperados" section. No slice adds migrations.
