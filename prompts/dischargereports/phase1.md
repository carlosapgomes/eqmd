# Phase 1 Prompt: Foundation (Core Model)

````
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
````

Create these files:

- apps/dischargereports/**init**.py (empty)
- apps/dischargereports/apps.py
- apps/dischargereports/models.py
- apps/dischargereports/admin.py
- apps/dischargereports/urls.py
- apps/dischargereports/views.py
- apps/dischargereports/forms.py

1. IMPLEMENT MODELS.PY:

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

1. IMPLEMENT APPS.PY:

```python
from django.apps import AppConfig


class DischargereportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dischargereports'
    verbose_name = 'Relatórios de Alta'
```

1. IMPLEMENT ADMIN.PY:

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

1. CREATE EMPTY FILES:

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

1. ADD TO INSTALLED_APPS in settings/base.py:
   Add 'apps.dischargereports' to INSTALLED_APPS list.

2. GENERATE AND RUN MIGRATION:

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


```
