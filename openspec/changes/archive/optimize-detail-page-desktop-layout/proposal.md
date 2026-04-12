# Proposal - Optimize detail page desktop layout

## Why

The current desktop layout for patient event detail pages uses a narrow sidebar for
patient context and page-specific metadata. In practice this causes the summary
cards to look compressed, consume more vertical space than necessary, and feel
visually misaligned with the full-width content card below.

## What changes

- Replace the desktop sidebar pattern with stacked full-width top cards.
- Keep the shared patient context component.
- Keep page-specific metadata outside the shared component.
- Keep mobile behavior unchanged.
- Roll out the layout adjustment in small slices:
  1. `dailynote_detail`
  2. `simplenote_detail`
  3. `historyandphysical_detail`

## Expected outcome

On desktop, each detail page should render:

1. a full-width patient context summary bar
2. a full-width metadata bar for the current event
3. the full-width content card below

This should reduce visual crowding and improve alignment across the detail view.
