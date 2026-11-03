# Consent forms — delta

## ADDED Requirements

### Requirement: Consent form duplication

The system SHALL provide a duplicate action that opens a duplication
form pre-filled from an existing consent form, letting the user
apply small text corrections before creating a new, independent,
printed-signature document.

#### Scenario: Duplicate form pre-filled with editable text

- **WHEN** an authorized user opens the duplicate action for a
  consent form
- **THEN** the form shows the source's rendered markdown as an
  editable field, the source's procedure description, the source's
  template as read-only provenance, and the document date defaulting
  to today
- **AND** occurrences of the source's document date (`dd/mm/aaaa`)
  in the pre-filled text are replaced by today's date in the same
  format

#### Scenario: Date replacement is best-effort

- **WHEN** the source's document date does not appear verbatim in
  the rendered markdown
- **THEN** the duplicate form still opens normally with the
  unmodified pre-filled text and no error
- **AND** the replacement happens once at prefill — changing the
  document date field afterwards does not alter the pre-filled
  text

#### Scenario: Duplicate creates an independent corrected term

- **WHEN** the user edits the markdown and submits the duplicate
  form
- **THEN** the system creates a new consent form for the same
  patient with the edited markdown frozen at submission time
- **AND** the copy carries today's chosen document date, the
  submitting user as author, a fresh render timestamp and the
  source's template reference
- **AND** the system redirects to the patient timeline

#### Scenario: Source consent form unchanged

- **WHEN** a duplicate is created
- **THEN** the source's rendered markdown, document date,
  procedure description, template, authorship and attachments
  remain unchanged
- **AND** no reference between the two documents is created

#### Scenario: Attachments are never copied

- **WHEN** a duplicate is created from a source with scanned
  attachments
- **THEN** the new consent form starts with zero attachments

#### Scenario: Timeline card duplicate action is gated

- **WHEN** a user holding `events.add_event` views the patient
  timeline
- **THEN** the consent form card shows a duplicate action
- **WHEN** a user without `events.add_event` views the timeline
- **THEN** the consent form card shows no duplicate action

#### Scenario: Patient access required

- **WHEN** a user without access to the source's patient opens the
  duplicate action
- **THEN** the system denies the request with an access error and no
  consent form is created

#### Scenario: Inactive template provenance allowed

- **WHEN** the source's template has been deactivated and a
  duplicate is created
- **THEN** the duplicate keeps the source's template reference and
  creation succeeds
