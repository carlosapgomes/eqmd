# Detailed Implementation Plan for EquipeMed Permission System

## Overview

This plan outlines a step-by-step approach to implement the EquipeMed permission system using a vertical slicing strategy. Each slice represents a complete, testable feature that builds upon previous slices.

## Vertical Slice 1: Basic Permission Framework Setup

### Step 1: Create Core Permission Utilities

1. Create the permission utility module structure:

   - Create `apps/core/permissions/` directory
   - Create `apps/core/permissions/__init__.py`
   - Create `apps/core/permissions/constants.py` for permission codes
   - Create `apps/core/permissions/utils.py` for utility functions

2. Define permission constants:

   - Define profession types (MEDICAL_DOCTOR, NURSE, etc.)
   - Define patient status types (INPATIENT, OUTPATIENT)
   - Define permission codes for each rule

3. Create test structure:
   - Create `apps/core/tests/test_permissions/` directory
   - Create test files for each permission category

### Step 2: Implement Basic Permission Utility Functions

1. Implement basic permission check functions:

   - Create patient access check function
   - Create event editing check function
   - Create patient status change check function

2. Write tests for basic permission functions:
   - Test with different user types
   - Test with different object states
   - Test edge cases

### Step 3: Create Permission Decorators

1. Implement basic permission decorators:

   - Create `patient_access_required` decorator
   - Create `doctor_required` decorator
   - Create `can_edit_event` decorator

2. Write tests for decorators:
   - Create mock views for testing
   - Test with authenticated and unauthenticated users
   - Test with users having different permissions

### Step 4: Verify Implementation

1. Create a simple view to test permissions:

   - Create a test view with decorators
   - Create a test template
   - Add URL pattern for testing

2. Run tests and verify functionality:
   - Run unit tests for utility functions
   - Run tests for decorators
   - Manually test the test view

## Vertical Slice 2: Hospital Context Management

### Step 1: Implement Hospital Context Middleware

1. Create middleware structure:

   - Create `apps/hospitals/middleware.py`
   - Define `HospitalContextMiddleware` class

2. Implement middleware functionality:

   - Add hospital context to user object
   - Handle session management for hospital selection
   - Add helper methods for switching hospitals

3. Write tests for middleware:
   - Test middleware with authenticated users
   - Test middleware with unauthenticated users
   - Test hospital switching functionality

### Step 2: Update Settings and Configure Middleware

1. Add middleware to settings:

   - Add middleware to `MIDDLEWARE` setting
   - Configure any required settings

2. Create hospital selection view:

   - Create view for selecting current hospital
   - Create template for hospital selection
   - Add URL pattern for hospital selection

3. Write tests for hospital selection:
   - Test hospital selection view
   - Test session management
   - Test middleware integration

### Step 3: Integrate Hospital Context with Permissions

1. Update permission utility functions:

   - Modify functions to use hospital context
   - Add hospital-specific permission checks

2. Update tests for hospital context:
   - Test permissions with different hospital contexts
   - Test edge cases for hospital context

### Step 4: Verify Implementation

1. Create test views for hospital context:

   - Create view that uses hospital context
   - Create template that displays hospital context
   - Add URL pattern for testing

2. Run tests and verify functionality:
   - Run unit tests for middleware
   - Run tests for integrated permissions
   - Manually test hospital switching

## Vertical Slice 3: Role-Based Permissions

### Step 1: Define User Groups and Permissions

1. Create management command for setting up groups:

   - Create `apps/core/management/commands/setup_groups.py`
   - Define groups based on profession types
   - Define permissions for each group

2. Implement group setup logic:

   - Create or update groups
   - Assign permissions to groups
   - Handle existing groups and permissions

3. Write tests for group setup:
   - Test group creation
   - Test permission assignment
   - Test idempotence (running command multiple times)

### Step 2: Implement User-Group Assignment

1. Create signal handlers for user creation:

   - Create `apps/accounts/signals.py`
   - Add signal handler for user post-save
   - Assign groups based on profession type

2. Update user model or profile:

   - Add profession type field if not exists
   - Add methods for checking profession type
   - Add methods for changing profession type

3. Write tests for user-group assignment:
   - Test automatic group assignment
   - Test profession type changes
   - Test permission inheritance

### Step 3: Integrate Role-Based Permissions with Existing System

1. Update permission utility functions:

   - Add role-based permission checks
   - Integrate with Django's permission system

2. Create template tags for permission checks:

   - Create `apps/core/templatetags/permission_tags.py`
   - Add tags for common permission checks
   - Add tags for role-based checks

3. Write tests for integrated permissions:
   - Test permission checks with different roles
   - Test template tags
   - Test combined permission scenarios

### Step 4: Verify Implementation

1. Create test views for role-based permissions:

   - Create views with role-based restrictions
   - Create templates that use permission tags
   - Add URL patterns for testing

2. Run tests and verify functionality:
   - Run unit tests for role-based permissions
   - Run tests for template tags
   - Manually test with different user roles

## Vertical Slice 4: Object-Level Permissions

### Step 1: Implement Patient-Related Permission Checks

1. Create patient permission utility functions:

   - Implement `can_access_patient` function
   - Implement `can_change_patient_status` function
   - Implement `can_change_patient_personal_data` function

2. Create patient permission decorators:

   - Create `patient_access_required` decorator
   - Create `patient_status_change_required` decorator
   - Create `patient_data_change_required` decorator

3. Write tests for patient permissions:
   - Test with different user roles
   - Test with different patient statuses
   - Test with different hospital contexts

### Step 2: Implement Event-Related Permission Checks

1. Create event permission utility functions:

   - Implement `can_edit_event` function
   - Implement `can_delete_event` function
   - Implement time-based restriction checks

2. Create event permission decorators:

   - Create `can_edit_event_required` decorator
   - Create `can_delete_event_required` decorator

3. Write tests for event permissions:
   - Test with event creators
   - Test with non-creators
   - Test with different time intervals

### Step 3: Implement Custom Permission Backend

1. Create custom permission backend:

   - Create `apps/core/backends.py`
   - Implement `EquipeMedPermissionBackend` class
   - Implement `has_perm` method

2. Configure backend in settings:

   - Add backend to `AUTHENTICATION_BACKENDS` setting

3. Write tests for custom backend:
   - Test with Django's permission checking API
   - Test with different permission scenarios
   - Test integration with existing permissions

### Step 4: Verify Implementation

1. Create comprehensive test views:

   - Create views that use all permission types
   - Create templates that display permission results
   - Add URL patterns for testing

2. Run tests and verify functionality:
   - Run all unit tests
   - Test integration points
   - Manually test with different scenarios

## Vertical Slice 5: UI Integration and Performance Optimization

### Step 1: Create Template Tags for UI Permissions

1. Implement comprehensive template tags:

   - Create tags for all permission types
   - Create tags for role checks
   - Create tags for hospital context

2. Create template filters:

   - Create filters for permission-based display
   - Create filters for role-based display

3. Write tests for template tags and filters:
   - Test with different contexts
   - Test with different user types
   - Test edge cases

### Step 2: Implement Permission Caching

1. Create permission cache mechanism:

   - Implement caching for expensive permission checks
   - Add cache invalidation logic
   - Configure cache settings

2. Update permission utility functions:

   - Add caching to permission functions
   - Add cache key generation
   - Add cache invalidation calls

3. Write tests for permission caching:
   - Test cache hits and misses
   - Test cache invalidation
   - Test performance improvements

### Step 3: Optimize Database Queries

1. Analyze and optimize permission-related queries:

   - Add select_related/prefetch_related where needed
   - Create optimized querysets for common scenarios
   - Add indexes to relevant fields

2. Create query utility functions:

   - Implement functions for common permission-related queries
   - Add optimization hints

3. Write tests for query optimization:
   - Test query counts
   - Test query performance
   - Test with different data volumes

### Step 4: Verify Implementation

1. Create performance test suite:

   - Create tests with timing measurements
   - Create tests with query counting
   - Create tests with different data volumes

2. Run tests and verify functionality:
   - Run performance tests
   - Compare before/after metrics
   - Verify correctness with optimizations

## Vertical Slice 6: Documentation and Final Integration

### Step 1: Create Comprehensive Documentation

1. Create developer documentation:

   - Document permission system architecture
   - Document utility functions and their usage
   - Document decorators and their usage
   - Document template tags and their usage

2. Create user documentation:

   - Document permission rules for end users
   - Document hospital context management
   - Document role-based access control

3. Create code documentation:
   - Add docstrings to all functions and classes
   - Add type hints where appropriate
   - Add examples in docstrings

### Step 2: Create Management Commands for Maintenance

1. Implement permission audit command:

   - Create command to list all permissions
   - Create command to check permission consistency
   - Create command to fix permission issues

2. Implement user permission management commands:

   - Create command to assign permissions to users
   - Create command to list user permissions
   - Create command to reset permissions

3. Write tests for management commands:
   - Test command outputs
   - Test command actions
   - Test error handling

### Step 3: Final Integration and Testing

1. Create integration test suite:

   - Create tests that cover all permission aspects
   - Create tests for different user workflows
   - Create tests for edge cases

2. Perform security audit:

   - Review permission checks for security holes
   - Test with unauthorized access attempts
   - Test with malformed inputs

3. Conduct user acceptance testing:
   - Create test scenarios for different user roles
   - Document expected behaviors
   - Verify actual behaviors

### Step 4: Verify Implementation

1. Run comprehensive test suite:

   - Run all unit tests
   - Run all integration tests
   - Run performance tests

2. Create demo application:

   - Create views that demonstrate all permission features
   - Create templates that show permission effects
   - Create sample data for testing

3. Final verification:
   - Verify all requirements are met
   - Verify all tests pass
   - Verify documentation is complete

## Testing Strategy

For each vertical slice, we'll implement the following types of tests:

1. **Unit Tests**:

   - Test individual permission functions
   - Test decorators
   - Test template tags
   - Test middleware

2. **Integration Tests**:

   - Test permission functions with real models
   - Test decorators with real views
   - Test middleware in request cycle

3. **Performance Tests**:

   - Test permission check performance
   - Test caching effectiveness
   - Test query optimization

4. **Security Tests**:
   - Test unauthorized access attempts
   - Test permission bypass attempts
   - Test edge cases and boundary conditions
