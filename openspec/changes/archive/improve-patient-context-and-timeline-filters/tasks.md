## Phase 1 - Reusable patient context component

- [x] 1.1 Add OpenSpec artifacts for reusable patient context and timeline UI
- [x] 1.2 Slice 01: introduce canonical compact patient context component in the timeline
- [x] 1.3 Review Slice 01 implementation report, changed files, and test evidence before approving Slice 02
- [x] 1.4 Slice 02: add optional expanded patient details in the timeline summary
- [x] 1.5 Review Slice 02 implementation report before approving detail-page adoption
- [x] 1.6 Slice 03: adopt the shared patient context component in `dailynote_detail`
- [x] 1.7 Review Slice 03 implementation report before approving Slice 04
- [x] 1.8 Slice 04: adopt the shared patient context component in `simplenote_detail`
- [x] 1.9 Review Slice 04 implementation report before approving Slice 05
- [x] 1.10 Slice 05: adopt the shared patient context component in `historyandphysical_detail`
- [x] 1.11 Review Slice 05 implementation report and phase-1 consistency before starting Phase 2

## Phase 2 - Timeline filters on demand

- [x] 2.1 Slice 06: add desktop filter trigger and offcanvas shell to the timeline
- [x] 2.2 Review Slice 06 implementation report before moving filter content
- [x] 2.3 Slice 07: move the existing desktop filter form into a shared
      partial rendered inside the offcanvas without changing filter semantics
- [x] 2.4 Review Slice 07 implementation report before removing the old sidebar
- [x] 2.5 Slice 08: remove the fixed desktop filter sidebar and widen the timeline event column
- [x] 2.6 Review Slice 08 implementation report before adding active-filter state refinements
- [x] 2.7 Slice 09: add active-filter indicator to the desktop trigger and preserve clear-filter flow
- [x] 2.8 Review Slice 09 implementation report and phase-2 consistency

## Verification notes

- Each slice must be implemented one at a time with TDD.
- The implementer must read `AGENTS.md` -> OpenSpec spec/design -> current slice.
- Only files listed in the slice may be touched, plus minimal context files.
- Use `./scripts/test.sh <target>` for slice verification.
- Before the next slice is approved, the implementer must hand back an
  implementation report with changed files, tests written, verification command
  results, blockers, and explicit out-of-scope confirmation.
- No breadcrumb work is included in this change.
