"""
Simplified utility functions for permission checking in EquipeMed.

This module provides simplified role-based permission checking logic
after removing hospital context complexity.
"""

from django.utils import timezone
from datetime import timedelta
from typing import Any, Optional

from .constants import (
    MEDICAL_DOCTOR,
    NURSE,
    PHYSIOTHERAPIST,
    RESIDENT,
    STUDENT,
    OUTPATIENT,
    DISCHARGED,
    EVENT_EDIT_TIME_LIMIT,
)


def can_access_patient(user: Any, patient: Any) -> bool:
    """
    Check if a user can access a specific patient.
    
    Simplified Rules:
    - All authenticated users can access all patients
    
    Args:
        user: The user requesting access
        patient: The patient object
        
    Returns:
        bool: True if access is allowed, False otherwise
    """
    if user is None or patient is None:
        return False
    return getattr(user, 'is_authenticated', False)


def can_edit_event(user: Any, event: Any) -> bool:
    """
    Check if a user can edit a specific event.
    
    Rules:
    - Only the event creator can edit events
    - Events can only be edited within 24 hours of creation
    
    Args:
        user: The user requesting to edit
        event: The event object
        
    Returns:
        bool: True if editing is allowed, False otherwise
    """
    if user is None or event is None:
        return False
    
    if not getattr(user, 'is_authenticated', False):
        return False
    
    # Check if user is the creator
    event_creator = getattr(event, 'created_by', None)
    if event_creator != user:
        return False
    
    # Check time limit
    created_at = getattr(event, 'created_at', None)
    if not created_at:
        return False
    
    time_limit = timedelta(hours=EVENT_EDIT_TIME_LIMIT)
    if timezone.now() - created_at > time_limit:
        return False
    
    return True


def can_change_patient_status(user: Any, patient: Any, new_status: str) -> bool:
    """
    Check if a user can change a patient's status.
    
    Simplified Rules:
    - Doctors/Residents: Can change any patient status (including discharge)
    - Others: Cannot discharge patients
    
    Args:
        user: The user requesting the change
        patient: The patient object
        new_status: The new status to set
        
    Returns:
        bool: True if status change is allowed, False otherwise
    """
    if user is None or patient is None:
        return False
    
    if not getattr(user, 'is_authenticated', False):
        return False
    
    # Get user profession type
    profession_type = getattr(user, 'profession_type', None)
    
    # Doctors and residents can change any status including discharge
    if profession_type in [0, 1]:  # MEDICAL_DOCTOR, RESIDENT
        return True
    
    # Others cannot discharge patients
    if new_status == DISCHARGED:
        return False
    
    # All other status changes are allowed for non-doctors
    return True


def is_doctor(user: Any) -> bool:
    """
    Check if a user is a doctor.
    
    Args:
        user: The user to check
        
    Returns:
        bool: True if user is a doctor, False otherwise
    """
    if user is None:
        return False
    
    if not getattr(user, 'is_authenticated', False):
        return False
    
    profession_type = getattr(user, 'profession_type', None)
    return profession_type == 0  # User.MEDICAL_DOCTOR


def is_doctor_or_resident(user: Any) -> bool:
    """
    Check if a user is a doctor or resident.
    
    Args:
        user: The user to check
        
    Returns:
        bool: True if user is a doctor or resident, False otherwise
    """
    if user is None:
        return False
    
    if not getattr(user, 'is_authenticated', False):
        return False
    
    profession_type = getattr(user, 'profession_type', None)
    return profession_type in [0, 1]  # MEDICAL_DOCTOR or RESIDENT


def has_django_permission(user: Any, permission: str) -> bool:
    """
    Check if user has a specific Django permission.

    Args:
        user: The user to check
        permission: Permission string (e.g., 'patients.add_patient')

    Returns:
        bool: True if user has permission, False otherwise
    """
    if not user.is_authenticated:
        return False

    return user.has_perm(permission)


def is_in_group(user: Any, group_name: str) -> bool:
    """
    Check if user is in a specific group.

    Args:
        user: The user to check
        group_name: Name of the group

    Returns:
        bool: True if user is in group, False otherwise
    """
    if not user.is_authenticated:
        return False

    return user.groups.filter(name=group_name).exists()


def get_user_profession_type(user: Any) -> Optional[str]:
    """
    Get user's profession type as a string constant.

    Args:
        user: The user to check

    Returns:
        str: Profession type constant or None
    """
    if not user.is_authenticated:
        return None

    profession_type = getattr(user, 'profession_type', None)
    profession_map = {
        0: MEDICAL_DOCTOR,
        1: RESIDENT,
        2: NURSE,
        3: PHYSIOTHERAPIST,
        4: STUDENT,
    }

    return profession_map.get(profession_type)


def can_manage_patients(user: Any) -> bool:
    """
    Check if user can manage patients (add, change, delete).

    Args:
        user: The user to check

    Returns:
        bool: True if user can manage patients, False otherwise
    """
    if not user.is_authenticated:
        return False

    required_permissions = [
        'patients.add_patient',
        'patients.change_patient',
        'patients.delete_patient',
    ]

    return all(user.has_perm(perm) for perm in required_permissions)


def can_view_patients(user: Any) -> bool:
    """
    Check if user can view patients.

    Args:
        user: The user to check

    Returns:
        bool: True if user can view patients, False otherwise
    """
    if not user.is_authenticated:
        return False

    return user.has_perm('patients.view_patient')


def can_manage_events(user: Any) -> bool:
    """
    Check if user can manage events (add, change, delete).

    Args:
        user: The user to check

    Returns:
        bool: True if user can manage events, False otherwise
    """
    if not user.is_authenticated:
        return False

    required_permissions = [
        'events.add_event',
        'events.change_event',
        'events.delete_event',
    ]

    return all(user.has_perm(perm) for perm in required_permissions)


def can_view_events(user: Any) -> bool:
    """
    Check if user can view events.

    Args:
        user: The user to check

    Returns:
        bool: True if user can view events, False otherwise
    """
    if not user.is_authenticated:
        return False

    return user.has_perm('events.view_event')


def can_change_patient_personal_data(user: Any, patient: Any) -> bool:
    """
    Check if a user can change a patient's personal data.

    Simplified Rules:
    - Only doctors and residents can change personal data

    Args:
        user: The user requesting the change
        patient: The patient object

    Returns:
        bool: True if personal data change is allowed, False otherwise
    """
    if user is None or patient is None:
        return False
    
    if not getattr(user, 'is_authenticated', False):
        return False

    # Only doctors and residents can change patient personal data
    return is_doctor_or_resident(user)


def can_delete_event(user: Any, event: Any) -> bool:
    """
    Check if a user can delete a specific event.

    Rules:
    - Only the event creator can delete events
    - Events can only be deleted within 24 hours of creation

    Args:
        user: The user requesting to delete
        event: The event object

    Returns:
        bool: True if deletion is allowed, False otherwise
    """
    if user is None or event is None:
        return False
    
    if not getattr(user, 'is_authenticated', False):
        return False

    # Check if user is the creator
    event_creator = getattr(event, 'created_by', None)
    if event_creator != user:
        return False

    # Check time limit
    created_at = getattr(event, 'created_at', None)
    if not created_at:
        return False

    time_limit = timedelta(hours=EVENT_EDIT_TIME_LIMIT)
    if timezone.now() - created_at > time_limit:
        return False

    return True


def can_see_patient_in_search(user: Any, patient: Any) -> bool:
    """
    Check if a user can see a patient in search results.

    Args:
        user: The user performing the search
        patient: The patient object

    Returns:
        bool: True if patient should be visible in search, False otherwise
    """
    # Same as can_access_patient
    return can_access_patient(user, patient)


def get_user_accessible_patients(user: Any):
    """
    Get patients accessible to user (simplified - all patients for authenticated users).
    
    Args:
        user: The user requesting access
        
    Returns:
        QuerySet: All patients for authenticated users
    """
    if not user.is_authenticated:
        from apps.patients.models import Patient
        return Patient.objects.none()
    
    from apps.patients.models import Patient
    return Patient.objects.all()


def can_create_event_type(user: Any, patient: Any, event_type: str) -> bool:
    """
    Check if user can create specific event type for patient.
    
    Simplified Rules:
    - All authenticated users can create all event types
    
    Args:
        user: The user requesting to create the event
        patient: The patient object
        event_type: The type of event to create
        
    Returns:
        bool: True if user can create this event type, False otherwise
    """
    return user.is_authenticated