"""
Constants for the EquipeMed permission system.

This module defines all constants used for profession types, patient statuses,
and permission codes throughout the application.
"""

# Profession types from accounts.EqmdCustomUser
MEDICAL_DOCTOR = 'medical_doctor'
NURSE = 'nurse'
PHYSIOTHERAPIST = 'physiotherapist'
RESIDENT = 'resident'
STUDENT = 'student'

PROFESSION_TYPES = [
    MEDICAL_DOCTOR,
    NURSE,
    PHYSIOTHERAPIST,
    RESIDENT,
    STUDENT,
]

# Patient status types from patients.Patient (using integer values to match model)
OUTPATIENT = 1
INPATIENT = 2
EMERGENCY = 3
DISCHARGED = 4
TRANSFERRED = 5
DECEASED = 6

PATIENT_STATUS_TYPES = [
    OUTPATIENT,
    INPATIENT,
    EMERGENCY,
    DISCHARGED,
    TRANSFERRED,
    DECEASED,
]

# Permission codes for different rules
PERM_ACCESS_PATIENT = 'access_patient'
PERM_EDIT_EVENT = 'edit_event'
PERM_DELETE_EVENT = 'delete_event'
PERM_CHANGE_PATIENT_STATUS = 'change_patient_status'
PERM_CHANGE_PATIENT_DATA = 'change_patient_data'
PERM_DISCHARGE_PATIENT = 'discharge_patient'

# Time-based permission settings (in hours)
EVENT_EDIT_TIME_LIMIT = 24  # Events can be edited for 24 hours after creation

# Cache settings for permission system
PERMISSION_CACHE_TIMEOUT = 300  # 5 minutes cache timeout for permission checks
PERMISSION_CACHE_PREFIX = 'eqmd_perm'  # Cache key prefix for permissions