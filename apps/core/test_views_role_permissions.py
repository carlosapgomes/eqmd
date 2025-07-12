"""
Test views for role-based permission system functionality.

These views are used to manually test the role-based permission system
and template tags.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.models import Group

from apps.core.permissions import (
    has_django_permission,
    is_in_group,
    get_user_profession_type,
    can_manage_patients,
    can_view_patients,
    can_manage_events,
    can_view_events,
)


@login_required
def role_permissions_test_view(request):
    """Test view to demonstrate role-based permission functionality."""
    user = request.user
    
    # Get user's profession information
    profession_type = get_user_profession_type(user)
    profession_display = user.get_profession_type_display() if hasattr(user, 'get_profession_type_display') else 'Unknown'
    
    # Get user's groups
    user_groups = user.groups.all()
    
    # Check specific permissions
    permission_checks = {
        'patients': {
            'can_manage': can_manage_patients(user),
            'can_view': can_view_patients(user),
            'can_add': has_django_permission(user, 'patients.add_patient'),
            'can_change': has_django_permission(user, 'patients.change_patient'),
            'can_delete': has_django_permission(user, 'patients.delete_patient'),
        },
        'events': {
            'can_manage': can_manage_events(user),
            'can_view': can_view_events(user),
            'can_add': has_django_permission(user, 'events.add_event'),
            'can_change': has_django_permission(user, 'events.change_event'),
            'can_delete': has_django_permission(user, 'events.delete_event'),
        },
        # 'hospitals': removed for single-hospital refactor
    }
    
    # Check group memberships
    profession_groups = [
        'Medical Doctors',
        'Residents',
        'Nurses',
        'Physiotherapists',
        'Students',
    ]
    
    group_memberships = {}
    for group_name in profession_groups:
        group_memberships[group_name] = is_in_group(user, group_name)
    
    # Get all available groups
    all_groups = Group.objects.all()
    
    context = {
        'user': user,
        'profession_type': profession_type,
        'profession_display': profession_display,
        'user_groups': user_groups,
        'permission_checks': permission_checks,
        'group_memberships': group_memberships,
        'all_groups': all_groups,
        'has_hospital_context': getattr(user, 'has_hospital_context', False),
        'current_hospital': getattr(user, 'current_hospital', None),
    }
    
    return render(request, 'core/test_role_permissions.html', context)


@login_required
def role_permissions_api_view(request):
    """API view that returns role permission information as JSON."""
    user = request.user
    
    # Get user's profession information
    profession_type = get_user_profession_type(user)
    
    # Get user's groups
    user_groups = [group.name for group in user.groups.all()]
    
    # Check specific permissions
    permissions = {
        'patients': {
            'manage': can_manage_patients(user),
            'view': can_view_patients(user),
            'add': has_django_permission(user, 'patients.add_patient'),
            'change': has_django_permission(user, 'patients.change_patient'),
            'delete': has_django_permission(user, 'patients.delete_patient'),
        },
        'events': {
            'manage': can_manage_events(user),
            'view': can_view_events(user),
            'add': has_django_permission(user, 'events.add_event'),
            'change': has_django_permission(user, 'events.change_event'),
            'delete': has_django_permission(user, 'events.delete_event'),
        },
        # 'hospitals': removed for single-hospital refactor
    }
    
    # Check group memberships
    profession_groups = [
        'Medical Doctors',
        'Residents',
        'Nurses',
        'Physiotherapists',
        'Students',
    ]
    
    group_memberships = {}
    for group_name in profession_groups:
        group_memberships[group_name] = is_in_group(user, group_name)
    
    data = {
        'user': {
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'profession_type': profession_type,
            'profession_display': user.get_profession_type_display() if hasattr(user, 'get_profession_type_display') else 'Unknown',
        },
        'groups': user_groups,
        'permissions': permissions,
        'group_memberships': group_memberships,
        'hospital_context': {
            'has_context': getattr(user, 'has_hospital_context', False),
            'current_hospital': getattr(user, 'current_hospital', {}).get('name') if getattr(user, 'current_hospital', None) else None,
        },
    }
    
    return JsonResponse(data)


@login_required
def test_template_tags_view(request):
    """Test view to demonstrate template tag functionality."""
    context = {
        'test_permissions': [
            'patients.add_patient',
            'patients.view_patient',
            'events.add_event',
            'events.view_event',
            'hospitals.add_hospital',
            'hospitals.view_hospital',
        ],
        'test_groups': [
            'Medical Doctors',
            'Residents',
            'Nurses',
            'Physiotherapists',
            'Students',
        ],
        'test_professions': [
            'medical_doctor',
            'resident',
            'nurse',
            'physiotherapist',
            'student',
        ],
    }
    
    return render(request, 'core/test_template_tags.html', context)
