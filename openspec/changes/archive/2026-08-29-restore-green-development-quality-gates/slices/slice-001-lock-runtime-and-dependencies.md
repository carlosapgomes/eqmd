# Slice 001 - Lock Runtime and Dependency Resolution

## Handoff for a zero-context implementer

Read completely, in order: `AGENTS.md`, `PROJECT_CONTEXT.md`, the three
workflow documents under `docs/workflows/`, ADR-0001, this change's proposal,
design, spec, tasks, and this slice. Implement only this slice and stop.

Initial planning evidence expected Django 6.1 in both lock and runtime. Slice
execution corrected that premise: `uv.lock` already resolved Django 5.2.1, but
the unlocked Docker image installed Django 6.1. Global
`makemigrations --check --dry-run` also exposes a separate legacy
`django-oidc-provider` AutoField contract drift under either runtime. See the
slice-001 report and reslice 001A before treating this foundation as complete.

## Mandatory DeepSeek4-Flash protocol

1. Record `BASE_REF`, `git status --short`, tool versions, `uv lock --check`,
   Django version, and migration-drift output before editing.
2. Do not overwrite unrelated patient-identity or Docker security changes.
3. Treat the unsupported runtime and unlocked build as RED evidence. Add an
   executable parity check if no existing command proves the requirement.
4. Implement the minimum lock-backed production/development Docker structure.
5. Do not install packages in the running container. Container image builds
   require explicit user approval before execution.
6. Run focused gates plus the full suite. Known downstream app failures may
   remain, but no new unexplained failure ID is allowed.
7. Write the required report. If any target gate fails, leave tasks unchecked,
   report `INCOMPLETE`, and do not start slice 002.
8. Do not commit or push.

## Objective

Make committed dependency metadata and Docker builds resolve the approved
Django 5.2 LTS line while keeping production and development dependency groups
separate.

## Requirements

- **R1:** constrain Django to `>=5.2.1,<5.3` and declare constrained Ruff/Mypy
  development tooling in the same lock update.
- **R2:** Docker dependency installation consumes `uv.lock` in frozen mode.
- **R3:** production output excludes the dev group; development output includes
  it without runtime installation.
- **R4:** local lock, Docker inspection, and CI resolution agree on the Django
  minor line.
- **R5:** unsupported runtime drift fails explicitly; never generate or edit a
  third-party migration as a workaround.

## Expected files

- `pyproject.toml`
- `uv.lock`
- `Dockerfile`
- `docker-compose.yml`
- one small parity script/test only if needed and justified

Do not edit application code, migrations, CI, quality scripts, or tests outside
a parity check. Preserve the existing loopback-only development port binding.

## TDD: RED -> GREEN -> REFACTOR

### RED

Capture failing assertions/commands proving Django 6.1 or unlocked Docker
installation. A text-only observation is insufficient if it can be encoded as
a deterministic check.

### GREEN

Apply the narrow dependency and Docker-target changes. Validate the exact `uv`
commands against the installed version; do not guess syntax. Do not rebuild or
recreate containers without user approval.

### REFACTOR

Remove duplicate install paths, keep stages named clearly, and ensure runtime
and development targets derive from one lock-backed base. No unrelated Docker
cleanup.

## Mandatory inspections

```bash
rg -n "django|ruff|mypy" pyproject.toml
rg -n 'name = "django"|name = "ruff"|name = "mypy"' uv.lock
rg -n "uv.lock|frozen|group dev|target:" Dockerfile docker-compose.yml
docker compose config
git diff --check
git diff --stat
```

Interpret exact resolved versions and prove production/dev separation in the
report.

## Verification commands

```bash
docker exec eqmd_dev uv lock --check
docker exec eqmd_dev python -c 'import django; print(django.get_version())'
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh apps.core.tests.test_urls apps.patients.tests.test_models
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-001-report.md
```

After explicit approval, also build and inspect both Docker targets without
mutating restored data. Record exact approved commands and image versions.

## Binary acceptance criteria

- [ ] Lock resolves Django `>=5.2.1,<5.3` plus declared Ruff/Mypy constraints.
- [ ] Frozen Docker build consumes `uv.lock`.
- [ ] Production and development dependency groups remain separated.
- [ ] Global migration drift is absent under the supported runtime.
- [ ] No third-party migration or application behavior changed.
- [ ] Focused tests pass and full-suite comparison has no new unexplained IDs.
- [ ] User approval evidence exists for any image build/recreation.

## Automatic `INCOMPLETE` conditions

Missing/modified lock, Django outside 5.2, dev tools in production output,
unlocked Docker install, failed migration gate after the approved runtime,
container rebuild without approval, new test failure, unexpected file, package
install in the running container, real PII, or missing report.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-001-report.md` with
status, requirement matrix, RED/GREEN evidence, resolved versions, Docker target
inspection, commands/exit codes, failure-ID comparison, diff scope, rollback,
and verifier handoff.

## Ready-to-run implementer prompt

```text
Read every file listed in slice-001-lock-runtime-and-dependencies.md. Implement
ONLY slice 001 using its DeepSeek protocol. Prove the current runtime/lock
mismatch as RED, make Docker and lock resolution deterministic on Django 5.2
LTS, keep prod/dev groups separate, and never install into the running
container. Request approval before any image build/recreation. Run every gate,
write the exact /tmp report, leave tasks unchecked on any failure, reply with
REPORT_PATH and STATUS, then STOP. Do not commit or push.
```
