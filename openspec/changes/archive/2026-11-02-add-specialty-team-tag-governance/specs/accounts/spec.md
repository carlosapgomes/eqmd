# Accounts delta: Specialty teams

## MODIFIED Requirements

### Requirement: User Specialties Property

The system SHALL provide a property on EqmdCustomUser that returns all active
medical specialties for which the user has active team membership.

#### Scenario: Get user specialties

- **WHEN** accessing user.specialties on a user with multiple active specialty
  assignments
- **THEN** the system returns a list of MedicalSpecialty objects for assignments
  where both membership and specialty are active

#### Scenario: Get specialties for user without assignments

- **WHEN** accessing user.specialties on a user with no active specialty assignments
- **THEN** the system returns an empty list

### Requirement: Primary Specialty Property

The system SHALL provide a property on EqmdCustomUser that returns the user's
primary eligible specialty, falling back to the first eligible specialty if none
is marked as primary. Eligibility SHALL require active membership and an active
specialty.

#### Scenario: Get primary specialty when marked

- **WHEN** accessing user.primary_specialty on a user with one eligible specialty
  marked as is_primary=True
- **THEN** the system returns that specialty object

#### Scenario: Get primary specialty when none marked

- **WHEN** accessing user.primary_specialty on a user with eligible specialties
  but none marked as primary
- **THEN** the system returns the first eligible specialty in the ordered list

#### Scenario: Get primary specialty with no assignments

- **WHEN** accessing user.primary_specialty on a user with no eligible specialty
  assignments
- **THEN** the system returns None

### Requirement: User Current Specialty

The system SHALL allow users to select at most one current specialty from their
active memberships in active specialties via their profile. An invalidated current
selection SHALL stop providing team context or privileges on the next request.

#### Scenario: Set current specialty

- **WHEN** a user updates their profile and selects a specialty from their active
  assigned list
- **THEN** the user's profile.current_specialty is set to the selected specialty

#### Scenario: Filter current specialty options

- **WHEN** a user views their profile update form
- **THEN** the dropdown only shows active specialties with active membership

#### Scenario: Display current specialty on profile

- **WHEN** viewing a user's profile page with a valid current specialty
- **THEN** the current specialty is displayed with a badge showing its name

#### Scenario: Membership revocation invalidates current context

- **WHEN** an administrator revokes the currently selected membership
- **THEN** the next request no longer uses that specialty as active
- **AND** another specialty is not silently selected for automatic filtering

### Requirement: Specialty Change API

The system SHALL provide an authenticated API endpoint for changing a user's
current specialty, requiring active membership and an active specialty at request
time.

#### Scenario: Valid specialty change request

- **WHEN** an authenticated user POSTs a valid specialty_id to the endpoint
- **THEN** the system validates active assignment and specialty, updates the
  profile, and returns success

#### Scenario: Invalid specialty ID format

- **WHEN** a user POSTs an invalid UUID format to the change-specialty endpoint
- **THEN** the system returns a 400 error with an invalid specialty ID message

#### Scenario: Specialty not assigned to user

- **WHEN** a user POSTs a specialty_id without active membership
- **THEN** the system returns a 403 error without changing the current specialty

#### Scenario: Inactive specialty change attempt

- **WHEN** a user POSTs a specialty_id for an inactive specialty
- **THEN** the system returns a 403 error and does not change the current specialty

## ADDED Requirements

### Requirement: Administrator-managed team membership and leadership

The system SHALL treat each specialty as one assistential team, allowing multiple
members and multiple leaders. Only authorized administrators SHALL grant/revoke
membership or leadership through Django Admin, recording actor and time.
Leadership SHALL require active membership in an active specialty.

#### Scenario: Multiple leaders and multiple teams

- **WHEN** an administrator assigns two leaders to CIRGER and a user to CIRGER
  and CARDIO
- **THEN** both leaders coexist and both memberships are retained
- **AND** granting leadership does not grant general Django Admin access

#### Scenario: Leadership does not permit membership administration

- **WHEN** a leader attempts to add members or grant leadership through a team page
- **THEN** the operation is unavailable and direct mutation is denied

### Requirement: Revocation retains preferences and immediately removes authority

The system SHALL preserve membership history and per-specialty preferences when
membership ends while immediately removing restricted-tag access, leadership
powers and current-specialty eligibility. Returning membership SHALL revalidate
retained preferences and SHALL NOT automatically restore leadership.

#### Scenario: User leaves and returns

- **WHEN** an administrator revokes and later restores a user's team membership
- **THEN** preferences remain retained and are revalidated before use
- **AND** no restricted authority exists during the inactive interval
- **AND** leadership requires an explicit administrative grant
