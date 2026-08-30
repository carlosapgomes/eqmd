# Slice 001 - Name and Birthday Review

## Handoff for a zero-context implementer

Read these files completely, in this order, before planning or editing:

1. `AGENTS.md`
2. `PROJECT_CONTEXT.md`
3. `docs/workflows/coding-standards.md`
4. `docs/workflows/llm-collab.md`
5. `docs/workflows/clean-code-skill.md`
6. `openspec/changes/harden-patient-identity-and-duplicate-prevention/proposal.md`
7. `openspec/changes/harden-patient-identity-and-duplicate-prevention/design.md`
8. `openspec/changes/harden-patient-identity-and-duplicate-prevention/specs/patients/spec.md`
9. `openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md`
10. This slice file

Implement exactly this slice and then stop. Start with empty conversational
context; this file is the authoritative handoff.

Current state:

- `PatientForm` validates required fields and creates the patient plus initial
  `PatientRecordNumber` atomically.
- `PatientCreateView` uses `PatientForm` and requires
  `patients.add_patient`.
- `patient_create.html` has no duplicate-review panel or explicit
  confirmation control.
- There is no `apps/patients/services/` directory.
- PostgreSQL has `pg_trgm` and `unaccent`; SQLite is unsupported.
- The planning audit found exact and fuzzy name/birthday candidates, but no
  identifiable production data may be copied into tests or reports.
- The last known full-suite baseline was red. Therefore the baseline protocol
  below is a real precondition, not optional documentation.

## Mandatory protocol for DeepSeek4-Flash

This slice will be implemented by a fast model with a tendency to conclude too
early. Follow this protocol literally. **If any item fails, the slice is
INCOMPLETE**: do not mark `tasks.md`, do not continue editing, and report the
blocker with evidence.

1. **Plan before editing**: record `BASE_REF=$(git rev-parse HEAD)` and
   `git status --short`. In the report, write a matrix
   `Requirement -> file(s) -> test(s)/inspection(s)`. If an expected file is
   already modified by someone else, stop rather than overwrite it. Preserve
   unrelated pre-existing changes.
2. **Full baseline before editing**: run exactly `./scripts/test.sh` and record
   exit code, `Ran N tests`, failures, errors, and skipped count. If exit code
   is nonzero or any failure/error exists, stop as `INCOMPLETE/BLOCKED` before
   changing code. A focused green test is not a waiver.
3. **Toolchain preflight**: verify `ruff` and `mypy` already exist inside
   `eqmd_dev`. Do not install packages. Missing tooling means
   `INCOMPLETE/BLOCKED`.
4. **Real RED**: write tests first and run the focused module. At least one new
   test must fail for the expected missing behavior. A syntax/import/setup
   failure is not an acceptable RED.
5. **Minimal GREEN**: implement only R1-R7. Do not anticipate CPF/CNS hard
   conflicts or record-number reservation from later slices.
6. **REFACTOR**: enforce clean code, DRY, YAGNI, explicit names, typed service
   signatures, cohesive functions, and no dead code. New functions must be at
   most 25 lines. Keep business querying out of forms/templates.
7. **Inspection plus quality gate**: run every command in this file. The final
   full suite must have exit code 0, zero failures/errors, and `Ran N tests`
   greater than or equal to baseline.
8. **Evidence, not opinion**: create the required temporary Markdown report
   with commands, exit codes, RED/GREEN proof, before/after snippets, scope
   justification, and verifier handoff. Never include real patient data.
9. **Version-control rule**: do not commit or push. `AGENTS.md` assigns version
   control to the user. Stop after reporting `REPORT_PATH=...`.

## Objective

Deliver an end-to-end server-side review step in patient creation: exact or
similar normalized name with the same birthday warns before persistence, and
an explicit second submission permits a possible homonym when no later strong
conflict exists.

## Functional scope

### R1 - Typed candidate service

Create a focused identity service with an immutable typed candidate result. It
must own name normalization, threshold, query, ordering, and result shaping.
It must not persist, merge, update, or delete patients.

### R2 - Candidate semantics

Search `Patient.all_objects` by the submitted birthday. Include:

- exact names after ignoring case, accents, punctuation, and repeated spaces;
- different normalized names with PostgreSQL trigram similarity `>= 0.80`.

Use the constant `NAME_SIMILARITY_THRESHOLD = 0.80`. Return deterministic
ordering and identify soft-deleted candidates. Do not introduce an index or a
new dependency.

### R3 - First POST warns without persistence

When advisory candidates exist and review was not explicitly confirmed, the
bound form must be invalid for this submission, expose its typed candidates to
the template, and create neither `Patient` nor `PatientRecordNumber`.

### R4 - Explicit review permits a homonym

Render an explicit confirmation control only with the warning. A confirmed
POST must rerun the server-side search and may proceed through the unchanged
atomic creation behavior. Never trust a prior GET, JavaScript state, or cached
candidate list.

### R5 - Minimal disclosure

The warning may show candidate name, birthday, current record number,
soft-delete state, evidence type, and detail link. It must not render raw CPF,
CNS, address, or phone. Tests must use obviously synthetic data.

### R6 - Regression behavior

No candidate or a similar name with a different birthday must preserve the
existing valid creation flow, redirect, current record creation, permissions,
and CSRF behavior.

### R7 - Brownfield containment

Put new business/query logic in the service. Changes to the oversized
`forms.py` and template must be small and local. Record before/after line counts
and do not refactor unrelated patient forms or inline CSS/JavaScript.

## Expected files

Create or modify only:

- `apps/patients/services/__init__.py` (new)
- `apps/patients/services/patient_identity.py` (new)
- `apps/patients/forms.py`
- `apps/patients/templates/patients/patient_create.html`
- `apps/patients/tests/test_duplicate_review_flow.py` (new)
- `openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md`
  only after every gate passes

Any extra file makes the slice incomplete unless the report proves it is
strictly necessary for R1-R7 and receives planner approval. Do not modify:

- models, migrations, signals, admin, URLs, permissions, import commands;
- CPF/CNS validation or labels;
- record-number uniqueness behavior;
- generated `static/` assets or dependencies.

## TDD: RED -> GREEN -> REFACTOR

### RED

Write focused tests first. At minimum cover:

1. exact case/accent/punctuation-normalized name plus same birthday warns;
2. a different name at or above 0.80 plus same birthday warns;
3. a different birthday does not create a name candidate;
4. a soft-deleted matching patient is returned and marked deleted;
5. first POST creates zero patient and record rows;
6. confirmed POST reruns search and creates exactly one patient/current record;
7. warning HTML omits synthetic raw CPF, CNS, address, and phone values;
8. existing permission denial and no-candidate creation still work.

Run and capture the expected behavior failure:

```bash
./scripts/test.sh apps.patients.tests.test_duplicate_review_flow
```

At least one assertion must fail because review behavior is absent, not because
of test setup.

### GREEN

Implement the smallest service, form integration, and Bootstrap warning needed
to pass the RED tests. Keep the original creation transaction and redirect.
Do not add client-side search or implement future slices.

### REFACTOR

- Remove duplicated normalization/query branches.
- Add parameter and return annotations to all new/changed functions.
- Keep each new function at most 25 lines and each class cohesive.
- Use a DTO rather than dictionaries with implicit keys.
- Confirm the service has no persistence side effects.
- Keep net additions to legacy oversized files minimal and report line counts.

## Mandatory inspection checks

Run and paste concise output plus interpretation into the report:

```bash
rg -n "NAME_SIMILARITY_THRESHOLD|TrigramSimilarity|unaccent|all_objects" \
  apps/patients/services/patient_identity.py
rg -n "duplicate_review_confirmed|duplicate_candidates|possível|possive[lí]" \
  apps/patients/forms.py \
  apps/patients/templates/patients/patient_create.html \
  apps/patients/tests/test_duplicate_review_flow.py
rg -n "Patient\\.objects\\.(create|update)|\.save\(" \
  apps/patients/services/patient_identity.py
rg -n "permission_required = 'patients.add_patient'" apps/patients/views.py
wc -l apps/patients/forms.py \
  apps/patients/templates/patients/patient_create.html \
  apps/patients/services/patient_identity.py
```

Expected interpretation:

- similarity, threshold, `unaccent`, and all-object lookup exist in the service;
- confirmation exists in form/template/tests;
- the service contains no patient persistence call;
- the existing add permission is unchanged;
- legacy line-count growth is small and explained.

## Verification commands

Run all commands; no substitutions or omitted gates:

```bash
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev ruff check \
  apps/patients/services/patient_identity.py \
  apps/patients/forms.py \
  apps/patients/tests/test_duplicate_review_flow.py
docker exec eqmd_dev ruff format --check \
  apps/patients/services/patient_identity.py \
  apps/patients/forms.py \
  apps/patients/tests/test_duplicate_review_flow.py
./scripts/typecheck.sh \
  apps/patients/services/patient_identity.py \
  apps/patients/forms.py
./scripts/test.sh apps.patients.tests.test_duplicate_review_flow
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh
openspec validate harden-patient-identity-and-duplicate-prevention --strict
markdownlint-cli2 \
  openspec/changes/harden-patient-identity-and-duplicate-prevention/tasks.md \
  /tmp/harden-patient-identity-and-duplicate-prevention-slice-001-report.md
```

## Binary success criteria

- [ ] R1-R7 each map to tests or an explicit inspection.
- [ ] Full pre-edit baseline passed with exit code 0 and zero failures/errors.
- [ ] RED failed for the expected absent behavior.
- [ ] Focused GREEN command passed.
- [ ] Exact, fuzzy, different-birthday, soft-delete, confirmation, permission,
      atomic creation, and disclosure cases passed.
- [ ] No CPF/CNS hard-block or record reservation was implemented early.
- [ ] Every quality and inspection command passed.
- [ ] Final full test count is not lower than baseline.
- [ ] Only expected files changed, or extras have approved justification.
- [ ] Tasks 1.1-1.5 were marked only after all previous items passed.
- [ ] The temporary report passed Markdown lint and contains no real PII.

## Self-evaluation gates

Answer each with `YES` plus evidence or `NO` and mark the slice incomplete:

1. Did the first matching POST persist zero patient and record rows?
2. Does confirmed POST execute a fresh server query rather than trust UI state?
3. Can a different birthday avoid the advisory match?
4. Are soft-deleted patients included without changing soft-delete behavior?
5. Is `0.80` defined once in the service?
6. Does the candidate DTO exclude raw CPF/CNS/address/phone?
7. Is all identity business logic outside the form and template?
8. Did permissions, CSRF, redirect, and atomic initial-record behavior remain?
9. Did every new function stay within 25 lines and receive type hints?
10. Did baseline and final full suite both have zero failures/errors?
11. Did you avoid commits, pushes, package installs, and unrelated edits?

### Automatic INCOMPLETE conditions

Mark the slice incomplete if any occurs:

- pre-edit full baseline was omitted, nonzero, or had any failure/error;
- `ruff` or `mypy` was unavailable inside the app container;
- a planned test was missing/not run, or RED was not a real behavior failure;
- any focused/full test, check, Ruff, typecheck, migration drift, OpenSpec, or
  Markdown gate failed;
- final test count was lower than baseline;
- report states only a pass count without exit code and explicit zero
  failures/errors;
- candidate confirmation bypassed a fresh server-side query;
- raw CPF/CNS/address/phone appeared in warning output or report;
- permissions were relaxed or future slices were implemented;
- an unexpected file was changed without prior planner approval;
- `tasks.md` was marked despite any pending item;
- the report was absent from the exact path;
- any commit, push, destructive command, or ad hoc package install occurred.

## Required temporary report

Create exactly:

`/tmp/harden-patient-identity-and-duplicate-prevention-slice-001-report.md`

It must contain:

1. `Status: COMPLETE` or `Status: INCOMPLETE`.
2. `BASE_REF`, initial `git status --short`, and preserved unrelated changes.
3. Matrix `Requirement -> file(s) -> test(s)/inspection(s)` for R1-R7.
4. Baseline command, exit code, `Ran N tests`, failures/errors/skips.
5. RED command, failing test names, failure excerpts, expected reason.
6. GREEN/refactor commands and summaries.
7. Small before/after code snippets for service integration, form gate, and UI.
8. Inspection commands, outputs, and interpretation.
9. File list, line counts before/after, and justification for any extra file.
10. Full quality-gate commands with exit codes.
11. Baseline-versus-final test count and explicit zero failures/errors.
12. Answers to all self-evaluation gates.
13. Risks/limitations and confirmation that no real patient data was used.
14. `Handoff for verifier` with:
    - changed files;
    - exact rerun commands;
    - requirement checklist R1-R7;
    - what to inspect manually;
    - known risks and scope intentionally deferred to slices 002-004.

## Ready-to-run prompt for the implementer

```text
Read AGENTS.md, PROJECT_CONTEXT.md, the three workflow/clean-code documents,
and every artifact under
openspec/changes/harden-patient-identity-and-duplicate-prevention listed in
slice-001-name-birthday-review.md. Implement ONLY slice 001.

Follow the DeepSeek4-Flash protocol literally: record BASE_REF/status, run the
FULL ./scripts/test.sh baseline before editing, stop INCOMPLETE if it is not
fully green, verify ruff/mypy already exist, create a real RED, implement the
minimal GREEN, REFACTOR with clean code/DRY/YAGNI and typed functions <=25
lines, run every inspection and quality gate, compare baseline vs final, and
write the exact temporary report required by the slice.

Do not implement CPF/CNS hard conflicts, record-number reservation, models,
migrations, signals, admin, URLs, permissions, imports, or unrelated cleanup.
Do not expose real patient data. Do not install packages, commit, or push.
Update only tasks 1.1-1.5 after every criterion passes. If any command/check is
missing or failing, if final tests have any failure/error, or if the final test
count is lower, report Status: INCOMPLETE and leave tasks unchecked.

Reply only with REPORT_PATH=/tmp/harden-patient-identity-and-duplicate-prevention-slice-001-report.md
and a one-line status, then STOP for third-LLM verification.
```
