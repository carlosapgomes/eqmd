"""
Utility functions for permission checking in EquipeMed.

This module provides the core permission checking logic for various
operations in the EquipeMed application. It integrates with Django's
permission system and role-based access control.
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
    INPATIENT,
    OUTPATIENT,
    EMERGENCY,
    DISCHARGED,
    TRANSFERRED,
    EVENT_EDIT_TIME_LIMIT,
)


def can_access_patient(user: Any, patient: Any) -> bool:
    """
    Check if a user can access a specific patient.
    
    Rules:
    - Doctors and nurses can access patients in their current hospital
    - Students can only access outpatients in their current hospital
    - No access if user is not in the same hospital as patient
    
    Args:
        user: The user requesting access
        patient: The patient object
        
    Returns:
        bool: True if access is allowed, False otherwise
    """
    if not user.is_authenticated:
        return False
    
    # Check if user has a current hospital context (updated to use middleware)
    if not has_hospital_context(user):
        return False
    
    current_hospital = getattr(user, 'current_hospital', None)
    if not current_hospital:
        return False
    
    # Check if patient is in the same hospital
    patient_hospital_id = None
    if hasattr(patient, 'current_hospital') and patient.current_hospital:
        patient_hospital_id = patient.current_hospital.id
    elif hasattr(patient, 'current_hospital_id'):
        patient_hospital_id = patient.current_hospital_id
    
    if current_hospital.id != patient_hospital_id:
        return False
    
    # Get user profession type
    profession_type = getattr(user, 'profession_type', None)
    
    # Map integer values to constants for comparison
    profession_map = {
        0: MEDICAL_DOCTOR,  # User.MEDICAL_DOCTOR
        1: RESIDENT,        # User.RESIDENT 
        2: NURSE,           # User.NURSE
        3: PHYSIOTHERAPIST, # User.PHYSIOTERAPIST
        4: STUDENT,         # User.STUDENT
    }
    
    profession = profession_map.get(profession_type)
    
    # Doctors, nurses, physiotherapists, and residents have full access
    if profession in [MEDICAL_DOCTOR, NURSE, PHYSIOTHERAPIST, RESIDENT]:
        return True
    
    # Students have limited access - only outpatients
    if profession == STUDENT:
        patient_status = getattr(patient, 'status', None)
        return patient_status == OUTPATIENT
    
    return False


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
    if not user.is_authenticated:
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
    
    Rules:
    - Doctors can change any patient status
    - Nurses can change from emergency to inpatient, but cannot discharge
    - Students cannot change patient status
    
    Args:
        user: The user requesting the change
        patient: The patient object
        new_status: The new status to set
        
    Returns:
        bool: True if status change is allowed, False otherwise
    """
    if not user.is_authenticated:
        return False
    
    # Get user profession type and map to constants
    profession_type = getattr(user, 'profession_type', None)
    profession_map = {
        0: MEDICAL_DOCTOR,  # User.MEDICAL_DOCTOR
        1: RESIDENT,        # User.RESIDENT 
        2: NURSE,           # User.NURSE
        3: PHYSIOTHERAPIST, # User.PHYSIOTERAPIST
        4: STUDENT,         # User.STUDENT
    }
    profession = profession_map.get(profession_type)
    
    # Students cannot change patient status
    if profession == STUDENT:
        return False
    
    # Doctors can change any status
    if profession == MEDICAL_DOCTOR:
        return True
    
    # Nurses have limited status change abilities
    if profession in [NURSE, PHYSIOTHERAPIST, RESIDENT]:
        current_status = getattr(patient, 'status', None)
        
        # Nurses cannot discharge patients
        if new_status == DISCHARGED:
            return False
        
        # Nurses can admit emergency patients
        if current_status == EMERGENCY and new_status == INPATIENT:
            return True
        
        # Nurses can change between inpatient/outpatient/transferred
        if new_status in [INPATIENT, OUTPATIENT, TRANSFERRED]:
            return True
    
    return False


def is_doctor(user: Any) -> bool:
    """
    Check if a user is a doctor.
    
    Args:
        user: The user to check
        
    Returns:
        bool: True if user is a doctor, False otherwise
    """
    if not user.is_authenticated:
        return False
    
    profession_type = getattr(user, 'profession_type', None)
    profession_map = {
        0: MEDICAL_DOCTOR,  # User.MEDICAL_DOCTOR
        1: RESIDENT,        # User.RESIDENT 
        2: NURSE,           # User.NURSE
        3: PHYSIOTHERAPIST, # User.PHYSIOTERAPIST
        4: STUDENT,         # User.STUDENT
    }
    profession = profession_map.get(profession_type)
    return profession == MEDICAL_DOCTOR


def has_hospital_context(user: Any) -> bool:
    """
    Check if a user has a valid hospital context.

    Args:
        user: The user to check

    Returns:
        bool: True if user has hospital context, False otherwise
    """
    if not user.is_authenticated:
        return False

    # Updated to use middleware-provided hospital context
    return getattr(user, 'has_hospital_context', False)


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


def can_manage_hospitals(user: Any) -> bool:
    """
    Check if user can manage hospitals (add, change, delete).

    Args:
        user: The user to check

    Returns:
        bool: True if user can manage hospitals, False otherwise
    """
    if not user.is_authenticated:
        return False

    required_permissions = [
        'hospitals.add_hospital',
        'hospitals.change_hospital',
        'hospitals.delete_hospital',
    ]

    return all(user.has_perm(perm) for perm in required_permissions)


def can_view_hospitals(user: Any) -> bool:
    """
    Check if user can view hospitals.

    Args:
        user: The user to check

    Returns:
        bool: True if user can view hospitals, False otherwise
    """
    if not user.is_authenticated:
        return False

    return user.has_perm('hospitals.view_hospital')