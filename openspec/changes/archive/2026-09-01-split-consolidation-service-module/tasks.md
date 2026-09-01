# Tasks: Split the consolidation service module

## 1. Refactor

- [x] 1.1 Single vertical slice: extract `consolidation_plan.py` and
      `consolidation_review.py` from
      `patient_record_consolidation.py` (verbatim moves), keep the
      executor + facade with `__all__` re-exports, annotate to
      strict-clean, prove purity via untouched importers + full suite
      _(verified 2026-09-01: 396→206+117+160; importers byte-identical;
      suite 2753 OK same count; strict mypy 0 errors vs 9 baseline;
      report at /tmp/split-consolidation-service-module-slice-01-report.md)_

## 2. Closure

- [x] 2.1 Full suite green (same count), strict mypy clean on the
      three service modules, ruff clean, archived with `--skip-specs`
      (internal refactor, no spec delta)
      _(closed 2026-09-01: suite 2753 OK same count; strict clean;
      archived normally — the module-boundary contract became a
      development-quality-gates requirement instead of skip-specs)_
