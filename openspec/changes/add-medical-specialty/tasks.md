## 1. Phase 1: Models and Database (TDD - Tests First)

- [x] 1.1 Write failing tests for MedicalSpecialty model creation and validation
- [x] 1.2 Write failing tests for UserSpecialty model creation and constraints
- [x] 1.3 Write failing tests for UserProfile.current_specialty field
- [x] 1.4 Implement MedicalSpecialty model with all fields
- [x] 1.5 Implement UserSpecialty model with user+specialty unique constraint
- [x] 1.6 Add current_specialty field to UserProfile
- [x] 1.7 Run tests and fix implementation until all pass
- [x] 1.8 Create and apply migration for new models and fields

## 2. Phase 2: User Model Properties (TDD - Tests First)

- [x] 2.1 Write failing tests for EqmdCustomUser.specialties property
- [x] 2.2 Write failing tests for EqmdCustomUser.primary_specialty property
- [x] 2.3 Write failing tests for EqmdCustomUser.specialty_display property
- [x] 2.4 Write failing tests for UserProfile.current_specialty_display property
- [x] 2.5 Implement specialties property on EqmdCustomUser
- [x] 2.6 Implement primary_specialty property on EqmdCustomUser
- [x] 2.7 Implement specialty_display property on EqmdCustomUser
- [x] 2.8 Implement current_specialty_display property on UserProfile
- [x] 2.9 Run tests and fix implementation until all pass

## 3. Phase 3: Admin Configuration (TDD - Tests First)

- [x] 3.1 Write failing admin tests for MedicalSpecialty CRUD operations
- [x] 3.2 Write failing admin tests for UserSpecialtyInline in user admin
- [x] 3.3 Write failing admin tests for specialty assignment via user admin
- [x] 3.4 Implement MedicalSpecialtyAdmin with list_display and filters
- [x] 3.5 Implement UserSpecialtyInline for user admin
- [x] 3.6 Register models in admin.py
- [x] 3.7 Run admin tests and fix implementation until all pass

## 4. Phase 4: Profile Form and Display (TDD - Tests First)

- [x] 4.1 Write failing form tests for current_specialty filtering
- [x] 4.2 Write failing view tests for profile display with specialties
- [x] 4.3 Write failing template tests for specialty badges in profile
- [x] 4.4 Modify UserProfileForm to filter current_specialty queryset
- [x] 4.5 Update profile.html template to display specialties
- [x] 4.6 Update profile update template to include specialty dropdown
- [x] 4.7 Run tests and fix implementation until all pass

## 5. Phase 5: Avatar Dropdown and AJAX (TDD - Tests First)

- [x] 5.1 Write failing view tests for change_specialty_api endpoint
- [x] 5.2 Write failing permission tests for specialty change endpoint
- [x] 5.3 Write failing integration tests for specialty switching flow
- [x] 5.4 Implement change_specialty_api view with validation
- [x] 5.5 Add URL route for specialty change endpoint
- [x] 5.6 Update base_app.html avatar dropdown to show specialty
- [x] 5.7 Add JavaScript function for specialty switching
- [x] 5.8 Run tests and fix implementation until all pass

## 6. Phase 6: Sample Data and Final Tests (TDD - Tests First)

- [ ] 6.1 Write failing tests for specialty display in various contexts
- [ ] 6.2 Write failing integration tests for complete user flow
- [ ] 6.3 Create data migration for initial specialties (Cirurgia Geral, etc.)
- [ ] 6.4 Run full test suite and fix any issues
- [ ] 6.5 Verify admin UI allows specialty creation and assignment
- [ ] 6.6 Verify profile page displays specialties correctly
- [ ] 6.7 Verify avatar dropdown shows and switches specialty
- [ ] 6.8 Run final test coverage report (target: 80%+)

## 7. Documentation and Cleanup

- [ ] 7.1 Update any relevant documentation
- [ ] 7.2 Remove any debug code or temporary imports
- [ ] 7.3 Run openspec validate to ensure proposal passes checks
- [ ] 7.4 Verify all tests pass with DJANGO_SETTINGS_MODULE=config.test_settings
