# Proposal: extend document duplication

## Why

A timeline audit (2026-11-02) mapped which patient-timeline document types
support duplication (create a new editable document from an existing one,
landing on a pre-filled editing surface). Findings:

- Outpatient prescriptions have a complete duplicate flow (change
  `2026-10-12-duplicate-outpatient-prescription`), but the action is only
  reachable from the detail page; the timeline card offers no duplicate
  action, so the feature is invisible where clinicians browse history.
- Reports (`apps/reports`) have no duplication at all; recurring report
  content must be retyped or copied as plain text via clipboard.
- The three text-document duplication flows (daily note, simple note,
  history and physical) lack POST-level regression coverage. Daily
  notes: GET/permission tests only. Simple notes: no duplication tests
  at all. History and physical: one basic POST test (302 + row count)
  asserting none of the copy-independence guarantees (creator
  attribution, fresh event datetime, source untouched, redirect target).
- URL namespaces are inconsistent for the three text apps: the URLconfs
  declare `app_name = "apps.dailynotes"` (and siblings) while
  `config/urls.py` mounts them as `namespace="dailynotes"`. Both the long
  (`apps.dailynotes:*`, ~30 references) and short (`dailynotes:*`,
  hundreds of references) spellings resolve today, but the divergence is
  fragile under refactoring or remounting.

## What Changes

1. **Report duplication**: new `ReportDuplicateView` following the
   established text-document pattern (GET renders a pre-filled creation
   form; POST creates an independent report), plus a duplicate action on
   the timeline report card.
2. **Prescription duplicate action on the timeline card**: POST form on
   `event_card_prescription.html` that hits the existing
   `outpatientprescriptions:outpatientprescription_duplicate` endpoint and
   lands on the copy's edit view.
3. **Duplication regression coverage**: POST-creates-an-independent-copy
   tests for the three text apps (daily note, simple note, history and
   physical), filling the gaps found by the audit.
4. **URL namespace consistency**: standardize the three text apps on the
   short namespace (`dailynotes`, `simplenotes`, `historyandphysicals`)
   by fixing `app_name` and rewriting the remaining long-form references.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `reports`: adds the report duplication requirement.
- `outpatientprescriptions`: adds duplicate-action availability on the
  patient timeline card.

## Non-goals

- **Discharge report duplication is deliberately excluded.** The active
  change `harden-discharge-report-collaborative-draft` (in flight in a
  separate worktree) redefines the discharge-report edit/finalization
  semantics and restructures `apps/dischargereports` and its timeline
  dispatch. Discharge report duplication will be designed in a follow-up
  change written against the post-hardening semantics.
- No changes to PDF form duplication (opt-in `allow_duplication` flow).
- No per-document-type or per-template opt-in flags for the new
  duplication flows (see `design.md`, Decision A).
- No cross-patient duplication; no `duplicated_from` audit linkage.
- No change to create/update/delete/print/PDF behavior of any app.
- Namespace prefixes with a long `app_name` in other apps
  (`apps.patients`, `apps.dischargereports`, `apps.accounts`,
  `apps.research` — same divergence, left for a separate cleanup if
  ever needed).

## Risks

- The in-flight `harden-discharge-report-collaborative-draft` worktree
  shows uncommitted modifications to
  `apps/events/templates/events/patient_timeline.html` (its plan names
  `apps/events/views.py` and forbids card markup changes, so the overlap
  may be incidental — re-verify against the real diff). The namespace
  slice that touches this file is ordered last and must re-verify the
  shared file against the then-current base.
- Report edit window: `Report.can_be_edited` anchors the 24h window at
  `event_datetime`, so a duplicate starts with a fresh window. This is
  the established behavior of every other duplication flow and is
  accepted by design.
- Prescription duplicate POST is not idempotent (double submit creates
  two drafts). Identical to the existing detail-page behavior; keeping
  consistency instead of adding confirmation friction.
