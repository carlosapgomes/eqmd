# Slice 07 - Move desktop filter form into shared offcanvas content

## Goal

Move the existing desktop filter form into a reusable partial rendered inside
the desktop offcanvas, without changing filter semantics yet.

## Scope boundaries

- Included: reusable filter form partial, desktop offcanvas filter content,
  focused timeline filter UI tests.
- Excluded: removing the old desktop sidebar, widening the event column,
  active-filter indicator refinements, mobile filter redesign.

## Files to create/modify

- `apps/events/templates/events/patient_timeline.html`
- `templates/components/_timeline_filter_form.html`
- `apps/patients/tests/test_patient_timeline_filter_ui.py`

## Tests to write FIRST (TDD)

- `test_timeline_offcanvas_renders_filter_form_fields`
- `test_timeline_offcanvas_preserves_filter_query_values`

## Implementation steps

1. Extract the desktop filter form markup into a reusable partial.
2. Render that partial inside the desktop offcanvas shell.
3. Keep existing filter names, form method, and query semantics unchanged.
4. Leave the old desktop sidebar in place for this slice.

## Refactor steps

- Keep one canonical desktop filter form partial for the offcanvas content.
- Avoid changing backend filter behavior or field names.

## Verification commands

- `./scripts/test.sh apps.patients.tests.test_patient_timeline_filter_ui`
