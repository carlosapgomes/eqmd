# Slice 09 - Active-filter indicator and clear-filter flow on desktop trigger

## Goal

Add active-filter state to the desktop filter trigger and preserve clear-filter
flow after the desktop sidebar has been removed.

## Scope boundaries

- Included: desktop trigger active state, focused timeline filter UI tests.
- Excluded: mobile filter redesign, backend filter behavior changes, broader
  timeline UI refactors.

## Files to create/modify

- `apps/events/templates/events/patient_timeline.html`
- `apps/patients/tests/test_patient_timeline_filter_ui.py`

## Tests to write FIRST (TDD)

- `test_timeline_desktop_filter_trigger_shows_active_state_when_filters_present`
- `test_timeline_desktop_offcanvas_keeps_clear_filter_flow`

## Implementation steps

1. Add an active-filter indicator to the desktop trigger when any timeline
   filters are active.
2. Preserve or expose the clear-filter flow in the offcanvas context.
3. Keep current filter semantics unchanged.
4. Keep current mobile filter behavior unchanged.

## Refactor steps

- Reuse existing filter-state conditions where possible.
- Avoid introducing new backend logic for filter detection.

## Verification commands

- `./scripts/test.sh apps.patients.tests.test_patient_timeline_filter_ui`
