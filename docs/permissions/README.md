# EquipeMed Permission System Documentation

## Overview

The EquipeMed permission system provides comprehensive role-based access control, hospital context management, and time-based restrictions for medical record operations. This documentation covers the complete permission framework implementation.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Permission Utilities](#permission-utilities)
3. [Decorators](#decorators)
4. [Template Tags](#template-tags)
5. [Hospital Context Management](#hospital-context-management)
6. [Role-Based Permissions](#role-based-permissions)
7. [Object-Level Permissions](#object-level-permissions)
8. [Performance Optimization](#performance-optimization)
9. [Management Commands](#management-commands)
10. [Testing](#testing)
11. [Security Considerations](#security-considerations)

## Architecture Overview

The permission system is organized into several modules:

```
apps/core/permissions/
├── __init__.py          # Public API exports
├── constants.py         # Permission constants and profession types
├── utils.py            # Core permission checking functions
├── decorators.py       # View-level permission decorators
├── cache.py            # Permission caching utilities
├── queries.py          # Query optimization utilities
└── backends.py         # Custom permission backend
```

### Key Components

- **Permission Utilities**: Core functions for checking permissions
- **Decorators**: View-level permission enforcement
- **Template Tags**: Permission checking in templates
- **Hospital Context Middleware**: Session-based hospital selection
- **Role-Based Groups**: Automatic group assignment based on profession
- **Object-Level Permissions**: Fine-grained access control
- **Performance Optimization**: Caching and query optimization
- **Custom Backend**: Integration with Django's permission system

## Permission Utilities

The core permission utilities are located in `apps/core/permissions/utils.py` and provide the foundation for all permission checking.

### Patient Access Control

#### `can_access_patient(user, patient)`
Controls access to specific patients based on hospital context and user role.

**Rules:**
- Doctors, nurses, physiotherapists, and residents: Full access to patients in their current hospital
- Students: Limited to outpatients in their current hospital
- No access if user lacks hospital context or patient is in different hospital

**Usage:**
```python
from apps.core.permissions import can_access_patient

if can_access_patient(request.user, patient):
    # User can access this patient
    pass
```

#### `can_change_patient_status(user, patient, new_status)`
Controls who can change patient status.

**Rules:**
- **Doctors**: Can change any patient status (including discharge)
- **Nurses/Physiotherapists/Residents**: Limited status changes (cannot discharge patients)
- **Students**: Cannot change patient status
- **Special rule**: Nurses can admit emergency patients to inpatient status

#### `can_change_patient_personal_data(user, patient)`
Controls who can modify patient personal information.

**Rules:**
- Only doctors can change patient personal data
- For outpatients: Any doctor can change data
- For inpatients/emergency/discharged/transferred: Doctor must be in same hospital with hospital context

### Event Management

#### `can_edit_event(user, event)`
Time-limited event editing permissions.

**Rules:**
- Only event creators can edit their events
- Editing restricted to 24 hours after event creation
- Supports audit trail for medical record integrity

#### `can_delete_event(user, event)`
Controls event deletion permissions.

**Rules:**
- Only event creators can delete their events
- Events can only be deleted within 24 hours of creation
- Same time-based restrictions as editing for audit trail integrity

### Role Checking

#### `is_doctor(user)`
Simple role verification for doctor-only operations.

#### `has_hospital_context(user)`
Validates that user has selected a current hospital context.

### Permission Helpers

#### `has_django_permission(user, permission)`
Check if user has a specific Django permission.

#### `is_in_group(user, group_name)`
Check if user is in a specific group.

#### `get_user_profession_type(user)`
Get the profession type for a user.

### Convenience Functions

#### `can_manage_patients(user)`
Check if user can manage patients (add, change, delete).

#### `can_view_patients(user)`
Check if user can view patients.

#### `can_manage_events(user)`
Check if user can manage events.

#### `can_view_events(user)`
Check if user can view events.

#### `can_manage_hospitals(user)`
Check if user can manage hospitals.

#### `can_view_hospitals(user)`
Check if user can view hospitals.

## Decorators

Permission decorators provide view-level access control and are located in `apps/core/permissions/decorators.py`.

### Available Decorators

#### `@patient_access_required`
Validates user access to the specified patient.

```python
from apps.core.permissions import patient_access_required

@patient_access_required
def patient_detail_view(request, patient_id):
    # User access to patient already validated
    patient = get_object_or_404(Patient, pk=patient_id)
    return render(request, 'patient_detail.html', {'patient': patient})
```

#### `@doctor_required`
Restricts view access to doctors only.

```python
from apps.core.permissions import doctor_required

@doctor_required
def discharge_patient_view(request, patient_id):
    # Only doctors can access this view
    pass
```

#### `@can_edit_event_required`
Validates user can edit the specified event.

```python
from apps.core.permissions import can_edit_event_required

@can_edit_event_required
def event_edit_view(request, event_id):
    # User permission to edit event already validated
    pass
```

#### `@hospital_context_required`
Ensures user has hospital context.

```python
from apps.core.permissions import hospital_context_required

@hospital_context_required
def hospital_specific_view(request):
    # User has selected a current hospital
    pass
```

#### `@patient_data_change_required`
Validates user can change patient personal data.

```python
from apps.core.permissions import patient_data_change_required

@patient_data_change_required
def patient_edit_personal_data_view(request, patient_id):
    # User permission to change patient personal data already validated
    pass
```

#### `@can_delete_event_required`
Validates user can delete the specified event.

```python
from apps.core.permissions import can_delete_event_required

@can_delete_event_required
def event_delete_view(request, event_id):
    # User permission to delete event already validated
    pass
```

## Template Tags

Template tags for permission checking are located in `apps/core/templatetags/permission_tags.py`.

### Basic Permission Checks

```django
{% load permission_tags %}

<!-- Django permission checks -->
{% if user|has_permission:"patients.add_patient" %}
    <a href="{% url 'patients:create' %}">Add Patient</a>
{% endif %}

<!-- Group membership checks -->
{% if user|in_group:"Medical Doctors" %}
    <p>Welcome, Doctor!</p>
{% endif %}

<!-- Profession type checks -->
{% if user|is_profession:"medical_doctor" %}
    <p>Doctor-specific content</p>
{% endif %}
```

### Convenience Permission Filters

```django
<!-- Convenience permission filters -->
{% if user|can_manage_patients %}
    <p>You can manage patients</p>
{% endif %}

{% if user|can_view_events %}
    <p>You can view events</p>
{% endif %}
```

### Multiple Permission Checks

```django
<!-- Multiple permission checks -->
{% check_multiple_permissions user "patients.add_patient" "patients.change_patient" as has_all_perms %}
{% if has_all_perms %}
    <p>You have all required permissions</p>
{% endif %}

<!-- Any permission check -->
{% check_any_permission user "patients.add_patient" "patients.view_patient" as has_any_perm %}
{% if has_any_perm %}
    <p>You have at least one permission</p>
{% endif %}
```

### Object-Level Permission Tags

```django
<!-- Patient personal data change permission -->
{% can_user_change_patient_personal_data user patient as can_change_data %}
{% if can_change_data %}
    <a href="{% url 'patients:edit_personal_data' patient.pk %}">Edit Personal Data</a>
{% endif %}

<!-- Event deletion permission -->
{% can_user_delete_event user event as can_delete %}
{% if can_delete %}
    <button class="btn btn-danger" onclick="deleteEvent('{{ event.pk }}')">Delete Event</button>
{% endif %}
```

### Debug and Performance Tags

```django
<!-- Permission debug widget -->
{% permission_debug user %}

<!-- Performance widget -->
{% permission_performance_widget user %}

<!-- Cache statistics -->
{% permission_cache_stats as cache_stats %}
```

## Hospital Context Management

Hospital context management is handled by the `HospitalContextMiddleware` located in `apps/hospitals/middleware.py`.

### How It Works

1. **Session Storage**: Current hospital selection is stored in Django sessions
2. **User Object Enhancement**: Adds `current_hospital` and `has_hospital_context` attributes to user objects
3. **Automatic Injection**: Hospital context is automatically available in all requests
4. **Error Handling**: Gracefully handles invalid hospital IDs by removing them from session

### Setting Hospital Context

```python
from apps.hospitals.middleware import HospitalContextMiddleware

# Set hospital context
hospital = HospitalContextMiddleware.set_hospital_context(request, hospital_id)

# Clear hospital context
HospitalContextMiddleware.clear_hospital_context(request)

# Get available hospitals for user
hospitals = HospitalContextMiddleware.get_available_hospitals(request.user)
```

### Using Hospital Context in Views

```python
def my_view(request):
    if request.user.has_hospital_context:
        current_hospital = request.user.current_hospital
        # Use hospital context
    else:
        # Redirect to hospital selection
        return redirect('hospitals:select')
```

### Hospital Selection Interface

The system provides a user-friendly hospital selection interface at `/hospitals/select/` with:

- Bootstrap 5 styled form
- Validation and error messaging
- Session persistence
- Integration with permission framework

## Role-Based Permissions

The system automatically assigns users to profession-based groups using Django signals and management commands.

### Automatic Group Assignment

Users are automatically assigned to groups based on their profession type:

- **Medical Doctors**: Full permissions for all models and operations
- **Residents**: Full access to patients, events, and hospital records in current hospital
- **Nurses**: Limited patient permissions (no delete), full event access, view-only hospitals
- **Physiotherapists**: Full access to patients, events, and hospital records in current hospital
- **Students**: View-only permissions for patients, events, and hospitals

### Group Setup

```bash
# Set up all profession-based groups with appropriate permissions
python manage.py setup_groups

# Force recreation of groups (removes existing groups first)
python manage.py setup_groups --force
```

### Signal-Based Assignment

Groups are automatically assigned when:
- A new user is created with a profession type
- An existing user's profession type is changed
- Groups are created/removed automatically based on profession changes

## Object-Level Permissions

The system implements fine-grained object-level permissions through a custom permission backend.

### Custom Permission Backend

The `EquipeMedPermissionBackend` integrates object-level permissions with Django's permission system:

```python
# Using Django's permission system with objects
if user.has_perm('patients.change_patient_personal_data', patient):
    # User can change this specific patient's personal data
    pass

if user.has_perm('events.delete_event', event):
    # User can delete this specific event
    pass
```

### Supported Object-Level Permissions

- `patients.access_patient`
- `patients.change_patient_personal_data`
- `patients.see_patient_in_search`
- `events.edit_event`
- `events.delete_event`

## Performance Optimization

The permission system includes comprehensive performance optimization features.

### Permission Caching

```python
from apps.core.permissions.cache import cache_permission_result

# Automatic caching with decorators
@cache_permission_result('can_access_patient', use_object_id=True)
def can_access_patient(user, patient):
    # Function implementation
    pass
```

### Cache Management

```python
from apps.core.permissions import (
    invalidate_user_permissions,
    invalidate_object_permissions,
    clear_permission_cache,
    get_cache_stats
)

# Invalidate user permissions
invalidate_user_permissions(user.id)

# Invalidate object permissions
invalidate_object_permissions('patient', patient.id)

# Clear all permission cache
clear_permission_cache()

# Get cache statistics
stats = get_cache_stats()
```

### Query Optimization

```python
from apps.core.permissions.queries import (
    get_optimized_user_queryset,
    get_optimized_patient_queryset,
    get_patients_for_user,
    get_permission_summary_optimized
)

# Get users with prefetched permission data
users = get_optimized_user_queryset().filter(is_active=True)

# Get patients accessible to user
patients = get_patients_for_user(user)

# Get comprehensive permission summary
summary = get_permission_summary_optimized(user)
```

## Management Commands

The system provides several management commands for maintenance and monitoring.

### Setup Groups Command

```bash
# Set up all profession-based groups
python manage.py setup_groups

# Force recreation of groups
python manage.py setup_groups --force
```

### Permission Performance Command

```bash
# Show cache statistics
python manage.py permission_performance --action=stats

# Run benchmarks
python manage.py permission_performance --action=benchmark --iterations=1000

# Clear cache
python manage.py permission_performance --action=clear-cache

# Test query optimization
python manage.py permission_performance --action=test-queries --user-id=1
```

## Testing

The permission system includes comprehensive test coverage:

- **45+ Total Tests**: Complete functionality coverage
- **Unit Tests**: Individual permission functions and decorators
- **Integration Tests**: End-to-end permission workflows
- **Performance Tests**: Cache effectiveness and query optimization
- **Security Tests**: Unauthorized access attempts and edge cases

### Running Tests

```bash
# Run all permission tests
python manage.py test apps.core.tests.test_permissions

# Run specific test modules
python manage.py test apps.core.tests.test_permissions.test_utils
python manage.py test apps.core.tests.test_permissions.test_decorators
python manage.py test apps.core.tests.test_permissions.test_object_level
```

## Security Considerations

The permission system implements multiple security layers:

- **Hospital Isolation**: Users can only access patients in their current hospital context
- **Time-Based Restrictions**: Medical record editing and deletion limited to 24-hour windows
- **Role-Based Access**: Different permissions for each medical profession via Django groups
- **Object-Level Permissions**: Fine-grained control over individual patient and event access
- **Custom Permission Backend**: Seamless integration with Django's permission system
- **Automatic Group Management**: Signal-based assignment ensures users always have correct permissions
- **Audit Trail Support**: Permission checks consider event creators and timestamps
- **Fail-Safe Defaults**: Permission functions return `False` for unauthorized access
- **CSRF Protection**: All permission-protected views include CSRF protection
- **Template-Level Security**: Permission checks available directly in templates
- **Personal Data Protection**: Strict controls on who can modify patient personal information

### Best Practices

1. **Always use decorators** for view-level permission checks
2. **Check permissions in templates** using template tags
3. **Use hospital context** for hospital-specific operations
4. **Implement object-level permissions** for fine-grained control
5. **Monitor performance** using cache statistics and benchmarks
6. **Test thoroughly** with different user roles and scenarios
7. **Follow time-based restrictions** for medical record integrity
8. **Use optimized queries** for better performance
9. **Invalidate cache** when permissions change
10. **Audit permission usage** regularly for security compliance
