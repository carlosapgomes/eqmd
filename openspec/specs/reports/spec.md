# Reports

## Purpose

Define behavior for generic report templates and patient reports, including
creation, permissions, and PDF output.

## Requirements

### Requirement: Manage report templates

The system SHALL allow authorized users (admin/staff, doctors, residents) to
create, update, and view report templates.

#### Scenario: Authorized template creation

- **WHEN** an admin/staff, doctor, or resident submits a new report template
- **THEN** the system saves the template and attributes it to the creator

#### Scenario: Unauthorized template creation blocked

- **WHEN** a user who is not admin/staff, doctor, or resident attempts to create
  a report template
- **THEN** the system denies the action

### Requirement: Template visibility rules

The system SHALL show public templates to all authenticated users and private
templates only to their creator.

#### Scenario: Public template visible

- **WHEN** an authenticated user lists report templates
- **THEN** the system includes templates marked as public

#### Scenario: Private template hidden

- **WHEN** an authenticated user lists report templates
- **THEN** the system excludes private templates created by other users

### Requirement: Strict placeholder validation

The system SHALL validate template placeholders against an allowlist and require
the `patient_name` placeholder.

#### Scenario: Unknown placeholder rejected

- **WHEN** a template contains a placeholder not in the allowlist
- **THEN** the system rejects the template with a validation error

#### Scenario: Missing required placeholders rejected

- **WHEN** a template omits `patient_name`
- **THEN** the system rejects the template with a validation error

### Requirement: Create reports from templates

The system SHALL allow users to create reports from templates, render
placeholders server-side, and allow editing of the resulting markdown before
saving.

#### Scenario: Template-based report creation

- **WHEN** a user selects a template and submits report creation
- **THEN** the system renders placeholders into markdown and saves the report
  content

#### Scenario: Manual report creation without template

- **WHEN** a user submits report content without selecting a template
- **THEN** the system saves the report content as provided

### Requirement: Report event behavior

Reports SHALL be stored as Event subtypes with event type `REPORT_EVENT` and
follow the 24-hour edit/delete window by creator.

#### Scenario: Report edit within window

- **WHEN** the report creator edits a report within 24 hours of creation
- **THEN** the system allows the update

#### Scenario: Report edit after window denied

- **WHEN** the report creator attempts to edit a report after 24 hours
- **THEN** the system denies the update

### Requirement: PDF generation with letterhead and signature

The system SHALL generate report PDFs with hospital letterhead, support page
breaks, and include a signature section.

#### Scenario: PDF download available

- **WHEN** an authorized user requests a report PDF
- **THEN** the system returns a PDF with letterhead, page breaks, and signature
  section

### Requirement: No report attachments

The system SHALL NOT support attachments for reports.

#### Scenario: Attachments not available

- **WHEN** a user views a report
- **THEN** the system does not provide attachment upload or listing

### Requirement: Report duplication

The system SHALL provide a duplicate action that creates a new report
from an existing report of the same patient, pre-filling the editable
creation form with the source title and content.

#### Scenario: Duplicate form pre-filled from source

- **WHEN** an authorized user opens the duplicate action for a report
- **THEN** the system renders the report creation form with the source
  report's title and content, and today's document date

#### Scenario: Duplicate creates an independent copy

- **WHEN** an authorized user submits the duplicate form
- **THEN** the system creates a new report for the same patient,
  attributed to the submitting user, with a fresh event datetime
- **AND** the new report is editable within its own 24-hour window
- **AND** the system redirects to the patient timeline

#### Scenario: Source report unchanged

- **WHEN** a duplicate is created
- **THEN** the source report's content, title, author, and event
  datetime remain unchanged

#### Scenario: Template provenance not copied

- **WHEN** the source report was created from a template
- **AND** a duplicate is created from it
- **THEN** the duplicate is saved without a template association and
  its content is the source's stored content (no template re-render)

#### Scenario: Unauthorized duplication denied

- **WHEN** a user without `events.add_event` or without access to the
  patient opens or submits the duplicate action
- **THEN** the system denies the request

#### Scenario: Duplicate action on the timeline card

- **WHEN** a user with `events.add_event` views a report event on the
  patient timeline
- **THEN** the report card exposes a duplicate action linking to the
  duplicate form
- **AND** users without the permission do not see the action
