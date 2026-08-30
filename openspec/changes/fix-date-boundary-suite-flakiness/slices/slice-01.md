# Slice 01 - Timezone-Consistent Day Scope and Anchors

## Handoff for a zero-context implementer

Read these files fully and in order:

1. `AGENTS.md`
2. `PROJECT_CONTEXT.md`
3. `docs/workflows/coding-standards.md`
4. `docs/workflows/llm-collab.md`
5. `docs/workflows/clean-code-skill.md`
6. `openspec/changes/fix-date-boundary-suite-flakiness/proposal.md`
7. `openspec/changes/fix-date-boundary-suite-flakiness/design.md`
8. `openspec/changes/fix-date-boundary-suite-flakiness/specs/development-quality-gates/spec.md`
9. `openspec/changes/fix-date-boundary-suite-flakiness/tasks.md`
10. This slice file

Implement exactly one slice and stop. Do not rely on conversation history.

Current code facts to verify before planning:

- `apps/dailynotes/templatetags/dailynote_tags.py` line 57,
  `apps/historyandphysicals/templatetags/historyandphysical_tags.py` line 60,
  and `apps/simplenotes/templatetags/simplenote_tags.py` line 60 use
  `today = timezone.now().date()` (UTC date) while their `__date` filters
  evaluate in the project `TIME_ZONE` (`America/Bahia`).
- `apps/dailynotes/tests/test_integration.py` `setUp` creates `dailynote1`
  at `now - timedelta(hours=2)`, `dailynote2` at `now - timedelta(hours=1)`,
  and `dailynote3` at `now - timedelta(days=1)`.
- Six detail-context tests and one timeline test compute expected
  `%d/%m/%Y` strings via `strftime` on the aware (UTC) datetime:
  `apps/dailynotes/tests/test_detail_context_ui.py` lines 102 and 163,
  `apps/historyandphysicals/tests/test_detail_context_ui.py` lines 105 and
  156, `apps/simplenotes/tests/test_detail_context_ui.py` lines 105 and 156,
  and `apps/patients/tests/test_patient_timeline_context_summary.py`
  line 335.
- `settings.TIME_ZONE` is read from the `TIME_ZONE` environment variable
  (`config/settings.py` line 207).
- `scripts/test.sh` does not forward `TIME_ZONE`; divergent-timezone runs
  must use `docker exec` directly (commands below).

## Mandatory protocol for DeepSeek4-Flash

If any protocol item fails, report `INCOMPLETE`, leave tasks unchecked, and
stop.

1. Record `BASE_REF=$(git rev-parse HEAD)` and `git status --short`. Preserve
   unrelated changes and stop if expected files contain unverified work.
2. Run the full pre-edit baseline `./scripts/test.sh`. Record exit code,
   `Ran N tests`, failures/errors/skips. A nonzero exit or any failure/error
   is an automatic blocker before edits. (Dispatch rule: run outside
   `UTC [00:00, 05:00)`; after this slice lands that restriction no longer
   applies to any slice.)
3. Confirm `ruff` and `mypy` already exist inside `eqmd_dev`; never install
   tooling in a slice.
4. Create the real RED first (divergent-timezone run, commands below). A
   missing-timezone or import error is not a valid RED.
5. Implement only R1-R3.
6. Run every inspection and quality gate. The final full suite must exit 0
   with zero failures/errors and no lower test count than baseline, and the
   focused modules must pass under BOTH the project timezone and the
   divergent timezone.
7. Create the exact `/tmp` Markdown report. Do not commit or push; stop for
   third-LLM verification.

## Objective

Make the full suite wall-clock independent by giving day-scoped dashboard
tags and date assertions a single, consistent timezone basis, and by
anchoring the count fixtures to local-midnight instants.

## Functional scope

### R1 - Day-scoped tags use the active-timezone local date

In the three tag modules, replace `timezone.now().date()` with
`timezone.localdate()` so the day basis matches the `__date` lookups and
template rendering. Change nothing else in those modules.

### R2 - Date assertions match template rendering

In the seven listed assertion sites, wrap the aware datetime with
`timezone.localtime(...)` before `strftime('%d/%m/%Y')`. Do not change the
fixtures of those tests (the timeline admission stays `now - 5 days`; the
detail-context events stay `timezone.now()`).

### R3 - Count fixtures are local-day stable

In `DailyNoteIntegrationTestCase.setUp`, compute
`local_midnight = timezone.localtime().replace(hour=0, minute=0, second=0,
microsecond=0)` and create `dailynote1` at `local_midnight`, `dailynote2`
at `local_midnight + timedelta(minutes=30)`, and `dailynote3` at
`local_midnight - timedelta(seconds=1)`. Keep every other fixture attribute
unchanged. `test_dailynotes_count_today` and `test_dailynotes_count_week`
must then pass at any wall-clock time under any timezone without further
edits.

## Expected files

Modify/create only:

- `apps/dailynotes/templatetags/dailynote_tags.py`
- `apps/historyandphysicals/templatetags/historyandphysical_tags.py`
- `apps/simplenotes/templatetags/simplenote_tags.py`
- `apps/dailynotes/tests/test_integration.py`
- `apps/dailynotes/tests/test_detail_context_ui.py`
- `apps/historyandphysicals/tests/test_detail_context_ui.py`
- `apps/simplenotes/tests/test_detail_context_ui.py`
- `apps/patients/tests/test_patient_timeline_context_summary.py`
- `openspec/changes/fix-date-boundary-suite-flakiness/tasks.md`
  only after all gates pass

Any other file needs planner approval. Forbidden: settings changes,
templates, migrations, models, views, URLs, the excluded same-pattern files
listed in the design (`outpatientprescriptions` and
`patients/tests/test_record_tracking_models.py`), and any unrelated
refactor.

## TDD: RED -> GREEN -> REFACTOR

### RED (divergent timezone; no waiting for a wall-clock window)

With `k = (utc_hour - 22) mod 24` at dispatch time, use `Etc/GMT+{k}`
(UTC-k) when `1 <= k <= 12` and `Etc/GMT-{24-k}` (UTC+(24-k)) when
`13 <= k <= 23`, so the divergent local clock sits in `[21:30, 23:30)`.
Example: at 06:00 UTC, `k = 8` -> `TIME_ZONE=Etc/GMT+8`.

Focused modules:

```text
apps.dailynotes.tests.test_integration
apps.dailynotes.tests.test_detail_context_ui
apps.historyandphysicals.tests.test_detail_context_ui
apps.simplenotes.tests.test_detail_context_ui
apps.patients.tests.test_patient_timeline_context_summary
```

```bash
docker exec -e DJANGO_SETTINGS_MODULE=config.test_settings \
  -e TIME_ZONE=<divergent zone> eqmd_dev \
  python manage.py test \
  apps.dailynotes.tests.test_integration \
  apps.dailynotes.tests.test_detail_context_ui \
  apps.historyandphysicals.tests.test_detail_context_ui \
  apps.simplenotes.tests.test_detail_context_ui \
  apps.patients.tests.test_patient_timeline_context_summary \
  --keepdb --noinput
```

Record the failing test list. Pre-fix expectation: exactly the eight
date-boundary tests fail (two per detail module, the count-today test, and
the timeline test); a missing-tooling or import error is not a valid RED.

### GREEN

Apply R1-R3 minimally.

### REFACTOR

No restructuring is expected; keep edits one-to-one with the requirements
and confirm no other `timezone.now().date()` or bare aware-datetime
`strftime('%d/%m/%Y')` anchors remain in the eight files.

## Mandatory inspection checks

Run before and after editing; include both outputs in the report:

```bash
rg -n 'timezone.now\(\).date\(\)|timezone.localdate\(\)' \
  apps/dailynotes/templatetags/dailynote_tags.py \
  apps/historyandphysicals/templatetags/historyandphysical_tags.py \
  apps/simplenotes/templatetags/simplenote_tags.py
rg -n "strftime\('%d/%m/%Y'\)" \
  apps/dailynotes/tests/test_detail_context_ui.py \
  apps/historyandphysicals/tests/test_detail_context_ui.py \
  apps/simplenotes/tests/test_detail_context_ui.py \
  apps/patients/tests/test_patient_timeline_context_summary.py
rg -n 'local_midnight|timedelta' apps/dailynotes/tests/test_integration.py
git diff --stat
```

Expected interpretation: after the edit, the three tag modules contain
`timezone.localdate()` and no `timezone.now().date()`; every listed
assertion is wrapped in `timezone.localtime(...)`; the integration fixtures
reference `local_midnight`.

## Verification commands

Execute all:

```bash
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev ruff check \
  apps/dailynotes/templatetags/dailynote_tags.py \
  apps/historyandphysicals/templatetags/historyandphysical_tags.py \
  apps/simplenotes/templatetags/simplenote_tags.py \
  apps/dailynotes/tests/test_integration.py \
  apps/dailynotes/tests/test_detail_context_ui.py \
  apps/historyandphysicals/tests/test_detail_context_ui.py \
  apps/simplenotes/tests/test_detail_context_ui.py \
  apps/patients/tests/test_patient_timeline_context_summary.py
docker exec eqmd_dev ruff format --check \
  apps/dailynotes/templatetags/dailynote_tags.py \
  apps/historyandphysicals/templatetags/historyandphysical_tags.py \
  apps/simplenotes/templatetags/simplenote_tags.py \
  apps/dailynotes/tests/test_integration.py \
  apps/dailynotes/tests/test_detail_context_ui.py \
  apps/historyandphysicals/tests/test_detail_context_ui.py \
  apps/simplenotes/tests/test_detail_context_ui.py \
  apps/patients/tests/test_patient_timeline_context_summary.py
./scripts/typecheck.sh \
  apps/dailynotes/templatetags/dailynote_tags.py \
  apps/historyandphysicals/templatetags/historyandphysical_tags.py \
  apps/simplenotes/templatetags/simplenote_tags.py
./scripts/test.sh apps.dailynotes.tests.test_integration \
  apps.dailynotes.tests.test_detail_context_ui \
  apps.historyandphysicals.tests.test_detail_context_ui \
  apps.simplenotes.tests.test_detail_context_ui \
  apps.patients.tests.test_patient_timeline_context_summary
docker exec -e DJANGO_SETTINGS_MODULE=config.test_settings \
  -e TIME_ZONE=<divergent zone used for RED> eqmd_dev \
  python manage.py test \
  apps.dailynotes.tests.test_integration \
  apps.dailynotes.tests.test_detail_context_ui \
  apps.historyandphysicals.tests.test_detail_context_ui \
  apps.simplenotes.tests.test_detail_context_ui \
  apps.patients.tests.test_patient_timeline_context_summary \
  --keepdb --noinput
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh
openspec validate fix-date-boundary-suite-flakiness --strict
markdownlint-cli2 \
  openspec/changes/fix-date-boundary-suite-flakiness/tasks.md \
  /tmp/fix-date-boundary-suite-flakiness-slice-01-report.md
```

## Binary success criteria

- [ ] R1-R3 map to inspection/test evidence.
- [ ] Full baseline passed before edits with exit 0 and zero failures/errors.
- [ ] RED recorded under the divergent timezone with the expected
      date-boundary failures.
- [ ] Focused modules pass under BOTH the project timezone and the divergent
      timezone after the fix.
- [ ] Final full suite exits 0 with zero failures/errors and a count not
      lower than baseline.
- [ ] Only the eight declared files changed (plus tasks.md after gates).
- [ ] No migration drift.
- [ ] Exact temporary report exists, is lint-clean, and contains no PII.

## Self-evaluation gates

Answer with `YES` and evidence or mark incomplete:

1. Do all three day-scoped tags use `timezone.localdate()`?
2. Are all seven assertion anchors wrapped in `timezone.localtime(...)`?
3. Are the integration fixtures anchored to `local_midnight` such that
   today/week counts hold at any wall-clock time?
4. Did the divergent-timezone run pass post-fix and fail pre-fix?
5. Did baseline and final full suites pass with no lower final count?
6. Were settings, templates, models, views, migrations, URLs, and the
   excluded files left untouched?
7. Is the report complete, lint-clean, and free of patient data?

### Automatic INCOMPLETE conditions

Mark incomplete if any applies:

- baseline missing/nonzero or containing failure/error;
- RED not reproduced under a divergent timezone or caused by import/tooling
  errors;
- any required command missing or failing;
- any focused module failing under either timezone after the fix;
- final suite nonzero, with failure/error, or lower count;
- an undeclared file changed;
- migration drift appears;
- PII in the report;
- tasks marked early, report missing, commit/push/install/destructive
  command.

## Required temporary report

Create exactly:

`/tmp/fix-date-boundary-suite-flakiness-slice-01-report.md`

Include:

1. Status.
2. `BASE_REF`, initial status, and unrelated changes preserved.
3. R1-R3 matrix.
4. Baseline command/exit/`Ran N tests`/failures/errors/skips.
5. RED: divergent zone chosen, formula application, failing test list.
6. GREEN/refactor evidence with before/after snippets for one tag and one
   assertion.
7. Inspection outputs before/after.
8. Every quality command and exit code (both timezone runs included).
9. Baseline/final comparison with explicit zero failures/errors.
10. All self-evaluation answers.
11. Scope justification and privacy statement.
12. `Handoff for verifier`: changed files, exact reruns (including the
    divergent-timezone command with the zone used), known limitations.

## Ready-to-run prompt for the implementer

```text
With zero conversation context, read AGENTS.md, PROJECT_CONTEXT.md, all
coding workflow documents, and every artifact of
fix-date-boundary-suite-flakiness including this slice file. Implement ONLY
slice 01.

Follow the protocol literally: record BASE_REF/status; run FULL
./scripts/test.sh before editing and stop if not fully green (dispatch
outside UTC [00:00, 05:00)); verify ruff/mypy exist without installing;
reproduce the RED by running the five focused modules under a divergent
TIME_ZONE computed as k = (utc_hour - 22) mod 24 -> Etc/GMT+{k} for
1 <= k <= 12, else Etc/GMT-{24-k}; apply the three minimal fixes
(timezone.localdate in the three tags; timezone.localtime wrappers on the
seven assertions; local_midnight fixture anchors); rerun the focused
modules under BOTH timezones and the full suite; run every remaining gate;
create the exact temporary report.

Do not touch settings, templates, models, views, migrations, URLs, the two
excluded same-pattern files, or anything unrelated. Do not install, commit,
push, or run destructive commands. Mark only tasks 1.1-1.4 after every gate
passes. Any missing/failing gate or failed timezone run means Status:
INCOMPLETE and unchecked tasks.

Reply only with REPORT_PATH=/tmp/fix-date-boundary-suite-flakiness-slice-01-report.md
and one-line status, then STOP for third-LLM verification.
```
