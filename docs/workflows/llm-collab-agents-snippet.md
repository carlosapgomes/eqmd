## Two‑LLM Workflow (Planner + Implementer)

- Use OpenSpec for non‑trivial changes or when requested.
- Planner creates proposal/design/specs/tasks + slice prompts.
- Implementer runs exactly ONE slice at a time (TDD), then stops.
- Implementer must read: AGENTS.md → spec/design → slice docs.
- Clean‑code baseline applies (see docs/workflows/llm-collab.md).
- Full clean‑code rules: docs/workflows/clean-code-skill.md
- Hard‑stop on destructive commands (rm -rf, git reset --hard, db drops) unless explicitly approved.
- Only touch files listed in the slice; no scope creep.
- Always run the slice’s verification command.
