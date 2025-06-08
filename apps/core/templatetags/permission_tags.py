"""
Template tags for permission checking in EquipeMed templates.

This module provides template tags and filters for checking permissions
and user roles in templates.
"""

from django import template
from django.contrib.auth.models import Group

from apps.core.permissions import (
    can_access_patient,
    can_edit_event,
    can_change_patient_status,
    can_change_patient_personal_data,
    can_delete_event,
    can_see_patient_in_search,
    is_doctor,
    has_hospital_context,
)
from apps.core.permissions.constants import (
    MEDICAL_DOCTOR,
    RESIDENT,
    NURSE,
    PHYSIOTHERAPIST,
    STUDENT,
)

register = template.Library()


@register.filter
def has_permission(user, permission_name):
    """
    Check if user has a specific Django permission.
    
    Usage: {% if user|has_permission:"patients.add_patient" %}
    """
    if not user.is_authenticated:
        return False
    
    return user.has_perm(permission_name)


@register.filter
def in_group(user, group_name):
    """
    Check if user is in a specific group.
    
    Usage: {% if user|in_group:"Medical Doctors" %}
    """
    if not user.is_authenticated:
        return False
    
    return user.groups.filter(name=group_name).exists()


@register.filter
def is_profession(user, profession_type):
    """
    Check if user has a specific profession type.
    
    Usage: {% if user|is_profession:"medical_doctor" %}
    """
    if not user.is_authenticated:
        return False
    
    profession_map = {
        'medical_doctor': 0,
        'resident': 1,
        'nurse': 2,
        'physiotherapist': 3,
        'student': 4,
    }
    
    expected_type = profession_map.get(profession_type)
    if expected_type is None:
        return False
    
    return getattr(user, 'profession_type', None) == expected_type


@register.simple_tag
def can_user_access_patient(user, patient):
    """
    Check if user can access a specific patient.
    
    Usage: {% can_user_access_patient user patient as can_access %}
    """
    return can_access_patient(user, patient)


@register.simple_tag
def can_user_edit_event(user, event):
    """
    Check if user can edit a specific event.
    
    Usage: {% can_user_edit_event user event as can_edit %}
    """
    return can_edit_event(user, event)


@register.simple_tag
def can_user_change_patient_status(user, patient, new_status):
    """
    Check if user can change patient status.
    
    Usage: {% can_user_change_patient_status user patient "discharged" as can_change %}
    """
    return can_change_patient_status(user, patient, new_status)


@register.filter
def is_doctor_user(user):
    """
    Check if user is a doctor.
    
    Usage: {% if user|is_doctor_user %}
    """
    return is_doctor(user)


@register.filter
def has_hospital_context_user(user):
    """
    Check if user has hospital context.
    
    Usage: {% if user|has_hospital_context_user %}
    """
    return has_hospital_context(user)


@register.inclusion_tag('core/tags/permission_debug.html')
def permission_debug(user):
    """
    Debug tag to show user permissions and groups.
    
    Usage: {% permission_debug user %}
    """
    if not user.is_authenticated:
        return {'user': None}
    
    # Get user groups
    groups = user.groups.all()
    
    # Get user permissions
    permissions = user.get_all_permissions()
    
    # Get profession info
    profession_type = getattr(user, 'profession_type', None)
    profession_display = user.get_profession_type_display() if profession_type is not None else 'Not set'
    
    # Get hospital context
    current_hospital = getattr(user, 'current_hospital', None)
    has_context = has_hospital_context(user)
    
    return {
        'user': user,
        'groups': groups,
        'permissions': sorted(permissions),
        'profession_type': profession_type,
        'profession_display': profession_display,
        'current_hospital': current_hospital,
        'has_hospital_context': has_context,
    }


@register.simple_tag
def get_user_profession_groups():
    """
    Get all profession-based groups.
    
    Usage: {% get_user_profession_groups as profession_groups %}
    """
    group_names = [
        'Medical Doctors',
        'Residents',
        'Nurses',
        'Physiotherapists', 
        'Students',
    ]
    
    return Group.objects.filter(name__in=group_names)


@register.filter
def profession_type_display(profession_type):
    """
    Convert profession type integer to display name.
    
    Usage: {{ user.profession_type|profession_type_display }}
    """
    profession_map = {
        0: 'Médico',
        1: 'Residente',
        2: 'Enfermeiro',
        3: 'Fisioterapeuta',
        4: 'Estudante',
    }
    
    return profession_map.get(profession_type, 'Não definido')


@register.simple_tag
def check_multiple_permissions(user, *permissions):
    """
    Check if user has all of the specified permissions.
    
    Usage: {% check_multiple_permissions user "patients.add_patient" "patients.change_patient" as has_all_perms %}
    """
    if not user.is_authenticated:
        return False
    
    return all(user.has_perm(perm) for perm in permissions)


@register.simple_tag
def check_any_permission(user, *permissions):
    """
    Check if user has any of the specified permissions.
    
    Usage: {% check_any_permission user "patients.add_patient" "patients.view_patient" as has_any_perm %}
    """
    if not user.is_authenticated:
        return False
    
    return any(user.has_perm(perm) for perm in permissions)


@register.filter
def can_manage_patients(user):
    """
    Check if user can manage patients (add, change, delete).
    
    Usage: {% if user|can_manage_patients %}
    """
    if not user.is_authenticated:
        return False
    
    required_perms = [
        'patients.add_patient',
        'patients.change_patient',
        'patients.delete_patient',
    ]
    
    return all(user.has_perm(perm) for perm in required_perms)


@register.filter
def can_view_patients(user):
    """
    Check if user can view patients.
    
    Usage: {% if user|can_view_patients %}
    """
    if not user.is_authenticated:
        return False
    
    return user.has_perm('patients.view_patient')


@register.filter
def can_manage_events(user):
    """
    Check if user can manage events (add, change, delete).
    
    Usage: {% if user|can_manage_events %}
    """
    if not user.is_authenticated:
        return False
    
    required_perms = [
        'events.add_event',
        'events.change_event',
        'events.delete_event',
    ]
    
    return all(user.has_perm(perm) for perm in required_perms)


@register.filter
def can_view_events(user):
    """
    Check if user can view events.

    Usage: {% if user|can_view_events %}
    """
    if not user.is_authenticated:
        return False

    return user.has_perm('events.view_event')


@register.simple_tag
def can_user_change_patient_personal_data(user, patient):
    """
    Check if user can change patient personal data.

    Usage: {% can_user_change_patient_personal_data user patient as can_change_data %}
    """
    return can_change_patient_personal_data(user, patient)


@register.simple_tag
def can_user_delete_event(user, event):
    """
    Check if user can delete a specific event.

    Usage: {% can_user_delete_event user event as can_delete %}
    """
    return can_delete_event(user, event)


@register.simple_tag
def can_user_see_patient_in_search(user, patient):
    """
    Check if user can see patient in search results.

    Usage: {% can_user_see_patient_in_search user patient as can_see %}
    """
    return can_see_patient_in_search(user, patient)


@register.filter
def can_change_patient_data(user):
    """
    Check if user can generally change patient personal data (based on role).

    Usage: {% if user|can_change_patient_data %}
    """
    return is_doctor(user)


@register.simple_tag
def permission_cache_stats():
    """
    Get permission cache statistics for debugging.

    Usage: {% permission_cache_stats as cache_stats %}
    """
    try:
        from apps.core.permissions.cache import get_cache_stats, is_caching_enabled
        if is_caching_enabled():
            return get_cache_stats()
        else:
            return {'caching_enabled': False}
    except ImportError:
        return {'error': 'Cache module not available'}


@register.inclusion_tag('core/tags/permission_performance.html')
def permission_performance_widget(user):
    """
    Display permission performance information.

    Usage: {% permission_performance_widget user %}
    """
    if not user.is_authenticated:
        return {'user': None}

    try:
        from apps.core.permissions.queries import get_permission_summary_optimized
        from apps.core.permissions.cache import get_cache_stats, is_caching_enabled

        summary = get_permission_summary_optimized(user)
        cache_stats = get_cache_stats() if is_caching_enabled() else None

        return {
            'user': user,
            'summary': summary,
            'cache_stats': cache_stats,
            'caching_enabled': is_caching_enabled()
        }
    except ImportError:
        return {'user': user, 'error': 'Performance modules not available'}


@register.simple_tag
def check_bulk_permissions(user, *permissions):
    """
    Check multiple permissions efficiently and return detailed results.

    Usage: {% check_bulk_permissions user "patients.add_patient" "events.add_event" as perm_results %}
    """
    if not user.is_authenticated:
        return {perm: False for perm in permissions}

    # Use bulk permission checking for better performance
    results = {}
    for perm in permissions:
        results[perm] = user.has_perm(perm)

    return results


@register.filter
def has_any_model_permission(user, app_label):
    """
    Check if user has any permission for a specific app/model.

    Usage: {% if user|has_any_model_permission:"patients" %}
    """
    if not user.is_authenticated:
        return False

    # Get all permissions for the user
    all_perms = user.get_all_permissions()

    # Check if any permission starts with the app label
    return any(perm.startswith(f"{app_label}.") for perm in all_perms)


@register.simple_tag
def get_user_accessible_models(user):
    """
    Get list of models/apps the user can access.

    Usage: {% get_user_accessible_models user as accessible_models %}
    """
    if not user.is_authenticated:
        return []

    accessible = []

    # Check main app permissions
    if user.has_perm('patients.view_patient'):
        accessible.append('patients')
    if user.has_perm('events.view_event'):
        accessible.append('events')
    if user.has_perm('hospitals.view_hospital'):
        accessible.append('hospitals')

    return accessible
