# Tasks: Block placeholder-only record numbers

## 1. Placeholder rule enforced at every entry point

- [x] 1.1 Single vertical slice: harden `validate_record_number_format`
      (>= 1 alphanumeric), enforce the rule inside
      `update_current_record_number` before any write, reject
      placeholder-only `renumber` targets during consolidation plan
      validation, and cover all three gates with TDD tests
      *(verified 2026-08-31: RED 5+1+2 → GREEN 13/13; full suite 2753 OK;
      mypy strict service OK; ruff delta-clean; report at
      /tmp/block-placeholder-record-numbers-slice-01-report.md)*

## 2. Closure

- [ ] 2.1 Full suite green, ruff delta-clean, spec delta merged on
      archive
