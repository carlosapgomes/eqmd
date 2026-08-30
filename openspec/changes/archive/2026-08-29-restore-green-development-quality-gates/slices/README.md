# Slice Execution Index

Implement exactly one slice at a time. Each slice contains its own zero-context
handoff and ready-to-run implementer prompt. Do not begin the next slice until a
third LLM approves the prior `/tmp` report. References in later slices to a
report range include required correction reports 001A, 004A, 004B, 005A,
and 006A when their base slice falls inside that range.

| Order | Slice                                                                                         | Required report                                                                                                                                                |
| ----: | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|     1 | [Lock runtime and dependencies](slice-001-lock-runtime-and-dependencies.md)                   | `/tmp/restore-green-development-quality-gates-slice-001-report.md`                                                                                             |
|    1A | [Complete runtime/OIDC contract](slice-001a-complete-runtime-and-oidc-contract.md)            | `/tmp/restore-green-development-quality-gates-slice-001a-report.md`                                                                                            |
|     2 | [Fail-closed tooling](slice-002-reproducible-fail-closed-tooling.md)                          | `/tmp/restore-green-development-quality-gates-slice-002-report.md`                                                                                             |
|     3 | [Patients static quality](slice-003-patients-static-quality.md)                               | `/tmp/restore-green-development-quality-gates-slice-003-report.md`                                                                                             |
|     4 | [Patients history/record fixtures](slice-004-patients-history-record-fixtures.md)             | `/tmp/restore-green-development-quality-gates-slice-004-report.md`                                                                                             |
|    4A | [Record-number create validation](slice-004a-record-number-create-validation.md)              | `/tmp/restore-green-development-quality-gates-slice-004a-report.md`                                                                                            |
|    4B | [Signal fixture/soft-delete recovery](slice-004b-signals-fixture-and-soft-delete-recovery.md) | `/tmp/restore-green-development-quality-gates-slice-004b-report.md`                                                                                            |
|     5 | [Patients API/development/performance](slice-005-patients-api-signals-utility-fixtures.md)    | `/tmp/restore-green-development-quality-gates-slice-005-report.md`                                                                                             |
|    5A | [Refresh command dry-run/verbosity](slice-005a-refresh-command-dry-run-and-verbosity.md)      | `/tmp/restore-green-development-quality-gates-slice-005a-report.md`                                                                                            |
|     6 | [Patient tag HTTP contracts](slice-006-patient-tag-http-contracts.md)                         | `/tmp/restore-green-development-quality-gates-slice-006-report.md`                                                                                             |
|    6A | [Tag-add 404/malformed-id repair](slice-006a-repair-tag-add-http404-and-malformed-id.md)      | `/tmp/restore-green-development-quality-gates-slice-006a-report.md`                                                                                            |
|     7 | [Patient tag architecture](slice-007-patient-tag-architecture.md)                             | `/tmp/restore-green-development-quality-gates-slice-007-report.md`                                                                                             |
|     8 | [Patient clinical workflows](slice-008-patient-clinical-workflows.md)                         | `/tmp/restore-green-development-quality-gates-slice-008-report.md`                                                                                             |
|     9 | [Entire patients app green](slice-009-patients-app-green.md)                                  | `/tmp/restore-green-development-quality-gates-slice-009-report.md`                                                                                             |
|    9A | [Patients static closure for CI gates](slice-009a-patients-static-closure.md)                 | `/tmp/restore-green-development-quality-gates-slice-009a-report.md`                                                                                            |
|    10 | [Drug templates](slice-010-drugtemplates-cohort.md)                                           | `/tmp/restore-green-development-quality-gates-slice-010-report.md`                                                                                             |
|    11 | [Outpatient prescriptions](slice-011-outpatient-prescriptions-cohort.md)                      | `/tmp/restore-green-development-quality-gates-slice-011-report.md`                                                                                             |
|    12 | [Mediafiles foundations](slice-012-mediafiles-foundations.md)                                 | `/tmp/restore-green-development-quality-gates-slice-012-report.md`                                                                                             |
|    13 | [Mediafiles HTTP/performance](slice-013-mediafiles-http-performance.md)                       | `/tmp/restore-green-development-quality-gates-slice-013-report.md`                                                                                             |
|    14 | [PDF forms foundations](slice-014-pdf-forms-domain-foundations.md)                            | `/tmp/restore-green-development-quality-gates-slice-014-report.md`                                                                                             |
|    15 | [PDF forms admin/HTTP/security](slice-015-pdf-forms-admin-http-security.md)                   | `/tmp/restore-green-development-quality-gates-slice-015-report.md`                                                                                             |
|    16 | [Events and history](slice-016-events-history-cohorts.md)                                     | `/tmp/restore-green-development-quality-gates-slice-016-report.md`                                                                                             |
|    17 | [Matrix/PDF generator/sample](slice-017-matrix-pdfgenerator-sample-content.md)                | `/tmp/restore-green-development-quality-gates-slice-017-report.md`                                                                                             |
|    18 | [Enforce full green baseline](slice-018-enforce-full-green-baseline.md)                       | `/tmp/restore-green-development-quality-gates-slice-018-report.md` (INCOMPLETE — protocol stop, zero edits)                                                    |
|   18A | [Static closure of frozen gate debt](slice-018a-static-closure-frozen-debt.md)                | `/tmp/restore-green-development-quality-gates-slice-018a-report.md` (COMPLETE — verified)                                                                      |
|   18B | [Core app discovery and cohort repair](slice-018b-core-discovery-and-cohort.md)               | `/tmp/restore-green-development-quality-gates-slice-018b-report.md` (COMPLETE — verificado com correção 018B-fix1; suíte 2177→2653, guard rail 214→168/core 0) |
|   18C | [Lifecycle zero, enforcement, and close](slice-018c-lifecycle-zero-enforcement-and-close.md)  | `/tmp/restore-green-development-quality-gates-slice-018c-report.md` (COMPLETE — verificado; guard rail 168→0, `max_allowed=0`, CI bloqueante, suíte 2654 OK)   |

## Stop rule

If a slice exceeds its file cap, encounters ambiguous contract authority, needs
a migration, requires a destructive command, or cannot make its target command
fully green, report `INCOMPLETE` and return to the planner for reslicing.
