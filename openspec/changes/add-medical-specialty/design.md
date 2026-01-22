## Context

The medical team management system needs to track multiple medical specialties per user. This is important because:

1. Many doctors have multiple specialties (e.g., General Surgery + Vascular Surgery)
2. Residents need to track their primary residency specialty
3. Future features may need to filter patients/events by treating specialty
4. Audit trails should track who assigned which specialty and when

The system already has profession types (doctor, nurse, resident, student) but lacks granular specialty tracking.

## Goals / Non-Goals

- Goals:
  - Allow admins to create and manage a registry of medical specialties
  - Allow admins to assign multiple specialties to doctors and residents
  - Allow users to change their current/active specialty from their profile
  - Display current specialty in user profile and avatar dropdown
  - Track audit trail for specialty assignments (who assigned what, when)
  - Support quick specialty switching from the UI without page reload
- Non-Goals:
  - Specialty-based patient filtering (future enhancement)
  - Specialty-specific permissions (all staff can see all patients)
  - Professional registration number tracking (CRM/RQE) in this phase
  - Bulk specialty assignment (only admin UI for now)

## Decisions

- **Model separation**: Use two separate models (`MedicalSpecialty` and `UserSpecialty`) to maintain clear separation between the specialty registry and user assignments.
- **Audit trail**: Include `assigned_by` and `assigned_at` fields in `UserSpecialty` to track assignment history.
- **Primary specialty**: Use `is_primary` boolean on `UserSpecialty` to mark the user's primary specialty (important for residents).
- **Current specialty**: Use `current_specialty` foreign key on `UserProfile` for user self-selection (changes frequently, separate from primary).
- **Inline admin**: Use Django's `TabularInline` for `UserSpecialty` in user admin for easy assignment.
- **Soft delete**: Use `is_active` on `MedicalSpecialty` instead of hard deletion to preserve historical assignments.
- **Permission model**: Only admins can create/modify specialties and assign them to users. Users can only change their `current_specialty` from their assigned list.
- **AJAX switching**: Use simple fetch API for specialty changes to avoid full page reload.

## Data Model

### MedicalSpecialty

- **id**: UUID primary key
- **name**: CharField(max_length=100, unique) - Full specialty name
- **abbreviation**: CharField(max_length=10, unique) - Short abbreviation
- **description**: TextField(blank) - Optional detailed description
- **is_active**: BooleanField(default=True) - Soft delete flag
- **created_at**: DateTimeField(auto_now_add=True) - Audit timestamp
- **updated_at**: DateTimeField(auto_now=True) - Last update timestamp

### UserSpecialty

- **id**: UUID primary key
- **user**: ForeignKey(EqmdCustomUser, CASCADE) - User with this specialty
- **specialty**: ForeignKey(MedicalSpecialty, PROTECT) - Assigned specialty
- **is_primary**: BooleanField(default=False) - Mark as primary specialty
- **assigned_at**: DateTimeField(auto_now_add=True) - When assigned
- **assigned_by**: ForeignKey(EqmdCustomUser, SET_NULL, null=True) - Who assigned it
- **Unique constraint**: (user, specialty) - No duplicate assignments

### UserProfile (extension)

- **current_specialty**: ForeignKey(MedicalSpecialty, SET_NULL, null=True) - User's currently selected specialty

## User Model Properties

### EqmdCustomUser.specialties

- Returns list of `MedicalSpecialty` objects for active specialties
- Filters by `specialty__is_active=True`

### EqmdCustomUser.primary_specialty

- Returns the `MedicalSpecialty` with `is_primary=True`
- Falls back to first specialty if no primary is set
- Returns None if no specialties

### EqmdCustomUser.specialty_display

- Returns display string (name) of primary/current specialty
- Returns empty string if no specialty

### UserProfile.current_specialty_display

- Returns `current_specialty.name` if set
- Falls back to `user.specialty_display` for backward compatibility

## Admin UX

- **MedicalSpecialtyAdmin**: Standard list view with filters for `is_active`, searchable by name and abbreviation
- **UserSpecialtyInline**: Tabular inline in `EqmdCustomUserAdmin` with fields (specialty, is_primary, assigned_at)
- **Inline actions**: Admin can add/remove specialties directly from user edit page

## User-Facing Features

### Profile Page

- Display current specialty with badge
- Display all assigned specialties with star icon on primary
- Allow editing current specialty via dropdown (filtered to assigned specialties only)

### Avatar Dropdown

- Show current specialty below user name
- If user has multiple specialties, show "Trocar Especialidade" section
- Allow quick switching via buttons
- AJAX endpoint to change specialty without page reload

## API Endpoint

### POST /accounts/api/change-specialty/

- **Authentication**: Login required
- **Body**: `{"specialty_id": "<uuid>"}`
- **Validation**:
  - specialty_id must be valid UUID
  - User must have this specialty assigned
  - Specialty must be active
- **Success**: Returns `{"success": true}`
- **Error**: Returns `{"success": false, "error": "message"}` with appropriate HTTP status

## Risks / Trade-offs

- **Additional queries**: The `specialties` property may cause N+1 queries if not prefetched. Mitigation: Use `prefetch_related` in views where needed.
- **Assignment history**: No explicit history model for specialty changes (assignments can be deleted/re-added). Future: Add versioning or audit log.
- **Primary vs current**: Two concepts (primary = training/residency specialty, current = currently using) may confuse users. Mitigation: Clear UI labels and tooltips.
- **Admin-only assignment**: Bulk assignment not supported for MVP. Admins must assign individually. Future: Add bulk import/assignment.

## Migration Plan

1. Create new models (`MedicalSpecialty`, `UserSpecialty`)
2. Add `current_specialty` field to `UserProfile`
3. Run migration
4. Populate sample specialties (data migration)
5. Test with sample users in dev environment
6. Deploy to production with admin access to manage specialties

## Open Questions

- None identified for this implementation.

## Future Enhancements

- Specialty-based patient filtering in views
- Specialty-specific dashboards
- Professional registration tracking (CRM/RQE numbers)
- Bulk specialty assignment (admin CSV import)
- Specialty assignment history audit log
- Specialty-based permissions for specific features
