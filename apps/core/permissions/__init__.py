"""
Permission system for EquipeMed application.

This module provides utilities, constants, and decorators for managing
permissions in the EquipeMed medical team collaboration platform.
"""

from .utils import (
    can_access_patient,
    can_edit_event,
    can_change_patient_status,
    can_change_patient_personal_data,
    can_delete_event,
    can_see_patient_in_search,
    is_doctor,
    has_hospital_context,
    has_django_permission,
    is_in_group,
    get_user_profession_type,
    can_manage_patients,
    can_view_patients,
    can_manage_events,
    can_view_events,
    can_manage_hospitals,
    can_view_hospitals,
)

from .decorators import (
    patient_access_required,
    doctor_required,
    can_edit_event_required,
    hospital_context_required,
    patient_data_change_required,
    can_delete_event_required,
)

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
)

__all__ = [
    'can_access_patient',
    'can_edit_event',
    'can_change_patient_status',
    'can_change_patient_personal_data',
    'can_delete_event',
    'can_see_patient_in_search',
    'is_doctor',
    'has_hospital_context',
    'has_django_permission',
    'is_in_group',
    'get_user_profession_type',
    'can_manage_patients',
    'can_view_patients',
    'can_manage_events',
    'can_view_events',
    'can_manage_hospitals',
    'can_view_hospitals',
    'patient_access_required',
    'doctor_required',
    'can_edit_event_required',
    'hospital_context_required',
    'patient_data_change_required',
    'can_delete_event_required',
    'MEDICAL_DOCTOR',
    'NURSE',
    'PHYSIOTHERAPIST',
    'RESIDENT',
    'STUDENT',
    'INPATIENT',
    'OUTPATIENT',
    'EMERGENCY',
    'DISCHARGED',
    'TRANSFERRED',
]