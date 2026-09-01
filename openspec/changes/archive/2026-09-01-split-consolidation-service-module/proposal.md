# Proposal: Split the consolidation service module

## Why

`apps/patients/services/patient_record_consolidation.py` grew to 396
lines holding three distinct responsibilities: plan parsing and
validation (pure), collision review/skeleton presentation (read-only),
and plan execution with void markers (mutations). The original change
flagged this split as backlog item 3; the module now also carries the
placeholder-rule parse gate, and every future consolidation feature
(prefill refinements, merge-duplicate-patients support) lands in an
increasingly entangled file.

## What Changes

- Extract plan parse/validate into
  `apps/patients/services/consolidation_plan.py` (types, constants
  `ACTION_*`, `ConsolidationPlanError`, parse + live validation).
- Extract review/skeleton into
  `apps/patients/services/consolidation_review.py`
  (`CollisionRowReview`, `CollisionGroupReview`,
  `build_collision_review`, `skeleton_document`).
- Keep execution (void markers, renumber routing, post-check) in
  `patient_record_consolidation.py`, which remains the public facade
  and re-exports the full previous surface (`__all__`), so command,
  prefill, and tests stay byte-identical.
- Type polish inside the executor during the move: annotate the
  untyped `operator` parameters and generic containers so every
  service module passes `mypy --strict` (fixes 9 pre-existing strict
  findings in this module; `consolidation_prefill.py` strict debt is
  explicitly out of scope).

## Out of Scope

- Any behavior, message, marker format, or public-API change.
- `consolidation_prefill.py` strict findings (separate debt).
- Command or test edits (the refactor is proven pure exactly by NOT
  touching them).

## Success Criteria

- Zero edits outside `apps/patients/services/` (git diff proof).
- Full suite green with the same test count (2753).
- Default mypy clean on `apps/patients/services`; `--strict` clean on
  the three consolidation service modules.
- ruff clean on all touched files.
