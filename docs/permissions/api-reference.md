# EquipeMed Permission System - API Reference

## Overview

This document provides a comprehensive API reference for the EquipeMed permission system, including all utility functions, decorators, template tags, and management commands for single hospital operations.

## Table of Contents

1. [Permission Utilities](#permission-utilities)
2. [Permission Decorators](#permission-decorators)
3. [Template Tags](#template-tags)
4. [Cache Utilities](#cache-utilities)
5. [Query Optimization](#query-optimization)
6. [Custom Permission Backend](#custom-permission-backend)
7. [Management Commands](#management-commands)
8. [Constants](#constants)

## Permission Utilities

All permission utility functions are available in `apps.core.permissions.utils`.

### Patient Access Functions

#### `can_access_patient(user, patient) -> bool`

Check if a user can access a specific patient.

**Parameters:**

- `user` (User): The user to check permissions for
- `patient` (Patient): The patient object to check access to

**Returns:**

- `bool`: True if user can access the patient, False otherwise

**Rules:**

- **Universal Access**: All medical staff can access all patients in the single hospital environment
- **Simplified Architecture**: No hospital context restrictions for single hospital operations

**Example:**

```python
from apps.core.permissions import can_access_patient

if can_access_patient(request.user, patient):
    # User can access this patient
    return render(request, 'patient_detail.html', {'patient': patient})
else:
    return HttpResponseForbidden("Access denied")
```

#### `can_change_patient_status(user, patient, new_status) -> bool`

Check if a user can change a patient's status.

**Parameters:**

- `user` (User): The user to check permissions for
- `patient` (Patient): The patient object
- `new_status` (str): The new status to change to

**Returns:**

- `bool`: True if user can change the status, False otherwise

**Rules:**

- Doctors & Residents: Can change any patient status (including discharge)
- Nurses/Physiotherapists: Limited status changes (cannot discharge patients)
- Students: Cannot change patient status
- Special rule: Nurses can admit emergency patients to inpatient status

**Example:**

```python
from apps.core.permissions import can_change_patient_status

if can_change_patient_status(request.user, patient, 'discharged'):
    # User can discharge this patient
    patient.status = 'discharged'
    patient.save()
```

#### `can_change_patient_personal_data(user, patient) -> bool`

Check if a user can modify patient personal information.

**Parameters:**

- `user` (User): The user to check permissions for
- `patient` (Patient): The patient object

**Returns:**

- `bool`: True if user can change personal data, False otherwise

**Rules:**

- **Doctors/Residents**: Can change patient personal data
- **Others**: Cannot change patient personal data
- **Universal Access**: All doctors and residents can edit personal data for any patient in the hospital

**Example:**

```python
from apps.core.permissions import can_change_patient_personal_data

if can_change_patient_personal_data(request.user, patient):
    # User can edit patient personal information
    form = PatientPersonalDataForm(instance=patient)
```

#### `can_see_patient_in_search(user, patient) -> bool`

Check if a patient should be visible in search results for a user.

**Parameters:**

- `user` (User): The user performing the search
- `patient` (Patient): The patient object

**Returns:**

- `bool`: True if patient should be visible, False otherwise

**Example:**

```python
from apps.core.permissions import can_see_patient_in_search

# Filter search results based on permissions
visible_patients = [
    patient for patient in search_results 
    if can_see_patient_in_search(request.user, patient)
]
```

### Event Management Functions

#### `can_edit_event(user, event) -> bool`

Check if a user can edit a specific event.

**Parameters:**

- `user` (User): The user to check permissions for
- `event` (Event): The event object

**Returns:**

- `bool`: True if user can edit the event, False otherwise

**Rules:**

- Only event creators can edit their events
- Editing restricted to 24 hours after event creation

**Example:**

```python
from apps.core.permissions import can_edit_event

if can_edit_event(request.user, event):
    # User can edit this event
    form = EventForm(instance=event)
```

#### `can_delete_event(user, event) -> bool`

Check if a user can delete a specific event.

**Parameters:**

- `user` (User): The user to check permissions for
- `event` (Event): The event object

**Returns:**

- `bool`: True if user can delete the event, False otherwise

**Rules:**

- Only event creators can delete their events
- Events can only be deleted within 24 hours of creation

**Example:**

```python
from apps.core.permissions import can_delete_event

if can_delete_event(request.user, event):
    # User can delete this event
    event.delete()
```

### Role and Context Functions

#### `is_doctor(user) -> bool`

Check if a user is a medical doctor.

**Parameters:**

- `user` (User): The user to check

**Returns:**

- `bool`: True if user is a doctor, False otherwise

**Example:**

```python
from apps.core.permissions import is_doctor

if is_doctor(request.user):
    # Doctor-only functionality
    pass
```

#### `get_user_profession_type(user) -> str`

Get the profession type for a user.

**Parameters:**

- `user` (User): The user to get profession type for

**Returns:**

- `str`: The profession type string

**Example:**

```python
from apps.core.permissions import get_user_profession_type

profession = get_user_profession_type(request.user)
if profession == 'medical_doctor':
    # Doctor-specific logic
    pass
```

### Django Permission Helpers

#### `has_django_permission(user, permission) -> bool`

Check if user has a specific Django permission.

**Parameters:**

- `user` (User): The user to check
- `permission` (str): Permission string (e.g., 'patients.add_patient')

**Returns:**

- `bool`: True if user has permission, False otherwise

**Example:**

```python
from apps.core.permissions import has_django_permission

if has_django_permission(request.user, 'patients.add_patient'):
    # User can add patients
    pass
```

#### `is_in_group(user, group_name) -> bool`

Check if user is in a specific group.

**Parameters:**

- `user` (User): The user to check
- `group_name` (str): Name of the group

**Returns:**

- `bool`: True if user is in group, False otherwise

**Example:**

```python
from apps.core.permissions import is_in_group

if is_in_group(request.user, 'Medical Doctors'):
    # User is in Medical Doctors group
    pass
```

### Convenience Functions

#### `can_manage_patients(user) -> bool`

Check if user can manage patients (add, change, delete).

#### `can_view_patients(user) -> bool`

Check if user can view patients.

#### `can_manage_events(user) -> bool`

Check if user can manage events.

#### `can_view_events(user) -> bool`

Check if user can view events.

**Example:**

```python
from apps.core.permissions import can_manage_patients, can_view_events

if can_manage_patients(request.user):
    # Show patient management interface
    pass

if can_view_events(request.user):
    # Show events list
    pass
```

## Permission Decorators

All decorators are available in `apps.core.permissions.decorators`.

### `@patient_access_required`

Decorator that checks if user can access the patient specified in the URL.

**Parameters:**

- Expects 'patient_id' or 'pk' parameter in the view function

**Returns:**

- `HttpResponseForbidden` if access denied
- Calls the original view if access granted

**Example:**

```python
from apps.core.permissions import patient_access_required

@patient_access_required
def patient_detail_view(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    return render(request, 'patient_detail.html', {'patient': patient})
```

### `@doctor_required`

Decorator that requires the user to be a doctor.

**Example:**

```python
from apps.core.permissions import doctor_required

@doctor_required
def discharge_patient_view(request, patient_id):
    # Only doctors can access this view
    pass
```

### `@can_edit_event_required`

Decorator that checks if user can edit the event specified in the URL.

**Parameters:**

- Expects 'event_id' or 'pk' parameter in the view function

**Example:**

```python
from apps.core.permissions import can_edit_event_required

@can_edit_event_required
def event_edit_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    # User can edit this event
    pass
```

### `@hospital_context_required`

Decorator that ensures user has hospital context.

**Example:**

```python
from apps.core.permissions import hospital_context_required

@hospital_context_required
def hospital_specific_view(request):
    # User has selected a current hospital
    current_hospital = request.user.current_hospital
    pass
```

### `@patient_data_change_required`

Decorator that checks if user can change patient personal data.

**Parameters:**

- Expects 'patient_id' or 'pk' parameter in the view function

**Example:**

```python
from apps.core.permissions import patient_data_change_required

@patient_data_change_required
def patient_edit_personal_data_view(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    # User can change patient personal data
    pass
```

### `@can_delete_event_required`

Decorator that checks if user can delete the event specified in the URL.

**Parameters:**

- Expects 'event_id' or 'pk' parameter in the view function

**Example:**

```python
from apps.core.permissions import can_delete_event_required

@can_delete_event_required
def event_delete_view(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    # User can delete this event
    pass
```

## Template Tags

All template tags are available by loading `permission_tags`.

### Basic Permission Filters

#### `has_permission`

Check if user has a specific Django permission.

**Usage:**

```django
{% load permission_tags %}
{% if user|has_permission:"patients.add_patient" %}
    <a href="{% url 'patients:create' %}">Add Patient</a>
{% endif %}
```

#### `in_group`

Check if user is in a specific group.

**Usage:**

```django
{% if user|in_group:"Medical Doctors" %}
    <p>Welcome, Doctor!</p>
{% endif %}
```

#### `is_profession`

Check if user has a specific profession type.

**Usage:**

```django
{% if user|is_profession:"medical_doctor" %}
    <p>Doctor-specific content</p>
{% endif %}
```

### Convenience Permission Filters

#### `can_manage_patients`

Check if user can manage patients.

**Usage:**

```django
{% if user|can_manage_patients %}
    <a href="{% url 'patients:create' %}">Add Patient</a>
{% endif %}
```

#### `can_view_events`

Check if user can view events.

**Usage:**

```django
{% if user|can_view_events %}
    <a href="{% url 'events:list' %}">View Events</a>
{% endif %}
```

### Object-Level Permission Tags

#### `can_user_change_patient_personal_data`

Check if user can change patient personal data.

**Usage:**

```django
{% can_user_change_patient_personal_data user patient as can_change_data %}
{% if can_change_data %}
    <a href="{% url 'patients:edit_personal_data' patient.pk %}">Edit Personal Data</a>
{% endif %}
```

#### `can_user_delete_event`

Check if user can delete an event.

**Usage:**

```django
{% can_user_delete_event user event as can_delete %}
{% if can_delete %}
    <button class="btn btn-danger" onclick="deleteEvent('{{ event.pk }}')">Delete Event</button>
{% endif %}
```

### Multiple Permission Tags

#### `check_multiple_permissions`

Check if user has all of the specified permissions.

**Usage:**

```django
{% check_multiple_permissions user "patients.add_patient" "patients.change_patient" as has_all_perms %}
{% if has_all_perms %}
    <p>You have all required permissions</p>
{% endif %}
```

#### `check_any_permission`

Check if user has any of the specified permissions.

**Usage:**

```django
{% check_any_permission user "patients.add_patient" "patients.view_patient" as has_any_perm %}
{% if has_any_perm %}
    <p>You have at least one permission</p>
{% endif %}
```

### Debug and Performance Tags

#### `permission_debug`

Display debug information about user permissions.

**Usage:**

```django
{% permission_debug user %}
```

#### `permission_performance_widget`

Display performance information about permission checks.

**Usage:**

```django
{% permission_performance_widget user %}
```

#### `permission_cache_stats`

Get cache statistics for permission system.

**Usage:**

```django
{% permission_cache_stats as cache_stats %}
<p>Cache hit ratio: {{ cache_stats.hit_ratio|floatformat:2 }}%</p>
```

## Cache Utilities

All cache utilities are available in `apps.core.permissions.cache`.

### `cache_permission_result(permission_type, use_object_id=False, timeout=None)`

Decorator for caching permission check results.

**Parameters:**

- `permission_type` (str): Type of permission being cached
- `use_object_id` (bool): Whether to include object ID in cache key
- `timeout` (int): Cache timeout in seconds

**Example:**

```python
from apps.core.permissions.cache import cache_permission_result

@cache_permission_result('can_access_patient', use_object_id=True)
def can_access_patient(user, patient):
    # Function implementation
    pass
```

### `invalidate_user_permissions(user_id)`

Invalidate all cached permissions for a specific user.

**Parameters:**

- `user_id` (int): The user's ID

**Example:**

```python
from apps.core.permissions import invalidate_user_permissions

# When user's role changes
invalidate_user_permissions(user.id)
```

### `invalidate_object_permissions(object_type, object_id)`

Invalidate cached permissions for a specific object.

**Parameters:**

- `object_type` (str): Type of object (e.g., 'patient', 'event')
- `object_id` (str): ID of the object

**Example:**

```python
from apps.core.permissions import invalidate_object_permissions

# When patient data changes
invalidate_object_permissions('patient', patient.id)
```

### `clear_permission_cache()`

Clear all permission cache.

**Example:**

```python
from apps.core.permissions import clear_permission_cache

# Clear all cached permissions
clear_permission_cache()
```

### `get_cache_stats()`

Get cache statistics.

**Returns:**

- `dict`: Cache statistics including hits, misses, and hit ratio

**Example:**

```python
from apps.core.permissions import get_cache_stats

stats = get_cache_stats()
print(f"Hit ratio: {stats['hit_ratio']:.2%}")
```

### `is_caching_enabled()`

Check if permission caching is enabled.

**Returns:**

- `bool`: True if caching is enabled, False otherwise

**Example:**

```python
from apps.core.permissions import is_caching_enabled

if is_caching_enabled():
    # Caching-specific logic
    pass
```

## Query Optimization

All query optimization utilities are available in `apps.core.permissions.queries`.

### `get_optimized_user_queryset()`

Get a user queryset with optimized permission-related queries.

**Returns:**

- `QuerySet`: Optimized user queryset

**Example:**

```python
from apps.core.permissions.queries import get_optimized_user_queryset

# Get users with prefetched permission data
users = get_optimized_user_queryset().filter(is_active=True)
```

### `get_optimized_patient_queryset()`

Get a patient queryset with optimized queries.

**Returns:**

- `QuerySet`: Optimized patient queryset

### `get_optimized_event_queryset()`

Get an event queryset with optimized queries.

**Returns:**

- `QuerySet`: Optimized event queryset

### `get_patients_for_user(user)`

Get patients accessible to a specific user.

**Parameters:**

- `user` (User): The user to get patients for

**Returns:**

- `QuerySet`: Patients accessible to the user

**Example:**

```python
from apps.core.permissions.queries import get_patients_for_user

# Get all patients user can access
accessible_patients = get_patients_for_user(request.user)
```

### `get_events_for_user(user)`

Get events accessible to a specific user.

**Parameters:**

- `user` (User): The user to get events for

**Returns:**

- `QuerySet`: Events accessible to the user

### `get_recent_patients_optimized(user, limit=10)`

Get recent patients with optimized queries.

**Parameters:**

- `user` (User): The user to get patients for
- `limit` (int): Maximum number of patients to return

**Returns:**

- `QuerySet`: Recent patients with optimized queries

### `get_permission_summary_optimized(user)`

Get a comprehensive permission summary with optimized queries.

**Parameters:**

- `user` (User): The user to get summary for

**Returns:**

- `dict`: Comprehensive permission summary

**Example:**

```python
from apps.core.permissions.queries import get_permission_summary_optimized

summary = get_permission_summary_optimized(request.user)
print(f"Total permissions: {summary['permission_counts']['total_permissions']}")
```

## Custom Permission Backend

The custom permission backend is available in `apps.core.backends.EquipeMedPermissionBackend`.

### Supported Object-Level Permissions

- `patients.access_patient`
- `patients.change_patient_personal_data`
- `patients.see_patient_in_search`
- `events.edit_event`
- `events.delete_event`

**Example:**

```python
# Using Django's permission system with objects
if user.has_perm('patients.change_patient_personal_data', patient):
    # User can change this specific patient's personal data
    pass

if user.has_perm('events.delete_event', event):
    # User can delete this specific event
    pass
```

## Management Commands

### setup_groups

Set up role-based permission groups.

**Usage:**

```bash
# Set up all profession-based groups
uv run python manage.py setup_groups

# Force recreation of groups
uv run python manage.py setup_groups --force
```

### permission_performance

Monitor and analyze permission system performance.

**Usage:**

```bash
# Show cache statistics
uv run python manage.py permission_performance --action=stats

# Run benchmarks
uv run python manage.py permission_performance --action=benchmark --iterations=1000

# Clear cache
uv run python manage.py permission_performance --action=clear-cache

# Test query optimization
uv run python manage.py permission_performance --action=test-queries --user-id=1
```

## Constants

All constants are available in `apps.core.permissions.constants`.

### Profession Types

- `MEDICAL_DOCTOR = 'medical_doctor'`
- `NURSE = 'nurse'`
- `PHYSIOTHERAPIST = 'physiotherapist'`
- `RESIDENT = 'resident'`
- `STUDENT = 'student'`

### Patient Status Types

- `INPATIENT = 'inpatient'`
- `OUTPATIENT = 'outpatient'`
- `EMERGENCY = 'emergency'`
- `DISCHARGED = 'discharged'`
- `TRANSFERRED = 'transferred'`

### Permission Codes

- `PERM_ACCESS_PATIENT = 'access_patient'`
- `PERM_EDIT_EVENT = 'edit_event'`
- `PERM_DELETE_EVENT = 'delete_event'`
- `PERM_CHANGE_PATIENT_STATUS = 'change_patient_status'`
- `PERM_CHANGE_PATIENT_DATA = 'change_patient_data'`
- `PERM_DISCHARGE_PATIENT = 'discharge_patient'`

### Time and Cache Settings

- `EVENT_EDIT_TIME_LIMIT = 24`  # Hours
- `PERMISSION_CACHE_TIMEOUT = 300`  # Seconds
- `PERMISSION_CACHE_PREFIX = 'eqmd_perm'`

**Example:**

```python
from apps.core.permissions.constants import MEDICAL_DOCTOR, EVENT_EDIT_TIME_LIMIT

if user.profession_type == MEDICAL_DOCTOR:
    # Doctor-specific logic
    pass

# Check if event is within edit time limit
time_since_creation = timezone.now() - event.created_at
if time_since_creation.total_seconds() / 3600 <= EVENT_EDIT_TIME_LIMIT:
    # Event can still be edited
    pass
```
