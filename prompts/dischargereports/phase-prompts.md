# Discharge Reports - Phase Implementation Prompts

## How to Use These Prompts

Each prompt below is **completely self-contained** and can be used with a coding assistant that has no prior context about this project. Simply copy the entire prompt for the phase you want to implement.

---

## Phase 1 Prompt: Foundation (Core Model)

```
Create a Django discharge reports app for a medical platform.

CONTEXT:
- Django 5 project with existing Event model in apps/events/models.py
- Event model uses inheritance with event_type constants
- DISCHARGE_REPORT_EVENT = 6 already exists in Event.EVENT_TYPE_CHOICES
- Project uses UUID primary keys, soft delete, and history tracking
- Bootstrap 5.3 for styling, Portuguese localization

GOAL: Create apps/dischargereports Django app with DischargeReport model extending Event.

TASKS:

1. CREATE APP STRUCTURE:
```bash
mkdir -p apps/dischargereports/{templates/dischargereports,templatetags,migrations,tests}
```

Create these files:
- apps/dischargereports/__init__.py (empty)
- apps/dischargereports/apps.py
- apps/dischargereports/models.py  
- apps/dischargereports/admin.py
- apps/dischargereports/urls.py
- apps/dischargereports/views.py
- apps/dischargereports/forms.py

2. IMPLEMENT MODELS.PY:
```python
from django.db import models
from apps.events.models import Event


class DischargeReport(Event):
    """Discharge report extending the base Event model"""
    
    # Date fields
    admission_date = models.DateField(
        verbose_name="Data de Admissão",
        help_text="Data da admissão hospitalar"
    )
    discharge_date = models.DateField(
        verbose_name="Data de Alta", 
        help_text="Data da alta hospitalar"
    )
    
    # Text content fields
    admission_history = models.TextField(
        verbose_name="História da Admissão",
        help_text="História clínica da admissão"
    )
    problems_and_diagnosis = models.TextField(
        verbose_name="Problemas e Diagnósticos",
        help_text="Problemas principais e diagnósticos"
    )
    exams_list = models.TextField(
        verbose_name="Lista de Exames", 
        help_text="Exames realizados durante a internação"
    )
    procedures_list = models.TextField(
        verbose_name="Lista de Procedimentos",
        help_text="Procedimentos realizados"
    )
    inpatient_medical_history = models.TextField(
        verbose_name="História Médica da Internação",
        help_text="Evolução médica durante a internação"
    )
    discharge_status = models.TextField(
        verbose_name="Status da Alta",
        help_text="Condições do paciente na alta"
    )
    discharge_recommendations = models.TextField(
        verbose_name="Recomendações de Alta",
        help_text="Orientações e recomendações para pós-alta"
    )
    
    # Classification field
    medical_specialty = models.CharField(
        max_length=100,
        verbose_name="Especialidade Médica",
        help_text="Especialidade responsável pela alta"
    )
    
    # Draft system
    is_draft = models.BooleanField(
        default=True,
        verbose_name="É Rascunho", 
        help_text="Indica se o relatório ainda é um rascunho editável"
    )
    
    class Meta:
        verbose_name = "Relatório de Alta"
        verbose_name_plural = "Relatórios de Alta"
        ordering = ["-event_datetime"]
        indexes = [
            models.Index(fields=['admission_date']),
            models.Index(fields=['discharge_date']),
            models.Index(fields=['is_draft', 'patient']),
            models.Index(fields=['medical_specialty']),
        ]
    
    def save(self, *args, **kwargs):
        """Override save to set the correct event type."""
        self.event_type = Event.DISCHARGE_REPORT_EVENT
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return the absolute URL for this discharge report."""
        from django.urls import reverse
        return reverse('apps.dischargereports:dischargereport_detail', kwargs={'pk': self.pk})

    def get_edit_url(self):
        """Return the edit URL for this discharge report.""" 
        from django.urls import reverse
        return reverse('apps.dischargereports:dischargereport_update', kwargs={'pk': self.pk})

    def __str__(self):
        """String representation of the discharge report."""
        draft_text = " (Rascunho)" if self.is_draft else ""
        return f"Relatório de Alta - {self.patient.name} - {self.discharge_date.strftime('%d/%m/%Y')}{draft_text}"
```

3. IMPLEMENT APPS.PY:
```python
from django.apps import AppConfig


class DischargereportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dischargereports'
    verbose_name = 'Relatórios de Alta'
```

4. IMPLEMENT ADMIN.PY:
```python
from django.contrib import admin
from .models import DischargeReport


@admin.register(DischargeReport)
class DischargeReportAdmin(admin.ModelAdmin):
    list_display = ['patient', 'medical_specialty', 'admission_date', 'discharge_date', 'is_draft', 'created_at']
    list_filter = ['is_draft', 'medical_specialty', 'admission_date', 'discharge_date']
    search_fields = ['patient__name', 'medical_specialty', 'problems_and_diagnosis']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('patient', 'event_datetime', 'description', 'is_draft')
        }),
        ('Datas', {
            'fields': ('admission_date', 'discharge_date')
        }),
        ('Especialidade', {
            'fields': ('medical_specialty',)
        }),
        ('Conteúdo Médico', {
            'fields': ('problems_and_diagnosis', 'admission_history', 'exams_list', 
                      'procedures_list', 'inpatient_medical_history', 'discharge_status', 
                      'discharge_recommendations'),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
```

5. CREATE EMPTY FILES:
```python
# apps/dischargereports/urls.py
from django.urls import path
from . import views

app_name = 'apps.dischargereports'
urlpatterns = []

# apps/dischargereports/views.py  
from django.shortcuts import render

# apps/dischargereports/forms.py
from django import forms
```

6. ADD TO INSTALLED_APPS in settings/base.py:
Add 'apps.dischargereports' to INSTALLED_APPS list.

7. GENERATE AND RUN MIGRATION:
```bash
uv run python manage.py makemigrations dischargereports
uv run python manage.py migrate
```

VERIFICATION:
- Django admin shows "Relatórios de Alta" section
- Can create discharge report in admin
- Model saves with correct event_type = 6
- All fields display properly in admin

DELIVERABLES:
- Working DischargeReport model
- Admin interface 
- Database migration applied
- App registered in settings
```

---

## Phase 2 Prompt: Basic CRUD Operations

```
Implement CRUD views and templates for Django discharge reports app.

CONTEXT:
- Phase 1 completed: DischargeReport model exists extending Event
- Model has fields: admission_date, discharge_date, medical_specialty, admission_history, problems_and_diagnosis, exams_list, procedures_list, inpatient_medical_history, discharge_status, discharge_recommendations, is_draft
- Bootstrap 5.3 styling, Portuguese localization
- Project uses LoginRequiredMixin, UUID primary keys
- Separate create/update templates required (don't reuse create for edit)

GOAL: Create complete CRUD interface with forms, views, and templates.

TASKS:

1. UPDATE FORMS.PY:
```python
from django import forms
from .models import DischargeReport


class DischargeReportForm(forms.ModelForm):
    """Form for discharge report create/update"""
    
    class Meta:
        model = DischargeReport
        fields = [
            'patient', 'event_datetime', 'description',
            'admission_date', 'discharge_date', 'medical_specialty',
            'admission_history', 'problems_and_diagnosis', 'exams_list',
            'procedures_list', 'inpatient_medical_history', 
            'discharge_status', 'discharge_recommendations'
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'event_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'description': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Descrição do relatório'}
            ),
            'admission_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'discharge_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'medical_specialty': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Ex: Cardiologia'}
            ),
            'admission_history': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'problems_and_diagnosis': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'exams_list': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'procedures_list': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
            'inpatient_medical_history': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 6}
            ),
            'discharge_status': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'discharge_recommendations': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4}
            ),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        admission_date = cleaned_data.get('admission_date')
        discharge_date = cleaned_data.get('discharge_date')
        
        if admission_date and discharge_date:
            if admission_date > discharge_date:
                raise forms.ValidationError(
                    "A data de admissão deve ser anterior à data de alta."
                )
        
        return cleaned_data
```

2. UPDATE VIEWS.PY:
```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, UpdateView, DetailView, ListView, DeleteView
from .models import DischargeReport
from .forms import DischargeReportForm


class DischargeReportListView(LoginRequiredMixin, ListView):
    """List all discharge reports"""
    model = DischargeReport
    template_name = 'dischargereports/dischargereport_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        return DischargeReport.objects.select_related('patient').order_by('-created_at')


class DischargeReportDetailView(LoginRequiredMixin, DetailView):
    """View discharge report details"""
    model = DischargeReport
    template_name = 'dischargereports/dischargereport_detail.html'
    context_object_name = 'report'


class DischargeReportCreateView(LoginRequiredMixin, CreateView):
    """Create new discharge report"""
    model = DischargeReport
    form_class = DischargeReportForm
    template_name = 'dischargereports/dischargereport_create.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        form.instance.event_datetime = form.instance.event_datetime or timezone.now()
        
        # Handle draft vs final save
        if 'save_final' in self.request.POST:
            form.instance.is_draft = False
            messages.success(self.request, 'Relatório de alta salvo definitivamente.')
        else:
            form.instance.is_draft = True
            messages.success(self.request, 'Relatório de alta salvo como rascunho.')
        
        return super().form_valid(form)


class DischargeReportUpdateView(LoginRequiredMixin, UpdateView):
    """Update discharge report - separate template"""
    model = DischargeReport
    form_class = DischargeReportForm
    template_name = 'dischargereports/dischargereport_update.html'
    
    def get_object(self):
        obj = super().get_object()
        # Check if editable (draft or within 24h window)
        if not obj.is_draft and not obj.can_be_edited:
            raise PermissionDenied("Relatório não pode mais ser editado.")
        return obj
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        
        # Handle draft vs final save
        if 'save_final' in self.request.POST:
            form.instance.is_draft = False
            messages.success(self.request, 'Relatório de alta finalizado.')
        else:
            messages.success(self.request, 'Relatório de alta atualizado.')
        
        return super().form_valid(form)


class DischargeReportDeleteView(LoginRequiredMixin, DeleteView):
    """Delete discharge report (drafts only)"""
    model = DischargeReport
    template_name = 'dischargereports/dischargereport_confirm_delete.html'
    success_url = reverse_lazy('apps.dischargereports:dischargereport_list')
    
    def get_object(self):
        obj = super().get_object()
        if not obj.is_draft:
            raise PermissionDenied("Apenas rascunhos podem ser excluídos.")
        return obj
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Rascunho do relatório de alta excluído.')
        return super().delete(request, *args, **kwargs)
```

3. UPDATE URLS.PY:
```python
from django.urls import path
from . import views

app_name = 'apps.dischargereports'

urlpatterns = [
    path('', views.DischargeReportListView.as_view(), name='dischargereport_list'),
    path('create/', views.DischargeReportCreateView.as_view(), name='dischargereport_create'),
    path('<uuid:pk>/', views.DischargeReportDetailView.as_view(), name='dischargereport_detail'),
    path('<uuid:pk>/update/', views.DischargeReportUpdateView.as_view(), name='dischargereport_update'),
    path('<uuid:pk>/delete/', views.DischargeReportDeleteView.as_view(), name='dischargereport_delete'),
]
```

4. CREATE TEMPLATES:

Create base directory structure:
```bash
mkdir -p apps/dischargereports/templates/dischargereports
```

apps/dischargereports/templates/dischargereports/dischargereport_create.html:
```html
{% extends 'base.html' %}
{% load static %}
{% load bootstrap5 %}

{% block title %}Novo Relatório de Alta{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h3>Novo Relatório de Alta</h3>
                    <a href="{% url 'apps.dischargereports:dischargereport_list' %}" class="btn btn-outline-secondary">
                        <i class="bi bi-arrow-left"></i> Voltar
                    </a>
                </div>
                <div class="card-body">
                    <form method="post">
                        {% csrf_token %}
                        
                        <!-- Basic Info -->
                        <div class="row mb-3">
                            <div class="col-md-6">
                                {% bootstrap_field form.patient %}
                            </div>
                            <div class="col-md-6">
                                {% bootstrap_field form.event_datetime %}
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            {% bootstrap_field form.description %}
                        </div>
                        
                        <!-- Date Fields -->
                        <div class="row mb-3">
                            <div class="col-md-6">
                                {% bootstrap_field form.admission_date %}
                            </div>
                            <div class="col-md-6">
                                {% bootstrap_field form.discharge_date %}
                            </div>
                        </div>
                        
                        <!-- Specialty -->
                        <div class="mb-3">
                            {% bootstrap_field form.medical_specialty %}
                        </div>
                        
                        <!-- Content Sections -->
                        <div class="mb-3">
                            {% bootstrap_field form.problems_and_diagnosis %}
                        </div>
                        
                        <div class="mb-3">
                            {% bootstrap_field form.admission_history %}
                        </div>
                        
                        <div class="mb-3">
                            {% bootstrap_field form.exams_list %}
                        </div>
                        
                        <div class="mb-3">
                            {% bootstrap_field form.procedures_list %}
                        </div>
                        
                        <div class="mb-3">
                            {% bootstrap_field form.inpatient_medical_history %}
                        </div>
                        
                        <div class="mb-3">
                            {% bootstrap_field form.discharge_status %}
                        </div>
                        
                        <div class="mb-3">
                            {% bootstrap_field form.discharge_recommendations %}
                        </div>
                        
                        <!-- Action Buttons -->
                        <div class="d-flex gap-2">
                            <button type="submit" name="save_draft" class="btn btn-warning">
                                <i class="bi bi-floppy"></i> Salvar Rascunho
                            </button>
                            <button type="submit" name="save_final" class="btn btn-success">
                                <i class="bi bi-check-circle"></i> Salvar Definitivo
                            </button>
                            <a href="{% url 'apps.dischargereports:dischargereport_list' %}" class="btn btn-secondary">
                                <i class="bi bi-x-circle"></i> Cancelar
                            </a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

Create similar templates for:
- dischargereport_update.html (same as create but with "Editar" title)
- dischargereport_detail.html (read-only view)
- dischargereport_list.html (table of reports)
- dischargereport_confirm_delete.html (deletion confirmation)

5. REGISTER URLS IN MAIN PROJECT:
Add to main urls.py:
```python
path('dischargereports/', include('apps.dischargereports.urls')),
```

VERIFICATION:
- All CRUD operations work
- Draft/final save buttons function
- Form validation works
- Templates display correctly
- Draft-only deletion enforced

DELIVERABLES:
- Complete CRUD interface
- Working forms with validation
- Bootstrap 5.3 templates
- Draft/final save logic
```

---

## Phase 3 Prompt: Event System Integration

```
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
{% extends "events/partials/event_card_base.html" %}
{% load permission_tags %}

{% comment %}
DischargeReport-specific event card template
Extends the base event card for discharge report events
{% endcomment %}

{% block event_actions %}
<div class="btn-group btn-group-sm">
    <!-- View Button -->
    <a href="{{ event.get_absolute_url }}" 
       class="btn btn-outline-primary btn-sm"
       aria-label="Visualizar relatório de alta"
       data-bs-toggle="tooltip" 
       data-bs-placement="top" 
       title="Ver relatório completo">
        <i class="bi bi-eye" aria-hidden="true"></i>
        <span class="visually-hidden">Visualizar</span>
    </a>
    
    <!-- Print Button -->
    <a href="{% url 'apps.dischargereports:dischargereport_print' pk=event.pk %}" 
       class="btn btn-outline-secondary btn-sm" 
       target="_blank"
       aria-label="Imprimir relatório"
       data-bs-toggle="tooltip" 
       data-bs-placement="top" 
       title="Imprimir relatório">
        <i class="bi bi-printer" aria-hidden="true"></i>
        <span class="visually-hidden">Imprimir</span>
    </a>
    
    <!-- Edit Button - Show if draft or within 24h window -->
    {% if event.is_draft or event_data.can_edit %}
        <a href="{{ event.get_edit_url }}" 
           class="btn btn-outline-warning btn-sm"
           aria-label="Editar relatório"
           data-bs-toggle="tooltip" 
           data-bs-placement="top" 
           title="Editar relatório">
            <i class="bi bi-pencil" aria-hidden="true"></i>
            <span class="visually-hidden">Editar</span>
        </a>
    {% endif %}
    
    <!-- Delete Button - Only for drafts -->
    {% if event.is_draft and perms.events.delete_event %}
        <a href="{% url 'apps.dischargereports:dischargereport_delete' pk=event.pk %}" 
           class="btn btn-outline-danger btn-sm"
           aria-label="Excluir rascunho"
           data-bs-toggle="tooltip" 
           data-bs-placement="top" 
           title="Excluir rascunho">
            <i class="bi bi-trash" aria-hidden="true"></i>
            <span class="visually-hidden">Excluir</span>
        </a>
    {% endif %}
</div>
{% endblock event_actions %}

{% block event_content %}
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
    {% endif %}
    
    {% if event.discharge_recommendations %}
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
{% load static %}
{% load hospital_tags %}
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Alta - {{ report.patient.name }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .patient-info { margin-bottom: 20px; }
        .content-section { margin-bottom: 20px; }
        .content-section h3 { border-bottom: 1px solid #ccc; }
        @media print { 
            .no-print { display: none; }
            body { margin: 0; }
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
        <p><strong>Data de Admissão:</strong> {{ report.admission_date|date:"d/m/Y" }}</p>
        <p><strong>Data de Alta:</strong> {{ report.discharge_date|date:"d/m/Y" }}</p>
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
<input type="checkbox" id="filter-discharge-reports" class="filter-checkbox" data-filter="discharge_reports" checked>
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
```

---

## Phase 4 Prompt: Print/PDF Generation

```
Create professional Portuguese PDF reports for discharge reports with hospital branding.

CONTEXT:
- Phase 3 completed: Basic print template exists
- Project uses hospital template tags for branding
- Need professional Portuguese layout with pagination
- Similar to outpatient prescriptions print system
- Bootstrap 5.3 available, but print uses custom CSS

GOAL: Create professional print/PDF discharge reports in Portuguese.

TASKS:

1. CREATE COMPREHENSIVE PRINT TEMPLATE:
apps/dischargereports/templates/dischargereports/dischargereport_print.html:
```html
{% load static %}
{% load hospital_tags %}
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Alta - {{ report.patient.name }} - {{ report.discharge_date|date:"d/m/Y" }}</title>
    <link rel="stylesheet" href="{% static 'dischargereports/css/print.css' %}">
</head>
<body>
    <button class="print-button no-print" onclick="window.print()">
        🖨️ Imprimir
    </button>
    
    <!-- Header (appears on every page) -->
    <div class="header">
        <div class="hospital-branding">
            {% hospital_logo as logo_url %}
            {% if logo_url %}
                <img src="{{ logo_url }}" alt="Logo do Hospital" class="hospital-logo">
            {% endif %}
            <div class="hospital-info">
                <div class="hospital-name">{% hospital_name %}</div>
                <div class="hospital-details">
                    {% hospital_address %} | {% hospital_phone %} | {% hospital_email %}
                </div>
            </div>
        </div>
        <div class="document-title">
            <h1>Relatório de Alta</h1>
            <h2>{{ report.medical_specialty }}</h2>
        </div>
    </div>
    
    <!-- Patient Information -->
    <div class="patient-info-section">
        <h3>Identificação do Paciente</h3>
        <div class="patient-info-grid">
            <div class="info-row">
                <div class="info-cell">
                    <span class="info-label">Nome:</span>
                    <span class="info-value">{{ report.patient.name }}</span>
                </div>
                <div class="info-cell">
                    <span class="info-label">Prontuário:</span>
                    <span class="info-value">{{ report.patient.current_record_number|default:"—" }}</span>
                </div>
            </div>
            <div class="info-row">
                <div class="info-cell">
                    <span class="info-label">Data de Nascimento:</span>
                    <span class="info-value">{{ report.patient.birthday|date:"d/m/Y"|default:"—" }}</span>
                </div>
                <div class="info-cell">
                    <span class="info-label">Gênero:</span>
                    <span class="info-value">{{ report.patient.get_gender_display|default:"—" }}</span>
                </div>
                <div class="info-cell">
                    <span class="info-label">Idade:</span>
                    <span class="info-value">{{ report.patient.age }} anos</span>
                </div>
            </div>
            <div class="info-row">
                <div class="info-cell">
                    <span class="info-label">Data de Admissão:</span>
                    <span class="info-value">{{ report.admission_date|date:"d/m/Y" }}</span>
                </div>
                <div class="info-cell">
                    <span class="info-label">Data de Alta:</span>
                    <span class="info-value">{{ report.discharge_date|date:"d/m/Y" }}</span>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Medical Content Sections -->
    <div class="content-section">
        <h3>Problemas e Diagnósticos</h3>
        <div class="content-text">{{ report.problems_and_diagnosis|linebreaks }}</div>
    </div>
    
    <div class="content-section">
        <h3>História da Admissão</h3>
        <div class="content-text">{{ report.admission_history|linebreaks }}</div>
    </div>
    
    <div class="content-section">
        <h3>Lista de Exames</h3>
        <div class="content-text">{{ report.exams_list|linebreaks }}</div>
    </div>
    
    <div class="content-section">
        <h3>Lista de Procedimentos</h3>
        <div class="content-text">{{ report.procedures_list|linebreaks }}</div>
    </div>
    
    <div class="content-section">
        <h3>História Médica da Internação</h3>
        <div class="content-text">{{ report.inpatient_medical_history|linebreaks }}</div>
    </div>
    
    <div class="content-section">
        <h3>Status da Alta</h3>
        <div class="content-text">{{ report.discharge_status|linebreaks }}</div>
    </div>
    
    <div class="content-section">
        <h3>Recomendações de Alta</h3>
        <div class="content-text">{{ report.discharge_recommendations|linebreaks }}</div>
    </div>
    
    <!-- Footer (appears on every page) -->
    <div class="page-footer">
        <div class="generation-info">
            <p><strong>Relatório gerado em:</strong> {{ now|date:"d/m/Y às H:i" }}</p>
            <p><strong>Gerado por:</strong> {{ user.get_full_name|default:user.username }}</p>
        </div>
        
        <div class="hospital-footer">
            <div class="hospital-footer-info">
                {% hospital_name %} - {% hospital_address %}<br>
                Tel: {% hospital_phone %} | Email: {% hospital_email %}
            </div>
            <div class="sistema-credit">
                criado por EquipeMed
            </div>
        </div>
    </div>
    
    <script>
        // Auto-print functionality
        document.addEventListener('DOMContentLoaded', function() {
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.get('print') === 'true') {
                window.print();
            }
        });
    </script>
</body>
</html>
```

2. CREATE PRINT CSS FILE:
Create directory and file:
```bash
mkdir -p apps/dischargereports/static/dischargereports/css
```

apps/dischargereports/static/dischargereports/css/print.css:
```css
/* Print Styles for Discharge Reports */

/* General Styles */
* {
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 12pt;
    line-height: 1.4;
    color: #333;
    margin: 0;
    padding: 20px;
    background: white;
}

/* Print-specific styles */
@media print {
    body {
        margin: 0;
        padding: 15px;
        font-size: 11pt;
    }
    
    .no-print {
        display: none !important;
    }
    
    .page-break {
        page-break-before: always;
    }
    
    .avoid-break {
        page-break-inside: avoid;
    }
    
    /* Page numbering */
    @page {
        margin: 2cm;
        
        @top-right {
            content: "Página " counter(page) " de " counter(pages);
            font-size: 9pt;
            color: #666;
        }
    }
}

/* Header Styles */
.header {
    text-align: center;
    margin-bottom: 30px;
    padding-bottom: 15px;
    border-bottom: 2px solid #0066cc;
    page-break-inside: avoid;
}

.hospital-branding {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 20px;
    margin-bottom: 15px;
}

.hospital-logo {
    max-height: 60px;
    width: auto;
}

.hospital-name {
    font-size: 18pt;
    font-weight: bold;
    color: #0066cc;
    margin-bottom: 5px;
}

.hospital-details {
    font-size: 10pt;
    color: #666;
    margin-bottom: 10px;
}

.document-title h1 {
    font-size: 16pt;
    font-weight: bold;
    color: #0066cc;
    margin: 10px 0 5px 0;
}

.document-title h2 {
    font-size: 14pt;
    font-weight: normal;
    color: #333;
    margin: 0;
}

/* Patient Info Styles */
.patient-info-section {
    margin-bottom: 25px;
    page-break-inside: avoid;
}

.patient-info-section h3 {
    font-size: 14pt;
    font-weight: bold;
    color: #0066cc;
    margin-bottom: 10px;
    padding-bottom: 5px;
    border-bottom: 1px solid #ccc;
}

.patient-info-grid {
    background: #f8f9fa;
    padding: 15px;
    border: 1px solid #dee2e6;
    border-radius: 5px;
}

.info-row {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    margin-bottom: 8px;
}

.info-row:last-child {
    margin-bottom: 0;
}

.info-cell {
    flex: 1;
    min-width: 200px;
}

.info-label {
    font-weight: bold;
    color: #495057;
}

.info-value {
    color: #212529;
    margin-left: 5px;
}

/* Content Section Styles */
.content-section {
    margin-bottom: 20px;
    page-break-inside: avoid;
}

.content-section h3 {
    font-size: 13pt;
    font-weight: bold;
    color: #0066cc;
    margin-bottom: 10px;
    padding-bottom: 5px;
    border-bottom: 1px solid #ccc;
}

.content-text {
    text-align: justify;
    line-height: 1.5;
    margin-bottom: 10px;
}

.content-text p {
    margin-bottom: 8px;
}

/* Print Button */
.print-button {
    position: fixed;
    top: 20px;
    right: 20px;
    background: #0066cc;
    color: white;
    border: none;
    padding: 10px 15px;
    border-radius: 5px;
    font-size: 14px;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    z-index: 1000;
}

.print-button:hover {
    background: #0052a3;
}

/* Footer Styles */
.page-footer {
    margin-top: 30px;
    padding-top: 15px;
    border-top: 1px solid #ccc;
    page-break-inside: avoid;
}

.generation-info {
    margin-bottom: 15px;
    font-size: 10pt;
    color: #666;
}

.generation-info p {
    margin: 2px 0;
}

.hospital-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 9pt;
    color: #666;
}

.hospital-footer-info {
    text-align: left;
}

.sistema-credit {
    text-align: right;
    font-style: italic;
}

/* Mobile Responsive */
@media (max-width: 768px) {
    .hospital-branding {
        flex-direction: column;
        gap: 10px;
    }
    
    .info-row {
        flex-direction: column;
        gap: 5px;
    }
    
    .info-cell {
        min-width: unset;
    }
    
    .hospital-footer {
        flex-direction: column;
        gap: 10px;
        text-align: center;
    }
}

/* Long Content Handling */
.content-text {
    overflow-wrap: break-word;
    word-wrap: break-word;
}

/* Table styles if needed for structured data */
.info-table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
}

.info-table td {
    padding: 5px 8px;
    border: 1px solid #dee2e6;
    vertical-align: top;
}

.info-table .label-cell {
    background: #f8f9fa;
    font-weight: bold;
    width: 30%;
}
```

3. UPDATE STATIC FILES:
Run webpack build to process the new CSS:
```bash
npm run build
```

4. ADD PRINT BUTTON TO DETAIL TEMPLATE:
Update apps/dischargereports/templates/dischargereports/dischargereport_detail.html to add print button:
```html
<!-- Add this button to the detail template -->
<a href="{% url 'apps.dischargereports:dischargereport_print' pk=report.pk %}" 
   class="btn btn-outline-secondary" target="_blank">
    <i class="bi bi-printer"></i> Imprimir Relatório
</a>
```

VERIFICATION:
- Print template displays all sections correctly
- Hospital branding appears properly
- CSS styling works in print preview
- Multi-page reports paginate correctly
- Print button works from detail view and event card

DELIVERABLES:
- Professional Portuguese print template
- Print-specific CSS styling
- Hospital branding integration
- Print buttons in UI
```

---

## Phase 5 Prompt: Firebase Import Command

```
Create Firebase import management command for discharge reports with PatientAdmission creation.

CONTEXT:
- DischargeReport model exists with all fields
- Firebase data in "patientDischargeReports" reference
- Need to create PatientAdmission records for each imported report
- Use similar structure to apps/core/management/commands/sync_firebase_data.py
- Firebase data format provided in requirements

GOAL: Create management command to import discharge reports from Firebase.

TASKS:

1. CREATE COMMAND DIRECTORY:
```bash
mkdir -p apps/dischargereports/management/commands
touch apps/dischargereports/management/__init__.py
touch apps/dischargereports/management/commands/__init__.py
```

2. CREATE IMPORT COMMAND:
apps/dischargereports/management/commands/import_firebase_discharge_reports.py:
```python
import json
import sys
from datetime import datetime, timezone, date
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone as django_timezone
from django.db import transaction

try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    firebase_admin = None

from apps.patients.models import Patient, PatientRecordNumber, PatientAdmission
from apps.dischargereports.models import DischargeReport

User = get_user_model()


class Command(BaseCommand):
    help = "Import discharge reports from Firebase Realtime Database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--credentials-file",
            type=str,
            required=True,
            help="Path to Firebase service account credentials JSON file",
        )
        parser.add_argument(
            "--database-url",
            type=str,
            required=True,
            help="Firebase Realtime Database URL (e.g., https://your-project.firebaseio.com)",
        )
        parser.add_argument(
            "--discharge-reports-reference",
            type=str,
            default="patientDischargeReports",
            help="Firebase database reference path for discharge reports (default: patientDischargeReports)",
        )
        parser.add_argument(
            "--user-email",
            type=str,
            help="Email of user to use as created_by/updated_by. If not provided, uses first admin user",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without actually importing",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of records to import (useful for testing)",
        )

    def handle(self, *args, **options):
        if firebase_admin is None:
            raise CommandError(
                "firebase-admin package is not installed. Please install it with: uv add firebase-admin"
            )

        self.dry_run = options["dry_run"]
        self.limit = options.get("limit")

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No data will be imported")
            )

        # Initialize Firebase
        try:
            self.init_firebase(options["credentials_file"], options["database_url"])
        except Exception as e:
            raise CommandError(f"Failed to initialize Firebase: {e}")

        # Get user for imports
        try:
            self.import_user = self.get_import_user(options.get("user_email"))
        except Exception as e:
            raise CommandError(f"Failed to get import user: {e}")

        self.stdout.write(
            f"Using import user: {self.import_user.username} ({self.import_user.email})"
        )

        # Import discharge reports
        try:
            imported_count = self.import_discharge_reports(
                options["discharge_reports_reference"]
            )
        except Exception as e:
            raise CommandError(f"Failed to import discharge reports: {e}")

        # Final report
        self.display_import_report(imported_count)

    def init_firebase(self, credentials_file, database_url):
        """Initialize Firebase Admin SDK"""
        try:
            import os

            if not os.path.exists(credentials_file):
                raise Exception(f"Credentials file not found: {credentials_file}")

            with open(credentials_file, "r") as f:
                json.load(f)

            cred = credentials.Certificate(credentials_file)
            firebase_admin.initialize_app(cred, {"databaseURL": database_url})
            self.stdout.write(self.style.SUCCESS("Firebase initialized successfully"))
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in credentials file: {e}")
        except Exception as e:
            raise Exception(f"Firebase initialization failed: {e}")

    def get_import_user(self, user_email):
        """Get user for imports"""
        if user_email:
            try:
                user = User.objects.get(email=user_email)
                return user
            except User.DoesNotExist:
                raise Exception(f"User with email {user_email} not found")
        else:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                raise Exception(
                    "No admin user found. Please create one or specify --user-email"
                )
            return user

    def import_discharge_reports(self, reports_reference):
        """Import discharge reports from Firebase"""
        self.stdout.write(f"\n=== IMPORTING DISCHARGE REPORTS ===")
        
        try:
            imported_count = 0
            error_count = 0
            skipped_count = 0
            
            # Get all discharge reports
            ref = db.reference(reports_reference)
            all_reports = ref.get()
            
            if not all_reports:
                self.stdout.write("No discharge reports found in Firebase")
                return 0
                
            total_reports = len(all_reports)
            self.stdout.write(f"Found {total_reports} discharge reports in Firebase")
            
            for firebase_key, report_data in all_reports.items():
                try:
                    result = self.process_firebase_discharge_report(
                        firebase_key, report_data
                    )
                    if result == "imported":
                        imported_count += 1
                    elif result == "skipped":
                        skipped_count += 1
                        
                    # Respect limit
                    if self.limit and imported_count >= self.limit:
                        self.stdout.write(f"Reached import limit of {self.limit}")
                        break
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error importing discharge report {firebase_key}: {e}"
                        )
                    )
            
            self.stdout.write(
                f"Discharge Reports: {imported_count} imported, {skipped_count} skipped, {error_count} errors"
            )
            return imported_count
            
        except Exception as e:
            raise Exception(f"Failed to import discharge reports: {e}")

    def process_firebase_discharge_report(self, firebase_key, report_data):
        """Process a single Firebase discharge report"""
        
        # Extract required fields
        content = report_data.get("content", {})
        patient_key = report_data.get("patient")
        datetime_ms = report_data.get("datetime")
        username = report_data.get("username", "Usuário não identificado")
        
        if not content:
            raise ValueError("Missing content field")
        if not patient_key:
            raise ValueError("Missing patient field")
        if not datetime_ms:
            raise ValueError("Missing datetime field")
            
        # Find patient using PatientRecordNumber
        patient_record = PatientRecordNumber.objects.filter(
            record_number=patient_key
        ).first()
        
        if not patient_record:
            return "skipped"  # Patient not found
            
        patient = patient_record.patient
        
        # Check if discharge report already exists
        existing_report = DischargeReport.objects.filter(
            patient=patient,
            description__icontains=f"Firebase ID: {firebase_key}",
        ).first()
        
        if existing_report:
            return "skipped"
            
        # Parse dates
        admission_date_str = content.get("admissionDate")
        discharge_date_str = content.get("dischargeDate")
        
        if not admission_date_str or not discharge_date_str:
            raise ValueError("Missing admission or discharge date")
            
        try:
            admission_date = datetime.strptime(admission_date_str, "%Y-%m-%d").date()
            discharge_date = datetime.strptime(discharge_date_str, "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(f"Invalid date format: {e}")
            
        # Parse event datetime
        try:
            event_datetime = datetime.fromtimestamp(int(datetime_ms) / 1000, tz=timezone.utc)
            event_datetime = event_datetime.astimezone(
                django_timezone.get_current_timezone()
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid datetime format: {e}")
            
        if self.dry_run:
            self.stdout.write(
                f"  Would import discharge report for: {patient.name} "
                f"({admission_date_str} -> {discharge_date_str})"
            )
            return "imported"
            
        # Create discharge report and admission record
        with transaction.atomic():
            # Create discharge report
            discharge_report = DischargeReport.objects.create(
                patient=patient,
                event_datetime=event_datetime,
                description=f"Relatório de alta importado - {content.get('specialty', 'N/A')}",
                admission_date=admission_date,
                discharge_date=discharge_date,
                medical_specialty=content.get("specialty", ""),
                admission_history=content.get("admissionHistory", ""),
                problems_and_diagnosis=content.get("problemsAndDiagnostics", ""),
                exams_list=content.get("examsList", ""),
                procedures_list=content.get("proceduresList", ""),
                inpatient_medical_history=content.get("inpatientMedicalHistory", ""),
                discharge_status=content.get("patientDischargeStatus", ""),
                discharge_recommendations=content.get("dischargeRecommendations", ""),
                is_draft=False,  # Imported reports are finalized
                created_by=self.import_user,
                updated_by=self.import_user,
            )
            
            # Add Firebase ID to description for tracking
            discharge_report.description += f"\n\nFirebase ID: {firebase_key}\nMédico: {username}"
            discharge_report.save()
            
            # Create PatientAdmission record
            stay_duration = (discharge_date - admission_date).days
            
            admission_datetime = django_timezone.datetime.combine(
                admission_date,
                django_timezone.datetime.min.time()
            ).replace(tzinfo=django_timezone.get_current_timezone())
            
            discharge_datetime = django_timezone.datetime.combine(
                discharge_date,
                django_timezone.datetime.min.time()
            ).replace(tzinfo=django_timezone.get_current_timezone())
            
            PatientAdmission.objects.create(
                patient=patient,
                admission_datetime=admission_datetime,
                discharge_datetime=discharge_datetime,
                admission_type=PatientAdmission.AdmissionType.SCHEDULED,
                discharge_type=PatientAdmission.DischargeType.MEDICAL,
                initial_bed="",
                final_bed="",
                ward=None,
                admission_diagnosis="",
                discharge_diagnosis="",
                stay_duration_days=stay_duration,
                is_active=False,
                created_by=self.import_user,
                updated_by=self.import_user,
            )
            
        self.stdout.write(
            f"  ✓ Imported discharge report: {patient.name} "
            f"({admission_date_str} -> {discharge_date_str})"
        )
        
        return "imported"

    def display_import_report(self, imported_count):
        """Display final import report"""
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("DISCHARGE REPORTS IMPORT COMPLETED"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN - No data was actually imported")
            )
            
        self.stdout.write("")
        self.stdout.write("Summary:")
        self.stdout.write(f"  Discharge reports imported: {imported_count}")
        
        if self.limit:
            self.stdout.write(f"  Limited to: {self.limit} records")
            
        self.stdout.write(self.style.SUCCESS("=" * 60))
```

3. CREATE FEATURE DOCUMENTATION:
Create docs/apps/dischargereports.md with comprehensive documentation including the Firebase import command usage, data mapping, and troubleshooting guide. Use the template from docs-template.md created earlier.

4. TEST THE COMMAND:
```bash
# Test with dry run
uv run python manage.py import_firebase_discharge_reports \
  --credentials-file firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --dry-run

# Test with limit
uv run python manage.py import_firebase_discharge_reports \
  --credentials-file firebase-key.json \
  --database-url https://your-project.firebaseio.com \
  --limit 5 \
  --dry-run
```

5. ADD DOCKER COMMAND EXAMPLES TO DOCS:
```bash
# Docker version
docker compose exec eqmd python manage.py import_firebase_discharge_reports \
  --credentials-file /app/firebase-key.json \
  --database-url https://your-project.firebaseio.com
```

VERIFICATION:
- Command runs without errors
- Dry run shows correct data parsing
- DischargeReport objects created correctly
- PatientAdmission objects created with proper fields
- Firebase ID tracking in description works
- Error handling works for missing patients

DELIVERABLES:
- Working Firebase import command
- PatientAdmission creation logic
- Comprehensive feature documentation
- Docker command examples
```

---

## Phase 6 Prompt: Advanced Features & Permissions

```
Implement draft logic, permissions, and UI polish for discharge reports.

CONTEXT:
- Phases 1-5 completed: Full CRUD, timeline integration, print, Firebase import
- Draft system partially implemented (is_draft field exists)
- Need to refine draft logic, permissions, and UI polish
- Project uses standard Event permission system with 24h edit window

GOAL: Polish the discharge reports feature with proper draft logic and permissions.

TASKS:

1. UPDATE MODELS.PY - ADD DRAFT VALIDATION:
```python
# Add this method to DischargeReport model
def can_be_edited_by_user(self, user):
    """Check if report can be edited by specific user"""
    if self.is_draft:
        # Drafts can be edited by creator or users with edit permissions
        return self.created_by == user or user.has_perm('events.change_event')
    else:
        # Finalized reports follow 24h rule
        return self.can_be_edited and (self.created_by == user or user.has_perm('events.change_event'))

def can_be_deleted_by_user(self, user):
    """Check if report can be deleted by specific user"""
    # Only drafts can be deleted
    return self.is_draft and (self.created_by == user or user.has_perm('events.delete_event'))

@property 
def status_display(self):
    """Get display text for report status"""
    if self.is_draft:
        return "Rascunho"
    else:
        return "Finalizado"

@property
def status_badge_class(self):
    """Get CSS class for status badge"""
    return "badge bg-warning text-dark" if self.is_draft else "badge bg-success"
```

2. UPDATE VIEWS.PY - IMPROVE PERMISSION LOGIC:
```python
# Update existing views with better permission checking

class DischargeReportUpdateView(LoginRequiredMixin, UpdateView):
    """Update discharge report - separate template"""
    model = DischargeReport
    form_class = DischargeReportForm
    template_name = 'dischargereports/dischargereport_update.html'
    
    def get_object(self):
        obj = super().get_object()
        # Check if user can edit this specific report
        if not obj.can_be_edited_by_user(self.request.user):
            if obj.is_draft:
                raise PermissionDenied("Você não tem permissão para editar este rascunho.")
            else:
                raise PermissionDenied("Este relatório não pode mais ser editado.")
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_finalize'] = self.object.is_draft
        return context
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        
        # Handle draft vs final save
        if 'save_final' in self.request.POST and self.object.is_draft:
            form.instance.is_draft = False
            messages.success(self.request, 'Relatório de alta finalizado com sucesso.')
        elif 'save_draft' in self.request.POST:
            form.instance.is_draft = True
            messages.success(self.request, 'Rascunho do relatório atualizado.')
        else:
            messages.success(self.request, 'Relatório de alta atualizado.')
        
        return super().form_valid(form)


class DischargeReportDeleteView(LoginRequiredMixin, DeleteView):
    """Delete discharge report (drafts only)"""
    model = DischargeReport
    template_name = 'dischargereports/dischargereport_confirm_delete.html'
    success_url = reverse_lazy('apps.dischargereports:dischargereport_list')
    
    def get_object(self):
        obj = super().get_object()
        if not obj.can_be_deleted_by_user(self.request.user):
            raise PermissionDenied("Este relatório não pode ser excluído.")
        return obj
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Rascunho do relatório de alta excluído com sucesso.')
        return super().delete(request, *args, **kwargs)
```

3. UPDATE TEMPLATES - IMPROVE DRAFT UI:

Update dischargereport_detail.html:
```html
{% extends 'base.html' %}
{% load static %}
{% load bootstrap5 %}

{% block title %}Relatório de Alta - {{ report.patient.name }}{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <div>
                        <h3>Relatório de Alta</h3>
                        <div class="d-flex align-items-center gap-2 mt-2">
                            <span class="{{ report.status_badge_class }}">
                                {% if report.is_draft %}
                                    <i class="bi bi-pencil-square"></i>
                                {% else %}
                                    <i class="bi bi-check-circle"></i>
                                {% endif %}
                                {{ report.status_display }}
                            </span>
                            <small class="text-muted">
                                {{ report.medical_specialty }} • 
                                {{ report.admission_date|date:"d/m/Y" }} - {{ report.discharge_date|date:"d/m/Y" }}
                            </small>
                        </div>
                    </div>
                    <div class="btn-group">
                        <!-- Print Button -->
                        <a href="{% url 'apps.dischargereports:dischargereport_print' pk=report.pk %}" 
                           class="btn btn-outline-secondary" target="_blank">
                            <i class="bi bi-printer"></i> Imprimir
                        </a>
                        
                        <!-- Edit Button -->
                        {% if report.can_be_edited_by_user:request.user %}
                            <a href="{% url 'apps.dischargereports:dischargereport_update' pk=report.pk %}" 
                               class="btn btn-warning">
                                <i class="bi bi-pencil"></i> 
                                {% if report.is_draft %}Editar Rascunho{% else %}Editar{% endif %}
                            </a>
                        {% endif %}
                        
                        <!-- Delete Button (drafts only) -->
                        {% if report.can_be_deleted_by_user:request.user %}
                            <a href="{% url 'apps.dischargereports:dischargereport_delete' pk=report.pk %}" 
                               class="btn btn-outline-danger">
                                <i class="bi bi-trash"></i> Excluir Rascunho
                            </a>
                        {% endif %}
                        
                        <a href="{% url 'patients:patient_events_timeline' patient_id=report.patient.pk %}" 
                           class="btn btn-outline-secondary">
                            <i class="bi bi-arrow-left"></i> Voltar
                        </a>
                    </div>
                </div>
                
                <div class="card-body">
                    <!-- Patient Info -->
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <h5>Paciente</h5>
                            <p><strong>{{ report.patient.name }}</strong></p>
                            <p>Prontuário: {{ report.patient.current_record_number|default:"—" }}</p>
                        </div>
                        <div class="col-md-6">
                            <h5>Datas</h5>
                            <p><strong>Admissão:</strong> {{ report.admission_date|date:"d/m/Y" }}</p>
                            <p><strong>Alta:</strong> {{ report.discharge_date|date:"d/m/Y" }}</p>
                            <p><strong>Permanência:</strong> {{ report.discharge_date|timeuntil:report.admission_date }}</p>
                        </div>
                    </div>
                    
                    <!-- Medical Content -->
                    <div class="row">
                        <div class="col-12">
                            {% if report.problems_and_diagnosis %}
                            <div class="mb-3">
                                <h6>Problemas e Diagnósticos</h6>
                                <div class="border p-3 bg-light">
                                    {{ report.problems_and_diagnosis|linebreaks }}
                                </div>
                            </div>
                            {% endif %}
                            
                            <!-- Add other sections similarly -->
                        </div>
                    </div>
                </div>
                
                <div class="card-footer">
                    <small class="text-muted">
                        Criado por {{ report.created_by.get_full_name|default:report.created_by.username }} 
                        em {{ report.created_at|date:"d/m/Y H:i" }}
                        {% if report.updated_at != report.created_at %}
                            • Atualizado em {{ report.updated_at|date:"d/m/Y H:i" }}
                        {% endif %}
                    </small>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

4. UPDATE LIST TEMPLATE - ADD STATUS COLUMN:
```html
<!-- Add to dischargereport_list.html table -->
<th>Status</th>
<th>Especialidade</th>
<th>Data da Alta</th>
<th>Ações</th>

<!-- In table body -->
<td>
    <span class="{{ report.status_badge_class }}">
        {{ report.status_display }}
    </span>
</td>
<td>{{ report.medical_specialty }}</td>
<td>{{ report.discharge_date|date:"d/m/Y" }}</td>
<td>
    <div class="btn-group btn-group-sm">
        <a href="{{ report.get_absolute_url }}" class="btn btn-outline-primary">
            <i class="bi bi-eye"></i>
        </a>
        {% if report.can_be_edited_by_user:request.user %}
            <a href="{{ report.get_edit_url }}" class="btn btn-outline-warning">
                <i class="bi bi-pencil"></i>
            </a>
        {% endif %}
    </div>
</td>
```

5. ADD HELP TEXT TO FORMS:
```python
# Update DischargeReportForm widgets with better help text
'is_draft': forms.HiddenInput(),  # Hide from form, controlled by buttons
# Add help text to other fields as needed
```

6. UPDATE EVENT CARD TEMPLATE:
```html
<!-- Update apps/events/templates/events/partials/event_card_dischargereport.html -->
<!-- Add draft status indicator -->
{% if event.is_draft %}
    <span class="badge bg-warning text-dark ms-2">
        <i class="bi bi-pencil-square"></i> Rascunho
    </span>
{% endif %}

<!-- Update edit button logic -->
{% if event.can_be_edited_by_user:request.user %}
    <a href="{{ event.get_edit_url }}" 
       class="btn btn-outline-warning btn-sm"
       title="{% if event.is_draft %}Editar rascunho{% else %}Editar relatório{% endif %}">
        <i class="bi bi-pencil"></i>
    </a>
{% endif %}
```

7. ADD ADMIN IMPROVEMENTS:
```python
# Update admin.py
@admin.register(DischargeReport)
class DischargeReportAdmin(admin.ModelAdmin):
    list_display = ['patient', 'medical_specialty', 'admission_date', 'discharge_date', 'status_display', 'created_at']
    list_filter = ['is_draft', 'medical_specialty', 'admission_date', 'discharge_date', 'created_at']
    search_fields = ['patient__name', 'medical_specialty', 'problems_and_diagnosis']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by', 'status_display']
    
    def status_display(self, obj):
        return obj.status_display
    status_display.short_description = 'Status'
```

VERIFICATION:
- Draft/finalized status displays correctly throughout UI
- Edit permissions work properly (drafts vs 24h window)
- Delete only works for drafts
- Status badges and indicators are consistent
- Admin interface shows status properly

DELIVERABLES:
- Refined draft logic and permissions
- Improved UI with status indicators
- Better permission checking
- Enhanced admin interface
```

---

## Phase 7 Prompt: Testing & Documentation

```
Create comprehensive tests and complete documentation for discharge reports feature.

CONTEXT:
- All previous phases completed: Full discharge reports functionality
- Need comprehensive test coverage for models, views, permissions, Firebase import
- Need to complete feature documentation
- Project uses pytest and Django test runner

GOAL: Complete test suite and comprehensive documentation.

TASKS:

1. CREATE TEST DIRECTORY STRUCTURE:
```bash
mkdir -p apps/dischargereports/tests
touch apps/dischargereports/tests/__init__.py
```

2. CREATE MODEL TESTS:
apps/dischargereports/tests/test_models.py:
```python
from datetime import date, datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.patients.models import Patient
from apps.events.models import Event
from apps.dischargereports.models import DischargeReport

User = get_user_model()


class DischargeReportModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.user,
            updated_by=self.user
        )
        
    def test_save_sets_event_type(self):
        """Test that save() sets correct event type"""
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            admission_history='Test history',
            problems_and_diagnosis='Test diagnosis',
            exams_list='Test exams',
            procedures_list='Test procedures',
            inpatient_medical_history='Test medical history',
            discharge_status='Test status',
            discharge_recommendations='Test recommendations',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(report.event_type, Event.DISCHARGE_REPORT_EVENT)
        
    def test_is_draft_default_true(self):
        """Test that is_draft defaults to True"""
        report = DischargeReport(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertTrue(report.is_draft)
        
    def test_string_representation(self):
        """Test __str__ method"""
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            created_by=self.user,
            updated_by=self.user
        )
        expected = f"Relatório de Alta - {self.patient.name} - 01/01/2024 (Rascunho)"
        self.assertEqual(str(report), expected)
        
    def test_can_be_edited_by_user_draft(self):
        """Test that drafts can be edited by creator"""
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Test report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=True,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertTrue(report.can_be_edited_by_user(self.user))
        
    def test_can_be_deleted_by_user_draft_only(self):
        """Test that only drafts can be deleted"""
        draft_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Draft report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        final_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Final report',
            admission_date=date(2024, 2, 1),
            discharge_date=date(2024, 2, 5),
            medical_specialty='Test Specialty',
            is_draft=False,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertTrue(draft_report.can_be_deleted_by_user(self.user))
        self.assertFalse(final_report.can_be_deleted_by_user(self.user))
        
    def test_status_display_properties(self):
        """Test status display properties"""
        draft_report = DischargeReport(is_draft=True)
        final_report = DischargeReport(is_draft=False)
        
        self.assertEqual(draft_report.status_display, "Rascunho")
        self.assertEqual(final_report.status_display, "Finalizado")
        
        self.assertEqual(draft_report.status_badge_class, "badge bg-warning text-dark")
        self.assertEqual(final_report.status_badge_class, "badge bg-success")
```

3. CREATE VIEW TESTS:
apps/dischargereports/tests/test_views.py:
```python
from datetime import date, datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from apps.patients.models import Patient
from apps.dischargereports.models import DischargeReport

User = get_user_model()


class DischargeReportViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.user,
            updated_by=self.user
        )
        
    def test_create_view_requires_login(self):
        """Test that create view requires authentication"""
        url = reverse('apps.dischargereports:dischargereport_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
    def test_create_view_saves_draft_by_default(self):
        """Test that create view saves as draft by default"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.dischargereports:dischargereport_create')
        
        data = {
            'patient': self.patient.pk,
            'event_datetime': datetime.now(),
            'description': 'Test report',
            'admission_date': date(2024, 1, 1),
            'discharge_date': date(2024, 1, 5),
            'medical_specialty': 'Test Specialty',
            'admission_history': 'Test history',
            'problems_and_diagnosis': 'Test diagnosis',
            'exams_list': 'Test exams',
            'procedures_list': 'Test procedures',
            'inpatient_medical_history': 'Test medical history',
            'discharge_status': 'Test status',
            'discharge_recommendations': 'Test recommendations',
            'save_draft': 'Save Draft'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after save
        
        report = DischargeReport.objects.get(patient=self.patient)
        self.assertTrue(report.is_draft)
        
    def test_create_view_saves_final(self):
        """Test that create view can save as final"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.dischargereports:dischargereport_create')
        
        data = {
            'patient': self.patient.pk,
            'event_datetime': datetime.now(),
            'description': 'Test report',
            'admission_date': date(2024, 1, 1),
            'discharge_date': date(2024, 1, 5),
            'medical_specialty': 'Test Specialty',
            'admission_history': 'Test history',
            'problems_and_diagnosis': 'Test diagnosis',
            'exams_list': 'Test exams',
            'procedures_list': 'Test procedures',
            'inpatient_medical_history': 'Test medical history',
            'discharge_status': 'Test status',
            'discharge_recommendations': 'Test recommendations',
            'save_final': 'Save Final'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        report = DischargeReport.objects.get(patient=self.patient)
        self.assertFalse(report.is_draft)
        
    def test_update_view_blocks_non_editable(self):
        """Test that update view blocks non-editable reports"""
        # Create final report older than 24 hours
        old_datetime = datetime.now() - timedelta(hours=25)
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=old_datetime,
            description='Old final report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=False,
            created_by=self.user,
            updated_by=self.user
        )
        # Manually set created_at to simulate old report
        DischargeReport.objects.filter(pk=report.pk).update(created_at=old_datetime)
        
        self.client.login(username='testuser', password='testpass123')
        url = reverse('apps.dischargereports:dischargereport_update', kwargs={'pk': report.pk})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # PermissionDenied
        
    def test_delete_view_allows_drafts_only(self):
        """Test that delete view only allows draft deletion"""
        draft_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Draft report',
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty='Test Specialty',
            is_draft=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        final_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=datetime.now(),
            description='Final report',
            admission_date=date(2024, 2, 1),
            discharge_date=date(2024, 2, 5),
            medical_specialty='Test Specialty',
            is_draft=False,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Draft can be deleted
        draft_url = reverse('apps.dischargereports:dischargereport_delete', kwargs={'pk': draft_report.pk})
        response = self.client.get(draft_url)
        self.assertEqual(response.status_code, 200)
        
        # Final report cannot be deleted
        final_url = reverse('apps.dischargereports:dischargereport_delete', kwargs={'pk': final_report.pk})
        response = self.client.get(final_url)
        self.assertEqual(response.status_code, 403)
```

4. CREATE FIREBASE IMPORT TESTS:
apps/dischargereports/tests/test_firebase_import.py:
```python
from datetime import date, datetime
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
from apps.patients.models import Patient, PatientRecordNumber, PatientAdmission
from apps.dischargereports.models import DischargeReport

User = get_user_model()


class FirebaseImportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Create patient with record number
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.user,
            updated_by=self.user
        )
        
        PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='firebase-patient-key',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Sample Firebase data
        self.firebase_data = {
            'report-key-1': {
                'content': {
                    'admissionDate': '2024-01-01',
                    'dischargeDate': '2024-01-05',
                    'specialty': 'Cardiologia',
                    'admissionHistory': 'Paciente admitido com dor torácica...',
                    'problemsAndDiagnostics': 'Angina instável',
                    'examsList': 'ECG, Ecocardiograma',
                    'proceduresList': 'Cateterismo cardíaco',
                    'inpatientMedicalHistory': 'Evolução favorável...',
                    'patientDischargeStatus': 'Alta melhorada',
                    'dischargeRecommendations': 'Seguimento ambulatorial'
                },
                'datetime': 1704067200000,  # 2024-01-01 timestamp
                'patient': 'firebase-patient-key',
                'username': 'Dr. Test'
            }
        }
        
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.firebase_admin')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.credentials')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.db')
    def test_successful_import(self, mock_db, mock_credentials, mock_firebase_admin):
        """Test successful Firebase import"""
        # Mock Firebase setup
        mock_ref = Mock()
        mock_ref.get.return_value = self.firebase_data
        mock_db.reference.return_value = mock_ref
        
        # Mock credentials and firebase initialization
        mock_firebase_admin.initialize_app = Mock()
        
        # Capture command output
        out = StringIO()
        
        # Run command
        call_command(
            'import_firebase_discharge_reports',
            '--credentials-file', '/fake/path.json',
            '--database-url', 'https://fake.firebaseio.com',
            '--dry-run',
            stdout=out
        )
        
        output = out.getvalue()
        self.assertIn('1 discharge reports', output)
        self.assertIn('DRY RUN', output)
        
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.firebase_admin')
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.credentials') 
    @patch('apps.dischargereports.management.commands.import_firebase_discharge_reports.db')
    def test_actual_import_creates_objects(self, mock_db, mock_credentials, mock_firebase_admin):
        """Test that actual import creates DischargeReport and PatientAdmission objects"""
        # Mock Firebase setup
        mock_ref = Mock()
        mock_ref.get.return_value = self.firebase_data
        mock_db.reference.return_value = mock_ref
        
        # Mock file operations
        with patch('builtins.open', mock_open(read_data='{"test": "data"}')):
            with patch('os.path.exists', return_value=True):
                with patch('json.load', return_value={"test": "data"}):
                    # Run actual import (not dry run)
                    call_command(
                        'import_firebase_discharge_reports',
                        '--credentials-file', '/fake/path.json',
                        '--database-url', 'https://fake.firebaseio.com',
                        stdout=StringIO()
                    )
        
        # Verify objects were created
        self.assertEqual(DischargeReport.objects.count(), 1)
        self.assertEqual(PatientAdmission.objects.count(), 1)
        
        report = DischargeReport.objects.first()
        self.assertEqual(report.patient, self.patient)
        self.assertEqual(report.medical_specialty, 'Cardiologia')
        self.assertFalse(report.is_draft)  # Imported reports are finalized
        
        admission = PatientAdmission.objects.first()
        self.assertEqual(admission.patient, self.patient)
        self.assertEqual(admission.admission_type, PatientAdmission.AdmissionType.SCHEDULED)
        self.assertFalse(admission.is_active)
```

5. CREATE INTEGRATION TESTS:
apps/dischargereports/tests/test_integration.py:
```python
from datetime import date, datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.patients.models import Patient
from apps.dischargereports.models import DischargeReport

User = get_user_model()


class DischargeReportIntegrationTests(TestCase):
    """Test complete workflows"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            name='Integration Test Patient',
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.user,
            updated_by=self.user
        )
        
    def test_complete_draft_to_final_workflow(self):
        """Test creating draft, editing, and finalizing"""
        self.client.login(username='testuser', password='testpass123')
        
        # Create draft
        create_url = reverse('apps.dischargereports:dischargereport_create')
        create_data = {
            'patient': self.patient.pk,
            'event_datetime': datetime.now(),
            'description': 'Test workflow report',
            'admission_date': date(2024, 1, 1),
            'discharge_date': date(2024, 1, 5),
            'medical_specialty': 'Integration Test',
            'admission_history': 'Initial history',
            'problems_and_diagnosis': 'Initial diagnosis',
            'exams_list': 'Initial exams',
            'procedures_list': 'Initial procedures',
            'inpatient_medical_history': 'Initial medical history',
            'discharge_status': 'Initial status',
            'discharge_recommendations': 'Initial recommendations',
            'save_draft': 'Save Draft'
        }
        
        response = self.client.post(create_url, create_data)
        self.assertEqual(response.status_code, 302)
        
        report = DischargeReport.objects.get(patient=self.patient)
        self.assertTrue(report.is_draft)
        
        # Edit draft
        update_url = reverse('apps.dischargereports:dischargereport_update', kwargs={'pk': report.pk})
        update_data = create_data.copy()
        update_data.update({
            'problems_and_diagnosis': 'Updated diagnosis',
            'save_final': 'Save Final'  # Finalize this time
        })
        
        response = self.client.post(update_url, update_data)
        self.assertEqual(response.status_code, 302)
        
        report.refresh_from_db()
        self.assertFalse(report.is_draft)
        self.assertEqual(report.problems_and_diagnosis, 'Updated diagnosis')
        
        # Verify can't delete finalized report
        delete_url = reverse('apps.dischargereports:dischargereport_delete', kwargs={'pk': report.pk})
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 403)
```

6. COMPLETE FEATURE DOCUMENTATION:
Create comprehensive docs/apps/dischargereports.md using the template from docs-template.md, including:
- All testing commands
- Troubleshooting section  
- Development notes
- Firebase import documentation

7. CREATE TEST RUNNER SCRIPT:
```bash
# Add to documentation - testing commands
# All tests
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/ -v

# Specific test files  
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_models.py -v
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_views.py -v
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/test_firebase_import.py -v

# With coverage
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/dischargereports/tests/ --cov=apps.dischargereports --cov-report=term-missing -v
```

VERIFICATION:
- All tests pass
- Good test coverage (>80%)
- Integration tests cover complete workflows
- Firebase import tests work with mocking
- Documentation is comprehensive and accurate

DELIVERABLES:
- Comprehensive test suite
- Feature documentation in docs/apps/dischargereports.md
- Testing command documentation
- Integration test coverage
```

Perfect! These prompts provide complete, self-contained implementation guides for each phase. Each prompt includes all necessary context, code examples, and verification steps needed to implement that specific phase successfully.