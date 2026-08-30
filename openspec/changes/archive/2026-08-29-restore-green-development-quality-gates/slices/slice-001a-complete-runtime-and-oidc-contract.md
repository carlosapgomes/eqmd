# Slice 001A - Complete Runtime and OIDC Primary-Key Contract

## Handoff for a zero-context implementer

Read completely, in order: `AGENTS.md`, `PROJECT_CONTEXT.md`, the three
workflow documents under `docs/workflows/`, ADR-0001, every artifact of this
change, slice 001, its report, this reslice, and the current diffs owned by
slice 001. Implement only this reslice and stop.

Required prior evidence:

- `/tmp/restore-green-development-quality-gates-slice-001-report.md`
- slice 001 is `INCOMPLETE`; tasks 1.1-1.5 remain unchecked;
- `uv.lock` already resolved Django 5.2.1 before slice 001;
- the unlocked image, not the lock, installed Django 6.1;
- under Django 5.2.1, migration drift is limited to six `oidc_provider` PKs;
- vendor migrations and all six restored PostgreSQL columns use `AutoField` /
  `integer`, while runtime models currently infer `BigAutoField`;
- PyPI 0.9.0 is the latest `django-oidc-provider` release.

The approved contract is a project-owned compatibility `AppConfig` that keeps
`oidc_provider` on `django.db.models.AutoField`. Do not upgrade/vendor the
package, generate a migration, alter existing columns, or change the project's
global `DEFAULT_AUTO_FIELD`.

## Mandatory DeepSeek4-Flash protocol

1. Record `BASE_REF`, `git status --short`, the slice-001 owned diff, current
   runtime/lock/uv versions, and aggregate RED evidence before editing.
2. Preserve every unrelated patient-identity, security, ADR, and slice-001
   change. Do not revert or broadly reformat them.
3. Add the focused OIDC regression test first and prove it fails for the
   expected `BigAutoField` reason.
4. Correct only the two deterministic-Docker defects and the OIDC app contract.
5. Do not install packages in a running container or modify restored data.
6. Ask for explicit user approval before any image build, recreation, or
   `docker compose run` command. Without approval, stop `INCOMPLETE`.
7. After approval, build and inspect both targets using ephemeral, no-dependency
   commands. Do not recreate the running `eqmd_dev` service.
8. Run every gate, write the exact report, reply with `REPORT_PATH` and
   `STATUS`, and stop. Do not start slice 002, commit, or push.

## Objective

Finish slice 001 by making Docker installation fully lock-closed, pinning the
validated uv build tool, and aligning the legacy OIDC model state with vendor
migrations and the retained PostgreSQL schema without a migration.

## Requirements

- **R1:** Docker copies uv from the validated `0.12.5` image tag or a verified
  immutable digest; `latest` is forbidden.
- **R2:** every editable project install uses `--no-deps` after the frozen lock
  export; no command can resolve project dependencies a second time.
- **R3:** a project-owned `AppConfig` subclasses the vendor OIDC config and sets
  `default_auto_field = "django.db.models.AutoField"`.
- **R4:** `INSTALLED_APPS` selects that compatibility config without changing
  the global `DEFAULT_AUTO_FIELD` used by project apps.
- **R5:** focused tests prove the six vendor models use `AutoField` and an OIDC
  client/response-type relation still supports synthetic CRUD.
- **R6:** under the built Django 5.2 development image, global
  `makemigrations --check --dry-run` exits 0 and creates no file.
- **R7:** built production and development targets both pass runtime parity;
  production excludes Ruff/Mypy and development contains locked versions.
- **R8:** supported-runtime focused and full-suite comparisons introduce no new
  unexplained failure ID.

## Expected files

- `Dockerfile`
- `config/settings.py`
- `config/third_party_apps.py` (new)
- `apps/core/tests/test_oidc_provider_config.py` (new)

Inspect but do not edit `pyproject.toml`, `uv.lock`, `docker-compose.yml`,
`scripts/check_runtime_parity.sh`, package files under `site-packages`, or any
migration. Stop and return to the planner if another semantic file is needed.

## TDD: RED -> GREEN -> REFACTOR

### RED

Create the focused test before production changes. It must fail because the
loaded OIDC app config and the six named model PKs resolve to `BigAutoField`.
Also record deterministic Docker RED evidence:

```bash
rg -n 'astral-sh/uv:latest|uv pip install --system --editable \.($|;)' \
  Dockerfile
```

Record the supported-runtime migration failure from the prior report or
reproduce it without writing files. The expected delta is only the six OIDC
`AlterField id` operations; any other drift is `INCOMPLETE`.

### GREEN

Implement the compatibility config, select it in settings, pin uv, and add
`--no-deps` to both editable installs. Use no migration, schema operation,
package upgrade, global setting change, or exception-based suppression.

### REFACTOR

Keep the compatibility class documented in one short module. Do not introduce
a generic third-party compatibility framework or duplicate the six model names
outside the focused test.

## Mandatory inspections

```bash
rg -n 'astral-sh/uv|uv export|uv pip install|INSTALL_DEV' Dockerfile
rg -n 'oidc_provider|DEFAULT_AUTO_FIELD' \
  config/settings.py config/third_party_apps.py
rg -n 'AutoField|Client|Code|ResponseType|RSAKey|Token|UserConsent' \
  apps/core/tests/test_oidc_provider_config.py
rg -n 'django|ruff|mypy' pyproject.toml
rg -n 'name = "django"|name = "ruff"|name = "mypy"' uv.lock
git diff --check
git diff --stat
```

The report must explicitly prove that no migration, package metadata, restored
row, global auto-field setting, or unrelated file changed.

## Verification before image approval

```bash
bash -n scripts/check_runtime_parity.sh
docker compose config
docker compose --profile prod config
docker exec eqmd_dev uv lock --check
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-001a-report.md
git diff --check
```

The currently running container may remain on Django 6.1 and is not valid
GREEN evidence for the new OIDC test or migration gate.

## Verification after explicit image-build approval

Use the approved equivalent of these commands. Do not run them without approval
recorded in the report.

```bash
docker compose build eqmd-dev
docker compose --profile prod build eqmd
docker compose run --rm --no-deps eqmd-dev \
  bash scripts/check_runtime_parity.sh
docker compose --profile prod run --rm --no-deps eqmd \
  bash scripts/check_runtime_parity.sh
docker compose run --rm --no-deps eqmd-dev ruff --version
docker compose run --rm --no-deps eqmd-dev mypy --version
docker compose --profile prod run --rm --no-deps eqmd \
  sh -c '! command -v ruff && ! command -v mypy'
docker compose run --rm --no-deps eqmd-dev \
  python manage.py check
docker compose run --rm --no-deps eqmd-dev \
  python manage.py makemigrations --check --dry-run
docker compose run --rm --no-deps eqmd-dev \
  python manage.py test --noinput \
  apps.core.tests.test_oidc_provider_config apps.botauth.tests
docker compose run --rm --no-deps eqmd-dev \
  python manage.py test --noinput
```

Also prove the exact resolved versions and production/development group
separation from both built targets. If Compose service discovery is required
for tests, request approval for the smallest non-destructive command adjustment
and document it; never recreate or drop the restored development database.

## Binary acceptance criteria

- [ ] Focused RED fails only for the pre-fix OIDC `BigAutoField` mismatch.
- [ ] uv is pinned; no `latest` reference remains in the Python build path.
- [ ] both editable installs include `--no-deps` after frozen exports.
- [ ] compatibility config is selected and global `DEFAULT_AUTO_FIELD` is
      unchanged.
- [ ] six OIDC PKs resolve to `AutoField`; synthetic OIDC relation CRUD passes.
- [ ] both built targets report locked Django 5.2 and correct dependency groups.
- [ ] global supported-runtime migration check exits 0 with no generated file.
- [ ] focused tests pass and full-suite comparison has no new unexplained ID.
- [ ] no migration, schema/data mutation, package upgrade, unrelated edit,
      container recreation, commit, push, or PII exists.
- [ ] explicit user approval for all build/run commands is quoted in the report.

## Automatic `INCOMPLETE` conditions

Missing image approval, failed target build, `uv:latest`, editable install
without `--no-deps`, migration drift, generated/vendor migration, OIDC package
upgrade or vendoring, changed global `DEFAULT_AUTO_FIELD`, schema/data mutation,
new unexplained test failure, unsupported runtime, unexpected file, real PII,
missing report, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-001a-report.md` with
status, approval evidence, RED/GREEN output, OIDC authority matrix, exact diff,
Docker commands and image versions, prod/dev package inspection, migration
gate, focused/full test comparison, no-data-mutation proof, rollback, and
third-LLM verifier handoff.

Do not mark tasks 1.1-1.5 or 1A.1-1A.5 yourself. A third-LLM planner marks them
only after both slice-001 reports and the actual diff are approved.

## Ready-to-run implementer prompt

```text
Read every prerequisite in slice-001a-complete-runtime-and-oidc-contract.md.
Implement ONLY reslice 001A with strict RED->GREEN->REFACTOR. Preserve slice
001 and unrelated work. Pin uv, add --no-deps to both editable installs, and
use a project-owned OIDC AppConfig with AutoField; never create a migration,
upgrade/vendor OIDC, change global DEFAULT_AUTO_FIELD, or touch restored data.
Request explicit approval before any Docker build/run. After approval inspect
both targets, require global migration exit 0, run focused and supported-runtime
full tests, write the exact /tmp report, reply REPORT_PATH and STATUS, then
STOP before slice 002. No install in the running container, commit, or push.
```
