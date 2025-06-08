"""
Demo views for showcasing the permission system features.

These views demonstrate all aspects of the EquipeMed permission system
including role-based access, hospital context, and object-level permissions.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from unittest.mock import Mock
from datetime import datetime, timedelta

from apps.core.permissions import (
    can_access_patient,
    can_edit_event,
    can_change_patient_status,
    can_change_patient_personal_data,
    can_delete_event,
    can_see_patient_in_search,
    is_doctor,
    has_hospital_context,
    get_user_profession_type,
    patient_access_required,
    doctor_required,
    hospital_context_required,
)
from apps.core.permissions.constants import (
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
from apps.core.permissions.cache import get_cache_stats, clear_permission_cache
from apps.core.permissions.queries import get_permission_summary_optimized

User = get_user_model()


@login_required
def permission_demo_dashboard(request):
    """Main dashboard for permission system demo."""
    
    # Create mock data for demonstration
    mock_patients = [
        {
            'id': 'patient-1',
            'name': 'João Silva',
            'status': INPATIENT,
            'hospital_id': 'hospital-1',
            'hospital_name': 'Hospital Central'
        },
        {
            'id': 'patient-2', 
            'name': 'Maria Santos',
            'status': OUTPATIENT,
            'hospital_id': 'hospital-1',
            'hospital_name': 'Hospital Central'
        },
        {
            'id': 'patient-3',
            'name': 'Pedro Costa',
            'status': EMERGENCY,
            'hospital_id': 'hospital-2',
            'hospital_name': 'Hospital Norte'
        }
    ]
    
    mock_events = [
        {
            'id': 'event-1',
            'description': 'Consulta inicial',
            'created_by': request.user,
            'created_at': datetime.now() - timedelta(hours=2),
            'patient_id': 'patient-1'
        },
        {
            'id': 'event-2',
            'description': 'Exame de rotina',
            'created_by': request.user,
            'created_at': datetime.now() - timedelta(hours=25),  # Beyond edit limit
            'patient_id': 'patient-2'
        }
    ]
    
    # Get user information
    user_info = {
        'email': request.user.email,
        'profession': get_user_profession_type(request.user),
        'is_doctor': is_doctor(request.user),
        'has_hospital_context': has_hospital_context(request.user),
        'current_hospital': getattr(request.user, 'current_hospital', None),
        'groups': list(request.user.groups.values_list('name', flat=True)),
    }
    
    # Test permission checks for each patient
    patient_permissions = []
    for patient_data in mock_patients:
        # Create mock patient object
        patient = Mock()
        patient.id = patient_data['id']
        patient.status = patient_data['status']
        patient.current_hospital_id = patient_data['hospital_id']
        
        # Mock hospital object
        hospital = Mock()
        hospital.id = patient_data['hospital_id']
        hospital.name = patient_data['hospital_name']
        patient.current_hospital = hospital
        
        permissions = {
            'patient': patient_data,
            'can_access': can_access_patient(request.user, patient),
            'can_change_personal_data': can_change_patient_personal_data(request.user, patient),
            'can_see_in_search': can_see_patient_in_search(request.user, patient),
            'can_change_to_discharged': can_change_patient_status(request.user, patient, DISCHARGED),
            'can_change_to_inpatient': can_change_patient_status(request.user, patient, INPATIENT),
        }
        patient_permissions.append(permissions)
    
    # Test event permissions
    event_permissions = []
    for event_data in mock_events:
        # Create mock event object
        event = Mock()
        event.id = event_data['id']
        event.created_by = event_data['created_by']
        event.created_at = event_data['created_at']
        
        permissions = {
            'event': event_data,
            'can_edit': can_edit_event(request.user, event),
            'can_delete': can_delete_event(request.user, event),
        }
        event_permissions.append(permissions)
    
    # Get cache statistics
    cache_stats = get_cache_stats()
    
    # Get permission summary
    permission_summary = get_permission_summary_optimized(request.user)
    
    context = {
        'user_info': user_info,
        'patient_permissions': patient_permissions,
        'event_permissions': event_permissions,
        'cache_stats': cache_stats,
        'permission_summary': permission_summary,
        'profession_types': {
            'MEDICAL_DOCTOR': MEDICAL_DOCTOR,
            'NURSE': NURSE,
            'PHYSIOTHERAPIST': PHYSIOTHERAPIST,
            'RESIDENT': RESIDENT,
            'STUDENT': STUDENT,
        },
        'patient_statuses': {
            'INPATIENT': INPATIENT,
            'OUTPATIENT': OUTPATIENT,
            'EMERGENCY': EMERGENCY,
            'DISCHARGED': DISCHARGED,
            'TRANSFERRED': TRANSFERRED,
        }
    }
    
    return render(request, 'core/permission_demo/dashboard.html', context)


@login_required
def permission_demo_api(request):
    """API endpoint for permission demo data."""
    
    # Get all users for comparison
    users_data = []
    for user in User.objects.all()[:10]:  # Limit to 10 users for demo
        user_data = {
            'id': user.id,
            'email': user.email,
            'profession': get_user_profession_type(user),
            'is_doctor': is_doctor(user),
            'has_hospital_context': has_hospital_context(user),
            'groups': list(user.groups.values_list('name', flat=True)),
            'is_active': user.is_active,
        }
        users_data.append(user_data)
    
    # Get all groups
    groups_data = []
    for group in Group.objects.all():
        group_data = {
            'name': group.name,
            'user_count': group.user_set.count(),
            'permission_count': group.permissions.count(),
        }
        groups_data.append(group_data)
    
    return JsonResponse({
        'users': users_data,
        'groups': groups_data,
        'cache_stats': get_cache_stats(),
        'current_user': {
            'email': request.user.email,
            'profession': get_user_profession_type(request.user),
            'permissions': list(request.user.get_all_permissions())[:20],  # Limit for demo
        }
    })


@patient_access_required
def demo_patient_detail(request, patient_id):
    """Demo view that requires patient access."""
    
    # Create mock patient for demo
    patient = Mock()
    patient.id = patient_id
    patient.name = f"Patient {patient_id}"
    patient.status = INPATIENT
    
    # Mock hospital
    hospital = Mock()
    hospital.id = 'hospital-1'
    hospital.name = 'Demo Hospital'
    patient.current_hospital = hospital
    patient.current_hospital_id = hospital.id
    
    context = {
        'patient': {
            'id': patient.id,
            'name': patient.name,
            'status': patient.status,
            'hospital': hospital.name,
        },
        'permissions': {
            'can_change_personal_data': can_change_patient_personal_data(request.user, patient),
            'can_change_status': can_change_patient_status(request.user, patient, DISCHARGED),
        }
    }
    
    return render(request, 'core/permission_demo/patient_detail.html', context)


@doctor_required
def demo_doctor_only(request):
    """Demo view that requires doctor privileges."""
    
    context = {
        'message': 'This view is only accessible to doctors.',
        'user_profession': get_user_profession_type(request.user),
    }
    
    return render(request, 'core/permission_demo/doctor_only.html', context)


@hospital_context_required
def demo_hospital_context(request):
    """Demo view that requires hospital context."""
    
    current_hospital = getattr(request.user, 'current_hospital', None)
    
    context = {
        'message': 'This view requires hospital context.',
        'current_hospital': {
            'id': current_hospital.id if current_hospital else None,
            'name': getattr(current_hospital, 'name', 'Unknown') if current_hospital else None,
        } if current_hospital else None,
    }
    
    return render(request, 'core/permission_demo/hospital_context.html', context)


@login_required
def demo_cache_management(request):
    """Demo view for cache management."""
    
    action = request.GET.get('action')
    
    if action == 'clear':
        clear_permission_cache()
        message = 'Permission cache cleared successfully.'
    elif action == 'stats':
        stats = get_cache_stats()
        message = f"Cache stats: {stats['hits']} hits, {stats['misses']} misses, {stats['hit_ratio']:.2%} hit ratio"
    else:
        message = 'Available actions: clear, stats'
    
    context = {
        'message': message,
        'cache_stats': get_cache_stats(),
    }
    
    return render(request, 'core/permission_demo/cache_management.html', context)


@login_required
def demo_permission_test(request):
    """Interactive permission testing view."""
    
    test_type = request.GET.get('test_type')
    result = None
    
    if test_type == 'patient_access':
        # Test patient access with different scenarios
        scenarios = [
            {'patient_status': INPATIENT, 'hospital_match': True},
            {'patient_status': OUTPATIENT, 'hospital_match': True},
            {'patient_status': INPATIENT, 'hospital_match': False},
            {'patient_status': OUTPATIENT, 'hospital_match': False},
        ]
        
        results = []
        for scenario in scenarios:
            # Create mock patient
            patient = Mock()
            patient.id = 'test-patient'
            patient.status = scenario['patient_status']
            
            if scenario['hospital_match'] and hasattr(request.user, 'current_hospital'):
                patient.current_hospital = request.user.current_hospital
                patient.current_hospital_id = request.user.current_hospital.id
            else:
                # Different hospital
                other_hospital = Mock()
                other_hospital.id = 'other-hospital'
                patient.current_hospital = other_hospital
                patient.current_hospital_id = other_hospital.id
            
            can_access = can_access_patient(request.user, patient)
            
            results.append({
                'scenario': scenario,
                'can_access': can_access,
            })
        
        result = {'type': 'patient_access', 'results': results}
    
    elif test_type == 'status_change':
        # Test status change permissions
        patient = Mock()
        patient.id = 'test-patient'
        patient.status = INPATIENT
        
        if hasattr(request.user, 'current_hospital'):
            patient.current_hospital = request.user.current_hospital
            patient.current_hospital_id = request.user.current_hospital.id
        
        status_tests = [DISCHARGED, OUTPATIENT, TRANSFERRED, EMERGENCY]
        results = []
        
        for new_status in status_tests:
            can_change = can_change_patient_status(request.user, patient, new_status)
            results.append({
                'new_status': new_status,
                'can_change': can_change,
            })
        
        result = {'type': 'status_change', 'results': results}
    
    context = {
        'test_result': result,
        'available_tests': ['patient_access', 'status_change'],
        'user_info': {
            'profession': get_user_profession_type(request.user),
            'has_hospital_context': has_hospital_context(request.user),
        }
    }
    
    return render(request, 'core/permission_demo/permission_test.html', context)


@login_required
def demo_role_comparison(request):
    """Compare permissions across different roles."""
    
    # Create mock users for each role
    roles = [
        {'name': 'Medical Doctor', 'profession': MEDICAL_DOCTOR},
        {'name': 'Nurse', 'profession': NURSE},
        {'name': 'Physiotherapist', 'profession': PHYSIOTHERAPIST},
        {'name': 'Resident', 'profession': RESIDENT},
        {'name': 'Student', 'profession': STUDENT},
    ]
    
    # Create mock patient scenarios
    patient_scenarios = [
        {'name': 'Inpatient - Same Hospital', 'status': INPATIENT, 'same_hospital': True},
        {'name': 'Outpatient - Same Hospital', 'status': OUTPATIENT, 'same_hospital': True},
        {'name': 'Emergency - Same Hospital', 'status': EMERGENCY, 'same_hospital': True},
        {'name': 'Inpatient - Different Hospital', 'status': INPATIENT, 'same_hospital': False},
    ]
    
    comparison_results = []
    
    for role in roles:
        # Create mock user
        mock_user = Mock()
        mock_user.is_authenticated = True
        mock_user.profession_type = role['profession']
        mock_user.has_hospital_context = True
        
        # Mock hospital
        user_hospital = Mock()
        user_hospital.id = 'user-hospital'
        mock_user.current_hospital = user_hospital
        
        role_results = {'role': role['name'], 'scenarios': []}
        
        for scenario in patient_scenarios:
            # Create mock patient
            patient = Mock()
            patient.status = scenario['status']
            
            if scenario['same_hospital']:
                patient.current_hospital = user_hospital
                patient.current_hospital_id = user_hospital.id
            else:
                other_hospital = Mock()
                other_hospital.id = 'other-hospital'
                patient.current_hospital = other_hospital
                patient.current_hospital_id = other_hospital.id
            
            # Test permissions
            permissions = {
                'can_access': can_access_patient(mock_user, patient),
                'can_change_personal_data': can_change_patient_personal_data(mock_user, patient),
                'can_discharge': can_change_patient_status(mock_user, patient, DISCHARGED),
                'can_change_to_inpatient': can_change_patient_status(mock_user, patient, INPATIENT),
            }
            
            role_results['scenarios'].append({
                'scenario': scenario['name'],
                'permissions': permissions,
            })
        
        comparison_results.append(role_results)
    
    context = {
        'comparison_results': comparison_results,
        'current_user_profession': get_user_profession_type(request.user),
    }
    
    return render(request, 'core/permission_demo/role_comparison.html', context)
