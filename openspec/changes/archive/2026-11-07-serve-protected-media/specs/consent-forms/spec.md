# Consent forms — delta

## ADDED Requirements

### Requirement: Authenticated consent attachment serving

The system SHALL serve consent-form scan attachments through
an authenticated view enforcing patient access, instead of
linking raw `/media/...` URLs.

#### Scenario: Authorized user views an attachment inline

- **WHEN** a user with `events.view_event` permission and
  patient access requests the serve route for an attachment
- **THEN** the system returns the file bytes with the
  stored MIME type and an inline `Content-Disposition`
  carrying the original filename
- **AND** the response is privately cacheable only

#### Scenario: Missing MIME type falls back safely

- **WHEN** the attachment has no stored MIME type
- **THEN** the system guesses from the file extension,
  defaulting to `application/octet-stream`

#### Scenario: Human-draft scans follow their parent page

- **WHEN** an authorized user requests a scan whose parent
  is a human draft (visible on detail/update pages)
- **THEN** the system returns the file (visibility matches
  the embedding pages)

#### Scenario: Bot-draft and deleted parents stay hidden

- **WHEN** the serve route is requested for an attachment
  whose parent is a bot draft or soft-deleted
- **THEN** the system returns 404

#### Scenario: Missing file on disk is a 404

- **WHEN** the serve route is requested for an attachment
  whose file is absent from storage
- **THEN** the system returns 404 without exposing
  filesystem paths

#### Scenario: No patient access is denied

- **WHEN** a user without access to the attachment's
  patient requests the serve route
- **THEN** the system returns 403

#### Scenario: Missing permission is denied

- **WHEN** a user without `events.view_event` requests the
  serve route
- **THEN** the system is denied access (login redirect or
  403 per the mixin contract)

#### Scenario: Detail and update pages link the serve route

- **WHEN** a user opens the consent detail or attachment
  management page
- **THEN** attachment links and inline images point to the
  serve route, not to raw media URLs

#### Scenario: Unknown attachment is a 404

- **WHEN** the serve route is requested with an unknown
  attachment id
- **THEN** the system returns 404

#### Scenario: Admin widget links the serve route

- **WHEN** staff opens the attachment inline or change form
  with an uploaded file
- **THEN** the existing-file widget link points to the
  serve route, not to the raw media URL
