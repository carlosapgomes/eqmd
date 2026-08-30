<!-- markdownlint-disable MD013 -->

# Slice 018A - Static Closure of Frozen Gate Debt

## Handoff for a zero-context implementer

Read standard artifacts, approved reports 001-018, correction reports 001A,
004A, 004B, 005A, and 006A, ADR-0001, and slice 018's report (INCOMPLETE,
zero edits, residual classification sections 4.2-4.4). This slice repairs the
three frozen static-gate residuals so the CI-mirror gates over
`$CHANGED_PY_FILES` exit 0. Start only after slice 018's verification.

`$CHANGED_PY_FILES` = the 89-file set defined in slice 018 report section 3.2
(`git diff --name-only e0124e9 HEAD -- '*.py'` + working-tree modifications +
untracked `apps/patients/services/**` and
`apps/patients/tests/test_duplicate_review_flow.py`).

## Mandatory protocol

Baseline all three gates BEFORE edits and record exact counts: `ruff check`
(4 errors in `config/settings.py`), `ruff format --check` (12 files), scoped
mypy (45 `var-annotated` in `apps/events/models.py`). These gates are the RED.
Zero behavior change: `config/settings.py` final values must be identical
before and after. No mypy ignore/override may be added for
`apps/events/models.py` (the pyproject override covers only
`apps.patients.models`/`apps.patients.views`). Formatting is mechanical only,
verified with `git diff -w`. Full suite must stay green. No install, commit,
push, or migration.

## Objective

Make `ruff check`, `ruff format --check`, and `./scripts/typecheck.sh` over
`$CHANGED_PY_FILES` exit 0 without any behavior change.

## Requirements

- **R1:** `config/settings.py` — fix I001 (import block), 2× PLW0127
  (self-assignments `DJANGO_DRF_FILEPOND_UPLOAD_TMP` /
  `DJANGO_DRF_FILEPOND_FILE_STORE_PATH` at lines ~345-346) and PLW1508
  (invalid env default type at ~396). The PLW0127 lines encode a fallback
  pattern: rewrite preserving the exact final values (prove with a
  before/after evaluation of the resulting settings via
  `manage.py shell`-free assertion or an inline test comparing
  `django.conf.settings` values captured before the edit).
- **R2:** `ruff format` the 12 frozen files listed in slice 018 report
  section 4.3 (11 events-family files + `config/settings.py`); diff must be
  whitespace/quote-only (`git diff -w` empty per file).
- **R3:** annotate the 45 frozen `var-annotated` findings in
  `apps/events/models.py` so `./scripts/typecheck.sh apps/events/models.py`
  exits 0. Use `ClassVar[...]` for declarative model/class attributes
  (precedents: slice 014 `field_mapping.py`, slice 016 RUF012 notes) and
  precise types for locals. Zero runtime behavior change; migrations must
  remain unchanged (`makemigrations --check --dry-run` clean).

## Expected files

- `config/settings.py`
- `apps/events/models.py`
- the 12 files of R2 (11 listed events-family files, overlapping settings)
- `openspec/changes/restore-green-development-quality-gates/slices/README.md`
  and `tasks.md` only for slice bookkeeping if required

## TDD and inspections

```bash
docker exec eqmd_dev ruff check --output-format concise $CHANGED_PY_FILES
docker exec eqmd_dev ruff format --check $CHANGED_PY_FILES
./scripts/typecheck.sh <CHANGED_PRODUCTION_PY_FILES>
git diff -w -- config/settings.py apps/events/models.py
git diff --check
```

## Verification commands

```bash
docker exec eqmd_dev ruff check $CHANGED_PY_FILES          # exit 0
docker exec eqmd_dev ruff format --check $CHANGED_PY_FILES # exit 0
./scripts/typecheck.sh $CHANGED_PRODUCTION_FILES           # exit 0
docker exec eqmd_dev python manage.py check
docker exec eqmd_dev python manage.py makemigrations --check --dry-run
./scripts/test.sh                                          # 2177 OK, skipped=12
./scripts/test.sh apps.events apps.historyandphysicals     # both OK
docker exec eqmd_dev ruff check --output-format concise apps config \
  > /tmp/ruff_repo_after_018a.txt
  # zero NEW vs /tmp/ruff_repo_before_018.txt
openspec validate restore-green-development-quality-gates --strict
markdownlint-cli2 \
  openspec/changes/restore-green-development-quality-gates/slices/slice-018a-static-closure-frozen-debt.md \
  /tmp/restore-green-development-quality-gates-slice-018a-report.md
```

## Binary criteria

- [ ] All three CI-mirror static gates exit 0 over `$CHANGED_PY_FILES`.
- [ ] No behavior change: settings values identical, migrations clean, full
      suite green with unchanged count and skips.
- [ ] Zero NEW findings versus `/tmp/ruff_repo_before_018.txt` (decreases
      recorded).
- [ ] No mypy escape hatch added; no noqa added.

## Automatic `INCOMPLETE`

Any nonzero gate after edits, behavior change in `config/settings.py`,
migration generated, new finding, new test failure, reduced skip count,
missing report, PII, install, commit, or push.

## Required report

Create `/tmp/restore-green-development-quality-gates-slice-018a-report.md`
with exact before/after gate outputs, the settings value-equality proof, the
`git diff -w` emptiness proof per formatted file, scope audit, and verifier
handoff.

## Ready-to-run implementer prompt

```text
Implement ONLY slice 018A after slice 018's INCOMPLETE verification. Repair
the three frozen static residuals (settings.py 4 ruff findings, format the 12
frozen files, annotate 45 events/models.py findings) with zero behavior
change. All gates green, full suite unchanged, write the report, STOP.
```
