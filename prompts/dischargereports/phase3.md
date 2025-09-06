# Phase 3 Prompt: Event System Integration

Integrate discharge reports with the patient timeline and event system.

CONTEXT:

- Phase 2 completed: DischargeReport CRUD interface works
- Project has existing Event system with patient timeline
- Event cards located in apps/events/templates/events/partials/
- Timeline has filtering system for different event types
- DischargeReport extends Event with event_type = DISCHARGE_REPORT_EVENT (6)

GOAL: Integrate discharge reports into patient timeline with custom event card and filtering.

TASKS:

1. CREATE EVENT CARD TEMPLATE:
   apps/events/templates/events/partials/event_card_dischargereport.html:

```html
{% extends "events/partials/event_card_base.html" %} {% load permission_tags %}
{% comment %} DischargeReport-specific event card template Extends the base
event card for discharge report events {% endcomment %} {% block event_actions
%}
<div class="btn-group btn-group-sm">
  <!-- View Button -->
  <a
    href="{{ event.get_absolute_url }}"
    class="btn btn-outline-primary btn-sm"
    aria-label="Visualizar relatório de alta"
    data-bs-toggle="tooltip"
    data-bs-placement="top"
    title="Ver relatório completo"
  >
    <i class="bi bi-eye" aria-hidden="true"></i>
    <span class="visually-hidden">Visualizar</span>
  </a>

  <!-- Print Button -->
  <a
    href="{% url 'apps.dischargereports:dischargereport_print' pk=event.pk %}"
    class="btn btn-outline-secondary btn-sm"
    target="_blank"
    aria-label="Imprimir relatório"
    data-bs-toggle="tooltip"
    data-bs-placement="top"
    title="Imprimir relatório"
  >
    <i class="bi bi-printer" aria-hidden="true"></i>
    <span class="visually-hidden">Imprimir</span>
  </a>

  <!-- Edit Button - Show if draft or within 24h window -->
  {% if event.is_draft or event_data.can_edit %}
  <a
    href="{{ event.get_edit_url }}"
    class="btn btn-outline-warning btn-sm"
    aria-label="Editar relatório"
    data-bs-toggle="tooltip"
    data-bs-placement="top"
    title="Editar relatório"
  >
    <i class="bi bi-pencil" aria-hidden="true"></i>
    <span class="visually-hidden">Editar</span>
  </a>
  {% endif %}

  <!-- Delete Button - Only for drafts -->
  {% if event.is_draft and perms.events.delete_event %}
  <a
    href="{% url 'apps.dischargereports:dischargereport_delete' pk=event.pk %}"
    class="btn btn-outline-danger btn-sm"
    aria-label="Excluir rascunho"
    data-bs-toggle="tooltip"
    data-bs-placement="top"
    title="Excluir rascunho"
  >
    <i class="bi bi-trash" aria-hidden="true"></i>
    <span class="visually-hidden">Excluir</span>
  </a>
  {% endif %}
</div>
{% endblock event_actions %} {% block event_content %}
<div class="discharge-report-summary">
  <div class="mb-2 d-flex justify-content-between align-items-start">
    <div>
      <strong class="text-primary">{{ event.medical_specialty }}</strong>
      {% if event.is_draft %}
      <span class="badge bg-warning text-dark ms-2">
        <i class="bi bi-pencil-square"></i> Rascunho
      </span>
      {% endif %}
    </div>
    <small class="text-muted">
      {{ event.event_datetime|date:"d/m/Y H:i" }}
    </small>
  </div>

  <div class="text-muted small mb-2">
    <div class="d-flex align-items-center">
      <i class="bi bi-calendar-plus me-1"></i>
      <span>{{ event.admission_date|date:"d/m/Y" }}</span>
      <i class="bi bi-arrow-right mx-2"></i>
      <i class="bi bi-door-open me-1"></i>
      <span>{{ event.discharge_date|date:"d/m/Y" }}</span>
      <span class="ms-2 text-secondary">
        ({{ event.discharge_date|timeuntil:event.admission_date }})
      </span>
    </div>
  </div>

  {% if event.problems_and_diagnosis %}
  <div class="mt-2">
    <small class="text-secondary">
      <strong>Problemas:</strong>
      {{ event.problems_and_diagnosis|truncatewords:15|striptags }}
    </small>
  </div>
  {% endif %} {% if event.discharge_recommendations %}
  <div class="mt-1">
    <small class="text-secondary">
      <strong>Recomendações:</strong>
      {{ event.discharge_recommendations|truncatewords:10|striptags }}
    </small>
  </div>
  {% endif %}
</div>
{% endblock event_content %}
```

2. ADD PRINT VIEW TO VIEWS.PY:

```python
# Add this to views.py
from django.http import HttpResponse
from django.template.loader import render_to_string

class DischargeReportPrintView(LoginRequiredMixin, DetailView):
    """Print-friendly view for discharge reports"""
    model = DischargeReport
    template_name = 'dischargereports/dischargereport_print.html'
    context_object_name = 'report'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context
```

3. ADD PRINT URL TO URLS.PY:

```python
# Add this to urlpatterns in urls.py
path('<uuid:pk>/print/', views.DischargeReportPrintView.as_view(), name='dischargereport_print'),
```

4. CREATE BASIC PRINT TEMPLATE:
   apps/dischargereports/templates/dischargereports/dischargereport_print.html:

```html
{% load static %} {% load hospital_tags %}
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Relatório de Alta - {{ report.patient.name }}</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        margin: 20px;
      }
      .header {
        text-align: center;
        margin-bottom: 30px;
      }
      .patient-info {
        margin-bottom: 20px;
      }
      .content-section {
        margin-bottom: 20px;
      }
      .content-section h3 {
        border-bottom: 1px solid #ccc;
      }
      @media print {
        .no-print {
          display: none;
        }
        body {
          margin: 0;
        }
      }
    </style>
  </head>
  <body>
    <button class="no-print" onclick="window.print()">🖨️ Imprimir</button>

    <div class="header">
      <h1>{% hospital_name %}</h1>
      <h2>Relatório de Alta - {{ report.medical_specialty }}</h2>
    </div>

    <div class="patient-info">
      <p><strong>Paciente:</strong> {{ report.patient.name }}</p>
      <p>
        <strong>Data de Admissão:</strong> {{ report.admission_date|date:"d/m/Y"
        }}
      </p>
      <p>
        <strong>Data de Alta:</strong> {{ report.discharge_date|date:"d/m/Y" }}
      </p>
    </div>

    <div class="content-section">
      <h3>Problemas e Diagnósticos</h3>
      <p>{{ report.problems_and_diagnosis|linebreaks }}</p>
    </div>

    <!-- Add other sections similarly -->
  </body>
</html>
```

5. UPDATE TIMELINE FILTERING:
   Find the timeline template (likely in apps/patients or apps/events) and add discharge reports to the filter options.

Look for JavaScript filter code and add:

```javascript
// Add to timeline filtering
case 'discharge_reports':
    return event.event_type === 6; // DISCHARGE_REPORT_EVENT
```

And add HTML filter option:

```html
<input
  type="checkbox"
  id="filter-discharge-reports"
  class="filter-checkbox"
  data-filter="discharge_reports"
  checked
/>
<label for="filter-discharge-reports">Relatórios de Alta</label>
```

6. VERIFY EVENT TYPE REGISTRATION:
   Confirm that apps/events/models.py has:

- DISCHARGE_REPORT_EVENT = 6 in constants
- "Relatório de Alta" in EVENT_TYPE_CHOICES
- Proper badge class and icon mappings

VERIFICATION:

- Discharge reports appear in patient timeline
- Event card displays correctly with proper buttons
- Print functionality works
- Timeline filtering includes discharge reports
- Draft status shows properly in event card

DELIVERABLES:

- Custom event card template
- Timeline integration
- Print view and template
- Updated timeline filtering
