"""
Decorators for permission checking in EquipeMed views.

This module provides decorators that can be applied to views to enforce
permission checking.
"""

from functools import wraps
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from .utils import (
    can_access_patient,
    can_edit_event,
    can_change_patient_personal_data,
    can_delete_event,
    is_doctor,
    is_doctor_or_resident,
)


def patient_access_required(view_func):
    """
    Decorator that checks if user can access the patient specified in the URL.
    
    Expects 'patient_id' parameter in the view function.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Get patient_id from kwargs
        patient_id = kwargs.get('patient_id') or kwargs.get('pk') or kwargs.get('patient_uuid')
        if not patient_id:
            return HttpResponseForbidden("Patient ID not provided")
        
        # Import here to avoid circular imports
        try:
            from apps.patients.models import Patient
            patient = get_object_or_404(Patient, pk=patient_id)
        except ImportError:
            # Fallback if patients app is not available
            return HttpResponseForbidden("Patients app not available")
        
        # Check permission
        if not can_access_patient(request.user, patient):
            return HttpResponseForbidden("You don't have permission to access this patient")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def doctor_required(view_func):
    """
    Decorator that requires the user to be a doctor.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_doctor(request.user):
            return HttpResponseForbidden("This action requires doctor privileges")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def doctor_or_resident_required(view_func):
    """
    Decorator that requires the user to be a doctor or resident.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_doctor_or_resident(request.user):
            return HttpResponseForbidden("This action requires doctor or resident privileges")

        return view_func(request, *args, **kwargs)

    return wrapper


def can_edit_event_required(view_func):
    """
    Decorator that checks if user can edit the event specified in the URL.
    
    Expects 'event_id' parameter in the view function.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Get event_id from kwargs
        event_id = kwargs.get('event_id') or kwargs.get('pk')
        if not event_id:
            return HttpResponseForbidden("Event ID not provided")
        
        # Import here to avoid circular imports
        try:
            from apps.events.models import Event
            event = get_object_or_404(Event, pk=event_id)
        except ImportError:
            # Fallback if events app is not available
            return HttpResponseForbidden("Events app not available")
        
        # Check permission
        if not can_edit_event(request.user, event):
            return HttpResponseForbidden("You don't have permission to edit this event")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper




def patient_data_change_required(view_func):
    """
    Decorator that checks if user can change patient personal data.

    Expects 'patient_id' parameter in the view function.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Get patient_id from kwargs
        patient_id = kwargs.get('patient_id') or kwargs.get('pk') or kwargs.get('patient_uuid')
        if not patient_id:
            return HttpResponseForbidden("Patient ID not provided")

        # Import here to avoid circular imports
        try:
            from apps.patients.models import Patient
            patient = get_object_or_404(Patient, pk=patient_id)
        except ImportError:
            # Fallback if patients app is not available
            return HttpResponseForbidden("Patients app not available")

        # Check permission
        if not can_change_patient_personal_data(request.user, patient):
            return HttpResponseForbidden("You don't have permission to change this patient's personal data")

        return view_func(request, *args, **kwargs)

    return wrapper


def can_delete_event_required(view_func):
    """
    Decorator that checks if user can delete the event specified in the URL.

    Expects 'event_id' parameter in the view function.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Get event_id from kwargs
        event_id = kwargs.get('event_id') or kwargs.get('pk')
        if not event_id:
            return HttpResponseForbidden("Event ID not provided")

        # Import here to avoid circular imports
        try:
            from apps.events.models import Event
            event = get_object_or_404(Event, pk=event_id)
        except ImportError:
            # Fallback if events app is not available
            return HttpResponseForbidden("Events app not available")

        # Check permission
        if not can_delete_event(request.user, event):
            return HttpResponseForbidden("You don't have permission to delete this event")

        return view_func(request, *args, **kwargs)

    return wrapper
