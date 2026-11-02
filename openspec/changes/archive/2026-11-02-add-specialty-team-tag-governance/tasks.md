# Tasks: Specialty team tag governance

Execute one approved slice per run in the sequence below. The shared execution
contract and requirement coverage are in [slices/README.md](slices/README.md).
Do not deploy a partial slice set. S1 is accepted and pending commit.

## 1. Team membership and leadership

Contract: [S1](slices/slice-001-team-membership.md). No predecessor.

- [x] 1.1 Deliver retained active/leader membership and admin grant/revoke;
      verify S1 PostgreSQL preservation and administrator authorization tests.
- [x] 1.2 Enforce current membership on properties/profile/switching API;
      verify specialty regressions and same-session revoke/rejoin scenarios.
- [x] 1.3 Update membership guidance and record S1 evidence; verify focused
      commands and project gates from the slice contract.

## 2. Namespaced catalogue and principal-tag configuration

Contract: [S2](slices/slice-002-catalogue-governance.md). Depends on S1
(accepted).

- [x] 2.1 Add origin/visibility/namespace and reserved-name constraints with
      additive backfill; verify identity-preservation and PostgreSQL collision tests.
- [x] 2.2 Deliver administrator catalogue creation/edit and principal mapping;
      verify same-team/public invariants, immutable creator and permission tests.
- [x] 2.3 Deliver read-only catalogue preflight and current catalogue docs;
      verify old/new-schema preflight cases and S2 evidence report.

## 3. Administrative lifecycle and responsibility transfer

Contract: [S3](slices/slice-003-catalogue-lifecycle.md). Depends on S2
(accepted).

- [x] 3.1 Deliver deactivate/reactivate/archive/restore with latest-action actors
      and full history; verify S3 lifecycle, identity and bulk-bypass tests.
- [x] 3.2 Add current responsibility and administrator transfer without changing
      creator; verify eligible-recipient and former-responsible denial cases.
- [x] 3.3 Document lifecycle/ownership and record S3 evidence; verify focused
      regressions, archived-name reservation and project gates.

## 4. Policy-checked assignment and atomic audit writes

Contract: [S4](slices/slice-004-audited-assignments.md). Depends on S3.

- [x] 4.1 Enforce individual/admin/bulk assignment policy and principal-team
      restrictions; verify S4 actor matrix and unauthorized-association retention.
- [x] 4.2 Persist assignments with stable audit references atomically, including
      conservative legacy backfill; verify rollback, concurrency and migration tests.
- [x] 4.3 Block ordinary tag-audit edit/delete and document audited write paths;
      verify correction-as-new-event tests and S4 evidence report.

## 5. Privacy-safe tag readers and timeline context

Contract: [S5](slices/slice-005-patient-tag-privacy.md). Depends on S4.

- [x] 5.1 Apply current membership/catalogue visibility to every tag reader;
      verify the reader inventory and outsider/revoked-user payload-negative tests.
- [x] 5.2 Deliver historical and mixed-bulk event redaction plus current timeline
      badges; verify full HTML/JSON/print and desktop/mobile fixtures.
- [x] 5.3 Protect existing filter-ID inputs and warm-cache metadata, document
      privacy surfaces and record S5 evidence; verify forged-ID and cache tests.

## 6. Responsible leader self-service

Contract: [S6](slices/slice-006-leader-tag-page.md). Depends on S5.

- [x] 6.1 Add the team page and own-responsibility create/edit/deactivate/reactivate
      actions; verify leadership/responsibility/forged-input request matrix.
- [x] 6.2 Deliver navigation and leader guidance; verify mobile/browser flow,
      no Django Admin escalation and S6 evidence report.

## 7. Searchable multi-tag patient-list filtering

Contract: [S7](slices/slice-007-multi-tag-list-filter.md). Depends on S5.
Execute after S6 in this sequential plan.

- [x] 7.1 Deliver searchable visible/historical lookup and shared ANY/ALL parsing;
      verify paginated lookup, namespace, compatibility and invalid-input tests.
- [x] 7.2 Integrate list results, clear state and repeated-parameter navigation;
      verify distinct/conjunctive query matrix and desktop/mobile flow.
- [x] 7.3 Document list filter contracts and record S7 evidence; verify focused
      regressions, source-asset build and project gates.

## 8. Per-specialty default preferences

Contract: [S8](slices/slice-008-specialty-preferences.md). Depends on S1 and S7.

- [x] 8.1 Persist shared user-specialty tags/mode with absent-vs-empty semantics;
      verify PostgreSQL uniqueness and independent/revoked-membership cases.
- [x] 8.2 Deliver profile preferences and explicit save/clear/reapply precedence;
      verify forged/stale targets, invalid-default warnings and no-GET-save tests.
- [x] 8.3 Document defaults and record S8 evidence; verify account/list browser
      workflows, additive migration tests, asset build and project gates.

## 9. Map parity and release verification

Contract: [S9](slices/slice-009-map-parity-release.md). Depends on S5 and S8.

- [x] 9.1 Reuse shared preferences/filters with live bounded assignment overlay;
      verify warm-cache assignment changes, privacy and ANY/ALL list-map parity.
- [x] 9.2 Recalculate totals and retain state through full/partial/refresh/empty
      ward navigation; verify outpatient-zero and stale-base-data regressions.
- [x] 9.3 Update map/cache guidance and confirm earlier docs against final
      behavior; verify browser scenarios without deferring earlier slice docs here.
- [x] 9.4 Produce S9 release evidence covering all nine reports, full suite,
      scoped lint/types, frontend build, migration drift, Markdown and strict
      OpenSpec validation; record separate production approval still required.
