# PDF forms — delta

## ADDED Requirements

### Requirement: Authenticated PDF template preview

The system SHALL serve blank PDF form templates through an
authenticated preview view that works regardless of `DEBUG`,
instead of linking raw `/media/...` URLs.

#### Scenario: Authenticated user previews a template

- **WHEN** an authenticated user requests the preview route
  for a template with a file on disk
- **THEN** the system returns the PDF bytes with
  `Content-Type: application/pdf` and an inline
  `Content-Disposition`
- **AND** the response is privately cacheable only

#### Scenario: Preview requires authentication

- **WHEN** an anonymous user requests the preview route
- **THEN** the system redirects to login

#### Scenario: Missing file on disk is a 404

- **WHEN** the preview route is requested for a template
  whose file is absent from storage
- **THEN** the system returns 404

#### Scenario: Unknown template is a 404

- **WHEN** the preview route is requested with an unknown
  template id
- **THEN** the system returns 404

#### Scenario: Inactive templates preview too

- **WHEN** an authenticated user requests the preview route
  for an inactive template
- **THEN** the system returns the PDF (the list filters
  actives; staff preview from the admin must still work)

#### Scenario: Admin links to the preview route

- **WHEN** staff views a template in the Django admin
- **THEN** the "View PDF" link points to the preview route,
  not to the raw media URL

#### Scenario: Admin change-form widget links the preview route

- **WHEN** staff opens a template change form with an
  uploaded file
- **THEN** the existing-file widget link points to the
  preview route, not to the raw media URL

#### Scenario: Template list links to the preview route

- **WHEN** a user opens the PDF template list
- **THEN** the "Ver PDF" button points to the preview route,
  not to the raw media URL
