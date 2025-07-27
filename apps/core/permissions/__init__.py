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
    has_django_permission,
    is_in_group,
    get_user_profession_type,
    can_manage_patients,
    can_view_patients,
    can_manage_events,
    can_view_events,
)

from .decorators import (
    patient_access_required,
    doctor_required,
    can_edit_event_required,
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
    DECEASED,
    PERMISSION_CACHE_TIMEOUT,
    PERMISSION_CACHE_PREFIX,
)

# Import cache utilities
from .cache import (
    cache_permission_result,
    invalidate_user_permissions,
    invalidate_object_permissions,
    get_cache_stats,
    clear_permission_cache,
    is_caching_enabled,
)

# Import query optimization utilities
from .queries import (
    get_optimized_user_queryset,
    get_optimized_patient_queryset,
    get_optimized_event_queryset,
    get_optimized_hospital_queryset,
    get_patients_for_user,
    get_events_for_user,
    get_hospitals_for_user,
    get_recent_patients_optimized,
    get_permission_summary_optimized,
)

__all__ = [
    # Permission utility functions
    'can_access_patient',
    'can_edit_event',
    'can_change_patient_status',
    'can_change_patient_personal_data',
    'can_delete_event',
    'can_see_patient_in_search',
    'is_doctor',
    'has_django_permission',
    'is_in_group',
    'get_user_profession_type',
    'can_manage_patients',
    'can_view_patients',
    'can_manage_events',
    'can_view_events',

    # Permission decorators
    'patient_access_required',
    'doctor_required',
    'can_edit_event_required',
    'patient_data_change_required',
    'can_delete_event_required',

    # Constants
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
    'DECEASED',
    'PERMISSION_CACHE_TIMEOUT',
    'PERMISSION_CACHE_PREFIX',

    # Cache utilities
    'cache_permission_result',
    'invalidate_user_permissions',
    'invalidate_object_permissions',
    'get_cache_stats',
    'clear_permission_cache',
    'is_caching_enabled',

    # Query optimization utilities
    'get_optimized_user_queryset',
    'get_optimized_patient_queryset',
    'get_optimized_event_queryset',
    'get_patients_for_user',
    'get_events_for_user',
    'get_recent_patients_optimized',
    'get_permission_summary_optimized',
]