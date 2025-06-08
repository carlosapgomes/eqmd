"""
Test views for verifying permission system implementation.

These views are used to manually test the permission decorators and functions.
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from .permissions import (
    patient_access_required,
    doctor_required,
    can_edit_event_required,
    hospital_context_required,
    patient_data_change_required,
    can_delete_event_required,
    can_access_patient,
    can_edit_event,
    can_change_patient_personal_data,
    can_delete_event,
    can_see_patient_in_search,
    is_doctor,
)


@login_required
def permission_test_view(request):
    """
    Test view to display permission checking results.
    """
    context = {
        'user': request.user,
        'is_doctor': is_doctor(request.user),
        'has_hospital_context': hasattr(request.user, 'current_hospital_id'),
    }
    
    # Test patient access (if patients app is available)
    try:
        from apps.patients.models import Patient
        patients = Patient.objects.all()[:3]  # Get first 3 patients for testing
        context['patients'] = []
        for patient in patients:
            context['patients'].append({
                'patient': patient,
                'can_access': can_access_patient(request.user, patient),
                'can_change_personal_data': can_change_patient_personal_data(request.user, patient),
                'can_see_in_search': can_see_patient_in_search(request.user, patient),
            })
    except ImportError:
        context['patients'] = []
    
    # Test event access (if events app is available)
    try:
        from apps.events.models import Event
        events = Event.objects.all()[:3]  # Get first 3 events for testing
        context['events'] = []
        for event in events:
            context['events'].append({
                'event': event,
                'can_edit': can_edit_event(request.user, event),
                'can_delete': can_delete_event(request.user, event),
            })
    except ImportError:
        context['events'] = []
    
    return render(request, 'core/permission_test.html', context)


@doctor_required
def doctor_only_view(request):
    """
    Test view that requires doctor privileges.
    """
    return JsonResponse({'message': 'Success! You have doctor privileges.'})


@hospital_context_required
def hospital_context_view(request):
    """
    Test view that requires hospital context.
    """
    return JsonResponse({
        'message': 'Success! You have hospital context.',
        'hospital_id': getattr(request.user, 'current_hospital_id', None)
    })


@patient_access_required
def patient_access_view(request, patient_id):
    """
    Test view that requires patient access.
    """
    return JsonResponse({
        'message': f'Success! You can access patient {patient_id}.'
    })


@can_edit_event_required
def event_edit_view(request, event_id):
    """
    Test view that requires event edit permission.
    """
    return JsonResponse({
        'message': f'Success! You can edit event {event_id}.'
    })


@patient_data_change_required
def patient_data_change_view(request, patient_id):
    """
    Test view that requires patient personal data change permission.
    """
    return JsonResponse({
        'message': f'Success! You can change personal data for patient {patient_id}.'
    })


@can_delete_event_required
def event_delete_view(request, event_id):
    """
    Test view that requires event delete permission.
    """
    return JsonResponse({
        'message': f'Success! You can delete event {event_id}.'
    })


@login_required
def object_level_permissions_test_view(request):
    """
    Test view to demonstrate object-level permissions.
    """
    context = {
        'user': request.user,
        'is_doctor': is_doctor(request.user),
    }

    # Test patient permissions (if patients app is available)
    try:
        from apps.patients.models import Patient
        patients = Patient.objects.all()[:5]  # Get first 5 patients for testing
        context['patients'] = []
        for patient in patients:
            context['patients'].append({
                'patient': patient,
                'can_access': can_access_patient(request.user, patient),
                'can_change_personal_data': can_change_patient_personal_data(request.user, patient),
                'can_see_in_search': can_see_patient_in_search(request.user, patient),
            })
    except ImportError:
        context['patients'] = []

    # Test event permissions (if events app is available)
    try:
        from apps.events.models import Event
        events = Event.objects.all()[:5]  # Get first 5 events for testing
        context['events'] = []
        for event in events:
            context['events'].append({
                'event': event,
                'can_edit': can_edit_event(request.user, event),
                'can_delete': can_delete_event(request.user, event),
            })
    except ImportError:
        context['events'] = []

    return render(request, 'core/object_level_permissions_test.html', context)