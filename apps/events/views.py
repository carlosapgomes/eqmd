from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch, Count
from django.views.generic import ListView
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from functools import lru_cache
from datetime import datetime, timedelta
import re
from .models import Event
from apps.patients.models import Patient
from apps.core.permissions.utils import (
    can_access_patient, 
    can_edit_event,
    can_edit_admission_data,
    can_edit_discharge_data,
    can_cancel_discharge,
    can_discharge_patient
)

User = get_user_model()

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


class PatientEventsTimelineView(ListView):
    """
    Optimized timeline view with caching and performance enhancements.
    """
    model = Event
    template_name = 'events/patient_timeline.html'
    context_object_name = 'events'
    paginate_by = 15
    paginate_orphans = 5
    
    def get_queryset(self):
        """Optimized queryset with prefetch and select_related."""
        self.patient = get_object_or_404(Patient, pk=self.kwargs['patient_id'])
        
        # Permission check
        if not can_access_patient(self.request.user, self.patient):
            raise PermissionDenied("You don't have permission to view this patient's events.")
        
        # Optimized base queryset
        queryset = Event.objects.filter(
            patient=self.patient
        ).select_subclasses().select_related(
            'created_by',
            'updated_by',
            'patient'
        ).prefetch_related(
            'created_by__groups'
        ).order_by('-created_at')
        
        # Apply filters with indexing considerations
        queryset = self._apply_optimized_filters(queryset)
        
        return queryset
    
    def _apply_optimized_filters(self, queryset):
        """Apply filtering with database optimization considerations."""
        
        # Event type filter (uses index)
        event_types = self.request.GET.getlist('types')
        if event_types:
            queryset = queryset.filter(event_type__in=event_types)
        
        # Date range filters (uses created_at index)
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=date_from)
            except ValueError:
                pass
                
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=date_to)
            except ValueError:
                pass
        
        # Quick date filters (optimized for common patterns)
        quick_filter = self.request.GET.get('quick_date')
        if quick_filter:
            now = timezone.now()
            if quick_filter == '24h':
                queryset = queryset.filter(created_at__gte=now - timedelta(hours=24))
            elif quick_filter == '7d':
                queryset = queryset.filter(created_at__gte=now - timedelta(days=7))
            elif quick_filter == '30d':
                queryset = queryset.filter(created_at__gte=now - timedelta(days=30))
        
        # Creator filter (uses created_by index)
        creator_id = self.request.GET.get('creator')
        if creator_id:
            try:
                creator_id = int(creator_id)
                queryset = queryset.filter(created_by_id=creator_id)
            except ValueError:
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add cached context data for improved performance."""
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        
        # Cache filter options for 5 minutes
        cache_key = f"timeline_filters_{self.patient.pk}"
        filter_data = cache.get(cache_key)
        
        if filter_data is None:
            filter_data = {
                'event_type_choices': Event.EVENT_TYPE_CHOICES,
                'available_creators': self._get_cached_creators(),
                'event_counts_by_type': self._get_event_counts_by_type(),
            }
            cache.set(cache_key, filter_data, 300)  # 5 minutes
        
        context.update(filter_data)
        
        # Add permission context for events (bulk check)
        events_with_permissions = self._bulk_permission_check(context['events'])
        context['events_with_permissions'] = events_with_permissions
        
        # Add current filter values
        context['current_filters'] = {
            'types': self.request.GET.getlist('types'),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'quick_date': self.request.GET.get('quick_date', ''),
            'creator': self.request.GET.get('creator', ''),
        }
        
        # Add counts (cached)
        counts_cache_key = f"event_counts_{self.patient.pk}"
        counts = cache.get(counts_cache_key)
        if counts is None:
            counts = {
                'total_events': Event.objects.filter(patient=self.patient).count(),
                'filtered_count': self.get_queryset().count(),
            }
            cache.set(counts_cache_key, counts, 60)  # 1 minute
        
        context.update(counts)
        
        return context
    
    def _bulk_permission_check(self, events):
        """Bulk permission checking to avoid N+1 queries."""
        events_with_permissions = []
        
        # Pre-calculate edit permissions for all events
        edit_permissions = {}
        for event in events:
            edit_permissions[event.pk] = can_edit_event(self.request.user, event)
        
        for event in events:
            event_data = {
                'event': event,
                'can_edit': edit_permissions.get(event.pk, False),
                'can_delete': edit_permissions.get(event.pk, False),
                'excerpt': event.get_excerpt(150)
            }
            
            # Add admission-specific permissions for admission/discharge events
            if hasattr(event, 'admission') and event.admission:
                admission = event.admission
                event_data['admission_permissions'] = {
                    'can_edit_admission': can_edit_admission_data(self.request.user, admission),
                    'can_edit_discharge': can_edit_discharge_data(self.request.user, admission),
                    'can_cancel_discharge': can_cancel_discharge(self.request.user, admission),
                    'can_discharge': can_discharge_patient(self.request.user, admission),
                }
            
            events_with_permissions.append(event_data)
        
        return events_with_permissions
    
    def _get_cached_creators(self):
        """Get creators list with caching."""
        cache_key = f"event_creators_{self.patient.pk}"
        creators = cache.get(cache_key)
        
        if creators is None:
            creators = list(
                User.objects.filter(
                    event_set__patient=self.patient
                ).distinct().values(
                    'id', 'first_name', 'last_name', 'profession_type'
                ).order_by('first_name', 'last_name')
            )
            # Add full name
            for creator in creators:
                creator['full_name'] = f"{creator['first_name']} {creator['last_name']}".strip()
            
            cache.set(cache_key, creators, 300)  # 5 minutes
        
        return creators
    
    def _get_event_counts_by_type(self):
        """Get event counts by type with caching."""
        cache_key = f"event_type_counts_{self.patient.pk}"
        counts = cache.get(cache_key)
        
        if counts is None:
            counts = dict(
                Event.objects.filter(patient=self.patient)
                .values_list('event_type')
                .annotate(count=Count('id'))
                .order_by('event_type')
            )
            cache.set(cache_key, counts, 300)  # 5 minutes
        
        return counts


# Add method decorator for view-level caching
@method_decorator(cache_page(60), name='get')  # Cache for 1 minute
class OptimizedPatientEventsTimelineView(PatientEventsTimelineView):
    pass


@login_required
@require_http_methods(["GET"])
def event_api_detail(request, pk):
    """
    API endpoint for event details (used by modal).
    Returns JSON data for quick event viewing.
    """
    event = get_object_or_404(Event, pk=pk)
    
    # Permission check
    if not can_access_patient(request.user, event.patient):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Prepare response data
    data = {
        'id': str(event.pk),
        'event_type': event.event_type,
        'event_type_display': event.get_event_type_display(),
        'content': getattr(event, 'content', None),
        'description': getattr(event, 'description', None),
        'created_at': event.created_at.isoformat(),
        'created_at_formatted': event.created_at.strftime('%d/%m/%Y %H:%M'),
        'updated_at': event.updated_at.isoformat(),
        'updated_at_formatted': event.updated_at.strftime('%d/%m/%Y %H:%M'),
        'created_by_name': event.created_by.get_full_name(),
        'created_by_profession': getattr(event.created_by, 'profession', ''),
        'can_edit': can_edit_event(request.user, event),
        'can_delete': can_edit_event(request.user, event),
        'detail_url': reverse('events:event_detail', args=[event.pk]),
        'edit_url': reverse('events:event_edit', args=[event.pk]) if can_edit_event(request.user, event) else None,
    }
    
    return JsonResponse(data)
