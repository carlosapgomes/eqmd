# Slice 05 - Adopt shared patient context in history and physical detail

## Goal

Replace the history and physical detail page's duplicated mobile and desktop
patient context field blocks with the shared patient context component.

## Scope boundaries

- Included: history and physical detail template adoption, focused H&P detail
  UI tests, minimal shared component adjustments if required.
- Excluded: timeline filter work and any broader H&P hardening.

## Files to create/modify

- `templates/components/_patient_context_summary.html` (only if needed for
  consumer-safe reuse)
- `apps/historyandphysicals/templates/historyandphysicals/historyandphysical_detail.html`
- `apps/historyandphysicals/tests/test_detail_context_ui.py`

## Tests to write FIRST (TDD)

- `test_historyandphysical_detail_uses_shared_patient_context_component`
- `test_historyandphysical_detail_keeps_event_actions_and_datetime_visible`

## Implementation steps

1. Replace the duplicated mobile and desktop patient context blocks in
   `historyandphysical_detail.html` with the shared component include.
2. Preserve the current mobile/desktop layout structure while centralizing the
   patient context rendering through the shared component.
3. Keep H&P-specific metadata such as event date/time and actions in the
   page-level wrapper.
4. Make only minimal markup adjustments required to preserve the page layout.

## Refactor steps

- Keep page-specific content outside the shared component.
- Avoid changing unrelated H&P detail behavior.
- Do not leave one of the old mobile/desktop patient context blocks behind.

## Verification commands

- `./scripts/test.sh apps.historyandphysicals.tests.test_detail_context_ui`
