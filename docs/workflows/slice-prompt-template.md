# Slice Prompt Template (Implementer LLM)

You are implementing exactly ONE slice of the “<change-name>” change.
Start with EMPTY context and follow these steps:

1) Read and obey: /home/carlos/projects/eqmd/AGENTS.md
2) Read requirements: /home/carlos/projects/eqmd/openspec/changes/<change-name>/specs/<capability>/spec.md
3) Read design: /home/carlos/projects/eqmd/openspec/changes/<change-name>/design.md
4) Read the slice files:
   - /home/carlos/projects/eqmd/openspec/changes/<change-name>/slices/slice-XX.md
   - /home/carlos/projects/eqmd/openspec/changes/<change-name>/slices/slice-XX-prompt.md

STRICT SCOPE RULES:
- Only implement what slice-XX.md includes.
- Do NOT implement future slices, even if you notice dependencies.
- Only read/modify files explicitly listed in slice-XX.md, plus minimal files needed for context.
- If you encounter missing info, STOP and ask.

CLEAN CODE RULES (baseline):
- Single responsibility per function/class
- Functions ≤ 25 lines
- No duplicated logic or magic numbers
- No business logic in controllers/views
- Avoid boolean flag arguments
- Explicit, descriptive naming

GUARDRAILS:
- Never run destructive commands (rm -rf, git reset --hard, db drops) unless explicitly approved.
- Do not modify Docker volumes or container lifecycle without approval.
- If a destructive or privileged action is needed, STOP and ask.

PROCESS RULES:
- TDD only (tests first, red -> green -> refactor).
- Use ./scripts/test.sh for verification.
- Use docker exec eqmd_dev only for python/pip/manage.py.
- No git commits.
- Stop after completing this slice (do not begin next).
- Mark checklist boxes as completed before stopping.

Begin now with slice-XX.
