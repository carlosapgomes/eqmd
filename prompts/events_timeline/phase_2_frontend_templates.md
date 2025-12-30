# Phase 2: Frontend Templates - Patient Events Timeline

## Overview

This phase creates the frontend templates and UI components for the timeline display, including summary cards, filtering interface, and pagination.

## Step 1: Create Main Timeline Template

### File: `apps/events/templates/events/patient_timeline.html`

**Action**: Create new template file

```html
{% extends "base_app.html" %}
{% load permission_tags %}
{% load static %}

{% block title %}Timeline - {{ patient.get_full_name }}{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'events/css/timeline.css' %}">
<style>
.timeline-card {
    border-left: 4px solid var(--bs-primary);
    transition: all 0.2s ease;
}
.timeline-card:hover {
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    transform: translateY(-1px);
}
.event-type-badge {
    font-size: 0.75rem;
    font-weight: 600;
}
.event-excerpt {
    color: #6c757d;
    font-size: 0.9rem;
    line-height: 1.4;
}
.filter-panel {
    background-color: #f8f9fa;
    border-radius: 8px;
    border: 1px solid #dee2e6;
}
.timeline-container {
    max-width: 800px;
}
.event-actions {
    opacity: 0;
    transition: opacity 0.2s ease;
}
.timeline-card:hover .event-actions {
    opacity: 1;
}
@media (max-width: 768px) {
    .event-actions {
        opacity: 1; /* Always show on mobile */
    }
}
</style>
{% endblock %}

{% block content %}
<div class="container-fluid">
    <!-- Header -->
    <div class="row mb-4">
        <div class="col">
            <div class="d-flex align-items-center justify-content-between">
                <div>
                    <h2 class="text-medical-primary mb-1">
                        <i class="bi bi-clock-history me-2"></i>
                        Timeline de Eventos
                    </h2>
                    <p class="text-muted mb-0">
                        <a href="{% url 'patients:patient_detail' patient.pk %}" class="text-decoration-none">
                            {{ patient.get_full_name }}
                        </a>
                        <span class="mx-2">•</span>
                        {% if filtered_count != total_events %}
                            {{ filtered_count }} de {{ total_events }} eventos
                        {% else %}
                            {{ total_events }} evento{{ total_events|pluralize }}
                        {% endif %}
                    </p>
                </div>
                <div>
                    <a href="{% url 'patients:patient_detail' patient.pk %}" class="btn btn-outline-medical-primary">
                        <i class="bi bi-arrow-left me-1"></i>
                        Voltar ao Paciente
                    </a>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <!-- Filters Panel -->
        <div class="col-lg-3 mb-4">
            <div class="filter-panel p-3">
                <h5 class="text-medical-primary mb-3">
                    <i class="bi bi-funnel me-2"></i>
                    Filtros
                </h5>
                
                <form method="get" id="timeline-filters">
                    <!-- Event Type Filter -->
                    <div class="mb-3">
                        <label class="form-label fw-semibold">Tipos de Evento</label>
                        {% for value, label in event_type_choices %}
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" 
                                       name="types" value="{{ value }}" id="type_{{ value }}"
                                       {% if value in current_filters.types %}checked{% endif %}>
                                <label class="form-check-label" for="type_{{ value }}">
                                    {{ label }}
                                </label>
                            </div>
                        {% endfor %}
                    </div>

                    <!-- Quick Date Filters -->
                    <div class="mb-3">
                        <label class="form-label fw-semibold">Período</label>
                        <div class="btn-group-vertical d-grid gap-1" role="group">
                            <input type="radio" class="btn-check" name="quick_date" value="" id="all_time"
                                   {% if not current_filters.quick_date %}checked{% endif %}>
                            <label class="btn btn-outline-secondary btn-sm" for="all_time">Todos</label>
                            
                            <input type="radio" class="btn-check" name="quick_date" value="24h" id="last_24h"
                                   {% if current_filters.quick_date == '24h' %}checked{% endif %}>
                            <label class="btn btn-outline-secondary btn-sm" for="last_24h">Últimas 24h</label>
                            
                            <input type="radio" class="btn-check" name="quick_date" value="7d" id="last_7d"
                                   {% if current_filters.quick_date == '7d' %}checked{% endif %}>
                            <label class="btn btn-outline-secondary btn-sm" for="last_7d">Últimos 7 dias</label>
                            
                            <input type="radio" class="btn-check" name="quick_date" value="30d" id="last_30d"
                                   {% if current_filters.quick_date == '30d' %}checked{% endif %}>
                            <label class="btn btn-outline-secondary btn-sm" for="last_30d">Últimos 30 dias</label>
                        </div>
                    </div>

                    <!-- Custom Date Range -->
                    <div class="mb-3">
                        <label class="form-label fw-semibold">Período Personalizado</label>
                        <div class="row g-2">
                            <div class="col-6">
                                <input type="date" class="form-control form-control-sm" 
                                       name="date_from" value="{{ current_filters.date_from }}"
                                       placeholder="De">
                            </div>
                            <div class="col-6">
                                <input type="date" class="form-control form-control-sm" 
                                       name="date_to" value="{{ current_filters.date_to }}"
                                       placeholder="Até">
                            </div>
                        </div>
                    </div>

                    <!-- Creator Filter -->
                    {% if available_creators %}
                    <div class="mb-3">
                        <label for="creator" class="form-label fw-semibold">Criado por</label>
                        <select name="creator" id="creator" class="form-select form-select-sm">
                            <option value="">Todos os profissionais</option>
                            {% for creator in available_creators %}
                                <option value="{{ creator.id }}" 
                                        {% if creator.id|stringformat:"s" == current_filters.creator %}selected{% endif %}>
                                    {{ creator.get_full_name }} ({{ creator.profession }})
                                </option>
                            {% endfor %}
                        </select>
                    </div>
                    {% endif %}

                    <!-- Filter Actions -->
                    <div class="d-grid gap-2">
                        <button type="submit" class="btn btn-medical-primary btn-sm">
                            <i class="bi bi-search me-1"></i>
                            Aplicar Filtros
                        </button>
                        <a href="{% url 'patients:patient_events_timeline' patient.pk %}" 
                           class="btn btn-outline-secondary btn-sm">
                            <i class="bi bi-arrow-counterclockwise me-1"></i>
                            Limpar Filtros
                        </a>
                    </div>
                </form>
            </div>
        </div>

        <!-- Timeline Content -->
        <div class="col-lg-9">
            <div class="timeline-container">
                {% if events_with_permissions %}
                    <!-- Events Timeline -->
                    <div class="timeline-events">
                        {% for event_data in events_with_permissions %}
                            {% with event=event_data.event %}
                            <div class="timeline-card card card-medical mb-3">
                                <div class="card-body">
                                    <!-- Event Header -->
                                    <div class="d-flex align-items-start justify-content-between mb-2">
                                        <div class="d-flex align-items-center">
                                            <span class="badge {{ event.get_event_type_badge_class }} event-type-badge me-2">
                                                <i class="{{ event.get_event_type_icon }} me-1"></i>
                                                {{ event.get_event_type_display }}
                                            </span>
                                            <small class="text-muted">
                                                <i class="bi bi-clock me-1"></i>
                                                {{ event.created_at|date:"d/m/Y H:i" }}
                                            </small>
                                        </div>
                                        
                                        <!-- Event Actions -->
                                        <div class="event-actions">
                                            <div class="btn-group btn-group-sm" role="group">
                                                <a href="{% url 'events:event_detail' event.pk %}" 
                                                   class="btn btn-outline-primary btn-sm" 
                                                   title="Visualizar">
                                                    <i class="bi bi-eye"></i>
                                                </a>
                                                {% if event_data.can_edit %}
                                                    <a href="{% url 'events:event_edit' event.pk %}" 
                                                       class="btn btn-outline-warning btn-sm"
                                                       title="Editar">
                                                        <i class="bi bi-pencil"></i>
                                                    </a>
                                                {% endif %}
                                                {% if event_data.can_delete %}
                                                    <button type="button" 
                                                            class="btn btn-outline-danger btn-sm"
                                                            title="Excluir"
                                                            data-bs-toggle="modal" 
                                                            data-bs-target="#deleteModal{{ event.pk }}">
                                                        <i class="bi bi-trash"></i>
                                                    </button>
                                                {% endif %}
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Event Content -->
                                    <div class="event-content">
                                        <div class="event-excerpt">
                                            {{ event_data.excerpt }}
                                        </div>
                                    </div>

                                    <!-- Event Metadata -->
                                    <div class="d-flex align-items-center justify-content-between mt-2 pt-2 border-top">
                                        <small class="text-muted">
                                            <i class="bi bi-person me-1"></i>
                                            {{ event.created_by.get_full_name }}
                                            {% if event.created_by.profession %}
                                                ({{ event.created_by.profession }})
                                            {% endif %}
                                        </small>
                                        {% if event.updated_at != event.created_at %}
                                            <small class="text-muted">
                                                <i class="bi bi-pencil-square me-1"></i>
                                                Editado em {{ event.updated_at|date:"d/m/Y H:i" }}
                                            </small>
                                        {% endif %}
                                    </div>
                                </div>
                            </div>

                            <!-- Delete Confirmation Modal -->
                            {% if event_data.can_delete %}
                                <div class="modal fade" id="deleteModal{{ event.pk }}" tabindex="-1">
                                    <div class="modal-dialog">
                                        <div class="modal-content">
                                            <div class="modal-header">
                                                <h5 class="modal-title">Confirmar Exclusão</h5>
                                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                            </div>
                                            <div class="modal-body">
                                                <p>Tem certeza que deseja excluir este evento?</p>
                                                <p><strong>{{ event.get_event_type_display }}</strong> - {{ event.created_at|date:"d/m/Y H:i" }}</p>
                                                <p class="text-muted small">Esta ação não pode ser desfeita.</p>
                                            </div>
                                            <div class="modal-footer">
                                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                                <form method="post" action="{% url 'events:event_delete' event.pk %}" class="d-inline">
                                                    {% csrf_token %}
                                                    <button type="submit" class="btn btn-danger">Excluir</button>
                                                </form>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            {% endif %}
                            {% endwith %}
                        {% endfor %}
                    </div>

                    <!-- Pagination -->
                    {% if is_paginated %}
                        <nav aria-label="Timeline pagination" class="mt-4">
                            <ul class="pagination justify-content-center">
                                {% if page_obj.has_previous %}
                                    <li class="page-item">
                                        <a class="page-link" href="?{% for key, value in request.GET.items %}{% if key != 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page=1">
                                            <i class="bi bi-chevron-double-left"></i>
                                        </a>
                                    </li>
                                    <li class="page-item">
                                        <a class="page-link" href="?{% for key, value in request.GET.items %}{% if key != 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page={{ page_obj.previous_page_number }}">
                                            <i class="bi bi-chevron-left"></i>
                                        </a>
                                    </li>
                                {% endif %}

                                {% for num in page_obj.paginator.page_range %}
                                    {% if page_obj.number == num %}
                                        <li class="page-item active">
                                            <span class="page-link">{{ num }}</span>
                                        </li>
                                    {% elif num > page_obj.number|add:'-3' and num < page_obj.number|add:'3' %}
                                        <li class="page-item">
                                            <a class="page-link" href="?{% for key, value in request.GET.items %}{% if key != 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page={{ num }}">{{ num }}</a>
                                        </li>
                                    {% endif %}
                                {% endfor %}

                                {% if page_obj.has_next %}
                                    <li class="page-item">
                                        <a class="page-link" href="?{% for key, value in request.GET.items %}{% if key != 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page={{ page_obj.next_page_number }}">
                                            <i class="bi bi-chevron-right"></i>
                                        </a>
                                    </li>
                                    <li class="page-item">
                                        <a class="page-link" href="?{% for key, value in request.GET.items %}{% if key != 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page={{ page_obj.paginator.num_pages }}">
                                            <i class="bi bi-chevron-double-right"></i>
                                        </a>
                                    </li>
                                {% endif %}
                            </ul>
                            
                            <!-- Pagination Info -->
                            <div class="text-center text-muted mt-2">
                                <small>
                                    Página {{ page_obj.number }} de {{ page_obj.paginator.num_pages }}
                                    ({{ page_obj.start_index }}-{{ page_obj.end_index }} de {{ page_obj.paginator.count }} eventos)
                                </small>
                            </div>
                        </nav>
                    {% endif %}

                {% else %}
                    <!-- Empty State -->
                    <div class="text-center py-5">
                        <div class="mb-4">
                            <i class="bi bi-clock-history text-muted" style="font-size: 4rem;"></i>
                        </div>
                        <h4 class="text-muted mb-3">Nenhum evento encontrado</h4>
                        {% if current_filters.types or current_filters.quick_date or current_filters.date_from or current_filters.date_to or current_filters.creator %}
                            <p class="text-muted mb-3">
                                Nenhum evento corresponde aos filtros selecionados.
                            </p>
                            <a href="{% url 'patients:patient_events_timeline' patient.pk %}" 
                               class="btn btn-outline-medical-primary">
                                <i class="bi bi-arrow-counterclockwise me-2"></i>
                                Limpar Filtros
                            </a>
                        {% else %}
                            <p class="text-muted mb-3">
                                Este paciente ainda não possui eventos registrados.
                            </p>
                            <a href="{% url 'events:event_create' %}?patient={{ patient.pk }}" 
                               class="btn btn-medical-primary">
                                <i class="bi bi-plus-circle me-2"></i>
                                Criar Primeiro Evento
                            </a>
                        {% endif %}
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Auto-submit filters on change
    const filterForm = document.getElementById('timeline-filters');
    const filterInputs = filterForm.querySelectorAll('input[type="checkbox"], input[type="radio"], select');
    
    filterInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Debounce for better UX
            setTimeout(() => {
                filterForm.submit();
            }, 100);
        });
    });
    
    // Date inputs submit on change (not immediate for better UX)
    const dateInputs = filterForm.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Clear quick date selection when custom dates are used
            const quickDateInputs = filterForm.querySelectorAll('input[name="quick_date"]');
            quickDateInputs.forEach(radio => {
                if (radio.value !== '') {
                    radio.checked = false;
                }
            });
        });
    });
    
    // Clear custom dates when quick date is selected
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
});
</script>
{% endblock %}
```

## Step 2: Create CSS Styles (Optional)

### File: `apps/events/static/events/css/timeline.css`

**Action**: Create dedicated CSS file (if you prefer external CSS over inline)

```css
/* Timeline Styles */
.timeline-card {
    border-left: 4px solid var(--bs-primary);
    transition: all 0.2s ease;
    position: relative;
}

.timeline-card:hover {
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    transform: translateY(-1px);
}

.timeline-card::before {
    content: '';
    position: absolute;
    left: -8px;
    top: 20px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background-color: var(--bs-primary);
    border: 3px solid white;
    box-shadow: 0 0 0 2px var(--bs-primary);
}

.event-type-badge {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.5px;
}

.event-excerpt {
    color: #6c757d;
    font-size: 0.9rem;
    line-height: 1.4;
    margin: 0.5rem 0;
}

.filter-panel {
    background-color: #f8f9fa;
    border-radius: 8px;
    border: 1px solid #dee2e6;
    position: sticky;
    top: 20px;
}

.timeline-container {
    max-width: 800px;
}

.event-actions {
    opacity: 0;
    transition: opacity 0.2s ease;
}

.timeline-card:hover .event-actions {
    opacity: 1;
}

/* Event type specific border colors */
.event-history_physical {
    border-left-color: var(--bs-primary);
}

.event-daily_notes {
    border-left-color: var(--bs-success);
}

.event-photos {
    border-left-color: var(--bs-info);
}

.event-exam_results {
    border-left-color: var(--bs-warning);
}

.event-procedures {
    border-left-color: var(--bs-danger);
}

/* Mobile optimizations */
@media (max-width: 768px) {
    .event-actions {
        opacity: 1; /* Always show on mobile */
    }
    
    .timeline-card::before {
        left: -6px;
        width: 8px;
        height: 8px;
    }
    
    .filter-panel {
        position: static;
        margin-bottom: 1rem;
    }
    
    .event-type-badge {
        font-size: 0.7rem;
    }
}

/* Print styles */
@media print {
    .filter-panel,
    .event-actions,
    .pagination {
        display: none !important;
    }
    
    .timeline-card {
        break-inside: avoid;
        margin-bottom: 1rem;
        box-shadow: none;
        border: 1px solid #ddd;
    }
}
```

## Step 3: Create Empty State Template (Alternative)

### File: `apps/events/templates/events/timeline_empty.html` (Optional)

**Action**: Create dedicated empty state template if you prefer modularity

```html
<div class="text-center py-5">
    <div class="mb-4">
        <i class="bi bi-clock-history text-muted" style="font-size: 4rem; opacity: 0.5;"></i>
    </div>
    <h4 class="text-muted mb-3">Nenhum evento encontrado</h4>
    
    {% if has_filters %}
        <p class="text-muted mb-3">
            Nenhum evento corresponde aos filtros selecionados.<br>
            Tente ajustar os critérios de busca ou remover alguns filtros.
        </p>
        <div class="d-grid gap-2 d-md-block">
            <a href="{% url 'patients:patient_events_timeline' patient.pk %}" 
               class="btn btn-outline-medical-primary">
                <i class="bi bi-arrow-counterclockwise me-2"></i>
                Limpar Todos os Filtros
            </a>
            <button type="button" class="btn btn-outline-secondary" 
                    onclick="window.history.back()">
                <i class="bi bi-arrow-left me-2"></i>
                Voltar
            </button>
        </div>
    {% else %}
        <p class="text-muted mb-3">
            Este paciente ainda não possui eventos médicos registrados.<br>
            Comece criando o primeiro evento para acompanhar o histórico do paciente.
        </p>
        <div class="d-grid gap-2 d-md-block">
            <a href="{% url 'events:event_create' %}?patient={{ patient.pk }}" 
               class="btn btn-medical-primary">
                <i class="bi bi-plus-circle me-2"></i>
                Criar Primeiro Evento
            </a>
            <a href="{% url 'dailynotes:create' %}?patient={{ patient.pk }}" 
               class="btn btn-outline-medical-success">
                <i class="bi bi-journal-text me-2"></i>
                Nova Evolução
            </a>
        </div>
    {% endif %}
</div>
```

## Step 4: Update Directory Structure

**Action**: Ensure the templates directory exists:

```bash
mkdir -p apps/events/templates/events
mkdir -p apps/events/static/events/css
mkdir -p apps/events/static/events/js
```

## Step 5: Create Mobile-Optimized Card Component

### File: `apps/events/templates/events/components/timeline_card.html`

**Action**: Create reusable card component (optional for modularity)

```html
{% load permission_tags %}

<div class="timeline-card card card-medical mb-3 event-{{ event.event_type }}">
    <div class="card-body">
        <!-- Mobile-first Event Header -->
        <div class="d-flex flex-column flex-sm-row align-items-start justify-content-between mb-2">
            <div class="d-flex align-items-center mb-2 mb-sm-0">
                <span class="badge {{ event.get_event_type_badge_class }} event-type-badge me-2">
                    <i class="{{ event.get_event_type_icon }} me-1"></i>
                    <span class="d-none d-sm-inline">{{ event.get_event_type_display }}</span>
                    <span class="d-sm-none">{{ event.get_event_type_display|truncatechars:10 }}</span>
                </span>
                <small class="text-muted">
                    <i class="bi bi-clock me-1"></i>
                    <span class="d-none d-sm-inline">{{ event.created_at|date:"d/m/Y H:i" }}</span>
                    <span class="d-sm-none">{{ event.created_at|date:"d/m H:i" }}</span>
                </small>
            </div>
            
            <!-- Event Actions -->
            <div class="event-actions align-self-end align-self-sm-start">
                <div class="btn-group btn-group-sm" role="group">
                    <a href="{% url 'events:event_detail' event.pk %}" 
                       class="btn btn-outline-primary btn-sm" 
                       title="Visualizar">
                        <i class="bi bi-eye"></i>
                        <span class="d-none d-lg-inline ms-1">Ver</span>
                    </a>
                    {% if can_edit %}
                        <a href="{% url 'events:event_edit' event.pk %}" 
                           class="btn btn-outline-warning btn-sm"
                           title="Editar">
                            <i class="bi bi-pencil"></i>
                            <span class="d-none d-lg-inline ms-1">Editar</span>
                        </a>
                    {% endif %}
                    {% if can_delete %}
                        <button type="button" 
                                class="btn btn-outline-danger btn-sm"
                                title="Excluir"
                                data-bs-toggle="modal" 
                                data-bs-target="#deleteModal{{ event.pk }}">
                            <i class="bi bi-trash"></i>
                        </button>
                    {% endif %}
                </div>
            </div>
        </div>

        <!-- Event Content -->
        <div class="event-content">
            <div class="event-excerpt">
                {{ excerpt }}
            </div>
        </div>

        <!-- Event Metadata -->
        <div class="d-flex flex-column flex-sm-row align-items-start align-items-sm-center justify-content-between mt-2 pt-2 border-top">
            <small class="text-muted">
                <i class="bi bi-person me-1"></i>
                {{ event.created_by.get_full_name }}
                {% if event.created_by.profession %}
                    <span class="d-none d-md-inline">({{ event.created_by.profession }})</span>
                {% endif %}
            </small>
            {% if event.updated_at != event.created_at %}
                <small class="text-muted mt-1 mt-sm-0">
                    <i class="bi bi-pencil-square me-1"></i>
                    <span class="d-none d-sm-inline">Editado em {{ event.updated_at|date:"d/m/Y H:i" }}</span>
                    <span class="d-sm-none">Editado {{ event.updated_at|date:"d/m H:i" }}</span>
                </small>
            {% endif %}
        </div>
    </div>
</div>
```

## Testing Steps

1. **Template rendering**: Ensure template loads without errors
2. **Responsive design**: Test on mobile, tablet, and desktop
3. **Filter functionality**: Test all filter combinations
4. **Pagination**: Test navigation between pages
5. **Permission display**: Verify action buttons show based on permissions
6. **Empty states**: Test with no events and with filtered results
7. **Accessibility**: Test keyboard navigation and screen reader compatibility

## Expected Results

After completing Phase 2:

- Fully functional timeline template with summary cards
- Responsive design that works on all devices
- Interactive filtering interface
- Pagination with preserved filter parameters
- Empty state handling
- Permission-aware action buttons
- Medical-themed styling consistent with the app

## Next Phase

Phase 3 will focus on integration with the patient detail page and UX enhancements like modal views and improved interactions.
