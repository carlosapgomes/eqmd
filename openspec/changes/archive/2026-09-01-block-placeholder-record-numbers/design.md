# Design: Block placeholder-only record numbers

## Context

- `validate_record_number_format` (apps/patients/validators.py) is the
  single format validator. Today: non-empty + `len(strip()) >= 3`.
- Call sites: model `clean()` (models.py:297) and three forms
  (forms.py:351, 601, 659).
- Managed flow `Patient.update_current_record_number`
  (models.py:894) writes via `PatientRecordNumber.objects.create`
  inside `_replace_current_record` — it does NOT invoke `clean()` nor
  the format validator. It checks lifetime conflicts
  (`_reject_record_conflict`) and maps the DB constraint to a domain
  `ValidationError`.
- Consolidation `_renumber_and_void`
  (services/patient_record_consolidation.py:356) calls
  `update_current_record_number` with the plan-provided
  `new_record_number`, so plan execution currently inherits the
  format bypass.

## Decisions

### D1 — Rule: at least one alphanumeric character

`any(ch.isalnum() for ch in value)` on the stripped value. Rejects
`---`, `...`, `___`, `???` while accepting every legitimate format
observed in production (`123456`, `PRONT-001`, `12.345-6`). No regex,
no whitelist — the narrowest rule that kills the placeholder class.

### D2 — Enforce at the service boundary, not only in forms

The format check runs at the top of `update_current_record_number`,
before opening the transaction (fail-closed: no partial writes). Forms
keep their existing calls; the service check adds defense in depth for
programmatic callers (consolidation executor, future imports) — same
principle that motivated the lifetime constraint.

### D3 — Plan validation fails fast on junk renumber targets

`validate_consolidation_plan` reuses the same validator for every
`renumber` action's `new_record_number`, so a bad plan is refused in
dry-run/parse time with a precise message, instead of failing (or
worse, succeeding) during execution.

### D4 — No data migration

Existing rows are never revalidated by ordinary flows (updates do not
touch record numbers; history is immutable). The voided/keeper `---`
rows from the 2026-08-31 consolidation remain as audit artifacts.

## Risks / Trade-offs

- A legitimate record number containing only punctuation is
  inconceivable for this hospital's series; the rule is safe.
- Adding a `ValidationError` path to `update_current_record_number`
  changes behavior for hypothetical callers passing junk — desired and
  documented in the spec delta.
