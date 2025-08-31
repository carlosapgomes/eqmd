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
    DECEASED,
    EVENT_EDIT_TIME_LIMIT,
    ADMISSION_EDIT_TIME_LIMIT,
    DISCHARGE_EDIT_TIME_LIMIT,
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
    
    Rules:
    - If patient is currently deceased: Only admin/superuser can change status
    - Changing TO deceased: Doctors/Residents can declare death
    - Discharge: Doctors/Residents only
    - Other status changes: All authenticated users
    
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
    
    # If patient is currently deceased, only admin/superuser can change status
    current_status = getattr(patient, 'status', None)
    if current_status == DECEASED:
        return getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)
    
    # Get user profession type
    profession_type = getattr(user, 'profession_type', None)
    
    # Changing TO deceased: Only doctors/residents can declare death
    if new_status == DECEASED:
        return profession_type in [0, 1]  # MEDICAL_DOCTOR, RESIDENT
    
    # Discharge: Only doctors/residents
    if new_status == DISCHARGED:
        return profession_type in [0, 1]  # MEDICAL_DOCTOR, RESIDENT
    
    # All other status changes are allowed for authenticated users
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


def can_manage_patient_tags(user: Any, patient: Any) -> bool:
    """
    Check if a user can manage (add/remove) tags for a patient.
    
    Rules:
    - User must be authenticated
    - User must have 'patients.change_patient' permission
    - User must be able to access the patient
    
    Args:
        user: The user requesting tag management
        patient: The patient object
        
    Returns:
        bool: True if tag management is allowed, False otherwise
    """
    if user is None or patient is None:
        return False
    
    if not getattr(user, 'is_authenticated', False):
        return False
    
    # Check if user can access patient
    if not can_access_patient(user, patient):
        return False
    
    # Check if user has required permission
    return user.has_perm('patients.change_patient')


def can_add_patient_tag(user: Any, patient: Any, allowed_tag: Any) -> bool:
    """
    Check if a user can add a specific tag to a patient.
    
    Rules:
    - Must pass can_manage_patient_tags check
    - AllowedTag must be active
    - Tag must not already be assigned to patient
    
    Args:
        user: The user requesting to add the tag
        patient: The patient object
        allowed_tag: The AllowedTag object to add
        
    Returns:
        bool: True if tag addition is allowed, False otherwise
    """
    if not can_manage_patient_tags(user, patient):
        return False
    
    # Check if allowed_tag is active
    if not getattr(allowed_tag, 'is_active', True):
        return False
    
    # Check if tag is already assigned to patient
    if patient.patient_tags.filter(allowed_tag=allowed_tag).exists():
        return False
    
    return True


def can_remove_patient_tag(user: Any, patient: Any, tag: Any) -> bool:
    """
    Check if a user can remove a specific tag from a patient.
    
    Rules:
    - Must pass can_manage_patient_tags check
    - Tag must be assigned to the patient
    
    Args:
        user: The user requesting to remove the tag
        patient: The patient object
        tag: The Tag object to remove
        
    Returns:
        bool: True if tag removal is allowed, False otherwise
    """
    if not can_manage_patient_tags(user, patient):
        return False
    
    # Check if tag is assigned to this patient
    if not patient.patient_tags.filter(pk=tag.pk).exists():
        return False
    
    return True


def can_view_patient_tags(user: Any, patient: Any) -> bool:
    """
    Check if a user can view tags for a patient.
    
    Rules:
    - User must be able to access the patient
    
    Args:
        user: The user requesting to view tags
        patient: The patient object
        
    Returns:
        bool: True if tag viewing is allowed, False otherwise
    """
    return can_access_patient(user, patient)


def can_edit_admission_data(user: Any, admission: Any) -> bool:
    """
    Edit admission info for active admissions.
    
    Rules:
    - Admission must be active (not discharged)
    - Creator has 24h window OR doctors/residents always can
    
    Args:
        user: The user requesting to edit
        admission: The PatientAdmission object
        
    Returns:
        bool: True if editing is allowed, False otherwise
    """
    if user is None or admission is None:
        return False
    
    if not getattr(user, 'is_authenticated', False):
        return False
    
    # Check if admission is active (not discharged)
    if getattr(admission, 'discharge_datetime', None):
        return False
    
    # Doctors/residents always can edit active admissions
    if is_doctor_or_resident(user):
        return True
    
    # Creator has 24h window
    admission_creator = getattr(admission, 'created_by', None)
    if admission_creator == user:
        created_at = getattr(admission, 'created_at', None)
        if created_at:
            time_limit = timedelta(hours=ADMISSION_EDIT_TIME_LIMIT)
            return timezone.now() - created_at <= time_limit
    
    return False


def can_discharge_patient(user: Any, admission: Any) -> bool:
    """
    Add discharge information to active admission.
    
    Rules:
    - Admission must be active
    - Only doctors/residents can discharge
    
    Args:
        user: The user requesting to discharge
        admission: The PatientAdmission object
        
    Returns:
        bool: True if discharge is allowed, False otherwise
    """
    if user is None or admission is None:
        return False
    
    if not getattr(user, 'is_authenticated', False):
        return False
    
    # Check if admission is active (not discharged)
    if getattr(admission, 'discharge_datetime', None):
        return False
    
    # Only doctors/residents can discharge
    return is_doctor_or_resident(user)


def can_edit_discharge_data(user: Any, admission: Any) -> bool:
    """
    Edit discharge info after discharge.
    
    Rules:
    - Admission must be completed (discharged)
    - Only doctors/residents can edit
    - Within 24h of discharge datetime
    
    Args:
        user: The user requesting to edit
        admission: The PatientAdmission object
        
    Returns:
        bool: True if editing is allowed, False otherwise
    """
    if user is None or admission is None:
        return False
    
    if not getattr(user, 'is_authenticated', False):
        return False
    
    # Check if admission is discharged
    discharge_datetime = getattr(admission, 'discharge_datetime', None)
    if not discharge_datetime:
        return False
    
    # Only doctors/residents can edit
    if not is_doctor_or_resident(user):
        return False
    
    # Within 24h of discharge datetime
    time_limit = timedelta(hours=DISCHARGE_EDIT_TIME_LIMIT)
    return timezone.now() - discharge_datetime <= time_limit


def can_cancel_discharge(user: Any, admission: Any) -> bool:
    """
    Cancel discharge and reactivate admission.
    
    Rules:
    - Admission must be completed (discharged)
    - Only doctors/residents can cancel
    - Within 24h of discharge datetime
    
    Args:
        user: The user requesting to cancel discharge
        admission: The PatientAdmission object
        
    Returns:
        bool: True if cancellation is allowed, False otherwise
    """
    if user is None or admission is None:
        return False
    
    if not getattr(user, 'is_authenticated', False):
        return False
    
    # Check if admission is discharged
    discharge_datetime = getattr(admission, 'discharge_datetime', None)
    if not discharge_datetime:
        return False
    
    # Only doctors/residents can cancel
    if not is_doctor_or_resident(user):
        return False
    
    # Within 24h of discharge datetime
    time_limit = timedelta(hours=DISCHARGE_EDIT_TIME_LIMIT)
    return timezone.now() - discharge_datetime <= time_limit