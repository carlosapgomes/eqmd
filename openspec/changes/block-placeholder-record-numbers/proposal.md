# Proposal: Block placeholder-only record numbers

## Why

Production data contains record numbers that are pure placeholder junk
(most notably `---`, shared by 7 different patients before the
consolidation). The current format validator only requires a
non-empty value of at least 3 characters, so `---`, `...` or `___`
pass validation today. Additionally, the managed renumber flow
(`Patient.update_current_record_number`) bypasses format validation
entirely: it only checks conflicts and the lifetime constraint, so a
programmatic caller (including a consolidation plan `renumber` action)
could introduce a placeholder-only number even after this validator is
hardened.

## What Changes

- Harden `validate_record_number_format` to require at least one
  alphanumeric character, rejecting placeholder-only values such as
  `---`, `...`, `___`.
- Enforce the same format rule inside the managed renumber flow
  (`update_current_record_number`) before any write, so every
  programmatic path (UI, consolidation executor, future imports) is
  protected, not only forms.
- Reject consolidation plans whose `renumber` actions target a
  placeholder-only `new_record_number` at plan-validation time
  (fail-closed before execution).

## Out of Scope

- Broader format policy (length caps beyond existing rules, character
  whitelists, normalization) — deferred; only the placeholder class is
  addressed.
- Migration or cleanup of existing historical junk rows — they are
  immutable audit artifacts; nothing revalidates them.
- Admin-side editing restrictions for `PatientRecordNumber`.

## Success Criteria

- Forms reject placeholder-only record numbers with a clear PT-BR
  message.
- `update_current_record_number` raises `ValidationError` for
  placeholder-only values before writing anything.
- Consolidation plan validation rejects a `renumber` action whose
  `new_record_number` is placeholder-only.
- Full suite green; ruff delta-clean on touched files.
