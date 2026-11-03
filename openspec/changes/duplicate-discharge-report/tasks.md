# Tasks: duplicate-discharge-report

## 1. Discharge report duplication flow

Contract: `slices/slice-001-discharge-report-duplication.md`

- [x] 1.1 Add `DischargeReportDuplicateForm` and
      `DischargeReportDuplicateView` (source-prefilled create; copy
      born draft; `can_access_patient` gate) with the
      `dischargereport_duplicate` route and the
      `dischargereport_duplicate.html` template.
- [x] 1.2 Add the gated duplicate action to
      `event_card_dischargereport.html` (parity with report and
      prescription cards).
- [x] 1.3 Add regression tests: GET prefill (incl. source dates
      winning over admission defaults), POST draft copy, POST
      final-save copy stamps its own finalization, expired-final
      source duplication allowed, source integrity, 403 without
      patient access, 404 unknown source, card gating.
- [x] 1.4 Full suite green (no new failures vs the recorded
      pre-existing baseline).
