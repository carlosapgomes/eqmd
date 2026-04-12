## Why

The patient timeline currently requires users to leave the page or scan multiple
screens to recover basic patient context such as record number, age, status,
and, when relevant, the patient's current ward and bed. In parallel, the
desktop filter sidebar keeps a large set of timeline filters visible at all
times, even though filtering is not part of every access path. This creates
unnecessary visual noise and reduces available space for the clinical event
list.

The project also already contains duplicated, inconsistent "compact patient
info" blocks across multiple patient-related detail pages. Without a canonical
component, future UI work will continue to copy and diverge.

## What Changes

- Introduce a reusable patient context UI component for patient-centric pages.
- Define a canonical compact summary with name, record number, age, and status
  for all patients.
- Show ward and bed in the compact summary only when the patient has an active
  admission.
- Phase 1: adopt the component first in the patient timeline, then in selected
  patient event detail pages.
- Add optional expanded details for birth date, gender, and, when the patient
  has an active admission, admission date and admission duration.
- Phase 2: move timeline filters to an on-demand offcanvas panel and remove the
  fixed desktop filter sidebar.
- Preserve current filter behavior and querystring semantics.
- Do not change breadcrumb behavior in this initiative.

## Non-Goals

- Enrich breadcrumbs with patient metadata.
- Redesign the patient detail page as part of this change.
- Change patient permissions, event permissions, or filter rules.
- Refactor every patient-related template in one pass.

## Impact

- Affected specs:
  - `patient-context-ui`
  - `patient-timeline`
- Affected code areas:
  - `templates/components/`
  - `apps/events/templates/events/patient_timeline.html`
  - patient event detail templates in `dailynotes`, `simplenotes`, and
    `historyandphysicals`
  - targeted template/view tests for the timeline and adopted detail pages
- No schema or migration changes are expected.
