# Phase 3: Integration & UX Enhancements

## Overview
This phase integrates the timeline with the patient detail page, adds UX enhancements like modal views, and implements mobile optimizations.

## Step 1: Update Patient Detail Page

### File: `apps/patients/templates/patients/patient_detail.html`

**Action**: Replace the placeholder Quick Actions section with timeline integration

**Find this section (around lines 317-355)**:
```html
<!-- Quick Actions -->
<div class="col-md-6">
    <div class="card card-medical">
        <div class="card-header bg-medical-teal text-white">
            <h5 class="card-title mb-0">
                <i class="bi bi-lightning-charge me-2"></i>
                Ações Rápidas
            </h5>
        </div>
        <div class="card-body text-center">
            <!-- Placeholder buttons -->
        </div>
    </div>
</div>
```

**Replace with**:
```html
<!-- Quick Actions & Recent Events -->
<div class="col-md-6">
    <div class="card card-medical">
        <div class="card-header bg-medical-teal text-white d-flex justify-content-between align-items-center">
            <h5 class="card-title mb-0">
                <i class="bi bi-lightning-charge me-2"></i>
                Ações Rápidas
            </h5>
            <a href="{% url 'patients:patient_events_timeline' patient.pk %}" 
               class="btn btn-sm btn-outline-light">
                <i class="bi bi-clock-history me-1"></i>
                Timeline Completa
            </a>
        </div>
        <div class="card-body">
            <!-- Quick Action Buttons -->
            <div class="row g-2 mb-3">
                <div class="col-6">
                    <a href="{% url 'dailynotes:patient_create' patient.pk %}" 
                       class="btn btn-medical-success btn-sm w-100">
                        <i class="bi bi-journal-text d-block fs-4 mb-1"></i>
                        <small>Nova Evolução</small>
                    </a>
                </div>
                <div class="col-6">
                    <a href="{% url 'events:event_create' %}?patient={{ patient.pk }}&type=exam_results" 
                       class="btn btn-medical-warning btn-sm w-100">
                        <i class="bi bi-clipboard2-data d-block fs-4 mb-1"></i>
                        <small>Novo Exame</small>
                    </a>
                </div>
                <div class="col-6">
                    <a href="{% url 'events:event_create' %}?patient={{ patient.pk }}&type=photos" 
                       class="btn btn-medical-info btn-sm w-100">
                        <i class="bi bi-camera d-block fs-4 mb-1"></i>
                        <small>Adicionar Foto</small>
                    </a>
                </div>
                <div class="col-6">
                    <a href="{% url 'events:event_create' %}?patient={{ patient.pk }}&type=procedures" 
                       class="btn btn-medical-danger btn-sm w-100">
                        <i class="bi bi-scissors d-block fs-4 mb-1"></i>
                        <small>Procedimento</small>
                    </a>
                </div>
            </div>

            <!-- Recent Events Widget -->
            <div class="border-top pt-3">
                <h6 class="text-medical-primary mb-2">
                    <i class="bi bi-clock me-1"></i>
                    Eventos Recentes
                </h6>
                <div id="recent-events-widget">
                    {% include 'events/widgets/recent_events.html' with patient=patient limit=3 %}
                </div>
            </div>
        </div>
    </div>
</div>
```

## Step 2: Create Recent Events Widget

### File: `apps/events/templates/events/widgets/recent_events.html`

**Action**: Create reusable widget for recent events

```html
{% load permission_tags %}

<div class="recent-events-list">
    {% if recent_events %}
        {% for event in recent_events %}
            <div class="recent-event-item d-flex align-items-center py-2 {% if not forloop.last %}border-bottom{% endif %}">
                <div class="flex-shrink-0 me-2">
                    <span class="badge {{ event.get_event_type_badge_class }} badge-sm">
                        <i class="{{ event.get_event_type_icon }}"></i>
                    </span>
                </div>
                <div class="flex-grow-1 min-width-0">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1 min-width-0">
                            <h6 class="mb-0 text-truncate">
                                {{ event.get_event_type_display }}
                            </h6>
                            <small class="text-muted">
                                {{ event.created_by.get_full_name }} • 
                                {{ event.created_at|timesince }} atrás
                            </small>
                        </div>
                        <div class="flex-shrink-0 ms-2">
                            <a href="{% url 'events:event_detail' event.pk %}" 
                               class="btn btn-outline-primary btn-xs"
                               title="Visualizar evento">
                                <i class="bi bi-eye"></i>
                            </a>
                        </div>
                    </div>
                    {% if event.get_excerpt %}
                        <p class="mb-0 mt-1 text-muted small text-truncate">
                            {{ event.get_excerpt|truncatechars:50 }}
                        </p>
                    {% endif %}
                </div>
            </div>
        {% endfor %}
        
        <!-- View All Link -->
        <div class="text-center mt-2">
            <a href="{% url 'patients:patient_events_timeline' patient.pk %}" 
               class="btn btn-outline-medical-primary btn-sm">
                <i class="bi bi-clock-history me-1"></i>
                Ver Timeline Completa
            </a>
        </div>
    {% else %}
        <div class="text-center py-3">
            <div class="text-muted mb-2">
                <i class="bi bi-clock-history" style="font-size: 2rem; opacity: 0.3;"></i>
            </div>
            <p class="text-muted small mb-2">Nenhum evento registrado</p>
            <a href="{% url 'dailynotes:patient_create' patient.pk %}" 
               class="btn btn-medical-success btn-sm">
                <i class="bi bi-plus-circle me-1"></i>
                Criar Primeiro Evento
            </a>
        </div>
    {% endif %}
</div>

<style>
.badge-sm {
    font-size: 0.65rem;
    padding: 0.25em 0.4em;
}
.btn-xs {
    padding: 0.125rem 0.25rem;
    font-size: 0.75rem;
    line-height: 1.2;
}
.recent-event-item:hover {
    background-color: rgba(0,0,0,0.02);
    border-radius: 4px;
}
.min-width-0 {
    min-width: 0;
}
</style>
```

## Step 3: Update Patient Detail View

### File: `apps/patients/views.py`

**Action**: Add recent events to the PatientDetailView context

**Find the PatientDetailView class and update it**:
```python
class PatientDetailView(DetailView):
    model = Patient
    template_name = 'patients/patient_detail.html'
    context_object_name = 'patient'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.get_object()
        
        # Check permission
        if not can_access_patient(self.request.user, patient):
            raise PermissionDenied("You don't have permission to view this patient.")
        
        # Add recent events (last 3)
        from apps.events.models import Event
        context['recent_events'] = Event.objects.filter(
            patient=patient
        ).select_related('created_by').order_by('-created_at')[:3]
        
        # Add events count
        context['total_events_count'] = Event.objects.filter(patient=patient).count()
        
        # Add permission context
        context['can_edit_patient'] = can_change_patient_personal_data(self.request.user, patient)
        
        return context
```

**Add required imports at the top**:
```python
from django.core.exceptions import PermissionDenied
from apps.core.permissions.utils import can_access_patient, can_change_patient_personal_data
```

## Step 4: Create Event Detail Modal Component

### File: `apps/events/templates/events/components/event_modal.html`

**Action**: Create modal component for quick event viewing

```html
<!-- Event Detail Modal -->
<div class="modal fade" id="eventModal" tabindex="-1" aria-labelledby="eventModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="eventModalLabel">
                    <span id="modal-event-type"></span>
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <!-- Loading state -->
                <div id="modal-loading" class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Carregando...</span>
                    </div>
                </div>
                
                <!-- Event content -->
                <div id="modal-content" style="display: none;">
                    <!-- Event metadata -->
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <strong>Data/Hora:</strong>
                            <span id="modal-datetime"></span>
                        </div>
                        <div class="col-md-6">
                            <strong>Profissional:</strong>
                            <span id="modal-creator"></span>
                        </div>
                    </div>
                    
                    <!-- Event content -->
                    <div class="mb-3">
                        <strong>Conteúdo:</strong>
                        <div id="modal-event-content" class="mt-2 p-3 bg-light rounded"></div>
                    </div>
                    
                    <!-- Last updated -->
                    <div class="text-muted small" id="modal-updated" style="display: none;">
                        <i class="bi bi-pencil-square me-1"></i>
                        <span></span>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                <a href="#" id="modal-view-full" class="btn btn-primary" style="display: none;">
                    <i class="bi bi-eye me-1"></i>
                    Visualizar Completo
                </a>
                <a href="#" id="modal-edit" class="btn btn-warning" style="display: none;">
                    <i class="bi bi-pencil me-1"></i>
                    Editar
                </a>
            </div>
        </div>
    </div>
</div>
```

## Step 5: Add JavaScript for Modal and AJAX

### File: `apps/events/static/events/js/timeline.js`

**Action**: Create JavaScript file for timeline interactions

```javascript
// Timeline interactions and modal handling
document.addEventListener('DOMContentLoaded', function() {
    
    // Event modal handling
    const eventModal = document.getElementById('eventModal');
    if (eventModal) {
        initializeEventModal();
    }
    
    // Timeline filter handling
    initializeTimelineFilters();
    
    // Infinite scroll (optional)
    initializeInfiniteScroll();
});

function initializeEventModal() {
    const modal = new bootstrap.Modal(document.getElementById('eventModal'));
    
    // Handle event card clicks for modal
    document.addEventListener('click', function(e) {
        const modalTrigger = e.target.closest('[data-event-modal]');
        if (modalTrigger) {
            e.preventDefault();
            const eventId = modalTrigger.dataset.eventModal;
            loadEventModal(eventId);
        }
    });
}

function loadEventModal(eventId) {
    const modal = bootstrap.Modal.getInstance(document.getElementById('eventModal'));
    const modalElement = document.getElementById('eventModal');
    
    // Show loading state
    modalElement.querySelector('#modal-loading').style.display = 'block';
    modalElement.querySelector('#modal-content').style.display = 'none';
    modalElement.querySelector('#modal-view-full').style.display = 'none';
    modalElement.querySelector('#modal-edit').style.display = 'none';
    
    // Show modal
    modal.show();
    
    // Fetch event data
    fetch(`/events/${eventId}/api/`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Event not found');
            }
            return response.json();
        })
        .then(data => {
            populateEventModal(data);
        })
        .catch(error => {
            console.error('Error loading event:', error);
            showModalError('Erro ao carregar evento');
        });
}

function populateEventModal(eventData) {
    const modalElement = document.getElementById('eventModal');
    
    // Hide loading, show content
    modalElement.querySelector('#modal-loading').style.display = 'none';
    modalElement.querySelector('#modal-content').style.display = 'block';
    
    // Populate data
    modalElement.querySelector('#modal-event-type').textContent = eventData.event_type_display;
    modalElement.querySelector('#modal-datetime').textContent = eventData.created_at_formatted;
    modalElement.querySelector('#modal-creator').textContent = eventData.created_by_name;
    modalElement.querySelector('#modal-event-content').innerHTML = eventData.content || eventData.description || 'Sem conteúdo';
    
    // Updated info
    if (eventData.updated_at !== eventData.created_at) {
        const updatedElement = modalElement.querySelector('#modal-updated');
        updatedElement.style.display = 'block';
        updatedElement.querySelector('span').textContent = `Última edição: ${eventData.updated_at_formatted}`;
    }
    
    // Action buttons
    const viewFullBtn = modalElement.querySelector('#modal-view-full');
    const editBtn = modalElement.querySelector('#modal-edit');
    
    viewFullBtn.href = eventData.detail_url;
    viewFullBtn.style.display = 'inline-block';
    
    if (eventData.can_edit) {
        editBtn.href = eventData.edit_url;
        editBtn.style.display = 'inline-block';
    }
}

function showModalError(message) {
    const modalElement = document.getElementById('eventModal');
    modalElement.querySelector('#modal-loading').style.display = 'none';
    modalElement.querySelector('#modal-content').innerHTML = `
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            ${message}
        </div>
    `;
    modalElement.querySelector('#modal-content').style.display = 'block';
}

function initializeTimelineFilters() {
    const filterForm = document.getElementById('timeline-filters');
    if (!filterForm) return;
    
    // Auto-submit on filter changes
    const filterInputs = filterForm.querySelectorAll('input[type="checkbox"], input[type="radio"], select');
    
    filterInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Add loading indicator
            showFilterLoading();
            
            // Debounce for better UX
            setTimeout(() => {
                filterForm.submit();
            }, 300);
        });
    });
    
    // Date input handling
    const dateInputs = filterForm.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Clear quick date selection
            const quickDateInputs = filterForm.querySelectorAll('input[name="quick_date"]');
            quickDateInputs.forEach(radio => {
                if (radio.value !== '') {
                    radio.checked = false;
                }
            });
        });
    });
    
    // Quick date handling
    const quickDateInputs = filterForm.querySelectorAll('input[name="quick_date"]');
    quickDateInputs.forEach(input => {
        input.addEventListener('change', function() {
            if (this.value !== '') {
                const dateInputs = filterForm.querySelectorAll('input[type="date"]');
                dateInputs.forEach(dateInput => {
                    dateInput.value = '';
                });
            }
        });
    });
}

function showFilterLoading() {
    const timelineContainer = document.querySelector('.timeline-events');
    if (timelineContainer) {
        timelineContainer.style.opacity = '0.6';
        timelineContainer.style.pointerEvents = 'none';
        
        // Add loading spinner if not exists
        if (!document.querySelector('.filter-loading')) {
            const loading = document.createElement('div');
            loading.className = 'filter-loading position-absolute top-50 start-50 translate-middle';
            loading.innerHTML = `
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
            `;
            timelineContainer.parentElement.style.position = 'relative';
            timelineContainer.parentElement.appendChild(loading);
        }
    }
}

function initializeInfiniteScroll() {
    const nextPageUrl = document.querySelector('[data-next-page]')?.dataset.nextPage;
    if (!nextPageUrl) return;
    
    const options = {
        root: null,
        rootMargin: '100px',
        threshold: 0.1
    };
    
    const loadMore = document.createElement('div');
    loadMore.className = 'load-more-trigger';
    loadMore.style.height = '1px';
    
    const timelineContainer = document.querySelector('.timeline-events');
    if (timelineContainer) {
        timelineContainer.appendChild(loadMore);
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    loadMoreEvents(nextPageUrl);
                    observer.unobserve(entry.target);
                }
            });
        }, options);
        
        observer.observe(loadMore);
    }
}

function loadMoreEvents(url) {
    // Implementation for infinite scroll loading
    // This would fetch the next page and append to the timeline
    console.log('Loading more events from:', url);
}
```

## Step 6: Add CSS for Enhanced Timeline

### File: Add to `apps/events/static/events/css/timeline.css`

**Action**: Add additional styles for new components

```css
/* Recent Events Widget Styles */
.recent-events-list .recent-event-item {
    transition: background-color 0.2s ease;
    margin: 0 -0.5rem;
    padding-left: 0.5rem;
    padding-right: 0.5rem;
}

.recent-events-list .recent-event-item:hover {
    background-color: rgba(var(--bs-primary-rgb), 0.05);
    border-radius: 4px;
}

.badge-sm {
    font-size: 0.65rem;
    padding: 0.25em 0.4em;
}

.btn-xs {
    padding: 0.125rem 0.25rem;
    font-size: 0.75rem;
    line-height: 1.2;
    border-radius: 0.25rem;
}

/* Modal Enhancements */
.modal-lg .modal-content {
    border-radius: 0.5rem;
    border: none;
    box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
}

.modal-header {
    border-bottom: 1px solid #dee2e6;
    background-color: #f8f9fa;
}

#modal-event-content {
    max-height: 300px;
    overflow-y: auto;
    border: 1px solid #dee2e6;
}

/* Filter Loading State */
.filter-loading {
    z-index: 10;
}

.timeline-events.loading {
    opacity: 0.6;
    pointer-events: none;
}

/* Quick Action Buttons */
.quick-action-grid .btn {
    aspect-ratio: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 0.75rem 0.5rem;
    text-align: center;
    min-height: 80px;
}

.quick-action-grid .btn i {
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
}

.quick-action-grid .btn small {
    font-size: 0.75rem;
    line-height: 1.2;
}

/* Responsive Timeline Improvements */
@media (max-width: 576px) {
    .timeline-card {
        margin-left: -0.5rem;
        margin-right: -0.5rem;
    }
    
    .quick-action-grid .btn {
        min-height: 70px;
        padding: 0.5rem 0.25rem;
    }
    
    .quick-action-grid .btn i {
        font-size: 1.25rem;
    }
    
    .recent-events-list .recent-event-item {
        flex-direction: column;
        align-items: flex-start;
    }
    
    .recent-events-list .btn-xs {
        margin-top: 0.5rem;
        align-self: flex-end;
    }
}

/* Print Optimizations */
@media print {
    .quick-action-grid,
    .modal,
    .filter-panel,
    .event-actions,
    .pagination,
    .btn {
        display: none !important;
    }
    
    .timeline-card {
        break-inside: avoid;
        margin-bottom: 1rem;
        box-shadow: none;
        border: 1px solid #000;
    }
    
    .card-header {
        background-color: #f0f0f0 !important;
        color: #000 !important;
    }
}
```

## Step 7: Update Template Tags for Widget Support

### File: `apps/events/templatetags/__init__.py`

**Action**: Create templatetags directory and init file if they don't exist

```python
# Empty file to make this a Python package
```

### File: `apps/events/templatetags/event_tags.py`

**Action**: Create template tags for events

```python
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
    ).select_related('created_by').order_by('-created_at')[:limit]
    
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
```

## Testing Steps

1. **Patient detail integration**: Check timeline link and recent events widget
2. **Modal functionality**: Test event modal loading and interactions
3. **Responsive design**: Test on different screen sizes
4. **JavaScript functionality**: Test filter auto-submission and modal behavior
5. **Permission handling**: Verify widgets respect user permissions
6. **Performance**: Check for N+1 queries in template tags

## Expected Results

After completing Phase 3:
- Timeline fully integrated with patient detail page
- Recent events widget showing latest 3 events
- Quick action buttons for common event types
- Modal component for quick event viewing
- Enhanced JavaScript interactions
- Mobile-optimized responsive design
- Permission-aware widget display

## Next Phase

Phase 4 will focus on performance optimizations, accessibility improvements, and final polish including print styles and advanced features.