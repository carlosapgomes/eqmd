# Slice 02 - Expandable patient details in timeline summary

## Goal

Add optional expanded patient details to the shared patient context component and
expose that behavior in the patient timeline, with admission-specific extended
fields shown only for active admissions.

## Scope boundaries

- Included: shared component expansion behavior, timeline integration,
  incremental timeline UI tests.
- Excluded: detail-page adoption, timeline filter changes.

## Files to create/modify

- `templates/components/_patient_context_summary.html`
- `apps/events/templates/events/patient_timeline.html`
- `apps/patients/tests/test_patient_timeline_context_summary.py`

## Tests to write FIRST (TDD)

- `test_timeline_summary_renders_expand_control_for_extended_details`
- `test_timeline_summary_extended_details_include_birthday_and_gender`
- `test_timeline_summary_extended_details_include_admission_date_and_duration_for_active_admission`
- `test_timeline_summary_extended_details_omit_admission_fields_without_active_admission`

## Implementation steps

1. Extend the shared component with an optional expandable details region.
2. Pass explicit toggle/collapse identifiers from the timeline template.
3. Render birth date and gender on demand while keeping the compact row always
   visible.
4. Render admission date and admission duration only when the patient has an
   active admission.

## Refactor steps

- Keep the shared component API narrow and explicit.
- Keep admission-specific extended fields conditional on active admission.
- Avoid timeline-specific labels leaking into the shared component.

## Verification commands

- `./scripts/test.sh apps.patients.tests.test_patient_timeline_context_summary`
