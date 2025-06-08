from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Event
from apps.patients.models import Patient

@login_required
def patient_events_list(request, patient_id):
    """
    Display a list of events for a specific patient with pagination.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    events_list = Event.objects.filter(patient=patient).select_subclasses()

    paginator = Paginator(events_list, 10)
    page_number = request.GET.get('page')
    events = paginator.get_page(page_number)

    return render(request, 'events/patient_events_list.html', {
        'patient': patient,
        'events': events,
    })

@login_required
def user_events_list(request):
    """
    Display a list of events created or updated by the current user with pagination.
    """
    events_list = Event.objects.filter(
        Q(created_by=request.user) | Q(updated_by=request.user)
    ).distinct()

    paginator = Paginator(events_list, 10)
    page_number = request.GET.get('page')
    events = paginator.get_page(page_number)

    return render(request, 'events/user_events_list.html', {
        'events': events,
    })
