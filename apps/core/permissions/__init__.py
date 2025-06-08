"""
Permission system for EquipeMed application.

This module provides utilities, constants, and decorators for managing
permissions in the EquipeMed medical team collaboration platform.
"""

from .utils import (
    can_access_patient,
    can_edit_event,
    can_change_patient_status,
    is_doctor,
    has_hospital_context,
)

from .decorators import (
    patient_access_required,
    doctor_required,
    can_edit_event_required,
    hospital_context_required,
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
    'is_doctor',
    'has_hospital_context',
    'patient_access_required',
    'doctor_required',
    'can_edit_event_required',
    'hospital_context_required',
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