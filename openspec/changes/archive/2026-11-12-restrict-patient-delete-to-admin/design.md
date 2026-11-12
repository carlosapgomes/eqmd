# Design: restrict-patient-delete-to-admin

## Context

- `apps/patients/views.py:PatientDeleteView` (`LoginRequiredMixin, View`) only
  defines `post()` guarded by `@method_decorator(doctor_required)`
  (`profession_type == 0`). Any `GET` falls through to Django's base `View`
  dispatch and returns `405`.
- Entry points are plain anchors (GET, no JS-to-POST, no form):
  `apps/patients/templates/patients/patient_detail.html:36` and
  `apps/patients/templates/patients/patient_list.html:219`.
- `apps/patients/templates/patients/patient_confirm_delete.html` contains a
  correct `POST` + `deletion_reason` form, but no view references it (orphan).
- A direct `POST` with `deletion_reason` as doctor succeeds today
  (`apps/patients/tests/test_views.py:test_patient_delete_view` → `302` +
  soft-delete).
- `PatientRestoreView` is already
  `@method_decorator(user_passes_test(lambda u: u.is_superuser))`.
- `PatientAdmin` (`apps/patients/admin.py`) already exposes
  `soft_delete_selected` / `restore_selected` to staff via `/admin/` with
  `get_queryset` over `all_objects`.

## Goals / Non-Goals

### Goals

- `POST /patients/<uuid>/delete/` is rejected with `403` for every
  non-superuser (including doctors holding `patients.delete_patient`).
- Clinical UI shows no `Excluir` affordance to non-superusers.
- No dead confirmation template remains.
- Existing admin bulk deletion/restoration keeps working unchanged (staff
  surface; the bulk action deletes directly with a generated audit reason and
  offers no per-object confirmation page).

### Non-Goals

- See proposal Non-Goals (no model, restore, or namespace changes).

## Decisions

1. **Gate = superuser, not staff, not `delete_patient` permission.** Matches
   `PatientRestoreView` and the requester's "só admin do Django". If the team
   wants staff-but-not-superuser to delete via this route, that is a new
   product decision (escalate, do not silently widen). Confirmed 2026-11-12:
   the database holds zero staff-non-superuser accounts (only `admin` is
   staff/superuser), so the clinical-route-superuser vs admin-bulk-staff
   asymmetry is moot in practice and is kept intentionally.
2. **No `GET` confirmation page for this route.** With no UI links left, the
   route stays POST-only (`GET` keeps returning `405`, which is correct for a
   destructive action without a confirmation step). The Django admin bulk
   action remains the supported deletion path for eligible staff; it is not a
   per-object confirmation page.
3. **Delete the orphan template** instead of wiring it, because no role needs a
   clinical confirmation page after this change.
4. **Buttons removed, not merely hidden by CSS.** Non-admin response HTML must
   not contain a delete link/form toward this route.

## Route/Behavior Design

- `PatientDeleteView` keeps `LoginRequiredMixin` and stays POST-only (no
  `get()` handler, so `GET` keeps returning `405` for every caller). Inside
  `post()`, replace `doctor_required` with an explicit superuser check that
  raises `PermissionDenied` (`403`) for authenticated non-superusers.
  Rationale: `user_passes_test` redirects failures to login instead of
  returning `403`, and applied at dispatch level it would also swallow the
  `405` for `GET`. Anonymous → login redirect (unchanged); authenticated
  non-superuser `POST` (doctor, staff non-superuser included) → `403`;
  superuser with empty/whitespace-only `deletion_reason` → existing redirect
  to detail with error message; superuser with reason → existing soft-delete
  and redirect to list.
- Templates: remove the `Excluir` anchor in `patient_detail.html` and
  `patient_list.html`, or gate it with `{% if user.is_superuser %}`. Preferred:
  remove entirely, since even superusers should use `/admin/` for deletion;
  gating is acceptable only if the team explicitly wants a superuser shortcut
  in the clinical UI (then the shortcut must POST, not GET).
- Delete `patient_confirm_delete.html`.
- `doctors`, `residents`, `nurses`, `physiotherapists`, `students`: no
  behavior change other than losing the crafted-POST path (now `403`).

## Test Design

- Update `test_patient_delete_view` (doctor `POST` → `403`, patient untouched)
  or keep it as the failing-before witness and add the new expectation.
- Add superuser `POST` success test (`302` to list, `is_deleted=True`,
  `deleted_by` and `deletion_reason` recorded, invisible to the default
  manager). Cover empty and whitespace-only reasons (no deletion, redirect
  to detail with error) and a staff-but-not-superuser `POST` → `403`.
- Add a `GET` regression test: `GET` keeps returning `405` (also for
  superusers), proving no confirmation page was introduced and the gate did
  not move to dispatch. Use the real URL via `reverse`, not the template
  namespace string.
- Add UI test: detail and list HTML for a non-superuser contain no reference
  to the delete route; superuser path per template decision (no link if
  removed).
- Keep `test_permission_required` (noperms `POST` → `403`) green.
- Focused suites: `apps.patients.tests.test_views`,
  `apps.patients.tests.test_soft_delete`.
