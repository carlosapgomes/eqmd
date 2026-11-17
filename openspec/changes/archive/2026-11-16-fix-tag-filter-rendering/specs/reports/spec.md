# Report filter rendering delta

## ADDED Requirements

### Requirement: Clean reliable report discovery presentation

Report catalogue and report-creation filters SHALL render without developer
comment delimiters or comment text. Their tag lookup SHALL expose clickable
matches on first entry with cache-safe assets and an input-anchored panel.
Responsive alignment SHALL preserve existing filter, explicit Apply and
clinical-content isolation behavior.

#### Scenario: Developer comments stay out of the page

- **WHEN** either report discovery surface renders
- **THEN** multiline template comments do not appear as visible page content.

#### Scenario: Independent report first entry

- **GIVEN** legacy static URLs were cached
- **WHEN** a report discovery surface is opened directly and a tag is searched
- **THEN** matching rows are visible without navigating to patient pages
- **AND** filtering does not alter in-progress clinical content.
