# patient-delete Specification

## Purpose

Define who may soft-delete a patient through the clinical delete route and
what the clinical UI exposes. Clinical patient deletion is a superuser-only
operation; the Django admin bulk action remains the supported deletion path
for eligible staff.

## Requirements

### Requirement: Clinical patient deletion is superuser-only

The system SHALL reject `POST /patients/<uuid>/delete/` with `403` for every
authenticated non-superuser, including doctors holding
`patients.delete_patient`, and SHALL soft-delete only on a superuser `POST`
with a non-empty `deletion_reason`.

#### Scenario: Doctor POST is rejected

- **GIVEN** an authenticated doctor and an active patient
- **WHEN** the doctor posts a `deletion_reason` to the delete route
- **THEN** the system responds `403`
- **AND** the patient remains active and unchanged.

#### Scenario: Superuser POST soft-deletes

- **GIVEN** an authenticated superuser and an active patient
- **WHEN** the superuser posts a non-empty `deletion_reason`
- **THEN** the patient is soft-deleted with `deleted_by` and `deletion_reason`
  recorded
- **AND** the patient disappears from the default manager queryset
- **AND** the user is redirected to the patient list.

#### Scenario: Missing reason is rejected without deleting

- **GIVEN** an authenticated superuser and an active patient
- **WHEN** the superuser posts an empty `deletion_reason`
- **THEN** no deletion occurs
- **AND** the user is redirected to the patient detail with an error message.

### Requirement: Clinical UI exposes no delete affordance to non-admins

The system SHALL NOT render any link or form targeting the clinical delete
route for non-superuser sessions on the patient detail or patient list pages.

#### Scenario: Non-superuser sees no Excluir control

- **GIVEN** an authenticated non-superuser viewing the patient detail or list
- **WHEN** the page renders
- **THEN** its HTML contains no `Excluir` control pointing at the delete
  route.
