# EquipeMed Simplified Permission System

## Overview

This document outlines the simplified permission system for EquipeMed. The system combines Django's built-in permission framework with streamlined object-level permissions to ensure users can only access and modify data according to their role and context.

## Key Concepts

### User Roles

Users in EquipeMed can have one of the following roles, determined by their `profession_type`:

- **Medical Doctor** (0): Full access to patient data and can change patient status
- **Resident** (1): Similar to doctors but with some restrictions
- **Nurse** (2): Can view and edit patient data but cannot change patient status
- **Physiotherapist** (3): Limited access to patient data
- **Student** (4): Limited access to patient data

### Hospital Context

A key concept in EquipeMed is the "hospital context":

- Users can be members of multiple hospitals
- Users can only be logged into one hospital at a time
- The current hospital is stored in the user's session
- Access to inpatient data is restricted based on the user's current hospital

### Patient Status

Patients can have one of the following statuses:

- **Inpatient** (0): Currently admitted to a hospital
- **Outpatient** (1): Not currently admitted
- **Deceased** (2): Deceased

Access to patient data depends on the patient's status and the user's hospital context.

## Permission Rules

### Patient Access

1. **All users can access outpatient data**
2. **All users can access inpatient data (except changing status or personal data)**
3. **For modifying inpatient status or personal data:**
   - Users must be members of the patient's hospital
   - Users must be logged into the patient's hospital

### Patient Status Changes

1. **Only medical doctors can change patient status**
2. **For inpatients:**
   - The doctor must be a member of the patient's hospital
   - The doctor must be logged into the patient's hospital
3. **For outpatients:**
   - Any doctor can change the status

### Patient Personal Data Changes

1. **For inpatients:**
   - Only medical doctors can change personal data
   - The doctor must be a member of the patient's hospital
   - The doctor must be logged into the patient's hospital
2. **For outpatients:**
   - Any doctor can change personal data

### Event Management

1. **All users can view and add events**
2. **Events can only be edited or deleted:**
   - By the user who created the event
   - Within 24 hours of creation

## Implementation

### Permission Checks

The system uses utility functions for permission checks:

- `can_access_patient(user, patient)`: Checks if a user can access a patient's data
- `can_change_patient_status(user, patient)`: Checks if a user can change a patient's status
- `can_change_patient_personal_data(user, patient)`: Checks if a user can change a patient's personal data
- `can_edit_event(user, event)`: Checks if a user can edit an event
- `can_delete_event(user, event)`: Checks if a user can delete an event
- `can_see_patient_in_search(user, patient)`: Checks if a user can see a patient in search results

### Hospital Context Management

The system uses a middleware to manage hospital context:

- `HospitalContextMiddleware`: Makes the current hospital available to views and templates

## Usage Examples

### Checking Permissions in Views

```python
from apps.core.permissions import can_access_patient

def get_object(self, queryset=None):
    obj = super().get_object()

    # Check if user can access this patient
    if not can_access_patient(self.request.user, obj):
        raise PermissionDenied("You don't have permission to access this patient's data")

    return obj
```

### Checking Permissions in Templates

```html
{% if can_change_patient_status(request.user, patient) %}
<a href="{% url 'patient_admit' patient.pk %}" class="btn btn-primary">Admit</a>
{% endif %}
```

## Setup and Maintenance

The permission system is set up using a management command:

```
python manage.py setup_permissions
```

This command:

1. Creates the permission groups
2. Assigns the appropriate permissions to each group
3. Assigns existing users to groups based on their profession type

When adding new users, make sure to assign them to the appropriate group based on their profession type.
