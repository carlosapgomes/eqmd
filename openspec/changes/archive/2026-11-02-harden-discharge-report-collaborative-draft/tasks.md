# Tasks: harden discharge report collaborative draft

Order: S1 and S2 are independent and may run in
any order; S3 runs after S1.

## 1. Slice 001 — single predicate and timeline dispatch

- [x] 1.1 Move the edit/delete predicates to
      `apps/dischargereports/services/permissions.py`
      with model/view delegation and re-exports, per
      `slices/slice-001-single-predicate-timeline-dispatch.md`.
- [x] 1.2 TDD: type-dispatched timeline bulk check
      (edit + delete), three-door equivalence,
      explicit update actions. RED → GREEN →
      REFACTOR; focused suites green.
- [x] 1.3 Full suite green; no new findings.

Contract: `slices/slice-001-single-predicate-timeline-dispatch.md`

## 2. Slice 002 — clinical identity guardrails

- [x] 2.1 Admin `profession_type` requirement with
      superuser/User-Manager exemptions, per
      `slices/slice-002-clinical-identity-guardrails.md`.
- [x] 2.2 TDD: read-only `audit_clinical_identity`
      command and `setup_groups` reconciliation
      lock-in. RED → GREEN → REFACTOR.
- [x] 2.3 Full suite green; no new findings.

Contract: `slices/slice-002-clinical-identity-guardrails.md`

## 3. Slice 003 — finalization window anchoring

- [x] 3.1 Migration adding `finalized_at` /
      `finalized_by` with a behavior-preserving
      backfill, per
      `slices/slice-003-finalization-window-anchoring.md`.
- [x] 3.2 TDD: anchor switch in the service
      predicate, flip/revert bookkeeping, display,
      delete lock-in. RED → GREEN → REFACTOR.
- [x] 3.3 Full suite green; no new findings.

Contract:
`slices/slice-003-finalization-window-anchoring.md`
