# Design: Split the consolidation service module

## D1 — Module boundaries by responsibility

`consolidation_plan.py` (parse/validate, movidos verbatim):
`ACTION_VOID`, `ACTION_RENUMBER`, `ConsolidationPlanError`,
`PlanAction`, `PlanGroup`, `ConsolidationPlan`,
`parse_consolidation_plan`, `_require_groups`,
`_require_non_empty_str`, `_parse_uuid`, `_parse_plan_group`,
`_parse_plan_action`, `validate_consolidation_plan`,
`_refuse_unmatched_canonicals`, `_validate_group_against_live`,
`_validate_action_reference`, `_validate_action_targets_live_row`.

`consolidation_review.py` (revisão/skeleton, read-only):
`CollisionRowReview`, `CollisionGroupReview`,
`build_collision_review`, `_review_rows`, `skeleton_document`,
`_skeleton_row`.

`patient_record_consolidation.py` (executor + facade):
`VOID_MARKER`, `ResidualCollisionError`,
`apply_consolidation_actions`, `enforce_zero_collisions`,
`execute_consolidation_plan`, `_residual_message`, `_apply_action`,
`_renumber_and_void`, `_void_assignment_by_id`, `_void_assignment`,
`_void_marker`, `_decision_reason`, mais os re-exports da D2.

`ACTION_*` são preocupação de parse (validam strings de ação);
`VOID_MARKER` pertence ao executor que escreve marcadores.
Docstrings de módulo declaram cada responsabilidade.

## D2 — Facade preserves the public surface

`patient_record_consolidation.py` keeps its name and re-exports the
previous public surface with an explicit `__all__` (satisfies ruff
F401 and documents the contract). Importers —
`consolidate_record_numbers` command, `consolidation_prefill`, both
test modules — must remain byte-identical; that IS the purity proof
for this refactor.

## D3 — No behavior change

Code is moved, not rewritten. The only edits beyond the move are
import blocks, module docstrings, and type annotations (D4). Marker
format, error messages, transaction boundaries, and ordering are
untouched; the 2753-test suite is the behavioral guard.

## D4 — Typing polish to strict-clean

The move annotates the 4 untyped executor `operator` parameters
(`AbstractBaseUser`, already imported) and parameterizes the 5 bare
`dict`/`list` generics (skeleton/rows/`_require_groups`). Result:
`mypy --strict` clean on the three service modules — better than the
9-finding baseline. `consolidation_prefill.py` keeps its pre-existing
strict debt (out of scope, frozen).

## Risks

- Circular imports: none — plan imports (patient_identity, models,
  validators); review imports (patient_identity, models); executor
  imports (plan, patient_identity). No module imports the facade.
- mypy `follow_imports=skip` and the django plugin being disabled do
  not affect re-export semantics here (facade declares `__all__`).
