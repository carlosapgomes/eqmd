# Spec - Detail page desktop layout

## ADDED Requirements

### Requirement: Desktop detail pages use stacked full-width top cards

Patient event detail pages that adopt this change MUST render desktop summary
and metadata areas as stacked full-width cards above the main content card
instead of using a fixed-width sidebar.

#### Scenario: Daily note desktop view uses full-width top cards

- **GIVEN** the user opens `dailynote_detail` on a desktop viewport
- **WHEN** the page renders the top summary and metadata area
- **THEN** the shared patient context summary is rendered above the content card
- **AND** the daily note metadata card is rendered above the content card
- **AND** the page does not rely on the previous fixed-width sidebar layout

### Requirement: Shared patient context component remains canonical

The reusable patient context summary component MUST remain the canonical shared
UI for patient context on adopted detail pages.

#### Scenario: Daily note desktop view still uses shared patient context summary

- **GIVEN** the user opens `dailynote_detail`
- **WHEN** the patient summary area renders
- **THEN** the page uses `components/_patient_context_summary.html`
- **AND** page-specific metadata remains outside the shared component

### Requirement: Mobile layout remains unchanged

This change MUST NOT alter the mobile-specific layout or behavior of the
adopted detail pages.

#### Scenario: Daily note mobile blocks remain in place

- **GIVEN** the current `dailynote_detail` mobile structure
- **WHEN** Slice 01 is implemented
- **THEN** the mobile patient context block remains intact
- **AND** the mobile metadata block remains intact
