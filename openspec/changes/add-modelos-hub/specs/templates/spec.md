## ADDED Requirements

### Requirement: Templates hub navigation

The system SHALL provide a "Modelos" hub page that serves as the entry point to all template categories.

#### Scenario: Access hub from sidebar

- **WHEN** a doctor or resident opens the main sidebar
- **THEN** a "Modelos" navigation link is visible
- **AND** selecting it opens the Modelos hub page

#### Scenario: Hub lists template categories

- **WHEN** a doctor or resident opens the Modelos hub
- **THEN** the page lists available template categories
- **AND** provides links to drug templates and prescription templates

### Requirement: Template access restrictions

The system SHALL restrict access to template-related pages to doctors and residents only.

#### Scenario: Doctor or resident accesses templates

- **WHEN** a doctor or resident visits any template page
- **THEN** access is granted

#### Scenario: Non-privileged user blocked

- **WHEN** a non-doctor/non-resident user attempts to access any template page
- **THEN** the request is rejected with a forbidden response
