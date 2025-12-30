# Projectlevelreqs Compliance Review (Codex)

**Date:** February 15, 2026  
**Scope:** Evaluate current repository against `prompts/projectlevelreqs.md` v1.1 (LLM-Optimized Django Architecture Requirements).

## Assessment Snapshot

- **Project Structure:** Partial – apps follow domain focus, but most lack `services.py`, `tasks.py`, and `prompts.py` modules called out in §2.1.
- **Models:** Strong – models remain explicit with audit fields and history tracking (§3).
- **Service Layer:** Non-compliant – business logic still lives in models and views rather than verb-led, typed service functions (§4).
- **Views:** Mixed – permissions enforced, yet views still own heavy query/business logic contrary to §5.
- **LLM Integration:** Missing – no dedicated `apps/llm/`, typed schemas, or provider abstraction (§6).
- **Prompt Versioning:** Missing – prompts live in ad-hoc markdown rather than versioned `prompts.py` modules (§7, §19).
- **Async Execution & Persistence:** Missing – no Celery/Django-RQ tasks or persisted LLM artifacts (§8–§9).
- **Testing:** Strong – pytest coverage across apps with descriptive test names, aligning with §11.

## Detailed Findings

### 1. Project Structure (§2)

- Strength: Every app is domain-oriented (`apps/patients`, `apps/events`, `apps/mediafiles`, etc.), and core Django entry points (`models.py`, `views.py`, `urls.py`) exist.
- Gap: Required companion modules are absent. For example, `apps/patients/` lacks `services.py`, `tasks.py`, and `prompts.py`. Similar gaps exist across other apps, so change localization for LLM work remains poor.
- Suggestion: Scaffold missing modules even if initially thin; organise imports so future services/tasks can be added without cross-app churn.

### 2. Models (§3)

- Evidence: `apps/patients/models.py` uses explicit fields, lifecycle flags, and `HistoricalRecords`. Soft-delete patterns are consistent (`SoftDeleteModel` usage).
- Opportunity: Complex methods such as `Patient.admit_patient` and `Patient.update_current_record_number` still embed workflow logic that §3 prefers to move to services for easier refactoring.

### 3. Service Layer (§4)

- Evidence: No project-wide `services.py` files with verb-led functions and type hints. Only a few minimal service classes exist (e.g., `apps/core/services/activity_tracking_simple.py`) and they omit type hints/docstrings beyond short summaries.
- Impact: Workflows like admissions, discharges, tag management, and event creation require touching models and views directly, increasing hallucination risk for LLM agents.
- Recommendation: Create service modules per app with single-purpose functions (e.g., `admit_patient`, `discharge_patient`, `update_tag_assignments`) returning typed dataclasses or ORM objects. Add docstrings that specify inputs/outputs for LLM consumption.

### 4. Views (§5)

- Evidence: `apps/events/views.py` and `apps/patients/views.py` contain 40–60 line query-building blocks and state transitions. Views read and mutate ORM objects directly.
- Issue: Violates “validate → call one service → respond” rule, making LLM-guided edits riskier.
- Recommendation: Refactor views to delegate to service functions, keeping only validation and response composition in the view layer.

### 5. LLM Integration Architecture (§6)

- Status: No dedicated LLM app or abstractions discovered; no typed schemas (`pydantic`, dataclasses) for LLM I/O.
- Consequence: Any future LLM work will start from scratch rather than plugging into a prepared scaffold.
- Suggestion: Introduce `apps/llm/` with `clients.py`, `schemas.py`, `evaluators.py`, `exceptions.py`, and provide a registry for provider backends.

### 6. Prompt Management (§7, §19)

- Observation: Prompts are stored as markdown plans inside `prompts/` (e.g., `prompts/augment-report.md`) rather than versioned constants in code.
- Risk: LLM prompts cannot be imported, tested, or versioned alongside services.
- Recommendation: Move actionable prompts into `prompts.py` modules inside each app (or within the new `apps/llm/`), with explicit version strings and accompanying scenario tests.

### 7. Async Execution & Persistence (§8–§9)

- Finding: Repository lacks Celery/Django-RQ configuration, async tasks, or persisted LLM outputs with metadata (`model_name`, `prompt_version`, tokens).
- Impact: Violates mandatory asynchronous execution flow and data retention requirements, blocking production-safe LLM features.
- Recommendation: Add task runner setup, enqueue LLM calls via tasks, and design tables to store generated content plus metadata.

### 8. Testing (§11)

- Strength: Comprehensive pytest suites per app (`apps/patients/tests/`, `apps/events/tests/`) with descriptive test names (e.g., `test_admit_patient_already_admitted_raises_error`). Aligns with §11 expectations.
- Next Step: As services emerge, add targeted unit tests for each service function and snapshot tests for prompt versions.

## Improvement Priorities

1. **Stand up the service layer**: Create `services.py` modules with typed, verb-led functions and migrate existing model/view logic.
2. **LLM foundation**: Add `apps/llm/`, prompt modules, typed schemas, and async task execution to satisfy §§6–9.
3. **Prompt migration**: Convert existing markdown prompts into importable, versioned code constants with documentation/test coverage.
4. **View slimming**: After services exist, refactor views to follow the “validate → service → respond” pipeline.
5. **Documentation alignment**: Update developer docs to reference new service/prompt patterns and reinforce LLM-oriented workflows.

## Overall Opinion

The codebase remains well-organized and medically focused, but it has not yet adopted the LLM-first architectural patterns mandated in `projectlevelreqs.md`. Prioritising a real service layer, LLM scaffolding, and asynchronous execution will materially reduce risk when future agents modify the system.
