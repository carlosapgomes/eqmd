You are implementing exactly ONE slice of the “add-reports-app” change.
Start with EMPTY context and follow these steps:

1) Read and obey: /home/carlos/projects/eqmd/AGENTS.md
2) Read requirements: /home/carlos/projects/eqmd/openspec/changes/add-reports-app/specs/reports/spec.md
3) Read design: /home/carlos/projects/eqmd/openspec/changes/add-reports-app/design.md
4) Read the slice files:
   - /home/carlos/projects/eqmd/openspec/changes/add-reports-app/slices/slice-02.md
   - /home/carlos/projects/eqmd/openspec/changes/add-reports-app/slices/slice-02-prompt.md

STRICT SCOPE RULES:
- Only implement what slice-02.md includes.
- Do NOT implement future slices, even if you notice dependencies.
- Only read/modify files explicitly listed in slice-02.md, plus minimal files needed for context.
- If you encounter missing info, STOP and ask.

PROCESS RULES:
- TDD only (tests first, red -> green -> refactor).
- Use ./scripts/test.sh for verification.
- Use docker exec eqmd_dev only for python/pip/manage.py.
- No git commits.
- Stop after completing this slice (do not begin next).

Begin now with slice-02.
