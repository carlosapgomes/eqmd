# EquipeMed Permission System Documentation

## Overview

The EquipeMed permission system provides simple role-based access control for medical staff in a single-hospital environment. This documentation covers the complete permission framework implementation.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Permission Model](#permission-model)
3. [Permission Utilities](#permission-utilities)
4. [Decorators](#decorators)
5. [Template Tags](#template-tags)
6. [Role-Based Permissions](#role-based-permissions)
7. [Object-Level Permissions](#object-level-permissions)
8. [Management Commands](#management-commands)
9. [Testing](#testing)
10. [Security Considerations](#security-considerations)

## Architecture Overview

The permission system is organized into several modules:

```
apps/core/permissions/
├── __init__.py          # Public API exports
├── constants.py         # Permission constants and profession types
├── utils.py            # Core permission checking functions
├── decorators.py       # View-level permission decorators
└── cache.py            # Permission caching utilities
```

### Key Components

- **Permission Utilities**: Core functions for checking permissions
- **Decorators**: View-level permission enforcement
- **Template Tags**: Permission checking in templates
- **Role-Based Groups**: Automatic group assignment based on profession
- **Object-Level Permissions**: Fine-grained access control
- **Performance Optimization**: Caching and query optimization

## Permission Model

**Simple 2-Tier System:**

### Tier 1: Doctors & Residents
- Full access to all patients regardless of status
- Can discharge patients
- Can edit patient personal data
- Can create and edit all types of events

### Tier 2: Others (Nurses, Physiotherapists, Students)
- Full access to all patients regardless of status
- Limited status changes (cannot discharge)
- Cannot edit patient personal data
- Can create and edit events (role-specific restrictions may apply)

**Key Simplifications:**
- **Universal Patient Access**: All medical staff can access all patients
- **No Hospital Context**: Single hospital environment eliminates hospital-based restrictions
- **Focus on Role Differences**: Permissions based on medical profession capabilities

## Permission Utilities

The core permission utilities are located in `apps/core/permissions/utils.py` and provide the foundation for all permission checking.

### Patient Access Control

#### `can_access_patient(user, patient)`
**Always returns True** - All medical staff can access all patients in the single-hospital environment.

```python
from apps.core.permissions import can_access_patient

if can_access_patient(request.user, patient):
    # All authenticated medical staff can access any patient
    pass
```

#### `can_change_patient_status(user, patient, new_status)`
Controls who can change patient status based on role.

**Rules:**
- **Doctors/Residents**: Can change any patient status (including discharge)
- **Others**: Limited status changes (cannot discharge patients)

#### `can_change_patient_personal_data(user, patient)`
Controls who can modify patient personal information.

**Rules:**
- **Doctors/Residents**: Can change patient personal data
- **Others**: Cannot change patient personal data

#### `get_user_accessible_patients(user)`
Returns all patients for all authenticated medical staff (universal access).

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

### Role Checking

#### `is_doctor(user)`
Check if user is a doctor.

#### `is_resident(user)`
Check if user is a resident.

#### `get_user_profession_type(user)`
Get the profession type for a user.

### Convenience Functions

#### `can_manage_patients(user)`
Check if user can manage patients (add, change, delete).

#### `can_view_patients(user)`
Check if user can view patients (always True for authenticated users).

#### `can_manage_events(user)`
Check if user can manage events.

#### `can_view_events(user)`
Check if user can view events.

## Decorators

Permission decorators provide view-level access control and are located in `apps/core/permissions/decorators.py`.

### Available Decorators

#### `@patient_access_required`
Validates user access to the specified patient (always passes for authenticated users).

```python
from apps.core.permissions import patient_access_required

@patient_access_required
def patient_detail_view(request, patient_id):
    # All authenticated users can access any patient
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

#### `@patient_data_change_required`
Validates user can change patient personal data.

```python
from apps.core.permissions import patient_data_change_required

@patient_data_change_required
def patient_edit_personal_data_view(request, patient_id):
    # Only doctors/residents can access this view
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

### Multiple Permission Checks

```django
<!-- Multiple permission checks -->
{% check_multiple_permissions user "patients.add_patient" "patients.change_patient" as has_all_perms %}
{% if has_all_perms %}
    <p>You have all required permissions</p>
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

## Role-Based Permissions

The system automatically assigns users to profession-based groups using Django signals and management commands.

### Automatic Group Assignment

Users are automatically assigned to groups based on their profession type:

- **Medical Doctors**: Full permissions for all models and operations
- **Residents**: Full patient access, can discharge, can edit personal data
- **Nurses**: Full patient access, limited status changes, cannot edit personal data
- **Physiotherapists**: Full patient access, limited status changes, cannot edit personal data
- **Students**: Full patient access, limited status changes, cannot edit personal data

### Group Setup

```bash
# Set up all profession-based groups with appropriate permissions
uv run python manage.py setup_groups

# Force recreation of groups (removes existing groups first)
uv run python manage.py setup_groups --force
```

## Object-Level Permissions

The system implements fine-grained object-level permissions through a custom permission backend.

### Supported Object-Level Permissions

- `patients.change_patient_personal_data`
- `events.edit_event`
- `events.delete_event`

```python
# Using Django's permission system with objects
if user.has_perm('patients.change_patient_personal_data', patient):
    # Only doctors/residents can change patient personal data
    pass

if user.has_perm('events.delete_event', event):
    # Only event creator can delete within 24h window
    pass
```

## Management Commands

### Setup Groups Command

```bash
# Set up all profession-based groups
uv run python manage.py setup_groups

# Force recreation of groups
uv run python manage.py setup_groups --force
```

### Permission Audit Command

```bash
# Show permission audit report
uv run python manage.py permission_audit --action=report

# Assign user to group
uv run python manage.py user_permissions --action=assign
```

## Testing

The permission system includes comprehensive test coverage for the simplified system:

- **Simplified Permission Tests**: Universal patient access validation
- **Role-Based Tests**: Doctor/resident vs others permission differences
- **Event Permission Tests**: Time-based editing and deletion restrictions
- **Integration Tests**: End-to-end permission workflows

### Running Tests

```bash
# Run all permission tests
uv run python manage.py test apps.core.tests.test_permissions

# Run specific test modules
uv run python manage.py test apps.core.tests.test_permissions.test_utils
uv run python manage.py test apps.core.tests.test_permissions.test_simplified_system
```

## Security Considerations

The simplified permission system maintains security while reducing complexity:

- **Universal Patient Access**: All medical staff can access all patients (appropriate for single hospital)
- **Role-Based Restrictions**: Different capabilities based on medical profession
- **Time-Based Restrictions**: Medical record editing limited to 24-hour windows
- **Personal Data Protection**: Only doctors/residents can modify sensitive patient data
- **Event Creator Protection**: Only creators can edit/delete their own events
- **Discharge Protection**: Only doctors/residents can discharge patients
- **Audit Trail Support**: All permission checks consider timestamps and creators

### Best Practices

1. **Use decorators** for view-level permission checks
2. **Check permissions in templates** using template tags
3. **Implement object-level permissions** for fine-grained control
4. **Test thoroughly** with different user roles and scenarios
5. **Follow time-based restrictions** for medical record integrity
6. **Audit permission usage** regularly for security compliance

### Migration from Multi-Hospital System

**Key Changes:**
- Removed hospital context requirements
- Universal patient access for all medical staff
- Simplified permission checking (no hospital membership validation)
- Focus on role-based capabilities rather than location-based access
- Environment-based hospital configuration instead of database models