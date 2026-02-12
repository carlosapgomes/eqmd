# Typing Rollout Plan

## Goal

Adopt reliable static typing in a large Django codebase without blocking delivery.

Target stack:
- `mypy`
- `django-stubs`

## Principles

- Enforce typing on new and changed code first
- Avoid large one-shot typing migrations
- Add strictness gradually by app and by layer
- Keep CI signal actionable (low noise, clear ownership)

## Phase 0: Tooling Baseline

Objective:
- Add and configure type-checking toolchain.

Deliverables:
- Add dev dependencies for `mypy` and `django-stubs`
- Add minimal `mypy` configuration in `pyproject.toml` or `mypy.ini`
- Add Django plugin settings for future activation
- Add a documented local command for type checks

Exit criteria:
- Type checker runs successfully on a small scoped path (for example one app or one module set)
- Team docs reference one canonical type-check command

Current baseline note:
- Keep `mypy_django_plugin` disabled if it causes internal crashes in current dependency versions.
- Re-enable it in a dedicated hardening step once compatibility is validated.

## Phase 1: New and Changed Code Policy

Objective:
- Prevent new untyped debt.

Rules:
- All new/changed Python functions must include parameter and return type hints
- Service-layer code must be fully typed
- New `Any` usage requires explicit justification

CI policy:
- Run type checks only on changed paths (or selected app paths)

Exit criteria:
- All merged changes in active development areas comply with typing policy for 2 consecutive weeks

## Phase 2: High-Value Surface First

Objective:
- Type the most bug-prone and business-critical code.

Priority order:
1. `services/` modules
2. Permission and security-sensitive modules
3. Complex query and data transformation logic
4. Integration boundaries (external APIs, parsers, import pipelines)

Tactics:
- Add typed DTOs/protocols for service boundaries
- Reduce dynamic attribute access in typed paths
- Isolate legacy dynamic code behind typed wrappers
- Re-test and enable `mypy_django_plugin` when stable in this project

Exit criteria:
- Priority modules pass type checks with stable CI
- No high-severity runtime typing issues in typed modules for one release cycle

## Phase 3: App-by-App Expansion

Objective:
- Expand coverage across apps without stalling feature work.

Rules:
- Pick one app at a time
- Define per-app minimum bar (for example: service and utils modules fully typed)
- Keep migrations and generated code out of strict checks

CI policy:
- Add per-app type-check targets as each app reaches baseline

Exit criteria:
- Majority of active apps included in type-check scope

## Phase 4: Stronger Enforcement

Objective:
- Move from selective to default enforcement.

Actions:
- Turn on stricter checks in mature typed areas
- Fail CI on new typing regressions
- Keep exception list small and time-bounded

Exit criteria:
- Type checks are part of standard merge gate
- Exception list is stable and reviewed regularly

## Suggested Command Convention

Use one command shape in docs and CI:

```bash
docker exec eqmd_dev mypy apps/
```

For incremental rollout, run scoped paths first:

```bash
docker exec eqmd_dev mypy apps/core/permissions apps/<target_app>/services
```

## Exception Process

When a module cannot be typed immediately:

1. Add a temporary scoped ignore (not global ignore)
2. Document reason and owner in the PR
3. Add a follow-up task with a deadline
4. Remove the ignore once module is migrated

Last updated: 2026-02-12
