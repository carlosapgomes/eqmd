## ADDED Requirements
### Requirement: Consent Template Administration
The system SHALL provide admin-only management of consent templates in the Django admin site. Templates SHALL be fully configurable without hardcoded types and SHALL include at least: name, markdown_body, is_active, and audit fields. Admins SHALL be able to deactivate or retire templates, and deactivated templates SHALL NOT be available for clinicians to select.

#### Scenario: Admin creates an active template
- **WHEN** an admin saves a new template with valid markdown and required placeholders
- **THEN** the template is available for selection in the consent form creation flow

#### Scenario: Admin retires a template
- **WHEN** an admin marks a template inactive
- **THEN** the template is hidden from clinician selection and remains visible in admin

#### Scenario: Non-admin access is denied
- **WHEN** a non-admin user attempts to access template management in Django admin
- **THEN** access is denied

### Requirement: Template Audit History
The system SHALL track template changes with django-simple-history and display who changed a template and when in the Django admin interface.

#### Scenario: Admin edits a template
- **WHEN** an admin updates a template
- **THEN** the change history shows the previous content, editor, and timestamp

### Requirement: Template Validation and Rendering
The system SHALL render consent templates using an allowlist-based placeholder renderer. Allowed placeholders are: patient_name, patient_record_number, document_date, procedure_description. Required placeholders are: patient_name, patient_record_number, document_date. Unknown placeholders SHALL raise a validation error. Templates missing required placeholders SHALL raise a validation error. Rendering SHALL output immutable, pure markdown.

#### Scenario: Render with valid placeholders
- **WHEN** a template uses only allowlisted placeholders and includes all required placeholders
- **THEN** the renderer produces a markdown snapshot with placeholders substituted

#### Scenario: Unknown placeholder is rejected
- **WHEN** a template includes an unknown placeholder
- **THEN** the template cannot be saved and an error is shown

#### Scenario: Missing required placeholder is rejected
- **WHEN** a template omits a required placeholder
- **THEN** the template cannot be saved and an error is shown

### Requirement: Consent Form Creation Flow
The system SHALL allow clinicians to create consent forms from the patient timeline "Create event" dropdown by selecting an active template. The creation form SHALL display patient_name and patient_record_number as read-only fields, document_date as defaulted to today and editable, and procedure_description as required. On save, the system SHALL render the template and create a consent form event.

#### Scenario: Clinician creates a consent form
- **WHEN** a clinician selects a template, fills required fields, and submits
- **THEN** a consent form event is created in the patient timeline with a rendered markdown snapshot

#### Scenario: Missing procedure description
- **WHEN** the procedure_description field is empty
- **THEN** the consent form is not created and validation errors are shown

### Requirement: Consent Form Event Model and Immutability
The system SHALL model consent forms as Events by subclassing the base Event model. Each consent form SHALL store the selected template, a rendered_markdown snapshot, rendered_at timestamp, and event metadata including created_by, updated_by, created_at, and updated_at. Changes to consent form records SHALL be tracked by the existing event history. The rendered_markdown SHALL be immutable after creation and SHALL remain unchanged even if the template is later edited or retired. The canonical stored content SHALL be the rendered markdown snapshot.

#### Scenario: Template changes do not alter existing events
- **WHEN** an admin edits a template after a consent form event exists
- **THEN** the existing event retains its original rendered_markdown snapshot

#### Scenario: Attachment edit is audited
- **WHEN** the creator adds or removes attachments within the edit window
- **THEN** updated_by and updated_at are recorded and the history shows the change

### Requirement: Consent Form Detail and Timeline Display
The system SHALL display consent form events in the patient timeline and detail view with the rendered markdown content and any attachments. The event type SHALL be distinguishable from other events.

#### Scenario: Consent form appears in timeline
- **WHEN** a consent form event is created
- **THEN** it appears in the patient timeline with a consent-specific label

### Requirement: PDF Generation for Consent Forms
The system SHALL provide on-demand PDF generation for consent forms using the existing pdfgenerator services. PDFs SHALL be generated from the stored rendered_markdown snapshot and SHALL be deterministic for a given snapshot and hospital configuration.

#### Scenario: User downloads a consent PDF
- **WHEN** a user requests the consent form PDF
- **THEN** the system returns application/pdf content that matches the stored markdown snapshot

### Requirement: Optional Scanned Attachments
Within the existing 24-hour edit window, the creator MAY upload attachments to a consent form event. Attachments SHALL be either a single PDF or 1-3 images (jpeg, png, webp, or heic). Mixed types or counts outside the limits SHALL be rejected. Attachments SHALL be visible on the consent form detail view.

#### Scenario: Upload image pages
- **WHEN** the creator uploads two image files within the edit window
- **THEN** the attachments are saved and displayed in the consent form detail view

#### Scenario: Upload count exceeds limit
- **WHEN** the creator uploads four images
- **THEN** the upload is rejected with a validation error

#### Scenario: Mixed PDF and image upload
- **WHEN** the creator uploads a PDF and an image together
- **THEN** the upload is rejected with a validation error

### Requirement: Authorization and Edit Window
The system SHALL reuse the existing event authorization rules: only the creator can edit or delete a consent form within 24 hours of creation. All users with patient access MAY view consent forms.

#### Scenario: Non-creator cannot edit
- **WHEN** a non-creator attempts to edit a consent form
- **THEN** access is denied

#### Scenario: Edit window expired
- **WHEN** the creator attempts to edit after 24 hours
- **THEN** access is denied

### Requirement: Consent Form Endpoints
The system SHALL provide endpoints consistent with existing event apps (dailynotes and simplenotes) for consent form creation, detail, editing, and PDF download. Read-only template selection data SHALL be available to clinicians via a JSON endpoint. At minimum, the system SHALL provide:
- GET consentforms/patient/<patient_pk>/create/ (template selection and creation form)
- POST consentforms/patient/<patient_pk>/create/ (create consent form)
- GET consentforms/<consent_pk>/ (detail view)
- GET consentforms/<consent_pk>/update/ and POST consentforms/<consent_pk>/update/ (attachments within edit window)
- GET consentforms/<consent_pk>/pdf/ (download PDF)
- GET api/consent-templates/?active=true (list active templates with id and name)

#### Scenario: Template list for selection
- **WHEN** a clinician opens the consent form creation flow
- **THEN** the system provides a list of active templates for selection

#### Scenario: Consent form PDF endpoint
- **WHEN** a consent form PDF is requested
- **THEN** the endpoint returns a PDF file generated from the stored markdown snapshot
