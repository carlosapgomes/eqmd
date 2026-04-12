# Design - Optimize detail page desktop layout

## Decision

For desktop detail pages, replace the two-column sidebar layout with stacked,
full-width cards above the main content card.

## Non-goals

- No changes to mobile layout or behavior.
- No changes to the shared component contract in
  `templates/components/_patient_context_summary.html`.
- No changes to event content rendering logic.
- No breadcrumb or action-bar redesign.

## Desktop structure

Each adopted detail page should follow this desktop structure:

1. shared patient context summary card
2. page-specific metadata card
3. main content card

All three blocks should use the same content width as the page body rather than a
fixed-width sidebar.

## Reuse rules

- Reuse `templates/components/_patient_context_summary.html` as-is unless a later
  slice proves a component-level spacing tweak is necessary.
- Keep note-specific or H&P-specific metadata in the page template.
- Prefer simple Bootstrap rows and columns inside the metadata card so data can
  flow horizontally on desktop and wrap naturally as needed.

## Rollout plan

- Slice 01: validate the new desktop pattern in `dailynote_detail`
- Slice 02: adopt the same pattern in `simplenote_detail`
- Slice 03: adopt the same pattern in `historyandphysical_detail`

## Test strategy

Each slice should update the page's focused UI test module to verify:

- the shared patient context component still renders
- the detail page no longer depends on the desktop sidebar layout classes
- key page metadata and actions remain visible
- mobile markup remains untouched by scope
