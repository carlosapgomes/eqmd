## ADDED Requirements

### Requirement: Patient pages SHALL expose a canonical compact patient context summary

The system SHALL provide a reusable patient context summary component for
adopted patient-centered pages, with the same canonical core fields visible in
compact form.

#### Scenario: Timeline shows canonical compact patient context

- **WHEN** an authorized user opens a patient timeline page
- **THEN** the page shows a compact patient context summary with the patient's
  name, current record number, age, and status

#### Scenario: Compact summary includes ward and bed only for active admission

- **WHEN** the patient has an active admission
- **THEN** the compact summary also shows the current ward and bed

#### Scenario: Compact summary hides ward and bed without active admission

- **WHEN** the patient has no active admission
- **THEN** the compact summary does not show ward or bed fields

#### Scenario: Missing record number is handled safely

- **WHEN** the patient has no current record number
- **THEN** the compact summary still renders with a safe placeholder and
  without breaking layout

### Requirement: Patient context summary SHALL support optional expanded details

The reusable patient context summary SHALL support an optional expanded details
section for adopted pages that need richer patient context without permanent UI
noise.

#### Scenario: Expanded details are available on demand

- **WHEN** an adopted page enables extended details for the patient context
- **THEN** the user can expand the summary to see additional patient context,
  including birth date and gender

#### Scenario: Admission-specific extended details are conditional

- **WHEN** the patient has an active admission and an adopted page enables
  extended details
- **THEN** the expanded section includes admission date and admission duration

#### Scenario: Admission-specific extended details are omitted without active admission

- **WHEN** the patient has no active admission and an adopted page enables
  extended details
- **THEN** the expanded section omits admission date and admission duration

### Requirement: Adopted patient event detail pages SHALL reuse the same context component

Patient event detail pages that adopt the shared context pattern SHALL reuse the
same canonical patient context component rather than defining page-local field
blocks for core patient context.

#### Scenario: Daily note detail reuses the shared component

- **WHEN** a user views a daily note detail page after adoption
- **THEN** the patient context area is rendered through the shared patient
  context component

#### Scenario: Simple note and history and physical details reuse the shared component

- **WHEN** a user views a simple note or history and physical detail page after
  adoption
- **THEN** each page renders its patient context area through the shared
  patient context component
