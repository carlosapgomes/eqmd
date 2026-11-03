# Slice 001 — Seed isolation

## Identity

- Slice: `slice-001-seed-isolation`
- Change: `isolate-sample-specialty-seed-from-tests`
- Tasks: `tasks.md` items 1.1–1.3 (Contract: this file)

## Objective

Make test databases build without the sample-specialty seed so the
74 pre-existing IntegrityErrors disappear, proven by the full suite
going to zero errors with no new failures.

## Read first

- `AGENTS.md`
- `openspec/changes/isolate-sample-specialty-seed-from-tests/proposal.md`
- `openspec/changes/isolate-sample-specialty-seed-from-tests/design.md` (D1–D4)
- `openspec/changes/isolate-sample-specialty-seed-from-tests/specs/development-quality-gates/spec.md`
- `apps/accounts/migrations/0005_populate_sample_specialties.py`
- `config/test_settings.py`
- `scripts/test.sh` (NOT to be used for evidence — runs against the
  `eqmd_dev` container bound to another checkout and defaults to
  `--keepdb`)
- The controller-provided evidence runner (in the slice evidence
  `logs/` dir): throwaway container mounting THIS worktree,
  `DJANGO_SETTINGS_MODULE=config.test_settings`,
  `DATABASE_TEST_NAME` propagated, `--noinput` (destroys any
  pre-existing named test DB without prompting), fresh database by
  default (`EQMD_TEST_KEEPDB` unset/0)
- Failing-module examples (context only): `apps/accounts/tests/test_team_membership.py`
  (note `MembershipBackfillMigrationTestCase` is a
  `TransactionTestCase` — relevant to why retained databases can
  false-GREEN), `apps/patients/tests/test_tag_catalogue_governance.py`,
  `apps/core/tests/test_cache_tag_privacy.py`

## Requirements

- **R1 — Guard**: `create_sample_specialties` in migration 0005
  returns early — BEFORE any `apps.get_model` access — when
  `getattr(settings, "EQMD_SEED_SAMPLE_SPECIALTIES", True)` is
  falsy. Import `django.conf.settings` inside the function body.
  Default stays `True`. The row list is untouched.
- **R2 — Test opt-out**: `config/test_settings.py` gains
  `EQMD_SEED_SAMPLE_SPECIALTIES = False`.
- **R3 — Canary and guard tests**: new
  `apps/accounts/tests/test_specialty_seed_isolation.py` with:
  1. an absence test asserting that NONE of the 30 bootstrap
     abbreviations from migration 0005 exists in the test database
     (loop the exact list);
  2. a guard unit test with THREE explicit cases, calling the real
     `create_sample_specialties` with a valid apps registry (e.g.
     via `django.apps.apps`) inside an ordinary `TestCase` so writes
     roll back: (a) flag `False` → returns early, creates nothing;
     (b) flag `True` → creates the expected rows; (c) flag ABSENT
     (delete the setting) → default-on seeding, exercising D1's
     `getattr` default.
  3. Keep the enabled-path writes inside `TestCase` methods
     (transactional rollback), separate from the absence test.
     The new canary module is the authorized exception to "do not edit
     test modules" (which refers to EXISTING modules).
- **R4 — Proof**: full suite via the evidence runner on a FRESH
  database: errors 74 → **0**, failures 0. Record BOTH the
  discovered and the run test counts (class-setup failures prevent
  bodies from running; the canary adds tests). Extract the
  before/after error-id sets with
  `grep -E "^ERROR:" <log> | sed -E 's/^ERROR: (\w+) \(([^)]+)\).*/\2.\1/' | sort`
  and show the before-set is empty after; additionally run the
  previously failing modules verbosely (focused) so individual
  passes are visible, not just the absence of errors.
- **R5 — Blast radius**: only migration 0005 (guard clause),
  `config/test_settings.py` (flag + narrowly scoped cleanup of its
  pre-existing lint problems), and the new canary module change.
  Narrowly scoped cleanup INSIDE these files is authorized and
  required for the CI gates: remove the unused `uuid` import in
  0005, add `# noqa: RUF012` comments to the two `Migration` class
  attributes in 0005 (supervisor-authorized during exec-1; repo
  precedent: dischargereports/0003), and fix the wildcard/`os`
  import issues in `config/test_settings.py`. No OTHER file changes;
  no edits to existing test modules, models, other migrations, CI
  workflows.

## Expected blast radius

Expected: exactly the three surfaces above (cleanup included).
Sensitive (escalate): any other file, especially existing test
modules and CI workflows. Extra files need justification.

## Failing-before plan

Both phases MUST run on freshly created test databases via the
evidence runner (no `--keepdb`; `--noinput` handles any pre-existing
named DB):

- Run `apps.accounts.tests.test_team_membership` isolated → record
  the IntegrityError output (name-key duplicates) — fresh DB.
- Write the canary first → it must FAIL against the current tree on
  a FRESH database (migrations run → seeded rows present). Record
  output. (A retained database may false-GREEN — that is why fresh
  creation is mandatory.)

Then implement R1–R2 → canary GREEN (fresh DB), failing modules
GREEN (fresh DB).

## Implementation constraints

- Do not edit 0005 beyond the guard + unused-import removal.
- Do not touch `scripts/test.sh`, CI workflows, or EXISTING test
  modules (the new canary module is the authorized exception).
- No commits/pushes; no tasks.md edits; no deps.

## Validation

- Focused (fresh DB): `apps.accounts apps.patients apps.events
apps.core` — zero errors (previously all 74 lived here); record
  discovered/ran counts.
- Full suite (fresh DB): errors 74 → 0; failures 0; record counts.
- CI-equivalent quality gates on the CHANGED files: absolute
  `ruff check` success AND `ruff format --check` success (matching
  `.github/workflows/ci-pr.yml`) — not a "zero NEW findings"
  comparison.

## Acceptance criteria

- [ ] AC1: guard present, before any `apps.get_model` access,
      default True (R1).
- [ ] AC2: test_settings opts out (R2).
- [ ] AC3: canary + 3-case guard test, RED→GREEN recorded on fresh
      DBs (R3).
- [ ] AC4: full suite 74→0 errors, 0 failures, no new errors;
      before-error-id set empty after; focused modules individually
      green (R4).
- [ ] AC5: diff limited to the three expected surfaces with the
      authorized cleanups; absolute ruff + format gates pass (R5).

## Escalation conditions

Stop with `BLOCKED_NEEDS_DECISION` if: removing the seed surfaces a
test that genuinely depends on seeded rows (report which), the guard
cannot live inside the data function, or new errors appear that are
not seed-related.

## Evidence report

Status; R1–R5 → evidence; failing-before and passing-after (fresh
DBs, runner identified, exit codes); discovered/ran counts; full
suite before/after; absolute ruff and format results;
`git diff --stat`; deviations; risks. End with `READY_FOR_REVIEW`
and `REPORT_PATH=<path>`.
