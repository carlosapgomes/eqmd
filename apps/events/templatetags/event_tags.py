from django import template
from django.db.models import Count
from apps.events.models import Event
from apps.core.permissions.utils import can_access_patient

register = template.Library()

@register.inclusion_tag('events/widgets/recent_events.html', takes_context=True)
def recent_events_widget(context, patient, limit=3):
    """Display recent events for a patient."""
    request = context['request']
    
    # Check if user can access patient
    if not can_access_patient(request.user, patient):
        return {'recent_events': [], 'patient': patient}
    
    # Get recent events
    recent_events = Event.objects.filter(
        patient=patient
    ).select_subclasses().select_related('created_by').order_by('-created_at')[:limit]
    
    return {
        'recent_events': recent_events,
        'patient': patient,
        'request': request
    }

@register.simple_tag
def events_count_for_patient(patient, event_type=None):
    """Get count of events for a patient, optionally filtered by type."""
    queryset = Event.objects.filter(patient=patient)
    if event_type:
        queryset = queryset.filter(event_type=event_type)
    return queryset.count()

@register.simple_tag
def events_count_by_type(patient):
    """Get count of events by type for a patient."""
    return Event.objects.filter(patient=patient).values('event_type').annotate(
        count=Count('id')
    ).order_by('event_type')