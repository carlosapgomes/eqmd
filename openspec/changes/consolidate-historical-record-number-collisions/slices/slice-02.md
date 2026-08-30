# Slice 02 - Module Split and Operator Runbook

## Handoff for a zero-context implementer

Read these files fully and in order:

1. `AGENTS.md`
2. `PROJECT_CONTEXT.md`
3. `docs/workflows/coding-standards.md` (file-length hard limit: 450)
4. `docs/workflows/llm-collab.md`
5. `docs/workflows/clean-code-skill.md`
6. Every artifact of
   `consolidate-historical-record-number-collisions` including the
   verified slice-01 report under `/tmp`
7. This slice file

Implement exactly one slice and stop.

Current code facts to verify before planning:

- `apps/patients/tests/test_patient_identity_record_numbers.py` is 639
  lines (21 slice-003 classes/tests plus 11 slice-004 constraint
  tests/classes).
- The five slice-004 constraint test classes are the extraction target;
  shared module-level helpers used by both halves must stay importable
  (duplicate them only if trivially small; otherwise move them to the
  new module and import from the old one).
- `docs/workflows/` holds the project runbooks (markdown, linted).
- The slice-01 correction 2 renumbered the migrations: `0002` widens
  `record_number` to 120; the verified constraint is now `0003`. The
  runbook must reflect this order (widen may apply before
  consolidation; the `0003` preflight still fails closed until zero).
- Disclosure 15.5 of the slice-01 report: passing `models.py` in the
  same mypy invocation as the services surfaces one `attr-defined` on
  `patient_identity.py` (`row.patient_id` implicit FK attribute). The
  planner ratified closing it inside this change via a string-based
  `values_list` refactor (R4 below), not a `type: ignore`.

## Mandatory protocol for DeepSeek4-Flash

Same protocol as slice 01 (baseline green before edits; tooling
pre-exists; real RED where behavior is touched; every gate; exact
report; stop for verification). For a pure move-plus-docs slice, the RED
step is replaced by a pre-edit measurement: record per-module test
counts and line counts; any count change other than the declared move is
a blocker.

## Objective

Bring the record-number test modules under the 450-line hard limit
without changing discovery counts, and give the project owner the
operator runbook for executing the audited consolidation and applying
`0002`.

## Functional scope

### R1 - Test module split

Create `apps/patients/tests/test_patient_record_constraint_database.py`
and move the five slice-004 constraint classes into it verbatim
(imports adjusted, shared helpers relocated or imported). Both modules
must end under 450 lines. Combined focused test count must equal the
pre-split count (32 across both modules).

### R2 - Operator runbook

Create `docs/workflows/record-number-consolidation-runbook.md` covering,
in order:

1. run the aggregate audit (`manage.py consolidate_record_numbers`);
2. review per-group detail with `--show-records` (operator console only);
3. author the JSON decision plan per the slice-01 schema, with the
   clinical rationale for every action; the plan file stays outside the
   repository and is never committed;
4. validate with `--plan ... --dry-run` and confirm the would-be end
   state shows zero collision groups;
5. execute with `--execute --user <operator>` (project owner only;
   implementer LLMs never run this against the restored database);
6. re-run the aggregate audit and confirm zero;
7. apply the migration (`manage.py migrate patients`) - the `0002`
   preflight re-verifies zero collisions and fails closed otherwise;
8. request third-LLM verification of the end state (aggregate audit,
   `showmigrations`, full suite).

State explicitly: no code path decides ownership automatically; the
marker preserves the original number verbatim; production rollout
follows the same sequence during a maintenance window.

### R3 - Gates

No behavior change: full suite count identical to baseline; both focused
modules green; docs lint-clean.

### R4 - Typing closure for the collision-group helper

In `apps/patients/services/patient_identity.py`, `_collision_group`
collects ids via model attribute access (`row.pk`, `row.patient_id`).
Refactor it to `.values_list("id", "patient_id")` (string-based, no
attribute access, same query semantics) so the STRICT combined mypy
invocation (`models.py` + the four slice-01 code files in one command)
is clean. No `type: ignore`. Behavior is covered by the existing
discovery tests; do not change them.

## Expected files

Modify/create only:

- `apps/patients/tests/test_patient_identity_record_numbers.py`
- `apps/patients/tests/test_patient_record_constraint_database.py` (new)
- `apps/patients/services/patient_identity.py` (R4 only)
- `docs/workflows/record-number-consolidation-runbook.md` (new)
- `openspec/changes/consolidate-historical-record-number-collisions/tasks.md`
  only after all gates pass

Any other file needs planner approval. Forbidden: production code
changes, migrations, settings, renames of test methods, count changes,
commits, pushes, installs.

## Verification commands

```bash
./scripts/test.sh apps.patients.tests.test_patient_identity_record_numbers
./scripts/test.sh apps.patients.tests.test_patient_record_constraint_database
docker exec eqmd_dev ruff check \
  apps/patients/tests/test_patient_identity_record_numbers.py \
  apps/patients/tests/test_patient_record_constraint_database.py
docker exec eqmd_dev ruff format --check \
  apps/patients/tests/test_patient_identity_record_numbers.py \
  apps/patients/tests/test_patient_record_constraint_database.py
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/typecheck.sh apps/patients/models.py \
  apps/patients/services/patient_identity.py \
  apps/patients/services/patient_record_consolidation.py \
  apps/patients/management/commands/consolidate_record_numbers.py \
  apps/patients/tests/test_record_consolidation.py
./scripts/test.sh
openspec validate consolidate-historical-record-number-collisions --strict
markdownlint-cli2 \
  openspec/changes/consolidate-historical-record-number-collisions/tasks.md \
  docs/workflows/record-number-consolidation-runbook.md \
  /tmp/consolidate-historical-record-number-collisions-slice-02-report.md
wc -l apps/patients/tests/test_patient_identity_record_numbers.py \
  apps/patients/tests/test_patient_record_constraint_database.py
```

## Binary success criteria

- [ ] Both modules under 450 lines; combined focused count equals the
      pre-split count (32).
- [ ] Full suite identical count to baseline, exit 0, zero failures.
- [ ] Runbook complete, lint-clean, states owner-only execution and
      never-commit plan rule, and reflects the renumbered migration
      order (`0002` widen, `0003` constraint).
- [ ] The strict combined mypy invocation (models.py plus the four
      slice-01 code files in one command) reports no issues, with no
      `type: ignore` added.
- [ ] Only the declared files changed.
- [ ] Exact temporary report exists and is lint-clean.

## Automatic INCOMPLETE conditions

Baseline not green; any test renamed/added/removed; a module still over
450 lines; production code touched; a gate failing; report missing;
commit/push/install.

## Required temporary report

`/tmp/consolidate-historical-record-number-collisions-slice-02-report.md`
with the same section structure as slice 01 (status, BASE_REF, matrix,
baseline, measurements instead of RED, evidence, inspections, commands,
comparison, self-evaluation, scope, handoff).

## Ready-to-run prompt for the implementer

```text
With zero conversation context, read AGENTS.md, PROJECT_CONTEXT.md, the
coding workflow documents, every artifact of
consolidate-historical-record-number-collisions, the verified slice-01
report, and this slice file. Implement ONLY slice 02.

Record BASE_REF/status; run the full baseline; record per-module line
and test counts. Move the five slice-004 constraint classes verbatim
into the new test_patient_record_constraint_database.py (both modules
under 450 lines, combined focused count unchanged). Refactor
_collision_group in patient_identity.py to string-based values_list
per R4. Write docs/workflows/record-number-consolidation-runbook.md
exactly per the slice's R2 outline (renumbered migration order). Run
every gate including the strict combined typecheck; compare counts;
create the exact temporary report.

No production code, migrations, settings, or test renames. Do not
install, commit, or push. Mark only tasks 2.1-2.3 after every gate
passes.

Reply only with
REPORT_PATH=/tmp/consolidate-historical-record-number-collisions-slice-02-report.md
and one-line status, then STOP for third-LLM verification.
```
