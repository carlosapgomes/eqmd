# Phase 4: Performance Optimizations & Final Polish

## Overview
This phase focuses on performance optimizations, accessibility improvements, caching strategies, and final polish including print styles and advanced features.

## Step 1: Performance Optimizations

### File: `apps/events/views.py`

**Action**: Add caching and query optimizations to PatientEventsTimelineView

```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.db.models import Prefetch, Count, Q
from django.contrib.auth import get_user_model

User = get_user_model()

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
        ).select_related(
            'created_by',
            'updated_by',
            'patient'
        ).prefetch_related(
            Prefetch(
                'created_by',
                queryset=User.objects.select_related('groups')
            )
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
            events_with_permissions.append(event_data)
        
        return events_with_permissions
    
    def _get_cached_creators(self):
        """Get creators list with caching."""
        cache_key = f"event_creators_{self.patient.pk}"
        creators = cache.get(cache_key)
        
        if creators is None:
            creators = list(
                User.objects.filter(
                    created_events__patient=self.patient
                ).distinct().values(
                    'id', 'first_name', 'last_name', 'profession'
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
class PatientEventsTimelineView(PatientEventsTimelineView):
    pass
```

## Step 2: Add Database Indexes

### File: `apps/events/migrations/0003_add_timeline_indexes.py`

**Action**: Create migration for performance indexes

```python
from django.db import migrations

class Migration(migrations.Migration):
    
    dependencies = [
        ('events', '0002_add_event_indexes'),  # Adjust based on your latest migration
    ]
    
    operations = [
        # Compound indexes for timeline queries
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_event_patient_created_type "
            "ON events_event (patient_id, created_at DESC, event_type);",
            reverse_sql="DROP INDEX IF EXISTS idx_event_patient_created_type;"
        ),
        
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_event_patient_creator_created "
            "ON events_event (patient_id, created_by_id, created_at DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_event_patient_creator_created;"
        ),
        
        # Index for date-based filtering
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_event_patient_date "
            "ON events_event (patient_id, (created_at::date));",
            reverse_sql="DROP INDEX IF EXISTS idx_event_patient_date;"
        ),
    ]
```

## Step 3: Add Event API Endpoint for Modal

### File: `apps/events/views.py`

**Action**: Add API endpoint for modal loading

```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

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

class EventAPIView(APIView):
    """
    Alternative DRF-based API view for events (if using DRF).
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        try:
            event = Event.objects.select_related('created_by', 'patient').get(pk=pk)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found'}, status=404)
        
        # Permission check
        if not can_access_patient(request.user, event.patient):
            return Response({'error': 'Permission denied'}, status=403)
        
        # Serialize data
        serializer = EventModalSerializer(event, context={'request': request})
        return Response(serializer.data)
```

### File: `apps/events/urls.py`

**Action**: Add API URL pattern

```python
from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # ... existing patterns ...
    path('<uuid:pk>/api/', views.event_api_detail, name='event_api_detail'),
    # ... rest of patterns ...
]
```

## Step 4: Add Accessibility Improvements

### File: `apps/events/templates/events/patient_timeline.html`

**Action**: Add accessibility enhancements to the timeline template

**Add these attributes and elements**:

```html
<!-- Update the main timeline container -->
<div class="timeline-container" role="main" aria-label="Timeline de eventos do paciente">
    
    <!-- Add skip navigation -->
    <a class="visually-hidden-focusable" href="#timeline-content">Pular para timeline</a>
    
    <!-- Update filter form -->
    <form method="get" id="timeline-filters" role="search" aria-label="Filtros da timeline">
        <fieldset>
            <legend class="visually-hidden">Filtros de eventos</legend>
            
            <!-- Event type filter with proper ARIA -->
            <div class="mb-3" role="group" aria-labelledby="event-types-label">
                <label id="event-types-label" class="form-label fw-semibold">Tipos de Evento</label>
                {% for value, label in event_type_choices %}
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" 
                               name="types" value="{{ value }}" id="type_{{ value }}"
                               {% if value in current_filters.types %}checked{% endif %}
                               aria-describedby="type-{{ value }}-desc">
                        <label class="form-check-label" for="type_{{ value }}">
                            {{ label }}
                        </label>
                        <span id="type-{{ value }}-desc" class="visually-hidden">
                            {% with count=event_counts_by_type|get_item:value %}
                                {{ count|default:0 }} evento{{ count|pluralize }}
                            {% endwith %}
                        </span>
                    </div>
                {% endfor %}
            </div>
            
            <!-- Update date inputs with proper labels -->
            <div class="mb-3">
                <fieldset>
                    <legend class="form-label fw-semibold">Período Personalizado</legend>
                    <div class="row g-2">
                        <div class="col-6">
                            <label for="date_from" class="visually-hidden">Data inicial</label>
                            <input type="date" class="form-control form-control-sm" 
                                   id="date_from" name="date_from" 
                                   value="{{ current_filters.date_from }}"
                                   aria-label="Data inicial do período">
                        </div>
                        <div class="col-6">
                            <label for="date_to" class="visually-hidden">Data final</label>
                            <input type="date" class="form-control form-control-sm" 
                                   id="date_to" name="date_to" 
                                   value="{{ current_filters.date_to }}"
                                   aria-label="Data final do período">
                        </div>
                    </div>
                </fieldset>
            </div>
        </fieldset>
    </form>
    
    <!-- Update timeline events container -->
    <div id="timeline-content" class="timeline-events" role="feed" 
         aria-label="Lista de eventos médicos" aria-live="polite">
         
        {% for event_data in events_with_permissions %}
            {% with event=event_data.event %}
            <article class="timeline-card card card-medical mb-3" 
                     role="article"
                     aria-labelledby="event-{{ event.pk }}-title"
                     aria-describedby="event-{{ event.pk }}-content">
                
                <div class="card-body">
                    <!-- Event header with proper heading -->
                    <header class="d-flex align-items-start justify-content-between mb-2">
                        <div class="d-flex align-items-center">
                            <h3 id="event-{{ event.pk }}-title" class="h6 mb-0 me-2">
                                <span class="badge {{ event.get_event_type_badge_class }} event-type-badge">
                                    <i class="{{ event.get_event_type_icon }} me-1" aria-hidden="true"></i>
                                    {{ event.get_event_type_display }}
                                </span>
                            </h3>
                            <time datetime="{{ event.created_at|date:'c' }}" 
                                  class="text-muted small">
                                <i class="bi bi-clock me-1" aria-hidden="true"></i>
                                {{ event.created_at|date:"d/m/Y H:i" }}
                            </time>
                        </div>
                        
                        <!-- Event actions with proper ARIA -->
                        <div class="event-actions" role="group" 
                             aria-label="Ações para {{ event.get_event_type_display }}">
                            <div class="btn-group btn-group-sm">
                                <a href="{% url 'events:event_detail' event.pk %}" 
                                   class="btn btn-outline-primary btn-sm"
                                   aria-label="Visualizar {{ event.get_event_type_display }} completo">
                                    <i class="bi bi-eye" aria-hidden="true"></i>
                                    <span class="visually-hidden">Visualizar</span>
                                </a>
                                {% if event_data.can_edit %}
                                    <a href="{% url 'events:event_edit' event.pk %}" 
                                       class="btn btn-outline-warning btn-sm"
                                       aria-label="Editar {{ event.get_event_type_display }}">
                                        <i class="bi bi-pencil" aria-hidden="true"></i>
                                        <span class="visually-hidden">Editar</span>
                                    </a>
                                {% endif %}
                            </div>
                        </div>
                    </header>

                    <!-- Event content -->
                    <div id="event-{{ event.pk }}-content" class="event-content">
                        <p class="event-excerpt">{{ event_data.excerpt }}</p>
                    </div>

                    <!-- Event metadata -->
                    <footer class="d-flex align-items-center justify-content-between mt-2 pt-2 border-top">
                        <small class="text-muted">
                            <i class="bi bi-person me-1" aria-hidden="true"></i>
                            <span aria-label="Criado por">{{ event.created_by.get_full_name }}</span>
                            {% if event.created_by.profession %}
                                <span aria-label="Profissão">({{ event.created_by.profession }})</span>
                            {% endif %}
                        </small>
                        {% if event.updated_at != event.created_at %}
                            <small class="text-muted">
                                <i class="bi bi-pencil-square me-1" aria-hidden="true"></i>
                                <time datetime="{{ event.updated_at|date:'c' }}">
                                    Editado em {{ event.updated_at|date:"d/m/Y H:i" }}
                                </time>
                            </small>
                        {% endif %}
                    </footer>
                </div>
            </article>
            {% endwith %}
        {% endfor %}
    </div>
</div>
```

## Step 5: Add Print Styles

### File: `apps/events/static/events/css/print.css`

**Action**: Create dedicated print stylesheet

```css
/* Print Styles for Timeline */
@media print {
    /* Hide interactive elements */
    .filter-panel,
    .event-actions,
    .pagination,
    .btn,
    .modal,
    .navbar,
    .sidebar,
    nav,
    .d-print-none {
        display: none !important;
    }
    
    /* Show print-only elements */
    .d-print-block {
        display: block !important;
    }
    
    .d-print-inline {
        display: inline !important;
    }
    
    /* Page layout */
    body {
        font-size: 12pt;
        line-height: 1.4;
        color: #000;
        background: #fff;
    }
    
    .container-fluid {
        max-width: none;
        margin: 0;
        padding: 0;
    }
    
    /* Timeline specific styles */
    .timeline-card {
        break-inside: avoid;
        margin-bottom: 1rem;
        border: 1px solid #000;
        box-shadow: none;
        page-break-inside: avoid;
    }
    
    .timeline-card .card-header {
        background-color: #f0f0f0 !important;
        color: #000 !important;
        -webkit-print-color-adjust: exact;
        color-adjust: exact;
    }
    
    /* Event type badges */
    .event-type-badge {
        border: 1px solid #000;
        background-color: #f0f0f0 !important;
        color: #000 !important;
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #000;
        page-break-after: avoid;
    }
    
    p {
        orphans: 3;
        widows: 3;
    }
    
    /* Tables and content */
    .event-excerpt {
        font-size: 11pt;
        color: #333;
    }
    
    /* Page breaks */
    .timeline-card:nth-child(10n) {
        page-break-after: always;
    }
    
    /* Print header */
    .print-header {
        display: block !important;
        text-align: center;
        margin-bottom: 2rem;
        border-bottom: 2px solid #000;
        padding-bottom: 1rem;
    }
    
    /* Footer */
    @page {
        margin: 2cm;
        @bottom-right {
            content: "Página " counter(page) " de " counter(pages);
        }
        @bottom-left {
            content: "Gerado em " string(print-date);
        }
    }
}

/* Print header template */
.print-header {
    display: none;
}

@media print {
    .print-header {
        display: block !important;
    }
}
```

## Step 6: Add Keyboard Navigation

### File: `apps/events/static/events/js/accessibility.js`

**Action**: Create accessibility-focused JavaScript

```javascript
// Accessibility enhancements for timeline
document.addEventListener('DOMContentLoaded', function() {
    initializeKeyboardNavigation();
    initializeScreenReaderSupport();
    initializeFocusManagement();
});

function initializeKeyboardNavigation() {
    // Arrow key navigation through timeline cards
    const timelineCards = document.querySelectorAll('.timeline-card');
    let currentIndex = -1;
    
    document.addEventListener('keydown', function(e) {
        if (e.target.closest('.timeline-events')) {
            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    navigateToCard(currentIndex + 1);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    navigateToCard(currentIndex - 1);
                    break;
                case 'Home':
                    e.preventDefault();
                    navigateToCard(0);
                    break;
                case 'End':
                    e.preventDefault();
                    navigateToCard(timelineCards.length - 1);
                    break;
                case 'Enter':
                case ' ':
                    if (currentIndex >= 0) {
                        e.preventDefault();
                        const card = timelineCards[currentIndex];
                        const viewLink = card.querySelector('.btn-outline-primary');
                        if (viewLink) viewLink.click();
                    }
                    break;
            }
        }
    });
    
    function navigateToCard(index) {
        if (index < 0 || index >= timelineCards.length) return;
        
        currentIndex = index;
        const card = timelineCards[index];
        
        // Remove previous focus
        timelineCards.forEach(c => c.classList.remove('keyboard-focused'));
        
        // Add focus to current card
        card.classList.add('keyboard-focused');
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Announce to screen readers
        const eventType = card.querySelector('.event-type-badge').textContent.trim();
        const timestamp = card.querySelector('time').textContent.trim();
        announceToScreenReader(`Evento ${index + 1} de ${timelineCards.length}: ${eventType}, ${timestamp}`);
    }
}

function initializeScreenReaderSupport() {
    // Live region for filter updates
    const liveRegion = document.getElementById('filter-live-region') || createLiveRegion();
    
    // Announce filter changes
    const filterInputs = document.querySelectorAll('#timeline-filters input, #timeline-filters select');
    filterInputs.forEach(input => {
        input.addEventListener('change', function() {
            const filterType = this.name;
            const filterValue = this.type === 'checkbox' ? 
                (this.checked ? this.nextElementSibling.textContent : 'removido') :
                this.value || 'todos';
            
            setTimeout(() => {
                announceToScreenReader(`Filtro ${filterType}: ${filterValue}`);
            }, 100);
        });
    });
}

function createLiveRegion() {
    const liveRegion = document.createElement('div');
    liveRegion.id = 'filter-live-region';
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.className = 'visually-hidden';
    document.body.appendChild(liveRegion);
    return liveRegion;
}

function announceToScreenReader(message) {
    const liveRegion = document.getElementById('filter-live-region');
    if (liveRegion) {
        liveRegion.textContent = message;
        setTimeout(() => {
            liveRegion.textContent = '';
        }, 1000);
    }
}

function initializeFocusManagement() {
    // Skip links
    const skipLink = document.querySelector('.visually-hidden-focusable');
    if (skipLink) {
        skipLink.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.focus();
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
    
    // Modal focus management
    const eventModal = document.getElementById('eventModal');
    if (eventModal) {
        eventModal.addEventListener('shown.bs.modal', function() {
            const firstFocusable = this.querySelector('button, input, select, textarea, a[href]');
            if (firstFocusable) firstFocusable.focus();
        });
        
        eventModal.addEventListener('hidden.bs.modal', function() {
            // Return focus to the trigger element
            const trigger = document.querySelector('[data-event-modal]:focus-within');
            if (trigger) trigger.focus();
        });
    }
}

// CSS for keyboard focus indication
const focusStyles = document.createElement('style');
focusStyles.textContent = `
    .keyboard-focused {
        outline: 3px solid #0d6efd;
        outline-offset: 2px;
        z-index: 10;
        position: relative;
    }
    
    .timeline-card:focus-within {
        outline: 2px solid #0d6efd;
        outline-offset: 1px;
    }
    
    .visually-hidden-focusable:focus {
        position: static !important;
        width: auto !important;
        height: auto !important;
        clip: auto !important;
        white-space: normal !important;
        background-color: #007bff;
        color: white;
        padding: 0.5rem;
        text-decoration: none;
        border-radius: 0.25rem;
    }
`;
document.head.appendChild(focusStyles);
```

## Step 7: Add Performance Monitoring

### File: `apps/events/management/commands/timeline_performance.py`

**Action**: Create management command for performance monitoring

```python
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from apps.events.models import Event
from apps.patients.models import Patient
import time

class Command(BaseCommand):
    help = 'Analyze timeline performance and suggest optimizations'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            choices=['analyze', 'test', 'report'],
            default='analyze',
            help='Action to perform'
        )
        
        parser.add_argument(
            '--patient-id',
            help='Specific patient ID to test'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'analyze':
            self.analyze_query_performance()
        elif action == 'test':
            self.test_timeline_performance(options.get('patient_id'))
        elif action == 'report':
            self.generate_performance_report()
    
    def analyze_query_performance(self):
        """Analyze common timeline queries for performance issues."""
        self.stdout.write("Analyzing timeline query performance...")
        
        # Test various query patterns
        queries = [
            ('Basic timeline query', lambda p: Event.objects.filter(patient=p).order_by('-created_at')[:15]),
            ('Optimized timeline query', lambda p: Event.objects.filter(patient=p).select_related('created_by').order_by('-created_at')[:15]),
            ('With prefetch', lambda p: Event.objects.filter(patient=p).select_related('created_by').prefetch_related('created_by__groups').order_by('-created_at')[:15]),
        ]
        
        patient = Patient.objects.first()
        if not patient:
            self.stdout.write(self.style.ERROR("No patients found for testing"))
            return
        
        for query_name, query_func in queries:
            start_time = time.time()
            start_queries = len(connection.queries)
            
            list(query_func(patient))  # Force evaluation
            
            end_time = time.time()
            end_queries = len(connection.queries)
            
            self.stdout.write(
                f"{query_name}: {end_time - start_time:.3f}s, "
                f"{end_queries - start_queries} queries"
            )
    
    def test_timeline_performance(self, patient_id=None):
        """Test timeline performance with real data."""
        if patient_id:
            try:
                patient = Patient.objects.get(pk=patient_id)
            except Patient.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Patient {patient_id} not found"))
                return
        else:
            # Find patient with most events
            patient = Patient.objects.annotate(
                event_count=Count('events')
            ).order_by('-event_count').first()
            
            if not patient:
                self.stdout.write(self.style.ERROR("No patients found"))
                return
        
        self.stdout.write(f"Testing timeline performance for patient: {patient}")
        
        # Simulate timeline view query
        start_time = time.time()
        start_queries = len(connection.queries)
        
        events = Event.objects.filter(
            patient=patient
        ).select_related(
            'created_by',
            'updated_by'
        ).order_by('-created_at')[:15]
        
        # Force evaluation and permission checks
        for event in events:
            _ = event.get_excerpt()
            _ = event.can_be_edited
        
        end_time = time.time()
        end_queries = len(connection.queries)
        
        self.stdout.write(
            f"Timeline loaded in {end_time - start_time:.3f}s with "
            f"{end_queries - start_queries} database queries"
        )
    
    def generate_performance_report(self):
        """Generate comprehensive performance report."""
        self.stdout.write("Generating timeline performance report...")
        
        # Database statistics
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(DISTINCT patient_id) as patients_with_events,
                    AVG(LENGTH(COALESCE(content, description, ''))) as avg_content_length
                FROM events_event
            """)
            stats = cursor.fetchone()
        
        self.stdout.write("=== Timeline Performance Report ===")
        self.stdout.write(f"Total events: {stats[0]:,}")
        self.stdout.write(f"Patients with events: {stats[1]:,}")
        self.stdout.write(f"Average content length: {stats[2]:.0f} characters")
        
        # Index usage analysis
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE tablename = 'events_event'
                ORDER BY idx_scan DESC
            """)
            indexes = cursor.fetchall()
        
        if indexes:
            self.stdout.write("\n=== Index Usage ===")
            for index in indexes:
                self.stdout.write(f"{index[2]}: {index[3]} scans, {index[4]} tuples read")
        
        # Recommendations
        self.stdout.write("\n=== Recommendations ===")
        if stats[0] > 10000:
            self.stdout.write("• Consider implementing pagination cache for large datasets")
        if stats[2] > 1000:
            self.stdout.write("• Consider truncating content in list views")
        
        self.stdout.write("• Enable query caching for filter options")
        self.stdout.write("• Use database connection pooling in production")
        self.stdout.write("• Consider CDN for static assets")
```

## Testing Steps

1. **Performance testing**: Run the performance command and check query counts
2. **Accessibility testing**: Test with screen readers and keyboard navigation
3. **Print testing**: Test print functionality across browsers
4. **Cache testing**: Verify caching is working and invalidating properly
5. **Load testing**: Test with large numbers of events
6. **Mobile testing**: Verify all features work on mobile devices

## Expected Results

After completing Phase 4:
- Optimized database queries with proper indexing
- Comprehensive caching strategy for improved performance
- Full accessibility compliance (WCAG 2.1 AA)
- Print-friendly timeline layouts
- Keyboard navigation support
- Performance monitoring tools
- Production-ready optimizations

This completes the timeline implementation with all performance optimizations and accessibility features in place.