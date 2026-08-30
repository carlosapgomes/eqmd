# Slice 002 - Strong CPF/CNS Evidence

## Handoff for a zero-context implementer

Read completely, in order:

1. `AGENTS.md`
2. `PROJECT_CONTEXT.md`
3. `docs/workflows/coding-standards.md`
4. `docs/workflows/llm-collab.md`
5. `docs/workflows/clean-code-skill.md`
6. `openspec/changes/harden-patient-identity-and-duplicate-prevention/proposal.md`
7. `openspec/changes/harden-patient-identity-and-duplicate-prevention/design.md`
8. `openspec/changes/harden-patient-identity-and-duplicate-prevention/specs/patients/spec.md`
9. `openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md`
10. `openspec/changes/harden-patient-identity-and-duplicate-prevention/slices/slice-001-name-birthday-review.md`
11. This slice file

Implement only this slice after slice 001 has been independently verified.
Start with zero conversational context and stop after its report.

Expected starting state from slice 001:

- `apps/patients/services/patient_identity.py` owns typed candidate discovery.
- Patient creation performs a fresh server-side name/birthday review and allows
  explicit confirmation of advisory candidates.
- Candidate output is minimal and includes soft-deleted patients.
- CPF/CNS do not yet classify strong conflicts.
- Both patient forms still contain private-plan wording for
  `healthcard_number`.
- No CPF/CNS database constraint is planned in this change.

Do not assume slice 001 is correct merely because tasks are checked. Inspect it
and rerun its focused module before writing new tests.

## Mandatory protocol for DeepSeek4-Flash

**Any failed or missing item means `INCOMPLETE`**. Do not mark tasks, commit, or
push.

1. Record `BASE_REF=$(git rev-parse HEAD)` and `git status --short`. Preserve
   unrelated pre-existing changes. Stop if an expected file has unreviewed
   edits.
2. Before editing, run full `./scripts/test.sh`. Record exit code, `Ran N
   tests`, failures/errors/skips. Stop before code changes unless exit code is
   0 with zero failures/errors.
3. Verify `ruff` and `mypy` already exist inside `eqmd_dev`; never install
   packages during the slice.
4. Build the report matrix `Requirement -> file(s) -> test(s)/inspection(s)`
   before implementation.
5. Add/adjust tests first. At least one new test must fail because strong
   identifier behavior or CNS wording is missing. Setup/import failures are
   invalid RED evidence.
6. Implement minimal GREEN for R1-R7 only. Do not add model fields,
   constraints, migrations, advisory locks, APIs, or record-number changes.
7. REFACTOR using clean code, DRY, YAGNI, typed signatures, no duplicated
   checksum logic, no functions over 25 lines, and no business logic in views
   or templates.
8. Run all inspection and quality commands. Final full tests must have exit
   code 0, zero failures/errors, and no lower test count than baseline.
9. Create the exact temporary report without real identifiers. Do not commit
   or push; the user owns version control.

## Objective

Upgrade the existing duplicate-review flow so valid exact CPF/CNS matches are
non-overridable conflicts in interactive creation and profile update, while
preserving unrelated edits for unchanged invalid legacy values and correcting
the interface to CNS terminology.

## Functional scope

### R1 - Canonical document utilities

Add single-source utilities for:

- CPF: digits only, 11 digits, reject repeated digits, verify both check digits;
- CNS: digits only, 15 digits, validate the official weighted checksum;
- empty values: remain optional and are not strong identifiers.

Use deterministic synthetic values generated in tests. Do not copy identifiers
from the restored database or hardcode plausible real patient data in reports.

### R2 - Validate only new or changed interactive values

On patient creation, any non-empty CPF/CNS must be valid and must be returned in
canonical digit-only form. On profile update, a changed non-empty value must be
valid. An invalid legacy raw value that is submitted unchanged must not block
an unrelated profile change.

Do not perform a bulk normalization or alter stored legacy rows.

### R3 - Strong creation conflict

Search `Patient.all_objects` for another patient with the same valid canonical
CPF or CNS. A strong match invalidates the form, creates no patient/record, and
cannot be bypassed by the advisory review confirmation from slice 001. Include
soft-deleted patients.

### R4 - Strong profile-update conflict

`PatientProfileForm` must exclude its own instance from conflict lookup. It
must reject assigning another patient's valid CPF/CNS and persist no partial
profile change. Its own unchanged valid identifier remains accepted.

### R5 - Evidence presentation and minimization

The duplicate panel may identify evidence as “CPF coincidente” or “CNS
coincidente”, but it must never render either raw value. Strong-conflict output
must direct the user to review the existing patient and must not render an
override control that can authorize the conflict.

### R6 - CNS-only terminology

Both create and profile-update forms must label the field as `CNS` or `Cartão
Nacional de Saúde`. Remove the private-health-plan placeholder and the visible
“Cartão de Saúde” wording in these two interfaces. Do not rename the model
field or create a migration.

### R7 - Preserve prior behavior

Keep slice 001 advisory name behavior, existing permissions, CSRF, profile
location preservation, atomic initial record creation, and all unrelated form
fields unchanged.

## Expected files

Modify only:

- `apps/patients/services/patient_identity.py`
- `apps/patients/validators.py`
- `apps/patients/forms.py`
- `apps/patients/templates/patients/patient_create.html`
- `apps/patients/templates/patients/patient_update.html`
- `apps/patients/tests/test_duplicate_review_flow.py`
- `openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md`
  only after all gates pass

Any extra file requires planner approval and evidence that R1-R7 cannot be met
otherwise. Explicitly forbidden:

- models, migrations, signals, admin, URLs, permissions, imports;
- CPF/CNS uniqueness constraints or broad data cleanup;
- record-number reservation from slices 003/004;
- new JavaScript, dependencies, or generated assets.

## TDD: RED -> GREEN -> REFACTOR

### RED

Extend the focused module. At minimum prove:

1. invalid new CPF is rejected and creates no rows;
2. invalid new CNS is rejected and creates no rows;
3. valid formatted inputs are stored canonically;
4. exact valid CPF blocks creation despite advisory confirmation;
5. exact valid CNS blocks creation despite advisory confirmation;
6. a soft-deleted owner still causes strong conflict;
7. profile update excludes self but rejects another patient's identifier;
8. conflict leaves all other submitted profile fields unchanged;
9. unchanged invalid legacy CPF/CNS allows an unrelated edit;
10. create/update pages use CNS wording and omit private-plan wording;
11. strong warning HTML contains evidence type but not raw identifier;
12. slice 001 advisory confirmation still succeeds without strong conflict.

Run:

```bash
./scripts/test.sh apps.patients.tests.test_duplicate_review_flow
```

Capture at least one expected assertion failure before production edits.

### GREEN

Implement the smallest utilities and service/form/template integration. Use
field-specific errors for invalid values and strong conflicts. Reuse the slice
001 candidate DTO rather than create a second result shape.

### REFACTOR

- One normalizer and one validator per identifier; no duplicated weights.
- Typed service/form helpers with intention-revealing names.
- New functions at most 25 lines and no boolean-flag argument when separate
  functions are clearer.
- Keep legacy file integrations short; report line counts before/after.
- Preserve unchanged invalid values through an explicit, tested comparison,
  not by swallowing all validation errors.

## Mandatory inspection checks

Run and explain:

```bash
rg -n "normalize_(cpf|cns)|validate_(cpf|cns)|checksum|weight" \
  apps/patients/validators.py \
  apps/patients/services/patient_identity.py \
  apps/patients/forms.py
rg -n "all_objects|exclude\(|strong|CPF|CNS" \
  apps/patients/services/patient_identity.py \
  apps/patients/tests/test_duplicate_review_flow.py
rg -n "plano de saúde|carteirinha|Cartão de Saúde" \
  apps/patients/forms.py \
  apps/patients/templates/patients/patient_create.html \
  apps/patients/templates/patients/patient_update.html
rg -n "CNS|Cartão Nacional de Saúde" \
  apps/patients/forms.py \
  apps/patients/templates/patients/patient_create.html \
  apps/patients/templates/patients/patient_update.html
rg -n "UniqueConstraint|AddConstraint|RunPython" \
  apps/patients/models.py apps/patients/migrations
wc -l apps/patients/forms.py apps/patients/validators.py \
  apps/patients/services/patient_identity.py \
  apps/patients/templates/patients/patient_create.html \
  apps/patients/templates/patients/patient_update.html
```

Expected interpretation:

- normalization/checksum logic has one home;
- self-exclusion and all-object lookup are visible;
- the forbidden private-plan wording has zero occurrences in scoped forms and
  templates;
- CNS wording exists in both interfaces;
- no new constraint/migration was introduced in this slice;
- growth in oversized legacy files is minimal and justified.

## Verification commands

Run every command:

```bash
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev ruff check \
  apps/patients/services/patient_identity.py \
  apps/patients/validators.py \
  apps/patients/forms.py \
  apps/patients/tests/test_duplicate_review_flow.py
docker exec eqmd_dev ruff format --check \
  apps/patients/services/patient_identity.py \
  apps/patients/validators.py \
  apps/patients/forms.py \
  apps/patients/tests/test_duplicate_review_flow.py
./scripts/typecheck.sh \
  apps/patients/services/patient_identity.py \
  apps/patients/validators.py \
  apps/patients/forms.py
./scripts/test.sh apps.patients.tests.test_duplicate_review_flow
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh
openspec validate harden-patient-identity-and-duplicate-prevention --strict
markdownlint-cli2 \
  openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md \
  /tmp/harden-patient-identity-and-duplicate-prevention-slice-002-report.md
```

## Binary success criteria

- [ ] R1-R7 map to test/inspection evidence.
- [ ] Full pre-edit baseline passed with zero failures/errors and exit code 0.
- [ ] RED failed for missing strong-conflict/CNS behavior.
- [ ] CPF/CNS valid, invalid, blank, formatted, own, other, and soft-deleted
      cases pass.
- [ ] Strong matches cannot be confirmed past the block.
- [ ] Conflicting update persists no other submitted profile changes.
- [ ] Unchanged invalid legacy data does not block unrelated update.
- [ ] Raw CPF/CNS never appears in warning output or report.
- [ ] CNS terminology is present and private-plan wording is absent.
- [ ] Slice 001 advisory behavior remains green.
- [ ] No migration, model, permission, API, import, or record work was added.
- [ ] All quality gates pass and final test count is not lower than baseline.
- [ ] Tasks 2.1-2.5 and report exist only after all gates pass.

## Self-evaluation gates

Answer with evidence:

1. Are CPF and CNS normalization/checksum rules each defined exactly once?
2. Are blank identifiers optional and excluded from strong matching?
3. Can advisory confirmation never override a valid exact CPF/CNS match?
4. Does profile lookup exclude only the current patient?
5. Does a rejected profile update leave every field unchanged?
6. Is legacy-invalid bypass limited to an unchanged value?
7. Does candidate rendering omit raw CPF/CNS in all branches?
8. Do both forms use CNS-only terminology?
9. Did slice 001 exact/fuzzy/confirmation tests remain green?
10. Did every new function receive types and stay within 25 lines?
11. Did baseline/final full suites have exit code 0 and zero failures/errors?
12. Did you avoid installs, commits, pushes, extra files, and future slices?

### Automatic INCOMPLETE conditions

The slice is incomplete if:

- baseline full suite was omitted or had nonzero exit/failures/errors;
- `ruff`/`mypy` was missing or installed ad hoc;
- no real behavior RED was recorded;
- any required test/inspection/quality command was missing or failed;
- final full suite has a failure/error, nonzero exit, or lower count;
- report omits explicit failure/error counts and exit codes;
- a strong conflict can be bypassed by confirmation;
- an invalid changed identifier is silently accepted;
- an unchanged invalid legacy value is rewritten without requirement;
- any raw identifier or real patient data appears in UI evidence/report;
- private-plan wording remains in either scoped patient form;
- a model/migration/constraint/permission/import/record behavior changed;
- unexpected files changed without approval;
- tasks were marked early or report path is absent;
- any commit, push, destructive command, or package installation occurred.

## Required temporary report

Create:

`/tmp/harden-patient-identity-and-duplicate-prevention-slice-002-report.md`

Required sections:

1. Status (`COMPLETE` or `INCOMPLETE`).
2. `BASE_REF`, initial status, and preserved unrelated work.
3. R1-R7 matrix.
4. Full baseline exit code and `Ran N tests` with failures/errors/skips.
5. RED command, failing assertions, excerpts, and expected reason.
6. GREEN and REFACTOR evidence.
7. Synthetic-only before/after snippets for validators, service classification,
   form update guard, and CNS labels.
8. Inspection outputs and interpretation, including forbidden-word zero match.
9. Changed files and before/after line counts; justify any extra file.
10. Every quality command and exit code.
11. Baseline/final comparison and explicit zero failures/errors.
12. Answers to all self-evaluation gates.
13. Security/privacy statement and remaining risk of out-of-band writes.
14. `Handoff for verifier` containing changed files, exact rerun commands,
    R1-R7 checklist, manual UI checks, risks, and deferred slices 003/004.

## Ready-to-run prompt for the implementer

```text
Read AGENTS.md, PROJECT_CONTEXT.md, all workflow standards, all artifacts for
harden-patient-identity-and-duplicate-prevention, verified slice 001, and
slice-002-strong-cpf-cns-evidence.md. Implement ONLY slice 002 with zero prior
conversation context.

Follow the DeepSeek4-Flash protocol exactly: record BASE_REF/status; run the
FULL ./scripts/test.sh baseline before editing and stop if it is not entirely
green; verify ruff/mypy already exist without installing; create a real RED;
implement minimal GREEN; REFACTOR with clean code, DRY, YAGNI, typed functions
<=25 lines; run all inspections and quality gates; compare full baseline/final;
and create the exact temporary evidence report.

Do not add models, migrations, constraints, signals, admin, URLs, permissions,
imports, record-number behavior, dependencies, or unrelated refactors. Never
use or report real patient identifiers. Do not commit or push. Mark only tasks
2.1-2.5 after every gate succeeds. Any missing/failing gate, any final
failure/error, or lower final test count requires Status: INCOMPLETE and
unchecked tasks.

Reply only with REPORT_PATH=/tmp/harden-patient-identity-and-duplicate-prevention-slice-002-report.md
and one-line status, then STOP for third-LLM verification.
```
