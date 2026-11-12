# Proposal: restrict-patient-delete-to-admin

## Why

Clicking `Excluir` on the patient profile in production returns `405 Method
Not Allowed` at `GET /patients/<uuid>/delete/`. The view only implements
`post()`, while both entry points (`patient_detail.html`, `patient_list.html`)
use plain `<a href>` (GET). A confirmation template
(`patient_confirm_delete.html`) exists but no view renders it.

Beyond the broken button, a crafted `POST` with `deletion_reason` as a doctor
still soft-deletes any patient. The request is to remove patient deletion from
every non-Django-admin user, keeping deletion available only through Django
admin (staff/superuser), consistent with the existing superuser-only restore
flow.

## What Changes

- Restrict `PatientDeleteView` (`POST /patients/<uuid>/delete/`) to Django
  admin (superuser, matching `PatientRestoreView`).
- Remove or gate the `Excluir` entry points in the clinical UI so non-admin
  users have no delete affordance.
- Remove the orphaned `patient_confirm_delete.html` (nothing renders it) to
  avoid dead confirmation UI.
- Update/extend focused tests: doctor `POST` is rejected, superuser `POST`
  soft-deletes, UI exposes no delete affordance to non-admins.

## Capabilities

### Modified Capabilities

- `patient-delete`: patient soft-deletion via the clinical UI becomes an
  admin-only operation; the Django admin bulk action remains the supported
  deletion path.

## Impact

- Apps affected: `apps.patients` (view + 2 templates + orphan template +
  focused tests).
- No database migration (soft-delete fields unchanged).
- No change to `PatientRestoreView` (already superuser-only) or to the admin
  bulk delete/restore actions.
- Doctor workflow impact: doctors lose the (currently broken-button but
  working-POST) delete path by design.

## Non-Goals

- Changing the soft-delete model, audit fields, or restore semantics.
- Changing `PatientUpdateView`, record-number, admission, or event edit rules.
- Fixing the `apps.patients:` vs `patients:` template namespace inconsistency.
- Adding a new admin-style confirmation page for the clinical delete route.
