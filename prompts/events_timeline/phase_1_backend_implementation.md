# Phase 1: Backend Implementation - Patient Events Timeline

## Overview
This phase implements the backend infrastructure for the patient events timeline, including views, URL patterns, and query optimizations.

## Step 1: Create Patient Events Timeline View

### File: `apps/events/views.py`

**Action**: Add new view class after existing views

```python
class PatientEventsTimelineView(ListView):
    """
    Timeline view for patient events with filtering and pagination.
    Displays events in reverse chronological order with summary cards.
    """
    model = Event
    template_name = 'events/patient_timeline.html'
    context_object_name = 'events'
    paginate_by = 15
    paginate_orphans = 5
    
    def get_queryset(self):
        """
        Get events for the specified patient with optimizations and filtering.
        """
        # Get patient from URL
        self.patient = get_object_or_404(Patient, pk=self.kwargs['patient_id'])
        
        # Check patient access permission
        if not can_access_patient(self.request.user, self.patient):
            raise PermissionDenied("You don't have permission to view this patient's events.")
        
        # Base queryset with optimizations
        queryset = Event.objects.filter(
            patient=self.patient
        ).select_related(
            'created_by',
            'updated_by'
        ).order_by('-created_at')
        
        # Apply filters
        queryset = self._apply_filters(queryset)
        
        return queryset
    
    def _apply_filters(self, queryset):
        """Apply filtering based on GET parameters."""
        
        # Event type filter
        event_types = self.request.GET.getlist('types')
        if event_types:
            queryset = queryset.filter(event_type__in=event_types)
        
        # Date range filter
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
        
        # Quick date filters
        quick_filter = self.request.GET.get('quick_date')
        if quick_filter:
            now = timezone.now()
            if quick_filter == '24h':
                queryset = queryset.filter(created_at__gte=now - timedelta(hours=24))
            elif quick_filter == '7d':
                queryset = queryset.filter(created_at__gte=now - timedelta(days=7))
            elif quick_filter == '30d':
                queryset = queryset.filter(created_at__gte=now - timedelta(days=30))
        
        # Creator filter
        creator_id = self.request.GET.get('creator')
        if creator_id:
            queryset = queryset.filter(created_by_id=creator_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add additional context for the template."""
        context = super().get_context_data(**kwargs)
        
        # Add patient to context
        context['patient'] = self.patient
        
        # Add permission context for each event
        events_with_permissions = []
        for event in context['events']:
            event_data = {
                'event': event,
                'can_edit': can_edit_event(self.request.user, event),
                'can_delete': can_edit_event(self.request.user, event),  # Same as edit for now
                'excerpt': self._get_event_excerpt(event)
            }
            events_with_permissions.append(event_data)
        
        context['events_with_permissions'] = events_with_permissions
        
        # Add filter options for template
        context['event_type_choices'] = Event.EVENT_TYPE_CHOICES
        context['available_creators'] = self._get_available_creators()
        
        # Add current filter values
        context['current_filters'] = {
            'types': self.request.GET.getlist('types'),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'quick_date': self.request.GET.get('quick_date', ''),
            'creator': self.request.GET.get('creator', ''),
        }
        
        # Add filter counts
        context['total_events'] = Event.objects.filter(patient=self.patient).count()
        context['filtered_count'] = self.get_queryset().count()
        
        return context
    
    def _get_event_excerpt(self, event):
        """Generate a short excerpt from event content."""
        if hasattr(event, 'content') and event.content:
            # Remove HTML tags and get first 150 characters
            import re
            clean_content = re.sub('<[^<]+?>', '', event.content)
            return clean_content[:150] + '...' if len(clean_content) > 150 else clean_content
        elif hasattr(event, 'description') and event.description:
            return event.description[:150] + '...' if len(event.description) > 150 else event.description
        else:
            return "No content available"
    
    @lru_cache(maxsize=1)
    def _get_available_creators(self):
        """Get list of users who have created events for this patient (cached)."""
        return User.objects.filter(
            created_events__patient=self.patient
        ).distinct().values('id', 'get_full_name', 'profession').order_by('get_full_name')
```

**Required Imports**: Add these to the top of the file:
```python
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils import timezone
from functools import lru_cache
from datetime import datetime, timedelta
import re
```

## Step 2: Update URL Patterns

### File: `apps/patients/urls.py`

**Action**: Add new URL pattern after existing patient URLs

```python
# Add this import at the top
from apps.events.views import PatientEventsTimelineView

# Add this URL pattern in the urlpatterns list
path('<uuid:patient_id>/timeline/', PatientEventsTimelineView.as_view(), name='patient_timeline'),
```

**Complete URL pattern should be**:
```python
urlpatterns = [
    # ... existing patterns ...
    path('<uuid:pk>/', views.PatientDetailView.as_view(), name='patient_detail'),
    path('<uuid:patient_id>/timeline/', PatientEventsTimelineView.as_view(), name='patient_timeline'),
    # ... rest of patterns ...
]
```

## Step 3: Add Helper Functions to Event Model

### File: `apps/events/models.py`

**Action**: Add these methods to the Event model class

```python
def get_excerpt(self, max_length=150):
    """Generate a short excerpt from event content."""
    content = getattr(self, 'content', None) or getattr(self, 'description', '')
    if content:
        # Remove HTML tags
        import re
        clean_content = re.sub('<[^<]+?>', '', str(content))
        return clean_content[:max_length] + '...' if len(clean_content) > max_length else clean_content
    return "No content available"

def get_event_type_badge_class(self):
    """Return CSS class for event type badge."""
    badge_classes = {
        'history_physical': 'bg-medical-primary',
        'daily_notes': 'bg-medical-success',
        'photos': 'bg-medical-info',
        'exam_results': 'bg-medical-warning',
        'procedures': 'bg-medical-danger',
        'medications': 'bg-medical-secondary',
        'discharge_summary': 'bg-medical-dark',
        'referrals': 'bg-medical-light',
        'progress_notes': 'bg-medical-teal',
        'other': 'bg-secondary'
    }
    return badge_classes.get(self.event_type, 'bg-secondary')

def get_event_type_icon(self):
    """Return Bootstrap icon class for event type."""
    icon_classes = {
        'history_physical': 'bi-clipboard2-heart',
        'daily_notes': 'bi-journal-text',
        'photos': 'bi-camera',
        'exam_results': 'bi-clipboard2-data',
        'procedures': 'bi-scissors',
        'medications': 'bi-capsule',
        'discharge_summary': 'bi-door-open',
        'referrals': 'bi-arrow-right-circle',
        'progress_notes': 'bi-graph-up',
        'other': 'bi-file-text'
    }
    return icon_classes.get(self.event_type, 'bi-file-text')

@property
def can_be_edited(self):
    """Check if event is within edit window (24 hours)."""
    if not self.created_at:
        return False
    edit_deadline = self.created_at + timedelta(hours=24)
    return timezone.now() <= edit_deadline
```

## Step 4: Create Timeline-Specific Manager (Optional Optimization)

### File: `apps/events/models.py`

**Action**: Add this manager class before the Event model

```python
class EventTimelineManager(models.Manager):
    """Custom manager for timeline queries with optimizations."""
    
    def for_patient_timeline(self, patient):
        """Get events for patient timeline with all optimizations."""
        return self.filter(
            patient=patient
        ).select_related(
            'created_by',
            'updated_by'
        ).prefetch_related(
            'created_by__groups'
        ).order_by('-created_at')
    
    def with_counts_by_type(self, patient):
        """Get event counts by type for filter display."""
        return self.filter(patient=patient).values('event_type').annotate(
            count=models.Count('id')
        ).order_by('event_type')
```

**Then add to Event model**:
```python
class Event(UUIDModel, TimeStampedModel):
    # ... existing fields ...
    
    # Add the manager
    objects = models.Manager()  # Default manager
    timeline = EventTimelineManager()  # Timeline-specific manager
```

## Step 5: Database Migration (if needed)

**Action**: If you added any new fields or indexes, create and run migration:

```bash
python manage.py makemigrations events
python manage.py migrate
```

## Step 6: Add URL Name to Patient App

### File: `apps/patients/urls.py`

**Action**: Ensure the URL has a clear name for reverse lookups:

```python
path('<uuid:patient_id>/timeline/', PatientEventsTimelineView.as_view(), name='patient_events_timeline'),
```

## Testing Steps

1. **Test URL routing**: Navigate to `/patients/<patient_uuid>/timeline/`
2. **Test filtering**: Add URL parameters like `?types=daily_notes&quick_date=7d`
3. **Test permissions**: Ensure only authorized users can access patient timelines
4. **Test pagination**: Create enough events to test pagination functionality
5. **Test performance**: Use Django Debug Toolbar to verify query optimization

## Expected Results

After completing Phase 1:
- New timeline view accessible at `/patients/<uuid>/timeline/`
- Filtering by event type, date range, and creator
- Pagination with 15 events per page
- Permission-aware event access
- Optimized database queries
- Event excerpts and metadata for summary cards

## Next Phase

Phase 2 will focus on creating the frontend templates and UI components for the timeline display.