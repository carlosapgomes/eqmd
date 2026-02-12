# Coding Standards

## Purpose

This document is the single source of truth for coding standards in `eqmd`.
Use it to keep standards consistent across `AGENTS.md`, `CLAUDE.md`, and `openspec/config.yaml`.

## Precedence

When guidance conflicts, apply rules in this order:

1. Enforced tooling/configuration (CI, linters, type checks, test commands)
2. This document (`docs/workflows/coding-standards.md`)
3. Workflow docs (`docs/workflows/llm-collab.md`, `docs/workflows/clean-code-skill.md`)
4. Agent/context files (`AGENTS.md`, `CLAUDE.md`, `openspec/config.yaml`)

## Tooling Standards

- Python linting and formatting: `ruff` (single tool)
- Type checking target: `mypy` with `django-stubs` (single checker; phased rollout)
- Django mypy plugin: enable after compatibility validation in rollout phases
- Test verification command: `./scripts/test.sh`
- Type checker rollout plan: `docs/workflows/typing-rollout-plan.md`

## Rule Levels

- `Mandatory`: must pass before merge
- `Recommended`: should be followed; deviations must be intentional

## Core Standards (Mandatory)

- Single responsibility per function/class
- Prefer clarity over cleverness
- Avoid duplicated logic and magic numbers
- No business logic in controllers/views/routes
- Use explicit, descriptive names
- Avoid boolean flag arguments when split functions are clearer
- Separate transport, business logic, and persistence concerns

## Size and Structure Thresholds

- File length:
  - Recommended soft limit: 300 lines
  - Mandatory hard limit: 450 lines
  - If a file crosses 300 lines, add a split plan in the same change
- Function length:
  - Recommended soft limit: 40 lines
  - Mandatory hard limit: 60 lines
  - If a function crosses 40 lines, extract helpers or move business logic to services
- For OpenSpec slices, prompts may enforce stricter limits (for example <= 25 lines); stricter rule wins
- Directory density:
  - Recommended soft limit: 12 files per feature directory
  - If exceeded, prefer grouping by subdomain (for example `views/`, `services/`)

## Architecture Expectations (Mandatory)

- Preferred flow: Controller/View -> Service -> Repository/Model -> DTO/Serializer (when applicable)
- Controller/View: input validation, authz/authn, response shaping only
- Service layer: business rules and orchestration
- Repository/Model: persistence and query concerns

### Service Layer Rules

- New business workflows belong in `services/` modules
- Views should call services instead of implementing business branching directly
- Cross-model business logic should not live in model methods unless it is truly model-local

## Testing Standards (Mandatory)

- Tests are required for all new behavior and bug fixes
- Cover success paths, failure paths, and edge cases
- Validate permissions for protected endpoints/views
- Run project verification with `./scripts/test.sh`

## Frontend Standards

- Use Bootstrap for user-facing templates
- Do not add Bootstrap styling/scripts to Django admin templates
- Prefer vanilla JavaScript in admin templates
- Edit source assets in `assets/`, not generated files in `static/`
- Rebuild frontend assets after source changes

### Template Component Rules

- Reusable template fragments belong in `templates/components/`
- Prefix reusable partials with underscore (for example `_task_row.html`)
- If a template block is reused more than two times, extract it into a component partial

## Typing Standards

- Mandatory for new or modified Python code:
  - Add parameter and return type hints for new/changed functions
  - Avoid `Any` unless justified in a short inline comment
  - Keep service-layer function signatures fully typed
- Legacy code typing is phased; see `docs/workflows/typing-rollout-plan.md`

## Operational Standards for LLM Workflows

- For non-trivial work, use OpenSpec + slice-based implementation
- Implement one slice at a time with TDD flow (RED -> GREEN -> CLEAN -> VERIFY)
- Respect hard-stop safety rules for destructive commands unless explicitly approved
- Keep changes in scope; avoid unrelated refactors

## Enforcement Map

| Standard | Level | Enforcement |
| --- | --- | --- |
| Lint and formatting via `ruff` | Mandatory | Local command + CI |
| Type checks via `mypy` + `django-stubs` | Mandatory (after phased rollout) | Local command + CI (phased gate) |
| File/function size thresholds | Mandatory/Recommended | Code review checklist |
| Service layer boundaries | Mandatory | Code review checklist + tests |
| Template component extraction rules | Recommended | Code review checklist |
| Tests for new behavior | Mandatory | `./scripts/test.sh` before merge |

## Ownership and Sync

- If a standard changes, update this file first
- Then update summary references in `AGENTS.md`, `CLAUDE.md`, and `openspec/config.yaml`
- Keep those files concise and link back here instead of duplicating full rule sets

Last updated: 2026-02-12
