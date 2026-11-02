# Outpatient Prescriptions — delta

## ADDED Requirements

### Requirement: Duplicate action on the patient timeline

The patient timeline prescription card SHALL expose the duplicate action
to users holding `events.add_event`, as a POST form targeting the
existing duplicate endpoint.

#### Scenario: Duplicate action visible on the card

- **WHEN** a user with `events.add_event` views an outpatient
  prescription event on the patient timeline
- **THEN** the prescription card renders a duplicate action that
  submits the duplicate endpoint for that prescription

#### Scenario: Duplicate action hidden without permission

- **WHEN** a user without `events.add_event` views the patient timeline
- **THEN** the prescription card does not render the duplicate action
- **AND** submitting the endpoint directly is still denied by the view

#### Scenario: Duplicating from the card lands on the copy's edit view

- **WHEN** an authorized user submits the duplicate action from the
  timeline card
- **THEN** the system creates a new draft prescription with the source's
  items and instructions (per the existing duplicate requirement) and
  redirects to the copy's edit view
