## ADDED Requirements

### Requirement: Medical Specialty Registry

The system SHALL provide a registry of medical specialties that can be managed only by administrators via Django admin.

#### Scenario: Create specialty via admin

- **WHEN** an administrator creates a medical specialty with name, abbreviation, and optional description
- **THEN** the specialty is saved in the database with is_active=True and generated timestamps

#### Scenario: Unique specialty constraint

- **WHEN** an administrator attempts to create a specialty with a duplicate name or abbreviation
- **THEN** the system rejects the creation with a validation error

#### Scenario: Soft delete specialty

- **WHEN** an administrator sets is_active=False on a specialty
- **THEN** the specialty is no longer available for assignment but existing assignments are preserved

### Requirement: User Specialty Assignment

The system SHALL allow administrators to assign one or more medical specialties to users via Django admin inline, tracking who assigned each specialty and when.

#### Scenario: Assign specialty to user

- **WHEN** an administrator assigns a specialty to a user via the user admin inline
- **THEN** a UserSpecialty record is created with the user, specialty, assigned_at timestamp, and assigned_by set to the current admin user

#### Scenario: Prevent duplicate assignments

- **WHEN** an administrator attempts to assign the same specialty to a user twice
- **THEN** the system prevents the duplicate assignment due to the unique constraint on (user, specialty)

#### Scenario: Mark primary specialty

- **WHEN** an administrator marks is_primary=True on a user's specialty assignment
- **THEN** the specialty is marked as the user's primary specialty

#### Scenario: Protect specialty with assigned users

- **WHEN** an administrator attempts to delete a MedicalSpecialty that has users assigned
- **THEN** the system prevents deletion due to PROTECT constraint and prompts to soft delete instead

### Requirement: User Specialties Property

The system SHALL provide a property on EqmdCustomUser that returns all active medical specialties assigned to the user.

#### Scenario: Get user specialties

- **WHEN** accessing user.specialties on a user with multiple active specialty assignments
- **THEN** the system returns a list of MedicalSpecialty objects for all assignments where specialty.is_active=True

#### Scenario: Get specialties for user without assignments

- **WHEN** accessing user.specialties on a user with no specialty assignments
- **THEN** the system returns an empty list

### Requirement: Primary Specialty Property

The system SHALL provide a property on EqmdCustomUser that returns the user's primary specialty, falling back to the first specialty if none is marked as primary.

#### Scenario: Get primary specialty when marked

- **WHEN** accessing user.primary_specialty on a user with one specialty marked as is_primary=True
- **THEN** the system returns that specialty object

#### Scenario: Get primary specialty when none marked

- **WHEN** accessing user.primary_specialty on a user with specialties but none marked as primary
- **THEN** the system returns the first specialty in the ordered list

#### Scenario: Get primary specialty with no assignments

- **WHEN** accessing user.primary_specialty on a user with no specialty assignments
- **THEN** the system returns None

### Requirement: Specialty Display Property

The system SHALL provide a property on EqmdCustomUser that returns a display string for the user's primary specialty.

#### Scenario: Get specialty display

- **WHEN** accessing user.specialty_display on a user with a primary specialty
- **THEN** the system returns the specialty's name as a string

#### Scenario: Get specialty display with no specialty

- **WHEN** accessing user.specialty_display on a user with no specialty
- **THEN** the system returns an empty string

### Requirement: User Current Specialty

The system SHALL allow users to select a current/active specialty from their assigned specialties via their profile.

#### Scenario: Set current specialty

- **WHEN** a user updates their profile and selects a specialty from their assigned list
- **THEN** the user's profile.current_specialty is set to the selected specialty

#### Scenario: Filter current specialty options

- **WHEN** a user views their profile update form
- **THEN** the current_specialty dropdown only shows specialties that are assigned to the user and active

#### Scenario: Display current specialty on profile

- **WHEN** viewing a user's profile page
- **THEN** the current specialty is displayed with a badge showing the specialty name

### Requirement: Profile Specialty Display

The system SHALL display all assigned specialties on the user's profile page with visual indication of the primary specialty.

#### Scenario: Display all specialties with badges

- **WHEN** viewing a user's profile page who has multiple assigned specialties
- **THEN** the system displays all specialties as badges, with the primary specialty highlighted in green and others in gray

#### Scenario: Display star icon on primary specialty

- **WHEN** viewing a user's profile page with a primary specialty marked
- **THEN** the primary specialty badge shows a star icon to distinguish it from other specialties

### Requirement: Avatar Specialty Display

The system SHALL display the user's current specialty in the avatar dropdown menu in the top-right navigation.

#### Scenario: Show current specialty in avatar dropdown

- **WHEN** a user with a current specialty views the avatar dropdown
- **THEN** the system displays the specialty name below the user's name with a stethoscope icon

#### Scenario: Show profession when no specialty

- **WHEN** a user without a current specialty views the avatar dropdown
- **THEN** the system displays the user's profession instead of specialty

### Requirement: Quick Specialty Switching

The system SHALL allow users to quickly change their current specialty from the avatar dropdown without page reload via AJAX.

#### Scenario: Switch specialty via dropdown

- **WHEN** a user with multiple assigned specialties clicks a specialty in the avatar dropdown
- **THEN** the system sends an AJAX POST request to change the current specialty and reloads the page on success

#### Scenario: Validate specialty change

- **WHEN** a user attempts to change to a specialty not assigned to them
- **THEN** the system returns an error response and does not change the current specialty

#### Scenario: Require authentication for specialty change

- **WHEN** an unauthenticated user attempts to access the specialty change endpoint
- **THEN** the system redirects to the login page

#### Scenario: Show checkmark on current specialty

- **WHEN** a user views the specialty selection list in the avatar dropdown
- **THEN** the currently selected specialty shows a checkmark icon

### Requirement: Specialty Change API

The system SHALL provide an authenticated API endpoint for changing a user's current specialty.

#### Scenario: Valid specialty change request

- **WHEN** an authenticated user POSTs a valid specialty_id to the change-specialty endpoint
- **THEN** the system validates the specialty is assigned and active, updates the profile, and returns success response

#### Scenario: Invalid specialty ID format

- **WHEN** a user POSTs an invalid UUID format to the change-specialty endpoint
- **THEN** the system returns a 400 error with an invalid specialty ID message

#### Scenario: Specialty not assigned to user

- **WHEN** a user POSTs a specialty_id for a specialty not assigned to them
- **THEN** the system returns a 403 error with a not assigned message

#### Scenario: Inactive specialty change attempt

- **WHEN** a user POSTs a specialty_id for an inactive specialty
- **THEN** the system returns a 403 error and does not change the current specialty

### Requirement: Specialty Admin Interface

The system SHALL provide a Django admin interface for managing medical specialties and assigning them to users.

#### Scenario: List specialties in admin

- **WHEN** an administrator views the medical specialties list in admin
- **THEN** the system displays name, abbreviation, is_active status, and created_at timestamp with filtering by is_active

#### Scenario: Search specialties in admin

- **WHEN** an administrator searches for specialties by name or abbreviation
- **THEN** the system filters the list to matching specialties

#### Scenario: Assign specialties inline in user admin

- **WHEN** an administrator edits a user in the admin interface
- **THEN** the system shows a tabular inline for managing user specialties with fields for specialty, is_primary, and readonly assigned_at

### Requirement: Sample Specialty Data

The system SHALL be pre-populated with common medical specialties from the Brazilian medical system.

#### Scenario: Load sample specialties

- **WHEN** the initial migration runs
- **THEN** the system creates common specialties including Cirurgia Geral, Cirurgia Vascular, Cardiologia, Pediatria, and others
