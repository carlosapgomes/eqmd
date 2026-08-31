# Slice 01 - Audited Consolidation Tooling

## Handoff for a zero-context implementer

Read these files fully and in order:

1. `AGENTS.md`
2. `PROJECT_CONTEXT.md`
3. `docs/workflows/coding-standards.md`
4. `docs/workflows/llm-collab.md`
5. `docs/workflows/clean-code-skill.md`
6. `openspec/changes/consolidate-historical-record-number-collisions/proposal.md`
7. `openspec/changes/consolidate-historical-record-number-collisions/design.md`
8. `openspec/changes/consolidate-historical-record-number-collisions/specs/patients/spec.md`
9. `openspec/changes/consolidate-historical-record-number-collisions/tasks.md`
10. This slice file
11. The verified slice 003 and 004 reports under `/tmp` (for the existing
    service helpers, constraint semantics, and audit conventions)

Implement exactly one slice and stop. Do not rely on conversation history.

Current code facts to verify before planning:

- `apps/patients/services/patient_identity.py` already owns
  `normalize_record_number`, `find_record_number_conflict`
  (`Lower(Trim(record_number))`, all retained rows), and the
  `RECORD_NUMBER_*` message constants.
- `Patient.update_current_record_number(record_number, user, reason,
effective_date=None)` is the audited append flow (transaction, recheck,
  deactivation, new row, denormalized sync).
- `PatientRecordNumber` has `change_reason`, `updated_by`,
  `effective_date`, `previous_record_number`; it is NOT simple-history
  tracked; ordinary interfaces keep it immutable (slice 003).
- Migration `0002` preflight aborts while collisions remain; it is the
  authoritative fail-closed gate and must not be modified.
- The restored production copy must never be mutated by an implementer.

## Mandatory protocol for DeepSeek4-Flash

If any protocol item fails, report `INCOMPLETE`, leave tasks unchecked,
and stop.

1. Record `BASE_REF=$(git rev-parse HEAD)` and `git status --short`.
   Preserve unrelated changes; stop if expected files contain unverified
   work.
2. Run the full pre-edit baseline `./scripts/test.sh`. Stop unless it
   exits 0 with zero failures/errors.
3. Confirm `ruff` and `mypy` already exist inside `eqmd_dev`; never
   install tooling.
4. Create the real RED first (the new test module against the absent
   service/command code). Setup or import errors are not a valid RED.
5. Implement only R1-R4.
6. Run every inspection and quality gate; the final full suite must exit
   0 with zero failures/errors and no lower test count than baseline.
7. Create the exact `/tmp` Markdown report. Do not commit or push; stop
   for third-LLM verification.

## Objective

Provide the audited, human-decided consolidation tooling that resolves
every canonical record-number collision group and proves the zero
collision end state, without automatic clinical decisions and without
touching the restored production copy.

## Functional scope

### R1 - Collision-group discovery

Extend `services/patient_identity.py` with a discovery helper that
groups retained rows by the canonical expression and returns, per group,
the canonical value, row count, and the row references (ids only);
plus an aggregate summary (group count, involved-row count). The command
prints the aggregate by default and per-group detail only with
`--show-records`. No names, CPF, or CNS in any output.

### R2 - Audited consolidation service

Add service functions that, given one validated group decision:

- keep the decided assignment untouched;
- for an `action: "renumber"` decision on a current assignment, call
  `update_current_record_number` with the decided new number and a
  reason carrying the plan reference, then void the deactivated old row
  per the next rule;
- for an `action: "void"` decision (including the row deactivated by a
  renumber), rewrite `record_number` to
  `<original>::voided::<plan-ref>` preserving the original value
  verbatim, set `change_reason` to the clinical rationale plus the plan
  reference, and set `updated_by` to the operator;
- never delete rows and never touch `effective_date`.

### R3 - Management command

`python manage.py consolidate_record_numbers`:

- default: print the aggregate audit (groups, involved rows) and exit 0;
- `--show-records`: print per-group detail (canonical number, assignment
  ids, patient ids) for the operator console only;
- `--plan <file>`: validate the JSON plan against live discovery
  (unknown, stale, or incomplete coverage refuses execution);
- `--dry-run` (default behavior when `--plan` is given): execute the
  plan inside `transaction.atomic()` with `set_rollback(True)`, then
  print the would-be end state;
- `--execute`: require an explicit `--user <username>` operator; run the
  whole plan in one transaction, then re-run discovery and raise unless
  the aggregate group count is zero;
- non-`--plan` runs never mutate anything.

Plan file format (author-owned, never committed):

```json
{
  "plan_ref": "consolidation-2026-08-30-a",
  "groups": [
    {
      "canonical": "<synthetic example>",
      "keep": "<assignment-uuid>",
      "actions": [
        {
          "assignment": "<assignment-uuid>",
          "action": "void",
          "rationale": "<clinical rationale>"
        }
      ]
    }
  ]
}
```

### R4 - Tests on synthetic data only

Cover: discovery aggregate and detail; dry-run byte-identical state;
void marker format (original preserved verbatim, plan reference present);
renumber path (new current via append flow, old row voided, denormalized
field synced); rationale/operator recorded; stale or unknown plan
refused; post-check rollback when a group remains; command output free
of names/CPF/CNS.

## Expected files

Modify/create only:

- `apps/patients/services/patient_identity.py`
- `apps/patients/management/commands/consolidate_record_numbers.py` (new)
- `apps/patients/tests/test_record_consolidation.py` (new)
- `openspec/changes/consolidate-historical-record-number-collisions/tasks.md`
  only after all gates pass

Any other file needs planner approval. Forbidden: models, migrations,
forms, views, templates, admin, signals, URLs, settings; touching the
restored `eqmd_dev` database for writes; automatic merging or any code
path that decides ownership without a plan; commits, pushes, installs.

## TDD: RED -> GREEN -> REFACTOR

### RED

Create the new test module first; run:

```bash
./scripts/test.sh apps.patients.tests.test_record_consolidation
```

Record import/attribute failures plus at least one real assertion
failure against a stub (for example, discovery returning no groups on
colliding synthetic data).

### GREEN

Implement R1-R3 minimally.

### REFACTOR

Keep discovery and canonical grouping single-source in the service;
command stays transport-only; typed helpers; functions at most 25 lines;
no broad exceptions.

## Mandatory inspection checks

```bash
rg -n 'voided|plan_ref|set_rollback|transaction.atomic' \
  apps/patients/services/patient_identity.py \
  apps/patients/management/commands/consolidate_record_numbers.py
rg -n 'delete\(|\.objects.filter.*delete|UPDATE|raw' \
  apps/patients/management/commands/consolidate_record_numbers.py \
  apps/patients/services/patient_identity.py
docker exec eqmd_dev python manage.py consolidate_record_numbers
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
```

Expected: markers and rollback/atomic visible; zero delete/DML paths;
the bare command prints an aggregate audit (on the dev database this is
a read-only query; it must not print names/CPF/CNS); no migration drift.

## Verification commands

Execute all:

```bash
./scripts/test.sh apps.patients.tests.test_record_consolidation
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev ruff check \
  apps/patients/services/patient_identity.py \
  apps/patients/management/commands/consolidate_record_numbers.py \
  apps/patients/tests/test_record_consolidation.py
docker exec eqmd_dev ruff format --check \
  apps/patients/services/patient_identity.py \
  apps/patients/management/commands/consolidate_record_numbers.py \
  apps/patients/tests/test_record_consolidation.py
./scripts/typecheck.sh \
  apps/patients/services/patient_identity.py \
  apps/patients/management/commands/consolidate_record_numbers.py
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
docker exec eqmd_dev python manage.py consolidate_record_numbers
./scripts/test.sh
openspec validate consolidate-historical-record-number-collisions --strict
markdownlint-cli2 \
  openspec/changes/consolidate-historical-record-number-collisions/tasks.md \
  /tmp/consolidate-historical-record-number-collisions-slice-01-report.md
```

## Binary success criteria

- [ ] R1-R4 map to test/inspection evidence.
- [ ] Full baseline green before edits.
- [ ] Real RED recorded.
- [ ] Dry-run proven byte-identical; execute proven single-transaction
      with zero-collision post-check and full rollback on failure.
- [ ] No deletion path; markers preserve originals; rationale/operator
      recorded.
- [ ] Command output free of names/CPF/CNS (asserted in tests).
- [ ] Restored database untouched (read-only audit query allowed).
- [ ] Every gate passes; final full count not lower than baseline.
- [ ] Exact temporary report exists, lint-clean, PII-free.

## Self-evaluation gates

1. Does discovery reuse the canonical expression single-source?
2. Is every mutation decision-backed (no automatic clinical merging)?
3. Are void markers verbatim-preserving and plan-referenced?
4. Does dry-run leave the database byte-identical?
5. Does execute verify zero collisions inside the same transaction?
6. Are ordinary interfaces' immutability guarantees untouched?
7. Is all output aggregate-only by default and identifier-detail gated?
8. Did baseline/final suites pass with no lower count?

### Automatic INCOMPLETE conditions

Baseline not green; no real RED; any gate failing; a deletion or DML
path; automatic ownership decision; PII in output/report; mutation of
the restored database; undeclared file changed; tasks marked early;
missing report; commit/push/install/destructive command.

## Required temporary report

Create exactly:

`/tmp/consolidate-historical-record-number-collisions-slice-01-report.md`

Include status; BASE_REF and initial status; R1-R4 matrix; baseline;
RED; GREEN/REFACTOR evidence with before/after snippets; inspection
outputs; every command and exit code; baseline/final comparison;
self-evaluation answers; scope/privacy statement; handoff for verifier
with exact reruns.

## Ready-to-run prompt for the implementer

```text
With zero conversation context, read AGENTS.md, PROJECT_CONTEXT.md, all
coding workflow documents, every artifact of
consolidate-historical-record-number-collisions, and this slice file.
Implement ONLY slice 01.

Follow the protocol literally: record BASE_REF/status; run FULL
./scripts/test.sh before editing and stop if not fully green; verify
ruff/mypy exist; create a real RED in the new test module; implement the
discovery helper, the audited consolidation service (append-flow
renumber + ::voided:: markers preserving originals), and the
consolidate_record_numbers command (aggregate audit, --show-records,
plan validation, --dry-run default with set_rollback, --execute with
single-transaction zero-collision post-check); run every inspection and
quality gate; compare baseline/final; create the exact temporary report.

Never touch models, migrations, forms, views, templates, admin,
signals, URLs, or settings. Never mutate the restored eqmd_dev database
(the bare aggregate audit query is the only allowed read). No automatic
clinical decisions, no deletions, no PII in output. Do not install,
commit, or push. Mark only tasks 1.1-1.5 after every gate passes.

Reply only with
REPORT_PATH=/tmp/consolidate-historical-record-number-collisions-slice-01-report.md
and one-line status, then STOP for third-LLM verification.
```
