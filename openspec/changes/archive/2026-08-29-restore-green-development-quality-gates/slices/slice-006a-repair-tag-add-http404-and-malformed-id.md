# Slice 006A - Repair Tag-Add Http404 Swallowing and Malformed Tag-Id

## Handoff for a zero-context implementer

Read completely, in order: `AGENTS.md`, `PROJECT_CONTEXT.md`, the canonical
workflow documents, ADR-0001, every artifact of this change, approved reports
001-005A, slice 006, its `INCOMPLETE` report, the third-LLM verification that
approved the production fix, this reslice, `PatientTagAddView.post`, and the
three current tag test modules. Implement only 006A and stop.

Preserve the accepted partial slice-006 work in exactly these files:

- `apps/patients/tests/test_tag_error_handling.py` (20/21 green);
- `apps/patients/tests/test_tag_management_basic_error_handling.py` (8/9);
- `apps/patients/tests/test_tag_management_error_handling.py` (15/16).

The planner has approved the production defect and the fix contract:

1. `allowed_tag = get_object_or_404(AllowedTag, pk=tag_id)` currently sits
   inside a broad `except Exception`; `Http404` subclasses `Exception`, so a
   well-formed but nonexistent `AllowedTag` id returns
   `500 {"error": "Erro interno do servidor"}` instead of the domain `404`;
2. the fix moves the lookup outside the broad except, mirroring the existing
   `Patient` lookup at the top of the same view;
3. a non-integer `tag_id` body value (`AllowedTag.pk` is an integer
   `AutoField`) is a malformed request, not a missing resource: it must return
   `400 {"error": "ID da tag inválido"}` — never `500`;
4. every other branch — missing `tag_id` 400, inactive/duplicate 400 payloads,
   success 200 payload, genuine unexpected-exception 500 — stays byte-identical.

Three RED tests prove item 2 (one per module, all `500 != 404`). A new RED
test must prove item 3 before production code changes.

Comparison baseline: `/tmp/full_suite_006.log` — 2,025 tests, 111 failures,
336 errors, 12 skips, 447 FAIL/ERROR headers.

## Mandatory DeepSeek4-Flash protocol

1. Record `BASE_REF`, ownership, checksums of the three accepted slice-006
   test files, the three RED tracebacks, the current 500 behavior of a
   malformed body value, and the baseline manifest before editing.
2. Add the malformed-body regression test first and rerun it to capture its
   RED (currently swallowed `ValueError` → 500).
3. Apply the approved minimal view fix. Do not reformat, restructure, or
   "clean up" anything else in `views.py`.
4. Run every listed gate sequentially. Any target failure or added full-suite
   header means `INCOMPLETE`.
5. Write the exact report, reply with `REPORT_PATH` and `STATUS`, and stop.
   Do not start slice 007, mark tasks, commit, or push.

## Objective

Close slice 006 by restoring the domain `404` for nonexistent `AllowedTag`
ids and the domain `400` for malformed tag-id body values in
`PatientTagAddView.post`, with all other tag HTTP contracts unchanged.

## Requirements

- **R1:** a well-formed but nonexistent integer `tag_id` returns `404` via
  `get_object_or_404`, no longer swallowed by the broad `except Exception`.
- **R2:** a non-integer `tag_id` body value returns
  `400 {"error": "ID da tag inválido"}`.
- **R3:** the missing-`tag_id` `400 {"error": "ID da tag é obrigatório"}`,
  inactive/duplicate `400 {"error": "Não é possível adicionar esta tag ao
paciente"}`, success `200 {success, message, tags}` (and event creation),
  and genuine-exception `500 {"error": "Erro interno do servidor"}` branches
  behave exactly as before.
- **R4:** no permission change: `Patient` 404, `can_manage_patient_tags` 403,
  and `patients.change_patient` enforcement remain identical.
- **R5:** the remove, remove-all, and tags-API views are not modified.
- **R6:** all three tag modules and every supporting gate finish green with no
  added full-suite header.

## Expected files

- `apps/patients/views.py`
- `apps/patients/tests/test_tag_error_handling.py`

Only `PatientTagAddView.post` may change in `views.py`. Do not edit the other
tag views, `urls.py`, models, signals, the other two test modules, forms,
templates, migrations, dependencies, scripts, CI, or OpenSpec tasks.

`apps/patients/views.py` carries extensive documented pre-existing
Ruff/Mypy debt. Do not format the file, add ignores, or repair unrelated
findings; only the isolated critical-subset gate below applies to it.

## TDD: RED -> GREEN -> REFACTOR

### RED 1 - the three existing defect tests

Run each individually before editing:

```bash
./scripts/test.sh apps.patients.tests.test_tag_error_handling.\
PatientTagErrorHandlingTests.test_add_tag_with_nonexistent_tag_id
./scripts/test.sh apps.patients.tests.test_tag_management_basic_error_handling.\
TagManagementBasicErrorHandlingTests.test_add_nonexistent_tag
./scripts/test.sh apps.patients.tests.test_tag_management_error_handling.\
TagManagementErrorHandlingTests.test_add_nonexistent_tag
```

Each must fail with `AssertionError: 500 != 404`.

### RED 2 - malformed body regression (added first, per protocol)

Add to `PatientTagErrorHandlingTests` in
`test_tag_error_handling.py`:

- create a patient and reverse `patients:patient_tag_add`;
- POST `{'tag_id': 'not-an-integer'}`;
- assert status `400` and exact payload
  `response.json()['error'] == 'ID da tag inválido'`.

Rerun it before production changes. It must fail with `500 != 400` (the
current code converts the raised `ValueError` into the generic 500 JSON),
proving the defect for the planner-approved malformed contract.

Do not weaken any existing assertion to obtain RED.

### GREEN - the approved minimal view fix

Restructure only the head of `PatientTagAddView.post` to the approved shape:

```python
def post(self, request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)

    # (unchanged permission check, 403)

    tag_id = request.POST.get('tag_id')
    if not tag_id:
        return JsonResponse(
            {'error': 'ID da tag é obrigatório'}, status=400
        )

    # AllowedTag.pk is an integer; a non-integer body value is a
    # malformed request, not a missing resource.
    try:
        tag_pk = int(tag_id)
    except (TypeError, ValueError):
        return JsonResponse(
            {'error': 'ID da tag inválido'}, status=400
        )

    # Resolved outside the broad except so a nonexistent AllowedTag id
    # yields the domain 404 instead of a swallowed Http404 (500).
    allowed_tag = get_object_or_404(AllowedTag, pk=tag_pk)

    try:
        # (can_add_patient_tag check onward: byte-identical)
```

Everything from the `can_add_patient_tag` check through the existing
`except Exception` logger/500 return must remain byte-for-byte unchanged,
with `allowed_tag` already bound. Do not catch `Http404` inside the broad
except, do not convert 404 to JSON, and do not alter the logger or its
message format.

### REFACTOR

None. If anything beyond the head of `PatientTagAddView.post` appears to need
a change, stop `INCOMPLETE` and return to the planner.

## Mandatory inspections

```bash
VIEWS_PATTERN="class PatientTagAddView|tag_pk|ID da tag inválido"
VIEWS_PATTERN="${VIEWS_PATTERN}|ID da tag é obrigatório|get_object_or_404"
VIEWS_PATTERN="${VIEWS_PATTERN}|except Exception"
rg -n "$VIEWS_PATTERN" apps/patients/views.py
TESTS_PATTERN="not-an-integer|ID da tag inválido|nonexistent_tag_id"
TESTS_PATTERN="${TESTS_PATTERN}|add_nonexistent_tag"
rg -n "$TESTS_PATTERN" \
  apps/patients/tests/test_tag_error_handling.py \
  apps/patients/tests/test_tag_management_basic_error_handling.py \
  apps/patients/tests/test_tag_management_error_handling.py
git diff --word-diff=porcelain -- apps/patients/views.py
git diff --check
git diff --stat
git status --short
```

The report must show the exact view token diff and prove that the remove,
remove-all, and API views and every unchanged branch are untouched.

## Static and migration verification

```bash
docker exec eqmd_dev ruff check --isolated \
  --select E9,F63,F7,F82 apps/patients/views.py
docker exec eqmd_dev ruff check apps/patients/tests/test_tag_error_handling.py
docker exec eqmd_dev python -m compileall -q apps/patients/views.py
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
```

Every command must exit 0. No ignore, `noqa`, configuration change, or
migration file may appear.

## Functional verification

Run sequentially; never run test processes concurrently against the shared
preserved PostgreSQL test database.

```bash
./scripts/test.sh apps.patients.tests.test_tag_error_handling
./scripts/test.sh apps.patients.tests.test_tag_management_basic_error_handling
./scripts/test.sh apps.patients.tests.test_tag_management_error_handling
./scripts/test.sh apps.patients.tests.test_views
./scripts/test.sh apps.core.tests.test_lifecycle_guard_rail
```

Required outcomes:

- tag error handling: 22/22 (21 prior + 1 new);
- basic error handling: 9/9;
- management error handling: 16/16;
- `test_views`: no new failures versus baseline;
- lifecycle guard rail command exits 0.

## Full comparison and artifact gates

```bash
./scripts/test.sh > /tmp/full_suite_006a.log 2>&1
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/tasks.md \
  /tmp/restore-green-development-quality-gates-slice-006a-report.md
git diff --check
git status --short
```

Extract sorted FAIL/ERROR headers identically from the new log and
`/tmp/full_suite_006.log`. The new result must:

- remove exactly the three defect-test FAIL headers and add zero headers;
- report test count 2,025 → 2,026 (one new passing regression);
- show failures 111 → 108 and errors unchanged at 336.

Any added header, including time-of-day flakes, means `INCOMPLETE`.

## Binary acceptance criteria

- [ ] The three defect tests are RED `500 != 404` before the fix and GREEN
      after, along with every other test in the three modules.
- [ ] The malformed-body regression is RED `500 != 400` before production
      changes and GREEN with the exact payload after.
- [ ] The view diff is exactly the approved head restructure; no other view,
      branch, message, or logger changed.
- [ ] Missing/inactive/duplicate/success/500 contracts and permission
      enforcement are byte-identical.
- [ ] All functional, static, migration, and artifact gates exit 0.
- [ ] Full suite removes exactly three headers, adds zero, and gains exactly
      one passing test.
- [ ] Only the two expected files change in 006A.
- [ ] No non-test database access/mutation, package install, container
      rebuild, PII, task edit, commit, push, ignore, or migration occurs.
- [ ] Tasks 6.x and 6A.x remain unchecked for third-LLM closure.

## Automatic `INCOMPLETE`

Report `INCOMPLETE` and stop if either RED stage is missing; any of the four
tag modules remains red; the fix requires touching another view or the broad
except's logger; a 404 becomes JSON or a 400 becomes 404/500; a
static/migration command fails; a full-suite header is added; another file
changes; or any non-test database access, install, PII, container rebuild,
task edit, commit, push, ignore, or migration occurs.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-006a-report.md`
with status, RED 1/RED 2 tracebacks, requirement matrix, exact view token
diff, per-branch before/after behavior proof, target/static/migration results,
full-suite ledger versus `/tmp/full_suite_006.log`, database-isolation proof,
scope audit, rollback, and third-LLM handoff.

## Ready-to-run implementer prompt

```text
Read every prerequisite in slice-006a-repair-tag-add-http404-and-malformed-id.md.
Implement ONLY reslice 006A with strict TDD. Preserve all slice-006 test
rewrites. First add the malformed tag_id regression to test_tag_error_handling
and capture its RED 500 != 400 plus the three existing 500 != 404 REDs. Then
apply the approved minimal PatientTagAddView.post fix: int-validate tag_id to
400 'ID da tag invalido', and resolve AllowedTag with get_object_or_404
OUTSIDE the broad except so missing ids return the domain 404. Touch only
views.py (that single method) and test_tag_error_handling.py. Run tests
sequentially, make every listed gate green, compare against
/tmp/full_suite_006.log expecting minus three headers and plus one test, write
/tmp/restore-green-development-quality-gates-slice-006a-report.md, reply with
REPORT_PATH and STATUS, then STOP before slice 007. Never access a non-test
database. No install, task edit, commit, or push.
```
