<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:

- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:

- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

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
