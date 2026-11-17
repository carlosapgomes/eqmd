# Patient tag filter rendering delta

## ADDED Requirements

### Requirement: Cache-safe first-load tag filter rendering

Tag-option lookup SHALL display its returned selectable rows on first entry
independently of previously visited pages and cached older static assets.
The option panel SHALL align directly below the search input. Search, mode
and action controls SHALL remain readable and usable at desktop/mobile widths
without changing explicit Apply or filter semantics.

#### Scenario: Legacy assets cannot hide found rows

- **GIVEN** a browser previously cached the legacy selector URL
- **WHEN** the updated patient list or map loads and a tag name is searched
- **THEN** current versioned assets display clickable matching rows immediately
- **AND** no visit to another page is necessary.

#### Scenario: Responsive filter controls

- **WHEN** filters render at 1440, 390 or 320 CSS pixels viewport width
- **THEN** labels, mode and Apply remain visible without horizontal overflow
- **AND** opening options does not grow the filter card.
