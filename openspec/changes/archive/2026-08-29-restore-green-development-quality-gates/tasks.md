# Tasks: Restore Green Development Quality Gates

## 0. Mandatory Preconditions

- [x] 0.1 Record `BASE_REF`, working-tree ownership, runtime/tool versions, and
      the aggregate baseline without exposing patient data
- [x] 0.2 Confirm PostgreSQL-only test execution and preserve unrelated changes
- [x] 0.3 Obtain planner approval before any container rebuild/recreation
- [x] 0.4 Implement exactly one slice at a time and obtain third-LLM approval
      before advancing

## 1. Slice 001 — Lock Runtime and Dependency Resolution

- [x] 1.1 Constrain Django to the approved 5.2 LTS minor line
- [x] 1.2 Make Docker dependency installation consume committed lock metadata
- [x] 1.3 Preserve separate production and development dependency outcomes
- [x] 1.4 Prove local/CI lock resolution and migration check use supported Django
- [x] 1.5 Create `/tmp/restore-green-development-quality-gates-slice-001-report.md`

## 1A. Reslice 001A — Complete Runtime and OIDC Contract

- [x] 1A.1 Pin the validated uv image and close editable installs with
      `--no-deps`
- [x] 1A.2 Add the project-owned OIDC `AutoField` compatibility AppConfig
- [x] 1A.3 Prove synthetic OIDC CRUD and zero supported-runtime migration drift
- [x] 1A.4 Build and inspect dev/prod targets only after explicit approval
- [x] 1A.5 Create
      `/tmp/restore-green-development-quality-gates-slice-001a-report.md`

## 2. Slice 002 — Reproducible Fail-Closed Development Tooling

- [x] 2.1 Declare and provision Ruff/Mypy in the development environment
- [x] 2.2 Remove runtime/root package installation from quality scripts
- [x] 2.3 Align CI and local quality commands on committed metadata
- [x] 2.4 Add fail-closed regression checks for missing tools
- [x] 2.5 Create `/tmp/restore-green-development-quality-gates-slice-002-report.md`

## 3. Slice 003 — Patients Static Quality Gate

- [x] 3.1 Isolate and baseline the mechanical `forms.py` formatting change
- [x] 3.2 Resolve scoped Ruff findings without blanket ignores
- [x] 3.3 Resolve the existing `InternalTransferForm.ward` Mypy error
- [x] 3.4 Prove patient form behavior is unchanged
- [x] 3.5 Create `/tmp/restore-green-development-quality-gates-slice-003-report.md`

## 4. Slice 004 — Patients History and Record-Tracking Fixtures

- [x] 4.1 Replace obsolete user fields in history and record-tracking tests
- [x] 4.2 Use supported navigation-ready lifecycle fixtures where applicable
- [x] 4.3 Preserve record/history business assertions
- [x] 4.4 Make all listed modules green
- [x] 4.5 Create `/tmp/restore-green-development-quality-gates-slice-004-report.md`

## 4A. Reslice 004A — Repair Record-Number Create Validation

- [x] 4A.1 Preserve the two existing green slice-004 modules
- [x] 4A.2 Add first-create and existing-current replacement regressions
- [x] 4A.3 Guard model uniqueness lookup on `patient_id` presence
- [x] 4A.4 Make all slice-004 targets and supporting regressions green
- [x] 4A.5 Create
      `/tmp/restore-green-development-quality-gates-slice-004a-report.md`

## 4B. Reslice 004B — Signal Fixture and Soft-Delete Recovery

- [x] 4B.1 Replace the obsolete signal-test user fixture
- [x] 4B.2 Capture the exposed soft-deleted event uniqueness RED
- [x] 4B.3 Restore the existing timeline event in place on source update
- [x] 4B.4 Make all 004/004A supporting modules and gates green
- [x] 4B.5 Create
      `/tmp/restore-green-development-quality-gates-slice-004b-report.md`

## 5. Slice 005 — Patients API, Development, and Performance Fixtures

- [x] 5.1 Repair obsolete user/lifecycle setup in the listed modules
- [x] 5.2 Preserve permission and performance assertions
- [x] 5.3 Make all listed modules green
- [x] 5.4 Create `/tmp/restore-green-development-quality-gates-slice-005-report.md`

## 5A. Reslice 005A — Refresh Command Dry-Run and Aggregate Verbosity

- [x] 5A.1 Strengthen normal command mutation evidence
- [x] 5A.2 Redefine command output as aggregate and non-identifying
- [x] 5A.3 Implement transactionally rolled-back `--dry-run`
- [x] 5A.4 Make all slice-005 targets and supporting gates green
- [x] 5A.5 Create
      `/tmp/restore-green-development-quality-gates-slice-005a-report.md`

## 6. Slice 006 — Patient Tag HTTP Contracts

- [x] 6.1 Remove lifecycle redirects from tag HTTP/error tests
- [x] 6.2 Align UUID parameters and response contracts with current routes
- [x] 6.3 Preserve permission and error-format assertions
- [x] 6.4 Make the tag HTTP cohort green
- [x] 6.5 Create `/tmp/restore-green-development-quality-gates-slice-006-report.md`

## 6A. Reslice 006A — Repair Tag-Add Http404 and Malformed Tag-Id

- [x] 6A.1 Capture the malformed tag-id body RED alongside the three 404 REDs
- [x] 6A.2 Restore domain 404 by resolving AllowedTag outside the broad except
- [x] 6A.3 Return domain 400 for non-integer tag-id body values
- [x] 6A.4 Make all tag modules and supporting gates green
- [x] 6A.5 Create
      `/tmp/restore-green-development-quality-gates-slice-006a-report.md`

## 7. Slice 007 — Patient Tag Architecture and Integration Contracts

- [x] 7.1 Align stale tag relations with the current patient-tag architecture
- [x] 7.2 Resolve integration/form contract drift without weakening assertions
- [x] 7.3 Make the tag architecture cohort green
- [x] 7.4 Create `/tmp/restore-green-development-quality-gates-slice-007-report.md`

## 8. Slice 008 — Patient Admission, Status, and Soft-Delete Contracts

- [x] 8.1 Resolve admission edit-window and message/redirect contracts
- [x] 8.2 Resolve status action and template contract drift
- [x] 8.3 Resolve patient soft-delete failures against canonical behavior
- [x] 8.4 Make the listed workflow modules green
- [x] 8.5 Create `/tmp/restore-green-development-quality-gates-slice-008-report.md`

## 9. Slice 009 — Entire Patients App Green

- [x] 9.1 Run `./scripts/test.sh apps.patients`
- [x] 9.2 Classify and fix only residual patients failures in approved files
- [x] 9.3 Obtain exit code 0 with zero failures/errors
- [x] 9.4 Re-run patient-focused static and migration gates
- [x] 9.5 Create `/tmp/restore-green-development-quality-gates-slice-009-report.md`

## 9A. Reslice 009A — Patients Static Closure for CI Gates

- [x] 9A.1 Fix Category B/C ruff findings in changed files using permitted classes
- [x] 9A.2 Add the two documented per-file-ignores and the mypy module override
- [x] 9A.3 Format the changed-but-unformatted files
- [x] 9A.4 Make all three CI-equivalent gates exit 0 with suites unchanged
- [x] 9A.5 Create `/tmp/restore-green-development-quality-gates-slice-009a-report.md`

## 10. Slice 010 — Drug Templates Cohort

- [x] 10.1 Restore drug-template model/form/source-tracking tests
- [x] 10.2 Restore drug-template access/view/admin/import tests
- [x] 10.3 Make the entire `drugtemplates` app suite green
- [x] 10.4 Create `/tmp/restore-green-development-quality-gates-slice-010-report.md`

## 11. Slice 011 — Outpatient Prescriptions Cohort

- [x] 11.1 Restore prescription model/form/search tests
- [x] 11.2 Restore prescription view/permission/integration tests
- [x] 11.3 Make the entire `outpatientprescriptions` app suite green
- [x] 11.4 Create `/tmp/restore-green-development-quality-gates-slice-011-report.md`

## 12. Slice 012 — Mediafiles Model, Form, and Security Foundations

- [x] 12.1 Restore supported Hospital, Patient, Photo, and media fixtures
- [x] 12.2 Align model/form tests with current media contracts
- [x] 12.3 Preserve security and validator assertions
- [x] 12.4 Make the listed foundation modules green
- [x] 12.5 Create `/tmp/restore-green-development-quality-gates-slice-012-report.md`

## 13. Slice 013 — Mediafiles HTTP, Integration, and Performance

- [x] 13.1 Restore view, template, and integration fixtures/contracts
- [x] 13.2 Restore performance and UAT scenarios without weakening thresholds
- [x] 13.3 Make the entire mediafiles app suite green
- [x] 13.4 Create `/tmp/restore-green-development-quality-gates-slice-013-report.md`

## 14. Slice 014 — PDF Forms Domain Foundations

- [x] 14.1 Restore model validation and form-data contracts
- [x] 14.2 Restore service, field-mapping, and linked-field contracts
- [x] 14.3 Make all listed PDF domain modules green
- [x] 14.4 Create `/tmp/restore-green-development-quality-gates-slice-014-report.md`

## 15. Slice 015 — PDF Forms Admin, HTTP, and Security

- [x] 15.1 Restore admin, command, URL, and national-form tests
- [x] 15.2 Restore view, permission, security, and template-tag contracts
- [x] 15.3 Make the entire `pdf_forms` app suite green
- [x] 15.4 Create `/tmp/restore-green-development-quality-gates-slice-015-report.md`

## 16. Slice 016 — Events and History-and-Physicals Cohorts

- [x] 16.1 Restore events soft-delete tests
- [x] 16.2 Restore history-and-physicals fixtures and permissions
- [x] 16.3 Make both complete app suites green
- [x] 16.4 Create `/tmp/restore-green-development-quality-gates-slice-016-report.md`

## 17. Slice 017 — Matrix, PDF Generator, and Sample Content

- [x] 17.1 Restore Matrix configuration and provisioning tests
- [x] 17.2 Restore PDF generator escaping/table tests
- [x] 17.3 Restore sample-content lifecycle/permission tests
- [x] 17.4 Make all three app suites green
- [x] 17.5 Create `/tmp/restore-green-development-quality-gates-slice-017-report.md`

## 18. Slice 018 — Enforce and Close the Full Green Baseline

- [x] 18.1 Set the lifecycle guard rail to zero unapproved violations
      (slice 018C: 168→0, `max_allowed=0`, negative synthetic test; see
      `/tmp/restore-green-development-quality-gates-slice-018c-report.md`)
- [x] 18.2 Run all static, lock, migration, and app gates with exit code 0
- [x] 18.3 Run `./scripts/test.sh` with zero failures/errors
- [x] 18.4 Re-run and verify patient-identity slice 001 without waivers
- [x] 18.5 Create `/tmp/restore-green-development-quality-gates-slice-018-report.md`

## 19. Release and Resume Gate

- [x] 19.1 Verify all twenty-three reports with a third LLM
      (all slice reports 001-018C verified cumulatively by the third LLM,
      including the 018A/018B/018C reslices and correction 018B-fix1)
- [x] 19.2 Confirm no real patient data appears in artifacts or reports
      (aggregate counts and synthetic fixtures only across all reports)
- [x] 19.3 Accept or supersede ADR-0001 after implementation evidence
      (ADR-0001 accepted 2026-08-29: lock/runtime parity, fail-closed
      tooling, guard rail enforced at zero, CI full-suite blocking)
- [x] 19.4 Mark patient-identity tasks 1.1-1.5 only after its gates pass
      (gates re-verified green 2026-08-29 in slice 018C R4; marked by the
      third LLM)
- [x] 19.5 Obtain explicit planner approval before starting identity
      slice 002 (approval granted 2026-08-29: slice 002 may start)
