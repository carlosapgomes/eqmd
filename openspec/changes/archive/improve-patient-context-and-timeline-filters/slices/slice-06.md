# Slice 06 - Desktop filter trigger and offcanvas shell in timeline

## Goal

Add a desktop filter trigger and offcanvas shell to the patient timeline without
moving the existing desktop filter form yet.

## Scope boundaries

- Included: desktop trigger UI, offcanvas shell markup, focused timeline filter
  UI tests.
- Excluded: moving filter form content, removing the desktop sidebar, active
  filter indicator refinements, mobile filter redesign.

## Files to create/modify

- `apps/events/templates/events/patient_timeline.html`
- `apps/patients/tests/test_patient_timeline_filter_ui.py`

## Tests to write FIRST (TDD)

- `test_timeline_desktop_header_shows_filter_trigger`
- `test_timeline_renders_desktop_filter_offcanvas_shell`

## Implementation steps

1. Add a desktop-visible filter trigger near the timeline header actions.
2. Add an offcanvas shell with a stable ID and accessible labels.
3. Keep the existing desktop sidebar filters unchanged in this slice.
4. Keep the current mobile collapse filters unchanged.

## Refactor steps

- Use stable IDs and labels that later slices can reuse.
- Keep the new offcanvas shell free of duplicated filter form markup for now.

## Verification commands

- `./scripts/test.sh apps.patients.tests.test_patient_timeline_filter_ui`
