# Slice 01 - Replace desktop sidebar layout in daily note detail

## Goal

Replace the desktop sidebar layout in `dailynote_detail` with stacked full-width
cards while keeping the mobile layout unchanged.

## Scope boundaries

- Included: desktop layout update for patient context and daily note metadata,
  focused UI tests for `dailynote_detail`.
- Excluded: changes to shared patient context component behavior, changes to
  mobile layout, adoption in `simplenote_detail`, adoption in
  `historyandphysical_detail`.

## Files to create/modify

- `apps/dailynotes/templates/dailynotes/dailynote_detail.html`
- `apps/dailynotes/tests/test_detail_context_ui.py`

## Tests to write FIRST (TDD)

- `test_dailynote_detail_desktop_no_longer_uses_sidebar_layout`
- `test_dailynote_detail_keeps_shared_context_metadata_and_actions_visible`

## Implementation steps

1. Remove the desktop two-column sidebar layout classes and structure.
2. Render the shared patient context component in a full-width desktop block.
3. Render the daily note metadata card in a full-width desktop block below it.
4. Keep the daily note content card below those blocks.
5. Keep the existing mobile-specific blocks unchanged.

## Refactor steps

- Remove only desktop sidebar-specific CSS and markup that no longer applies.
- Prefer simple full-width stacked blocks over introducing another custom
  layout abstraction.
- Keep page-specific metadata outside the shared component.

## Verification commands

- `./scripts/test.sh apps.dailynotes.tests.test_detail_context_ui`
