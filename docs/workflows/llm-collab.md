# Two‑LLM Workflow (Planner + Implementer)

Purpose: a reproducible, low‑risk workflow for greenfield and brownfield work using

- **Planner/Debugger LLM** (you/me) for design, OpenSpec, slicing, and troubleshooting
- **Implementer LLM** (glm‑4.7 via pi) for small, scoped implementation only

This workflow assumes strong guardrails because the implementer is permissive.

---

## When to Use OpenSpec

Use OpenSpec when the change is **non‑trivial** or when explicitly requested:

- New app/module
- Cross‑cutting change across multiple apps
- Schema changes + UI changes + services
- Any change requiring multiple slices

Trivial fixes: skip OpenSpec and write a small slice plan only.

---

## Roles

**Planner/Debugger LLM (Codex)**

- Creates/updates OpenSpec artifacts (proposal, design, specs, tasks)
- Defines slices and prompts
- Sets guardrails, checklists, test commands
- Debugs failed builds/tests and provides minimal guidance
- Never implements unless explicitly asked

**Implementer LLM (glm‑4.7 / pi)**

- Implements exactly ONE slice at a time
- Follows TDD: tests → minimal code → refactor → verify
- Runs only approved commands
- Stops after slice completion

---

## Clean Code Baseline (Implementer)

Hard constraints (keep small and enforceable):
- Single responsibility per function/class
- Functions ≤ 25 lines
- No duplicated logic
- No magic numbers (extract constants)
- No business logic in controllers/views
- Avoid boolean flag arguments (split functions)
- Use dependency injection for external services
- Explicit, descriptive naming (no abbreviations)

Architecture expectation:
Controller/View → Service → Repository/Model → DTO/Serializer (when applicable)

Self‑review pass:
After implementing, perform a strict clean‑code audit and fix any violations.

Reference: `docs/workflows/clean-code-skill.md` (full ruleset).

---

## Guardrails (Implementer)

**Hard‑Stop (never run):**

- `rm -rf`, `git reset --hard`, `git checkout --`, `docker compose down -v`
- Any DB destructive action (drop, truncate, reset) without explicit approval
- Package installs outside the app container

**Approval Required:**

- Any command that drops/creates databases
- Any command that modifies Docker volumes or container lifecycle
- Any data migration or restoration

**Scope Control:**

- Only implement what the slice lists
- Only touch files listed in the slice (plus minimal context files)
- Do not refactor unrelated code
- If blocked, STOP and ask

---

## Pre‑Read Order (Implementer)

1) `AGENTS.md`
2) OpenSpec specs/design for the change (if present)
3) Slice file and slice prompt for the current slice

---

## Standard Slice Loop

1) **Read** scope + constraints
2) **Write tests first** (RED)
3) **Implement minimal code** (GREEN)
4) **Refactor + clean‑code audit** (CLEAN)
5) **Verify** with provided command
6) **Stop** and report results
7) **Mark checklist boxes** as completed in the slice prompt before stopping

---

## Required Output From Implementer

- Files changed (paths only)
- Tests run (command + result)
- Any failures or blockers
- Confirmation that no out‑of‑scope work was done

---

## Brownfield vs Greenfield Notes

- **Greenfield**: prefer OpenSpec + full slice plan.
- **Brownfield**: use smaller slices, avoid broad refactors, prefer adapters to existing patterns.

---

## Failure Handling

- If tests fail due to missing deps or pre‑existing failures: report and stop.
- If migrations are required, ask for approval first.
- If a destructive command is needed, request explicit user approval.

---

## Handoff Checklist (Implementer)

Spec
- [ ] requirements understood

Tests (RED)
- [ ] failing tests written
- [ ] tests cover behavior and edge cases

Implementation (GREEN)
- [ ] minimal code added
- [ ] tests pass

Refactor (CLEAN)
- [ ] responsibilities separated
- [ ] duplication removed
- [ ] functions small
- [ ] naming improved
- [ ] business logic only in services

Verification
- [ ] pytest passes
- [ ] lint/typecheck passes (if configured)

STOP RULE
- [ ] stop here and do NOT start next slice

---

## Notes / FAQ

**Do I need a separate “clean code skill”?**
- Not required. Keep clean code constraints inside AGENTS.md + slice prompts.
- OpenSpec does not conflict with clean code or TDD; it complements them by structuring scope.

**Is slicing still a good fit for LLMs?**
- Yes. Small, vertical slices reduce hallucinations and make verification deterministic.

**Should tasks use checkboxes?**
- Yes if you use OpenSpec tasks. Checkboxes make progress explicit and auditable.

**What should the implementer read before each slice?**
- AGENTS.md, then spec/design for the change, then the slice files. (See Pre‑Read Order.)

**Should context be cleared between slices?**
- Yes. Start each slice with empty context to minimize drift and scope creep.
