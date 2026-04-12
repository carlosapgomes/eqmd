# Slice 01 - Canonical compact patient context in timeline

## Goal

Introduce the reusable patient context component and render its compact summary
in the patient timeline header with conditional ward and bed display for active
admissions.

## Scope boundaries

- Included: shared patient context component partial, timeline template
  integration, focused timeline UI tests.
- Excluded: expandable details, detail-page adoption, timeline filter changes.

## Files to create/modify

- `templates/components/_patient_context_summary.html`
- `apps/events/templates/events/patient_timeline.html`
- `apps/patients/tests/test_patient_timeline_context_summary.py`

## Tests to write FIRST (TDD)

- `test_timeline_shows_compact_patient_context_summary`
- `test_timeline_summary_shows_ward_and_bed_for_active_admission`
- `test_timeline_summary_hides_ward_and_bed_without_active_admission`
- `test_timeline_summary_handles_missing_record_number`

## Implementation steps

1. Create a reusable Bootstrap partial for the compact patient context summary.
2. Render the partial near the top of `patient_timeline.html` with the patient
   object and active-admission-aware context.
3. Keep the existing title and action buttons intact while adding the compact
   context block.
4. Show name, record number, age, and status for all patients.
5. Show ward and bed only when the patient has an active admission.

## Refactor steps

- Keep the shared component focused on canonical compact fields.
- Keep admission-specific fields conditional on active admission.
- Avoid duplicating patient context markup in the timeline template.

## Verification commands

- `./scripts/test.sh apps.patients.tests.test_patient_timeline_context_summary`
