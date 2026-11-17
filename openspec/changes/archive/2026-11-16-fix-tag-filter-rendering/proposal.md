# Fix tag filter rendering regressions

## Why

Patient list, ward map and report discovery have cramped filter cards, invisible
tag options with cached legacy assets, and raw developer comments in report HTML.

## What Changes

- Use content-versioned URLs for the shared stylesheet and tag-filter scripts,
  so cached pre-panel JavaScript cannot hide the new result container.
- Anchor tag results directly below the input and use responsive, spacious
  filter rows with a separate action area.
- Replace invalid multiline inline Django comments with block comments.
- Add rendered-template, asset-version and real-browser regression evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `patient-tag-filtering`: reliable first-load options and responsive controls.
- `reports`: the same reliable discovery and comment-free rendered markup.

## Impact

Presentation and static delivery only, including report creation's shared
component. No schema, permissions, query semantics, preference changes or
change to explicit Apply. One corrective vertical slice.
