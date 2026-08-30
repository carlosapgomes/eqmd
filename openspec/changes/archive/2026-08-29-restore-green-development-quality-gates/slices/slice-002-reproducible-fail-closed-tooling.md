# Slice 002 - Reproducible Fail-Closed Development Tooling

## Handoff for a zero-context implementer

Read `AGENTS.md`, `PROJECT_CONTEXT.md`, all canonical workflow documents,
ADR-0001, all artifacts of this change, the approved slice-001 and slice-001A
reports, and this file. Start only after third-LLM approval of both reports and
the completed foundation diff.

Current behavior: `scripts/typecheck.sh` installs the dev group as root when
Mypy is absent; `scripts/install-dev-deps.sh` mutates a running container; CI
uses `uv sync --group dev` but does not enforce all documented Ruff/format and
migration gates. Slice 001 must already provide lock-backed dev tools.

## Mandatory DeepSeek4-Flash protocol

Record baseline commands and script contents before editing. Use missing-tool
PATH/process tests as RED. Never actually remove tools from the shared
container and never install packages. Implement only script/CI gate behavior,
run focused shell checks and full regression comparison, create the report, and
stop. Any target failure means `INCOMPLETE` and tasks remain unchecked.

## Objective

Make local quality scripts and CI consume prebuilt tools, fail clearly when a
tool is absent, and never mutate the environment under test.

## Requirements

- **R1:** `typecheck.sh` checks for Mypy and exits nonzero with rebuild guidance
  when absent; it never installs or elevates privileges.
- **R2:** the legacy dev-dependency installer is removed, deprecated, or changed
  to a non-mutating diagnostic entry point with no hidden callers.
- **R3:** local and CI commands use committed lock metadata and the same Ruff,
  format, Mypy, check, and migration semantics.
- **R4:** docs-only CI behavior remains unchanged and production behavior is
  untouched.

## Expected files

- `scripts/typecheck.sh`
- `scripts/install-dev-deps.sh`
- `.github/workflows/ci-pr.yml`
- one focused shell test under `scripts/tests/` if required

Do not modify dependencies, lockfile, Dockerfiles, application code, or tests.
If slice 001 left a tooling defect, stop and return it to the planner.

## TDD

### RED

Run the script in a controlled shell where `mypy` cannot be found and prove it
attempts mutation or lacks the required fail-closed contract. Add a shell test
before implementation where practical. Do not alter the live container.

### GREEN

Replace mutation with an explicit prerequisite failure and align CI gates.
Keep commands small, quoted, and `set -euo pipefail` compatible.

### REFACTOR

Remove duplicated command construction without introducing a generalized
framework. Preserve existing CLI usage and exit codes where not changed by R1.

## Mandatory inspections

```bash
rg -n "pip install|uv pip|--user root|command -v|ruff|mypy|makemigrations" \
  scripts/typecheck.sh scripts/install-dev-deps.sh .github/workflows/ci-pr.yml
bash -n scripts/typecheck.sh scripts/install-dev-deps.sh
git diff --check
git diff --stat
```

The report must show zero runtime install/elevation paths in quality scripts.

## Verification commands

```bash
./scripts/typecheck.sh apps/patients/services/patient_identity.py
docker exec eqmd_dev ruff --version
docker exec eqmd_dev mypy --version
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh apps.core.tests.test_urls
./scripts/test.sh
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-002-report.md
```

Also execute the safe missing-tool regression test defined during RED.

## Binary acceptance criteria

- [ ] Missing Mypy/Ruff fails without package installation or root execution.
- [ ] Existing scoped typecheck succeeds in the approved dev image.
- [ ] CI installs from lock and executes documented gates.
- [ ] Docs-only short circuit and app-scoped test detection remain intact.
- [ ] Focused tests pass; full suite has no new unexplained failure IDs.

## Automatic `INCOMPLETE` conditions

Any package install in a quality script, tool version outside the lock, CI/local
semantic drift, failed focused check, unapproved file, weakened CI scope,
missing full comparison, missing report, or commit/push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-002-report.md` with
RED/GREEN proof, script before/after snippets, CI inspection, all exit codes,
full-suite comparison, rollback, and verifier handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 002 after reading its prerequisites and both approved
slice-001 reports. TDD the missing-tool path, remove all runtime/root installs
from quality scripts, align CI with locked tools, preserve docs-only and scoped
test behavior, run every gate, write the required /tmp report, and STOP. Any
missing/failing gate is INCOMPLETE. Do not edit dependencies or app code, and
do not commit or push.
```
