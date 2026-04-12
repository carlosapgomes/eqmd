# Slice 08 - Remove desktop filter sidebar and widen timeline content

## Goal

Remove the fixed desktop filter sidebar and expand the desktop timeline event
column after the offcanvas filter content is in place.

## Scope boundaries

- Included: removal of desktop sidebar filter panel, timeline layout update,
  focused timeline filter UI tests.
- Excluded: active-filter indicator refinements, mobile filter redesign,
  backend filter behavior changes.

## Files to create/modify

- `apps/events/templates/events/patient_timeline.html`
- `apps/patients/tests/test_patient_timeline_filter_ui.py`

## Tests to write FIRST (TDD)

- `test_timeline_desktop_no_longer_renders_fixed_filter_sidebar`
- `test_timeline_desktop_event_column_uses_full_width_without_sidebar`

## Implementation steps

1. Remove the fixed desktop filter sidebar markup.
2. Update the desktop content column so the event list uses the freed width.
3. Keep the desktop offcanvas trigger and offcanvas content working.
4. Keep current mobile filter behavior unchanged.

## Refactor steps

- Remove only sidebar-specific desktop filter markup.
- Keep the event list structure unchanged outside layout width adjustments.

## Verification commands

- `./scripts/test.sh apps.patients.tests.test_patient_timeline_filter_ui`
