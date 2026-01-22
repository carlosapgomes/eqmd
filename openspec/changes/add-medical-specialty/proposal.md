## Why

The system currently lacks the ability to track and manage medical specialties for doctors and residents. This capability is essential for proper role identification, audit trails, and future specialty-based filtering of patient care records.

## What Changes

- Add `MedicalSpecialty` model to manage a registry of medical specialties (admin-only CRUD)
- Add `UserSpecialty` model to associate users with multiple specialties (admin-only assignment)
- Add `current_specialty` field to `UserProfile` for user self-selection
- Add inline admin for assigning specialties directly in user admin
- Add properties to `EqmdCustomUser` for accessing specialties and primary specialty
- Add AJAX endpoint for quick specialty switching from avatar dropdown
- Update profile page to display all assigned specialties with primary marked
- Update avatar dropdown to show current specialty and allow quick switching

**BREAKING**: Database migration required for new models and fields

## Impact

- Affected specs: `accounts` (new capability for medical specialty management)
- Affected code: `apps/accounts/models.py`, `apps/accounts/admin.py`, `apps/accounts/forms.py`, `apps/accounts/views.py`, `apps/accounts/urls.py`, `apps/accounts/templates/accounts/profile.html`, `templates/base_app.html`
