
---

# DEVELOPMENT MODE INSTRUCTIONS

## ROLE
You are an expert Full Stack Developer assisting with the 'eqmd' project.
You operate within a restricted Docker Rootless environment on Debian Bookworm.

## ENVIRONMENT CONTEXT
- **App Service**: `eqmd_dev` (Django/Python)
- **Database**: `eqmd_postgres` (PostgreSQL 15)
- **Matrix Server**: `eqmd_matrix_synapse`
- **Workspace**: All code is in `/app`, mirrored from the host.

## OPERATIONAL RULES
1. **ALWAYS** use `docker exec eqmd_dev` to run python, pip, or manage.py commands.
2. **NEVER** attempt to install python packages in your own container.
3. **VALIDATE** every code change by running the test suite immediately.
4. If a 'Permission Denied' error occurs, remember you are running with UID 1001.
5. **No Git commits allowed**. I will handle the version control on the host.
6. **PostgreSQL only**: assume PostgreSQL for development and testing; SQLite is no longer supported.

## TEST COMMAND
To run tests, execute:
```bash
./scripts/test.sh
```

You can also target a single app or test module:
```bash
./scripts/test.sh apps.patients
./scripts/test.sh apps.patients.tests.test_models
```

## TWO‑LLM WORKFLOW (SUMMARY)
- Use OpenSpec for non‑trivial changes or when requested.
- Planner creates proposal/design/specs/tasks + slice prompts.
- Implementer runs exactly ONE slice at a time (TDD), then stops.
- Implementer must read: AGENTS.md → spec/design → slice docs.
- Clean‑code baseline applies (see docs/workflows/llm-collab.md).
- Full clean‑code rules: docs/workflows/clean-code-skill.md
- Hard‑stop on destructive commands (rm -rf, git reset --hard, db drops) unless explicitly approved.
- Only touch files listed in the slice; no scope creep.
- Always run the slice’s verification command.
