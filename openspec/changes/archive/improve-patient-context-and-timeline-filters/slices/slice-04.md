# Slice 04 - Adopt shared patient context in simple note detail

## Goal

Replace the simple note detail page's duplicated mobile and desktop patient
context field blocks with the shared patient context component.

## Scope boundaries

- Included: simple note detail template adoption, focused simple note detail UI
  tests, minimal shared component adjustments if required.
- Excluded: history and physical adoption, timeline filter work.

## Files to create/modify

- `templates/components/_patient_context_summary.html` (only if needed for
  consumer-safe reuse)
- `apps/simplenotes/templates/simplenotes/simplenote_detail.html`
- `apps/simplenotes/tests/test_detail_context_ui.py`

## Tests to write FIRST (TDD)

- `test_simplenote_detail_uses_shared_patient_context_component`
- `test_simplenote_detail_keeps_event_actions_and_datetime_visible`

## Implementation steps

1. Replace the duplicated mobile and desktop patient context blocks in
   `simplenote_detail.html` with the shared component include.
2. Preserve the current mobile/desktop layout structure while centralizing the
   patient context rendering through the shared component.
3. Keep simple note-specific metadata such as event date/time and actions in
   the page-level wrapper.
4. Make only minimal markup adjustments required to preserve the page layout.

## Refactor steps

- Keep page-specific content outside the shared component.
- Avoid changing unrelated simple note detail behavior.
- Do not leave one of the old mobile/desktop patient context blocks behind.

## Verification commands

- `./scripts/test.sh apps.simplenotes.tests.test_detail_context_ui`
