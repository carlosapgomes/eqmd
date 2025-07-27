# Phase 2: Event Integration and Timeline

## Overview

Integrate the new record tracking models with the existing Event system to provide timeline visibility and leverage the existing permission and audit infrastructure.

## Step-by-Step Implementation

### Step 2.1: Add New Event Types

**File**: `apps/events/models.py` - Update Event.EVENT_TYPE_CHOICES

```python
class Event(models.Model):
    # ... existing fields ...
    
    # Update EVENT_TYPE_CHOICES to include new types
    HISTORY_PHYSICAL_EVENT = 1
    DAILY_NOTE_EVENT = 2
    PHOTO_EVENT = 3
    EXAM_RESULT_EVENT = 4
    PRESCRIPTION_EVENT = 5
    DISCHARGE_SUMMARY_EVENT = 6
    PROCEDURE_EVENT = 7
    CONSULTATION_EVENT = 8
    PHOTO_SERIES_EVENT = 9
    VIDEO_CLIP_EVENT = 10
    RECORD_NUMBER_CHANGE_EVENT = 11  # NEW
    ADMISSION_EVENT = 12             # NEW
    DISCHARGE_EVENT = 13             # NEW
    
    EVENT_TYPE_CHOICES = [
        (HISTORY_PHYSICAL_EVENT, "História e Exame Físico"),
        (DAILY_NOTE_EVENT, "Evolução"),
        (PHOTO_EVENT, "Foto"),
        (EXAM_RESULT_EVENT, "Resultado de Exame"),
        (PRESCRIPTION_EVENT, "Prescrição"),
        (DISCHARGE_SUMMARY_EVENT, "Sumário de Alta"),
        (PROCEDURE_EVENT, "Procedimento"),
        (CONSULTATION_EVENT, "Consulta"),
        (PHOTO_SERIES_EVENT, "Série de Fotos"),
        (VIDEO_CLIP_EVENT, "Vídeo"),
        (RECORD_NUMBER_CHANGE_EVENT, "Alteração de Prontuário"),  # NEW
        (ADMISSION_EVENT, "Admissão Hospitalar"),                 # NEW
        (DISCHARGE_EVENT, "Alta Hospitalar"),                     # NEW
    ]
```

### Step 2.2: Create RecordNumberChangeEvent Model

**File**: `apps/events/models.py` - Add new Event subclass

```python
class RecordNumberChangeEvent(Event):
    """Event for tracking record number changes in patient timeline"""
    
    record_change = models.OneToOneField(
        'patients.PatientRecordNumber',
        on_delete=models.CASCADE,
        related_name='timeline_event',
        verbose_name="Alteração de Prontuário"
    )
    
    # Denormalized fields for performance and display
    old_record_number = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name="Número Anterior",
        help_text="Número de prontuário anterior"
    )
    new_record_number = models.CharField(
        max_length=50,
        verbose_name="Novo Número",
        help_text="Novo número de prontuário"
    )
    change_reason = models.TextField(
        blank=True,
        verbose_name="Motivo da Alteração",
        help_text="Razão para a mudança do número"
    )
    
    class Meta:
        verbose_name = "Evento de Alteração de Prontuário"
        verbose_name_plural = "Eventos de Alteração de Prontuário"
    
    def save(self, *args, **kwargs):
        """Override save to set event_type and sync with record_change"""
        self.event_type = self.RECORD_NUMBER_CHANGE_EVENT
        
        # Sync data from related PatientRecordNumber if available
        if self.record_change_id:
            record = self.record_change
            self.new_record_number = record.record_number
            self.old_record_number = record.previous_record_number
            self.change_reason = record.change_reason
            self.patient = record.patient
            self.event_datetime = record.effective_date
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.old_record_number:
            return f"Alteração de prontuário: {self.old_record_number} → {self.new_record_number}"
        return f"Novo prontuário: {self.new_record_number}"
```

### Step 2.3: Create AdmissionEvent Model

**File**: `apps/events/models.py` - Add new Event subclass

```python
class AdmissionEvent(Event):
    """Event for tracking patient admissions in timeline"""
    
    admission = models.OneToOneField(
        'patients.PatientAdmission',
        on_delete=models.CASCADE,
        related_name='timeline_event',
        verbose_name="Internação"
    )
    
    # Denormalized fields for performance and display
    admission_type = models.CharField(
        max_length=20,
        verbose_name="Tipo de Admissão",
        help_text="Tipo da admissão hospitalar"
    )
    initial_bed = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="Leito Inicial",
        help_text="Leito/quarto inicial"
    )
    admission_diagnosis = models.TextField(
        blank=True,
        verbose_name="Diagnóstico de Admissão",
        help_text="Diagnóstico principal na admissão"
    )
    
    class Meta:
        verbose_name = "Evento de Admissão"
        verbose_name_plural = "Eventos de Admissão"
    
    def save(self, *args, **kwargs):
        """Override save to set event_type and sync with admission"""
        self.event_type = self.ADMISSION_EVENT
        
        # Sync data from related PatientAdmission if available
        if self.admission_id:
            admission = self.admission
            self.admission_type = admission.get_admission_type_display()
            self.initial_bed = admission.initial_bed
            self.admission_diagnosis = admission.admission_diagnosis
            self.patient = admission.patient
            self.event_datetime = admission.admission_datetime
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Admissão - {self.get_admission_type_display()}"
```

### Step 2.4: Create DischargeEvent Model

**File**: `apps/events/models.py` - Add new Event subclass

```python
class DischargeEvent(Event):
    """Event for tracking patient discharges in timeline"""
    
    admission = models.OneToOneField(
        'patients.PatientAdmission',
        on_delete=models.CASCADE,
        related_name='discharge_timeline_event',
        verbose_name="Internação"
    )
    
    # Denormalized fields for performance and display
    discharge_type = models.CharField(
        max_length=20,
        verbose_name="Tipo de Alta",
        help_text="Tipo da alta hospitalar"
    )
    final_bed = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="Leito Final",
        help_text="Último leito/quarto"
    )
    discharge_diagnosis = models.TextField(
        blank=True,
        verbose_name="Diagnóstico de Alta",
        help_text="Diagnóstico principal na alta"
    )
    stay_duration_days = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="Duração da Internação (dias)",
        help_text="Duração total em dias"
    )
    
    class Meta:
        verbose_name = "Evento de Alta"
        verbose_name_plural = "Eventos de Alta"
    
    def save(self, *args, **kwargs):
        """Override save to set event_type and sync with admission"""
        self.event_type = self.DISCHARGE_EVENT
        
        # Sync data from related PatientAdmission if available
        if self.admission_id:
            admission = self.admission
            self.discharge_type = admission.get_discharge_type_display()
            self.final_bed = admission.final_bed
            self.discharge_diagnosis = admission.discharge_diagnosis
            self.stay_duration_days = admission.stay_duration_days
            self.patient = admission.patient
            self.event_datetime = admission.discharge_datetime
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        duration_text = f" ({self.stay_duration_days}d)" if self.stay_duration_days else ""
        return f"Alta - {self.get_discharge_type_display()}{duration_text}"
```

### Step 2.5: Create Event Card Templates

**File**: `apps/events/templates/events/partials/event_card_record_change.html`

```html
{% extends "events/partials/event_card_base.html" %}
{% load hospital_tags %}

{% block event_content %}
<div class="d-flex justify-content-between align-items-start">
    <div class="flex-grow-1">
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-muted mb-1">Alteração de Prontuário</h6>
                {% if event.old_record_number %}
                    <p class="mb-1">
                        <strong>Anterior:</strong> 
                        <span class="badge bg-secondary">{{ event.old_record_number }}</span>
                    </p>
                {% endif %}
                <p class="mb-1">
                    <strong>Novo:</strong> 
                    <span class="badge bg-primary">{{ event.new_record_number }}</span>
                </p>
            </div>
            {% if event.change_reason %}
            <div class="col-md-6">
                <h6 class="text-muted mb-1">Motivo</h6>
                <p class="mb-0 text-muted">{{ event.change_reason }}</p>
            </div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}

{% block event_actions %}
{% if perms.patients.change_patientrecordnumber %}
    <a href="{% url 'patients:record_number_update' event.record_change.pk %}" 
       class="btn btn-outline-secondary btn-sm" title="Editar">
        <i class="fas fa-edit"></i>
    </a>
{% endif %}
{% if perms.patients.delete_patientrecordnumber %}
    <a href="{% url 'patients:record_number_delete' event.record_change.pk %}" 
       class="btn btn-outline-danger btn-sm" title="Excluir">
        <i class="fas fa-trash"></i>
    </a>
{% endif %}
{{ block.super }}
{% endblock %}
```

**File**: `apps/events/templates/events/partials/event_card_admission.html`

```html
{% extends "events/partials/event_card_base.html" %}
{% load hospital_tags %}

{% block event_content %}
<div class="d-flex justify-content-between align-items-start">
    <div class="flex-grow-1">
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-muted mb-1">Admissão Hospitalar</h6>
                <p class="mb-1">
                    <strong>Tipo:</strong> 
                    <span class="badge bg-success">{{ event.admission_type }}</span>
                </p>
                {% if event.initial_bed %}
                <p class="mb-1">
                    <strong>Leito:</strong> {{ event.initial_bed }}
                </p>
                {% endif %}
            </div>
            {% if event.admission_diagnosis %}
            <div class="col-md-6">
                <h6 class="text-muted mb-1">Diagnóstico de Admissão</h6>
                <p class="mb-0 text-muted">{{ event.admission_diagnosis|truncatewords:20 }}</p>
            </div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}

{% block event_actions %}
{% if perms.patients.change_patientadmission %}
    <a href="{% url 'patients:admission_update' event.admission.pk %}" 
       class="btn btn-outline-secondary btn-sm" title="Editar">
        <i class="fas fa-edit"></i>
    </a>
{% endif %}
{{ block.super }}
{% endblock %}
```

**File**: `apps/events/templates/events/partials/event_card_discharge.html`

```html
{% extends "events/partials/event_card_base.html" %}
{% load hospital_tags %}

{% block event_content %}
<div class="d-flex justify-content-between align-items-start">
    <div class="flex-grow-1">
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-muted mb-1">Alta Hospitalar</h6>
                <p class="mb-1">
                    <strong>Tipo:</strong> 
                    <span class="badge bg-info">{{ event.discharge_type }}</span>
                </p>
                {% if event.final_bed %}
                <p class="mb-1">
                    <strong>Leito:</strong> {{ event.final_bed }}
                </p>
                {% endif %}
                {% if event.stay_duration_days %}
                <p class="mb-1">
                    <strong>Duração:</strong> {{ event.stay_duration_days }} dias
                </p>
                {% endif %}
            </div>
            {% if event.discharge_diagnosis %}
            <div class="col-md-6">
                <h6 class="text-muted mb-1">Diagnóstico de Alta</h6>
                <p class="mb-0 text-muted">{{ event.discharge_diagnosis|truncatewords:20 }}</p>
            </div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}

{% block event_actions %}
{% if perms.patients.change_patientadmission %}
    <a href="{% url 'patients:admission_update' event.admission.pk %}" 
       class="btn btn-outline-secondary btn-sm" title="Editar">
        <i class="fas fa-edit"></i>
    </a>
{% endif %}
{{ block.super }}
{% endblock %}
```

### Step 2.6: Update Timeline Template Logic

**File**: `apps/events/templates/events/patient_timeline.html` - Update template selection logic

```html
<!-- Update the event card rendering section -->
{% for event in events %}
    <div class="col-12 mb-3">
        {% if event.event_type == 1 %}
            {% include "events/partials/event_card_default.html" %}
        {% elif event.event_type == 2 %}
            {% include "events/partials/event_card_dailynote.html" %}
        {% elif event.event_type == 11 %}
            {% include "events/partials/event_card_record_change.html" %}
        {% elif event.event_type == 12 %}
            {% include "events/partials/event_card_admission.html" %}
        {% elif event.event_type == 13 %}
            {% include "events/partials/event_card_discharge.html" %}
        {% else %}
            {% include "events/partials/event_card_default.html" %}
        {% endif %}
    </div>
{% endfor %}
```

### Step 2.7: Create Signal Handlers for Event Creation

**File**: `apps/patients/signals.py` - Create new file

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import PatientRecordNumber, PatientAdmission
from apps.events.models import RecordNumberChangeEvent, AdmissionEvent, DischargeEvent


@receiver(post_save, sender=PatientRecordNumber)
def create_record_change_event(sender, instance, created, **kwargs):
    """Create timeline event when record number is changed"""
    if created or instance.is_current:
        # Create or update the timeline event
        event, event_created = RecordNumberChangeEvent.objects.get_or_create(
            record_change=instance,
            defaults={
                'patient': instance.patient,
                'event_datetime': instance.effective_date,
                'description': f"Alteração de prontuário para {instance.record_number}",
                'created_by': instance.created_by,
                'updated_by': instance.updated_by,
            }
        )
        
        if not event_created:
            # Update existing event
            event.event_datetime = instance.effective_date
            event.description = f"Alteração de prontuário para {instance.record_number}"
            event.updated_by = instance.updated_by
            event.save()


@receiver(post_save, sender=PatientAdmission)
def create_admission_discharge_events(sender, instance, created, **kwargs):
    """Create timeline events for admission and discharge"""
    
    # Create or update admission event
    admission_event, admission_created = AdmissionEvent.objects.get_or_create(
        admission=instance,
        defaults={
            'patient': instance.patient,
            'event_datetime': instance.admission_datetime,
            'description': f"Admissão hospitalar - {instance.get_admission_type_display()}",
            'created_by': instance.created_by,
            'updated_by': instance.updated_by,
        }
    )
    
    if not admission_created:
        # Update existing admission event
        admission_event.event_datetime = instance.admission_datetime
        admission_event.description = f"Admissão hospitalar - {instance.get_admission_type_display()}"
        admission_event.updated_by = instance.updated_by
        admission_event.save()
    
    # Handle discharge event
    if instance.discharge_datetime:
        # Create or update discharge event
        discharge_event, discharge_created = DischargeEvent.objects.get_or_create(
            admission=instance,
            defaults={
                'patient': instance.patient,
                'event_datetime': instance.discharge_datetime,
                'description': f"Alta hospitalar - {instance.get_discharge_type_display()}",
                'created_by': instance.created_by,
                'updated_by': instance.updated_by,
            }
        )
        
        if not discharge_created:
            # Update existing discharge event
            discharge_event.event_datetime = instance.discharge_datetime
            discharge_event.description = f"Alta hospitalar - {instance.get_discharge_type_display()}"
            discharge_event.updated_by = instance.updated_by
            discharge_event.save()
    else:
        # Remove discharge event if discharge was cancelled
        DischargeEvent.objects.filter(admission=instance).delete()


@receiver(post_delete, sender=PatientRecordNumber)
def delete_record_change_event(sender, instance, **kwargs):
    """Delete timeline event when record number is deleted"""
    RecordNumberChangeEvent.objects.filter(record_change=instance).delete()


@receiver(post_delete, sender=PatientAdmission)
def delete_admission_events(sender, instance, **kwargs):
    """Delete timeline events when admission is deleted"""
    AdmissionEvent.objects.filter(admission=instance).delete()
    DischargeEvent.objects.filter(admission=instance).delete()
```

### Step 2.8: Register Signal Handlers

**File**: `apps/patients/__init__.py`

```python
default_app_config = 'apps.patients.apps.PatientsConfig'
```

**File**: `apps/patients/apps.py`

```python
from django.apps import AppConfig


class PatientsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.patients'
    verbose_name = 'Patients'
    
    def ready(self):
        import apps.patients.signals  # Import signal handlers
```

### Step 2.9: Update Admin to Include Event Models

**File**: `apps/events/admin.py` - Add new event admins

```python
from .models import (
    Event, RecordNumberChangeEvent, AdmissionEvent, DischargeEvent
)

@admin.register(RecordNumberChangeEvent)
class RecordNumberChangeEventAdmin(admin.ModelAdmin):
    list_display = ['patient', 'event_datetime', 'old_record_number', 'new_record_number', 'created_by']
    list_filter = ['event_datetime', 'created_at']
    search_fields = ['patient__name', 'old_record_number', 'new_record_number']
    readonly_fields = ['event_type', 'created_at', 'updated_at']

@admin.register(AdmissionEvent)
class AdmissionEventAdmin(admin.ModelAdmin):
    list_display = ['patient', 'event_datetime', 'admission_type', 'initial_bed', 'created_by']
    list_filter = ['admission_type', 'event_datetime', 'created_at']
    search_fields = ['patient__name', 'admission_diagnosis']
    readonly_fields = ['event_type', 'created_at', 'updated_at']

@admin.register(DischargeEvent)
class DischargeEventAdmin(admin.ModelAdmin):
    list_display = ['patient', 'event_datetime', 'discharge_type', 'stay_duration_days', 'created_by']
    list_filter = ['discharge_type', 'event_datetime', 'created_at']
    search_fields = ['patient__name', 'discharge_diagnosis']
    readonly_fields = ['event_type', 'created_at', 'updated_at']
```

### Step 2.10: Create Database Tables for Events

**Commands to run:**

```bash
# Create migration for new event models
uv run python manage.py makemigrations events

# Apply migration
uv run python manage.py migrate
```

### Step 2.11: Test Event Integration

**File**: `apps/events/tests/test_record_tracking_events.py`

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.patients.models import Patient, PatientRecordNumber, PatientAdmission
from ..models import RecordNumberChangeEvent, AdmissionEvent, DischargeEvent

User = get_user_model()

class EventIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_record_number_creates_event(self):
        """Test that creating a record number creates a timeline event"""
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check that event was created
        event = RecordNumberChangeEvent.objects.filter(record_change=record).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.patient, self.patient)
        self.assertEqual(event.new_record_number, 'REC001')
    
    def test_admission_creates_events(self):
        """Test that admission and discharge create timeline events"""
        admission_time = timezone.now() - timedelta(days=2)
        discharge_time = timezone.now()
        
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=admission_time,
            discharge_datetime=discharge_time,
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check admission event
        admission_event = AdmissionEvent.objects.filter(admission=admission).first()
        self.assertIsNotNone(admission_event)
        self.assertEqual(admission_event.patient, self.patient)
        
        # Check discharge event
        discharge_event = DischargeEvent.objects.filter(admission=admission).first()
        self.assertIsNotNone(discharge_event)
        self.assertEqual(discharge_event.patient, self.patient)
        self.assertEqual(discharge_event.stay_duration_days, 2)
```

## Success Criteria

- ✅ New event types added to Event.EVENT_TYPE_CHOICES
- ✅ RecordNumberChangeEvent, AdmissionEvent, DischargeEvent models created
- ✅ Event card templates created for timeline display
- ✅ Timeline template updated to handle new event types
- ✅ Signal handlers created for automatic event creation
- ✅ Admin interfaces configured for new event models
- ✅ Database migrations created and applied
- ✅ Integration tests passing
- ✅ Events appear correctly in patient timeline
- ✅ Proper denormalization of display data in event models

## Next Phase

Continue to **Phase 3: Business Logic and Automation** to implement the business rules, validation, and automatic updates for maintaining data consistency.