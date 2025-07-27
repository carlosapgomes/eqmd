# Phase 4: User Interface and Forms

## Overview

Create user-friendly forms and templates for managing patient record numbers and admission/discharge processes, integrating with the existing UI patterns and restoring functionality from the previous multi-hospital implementation.

## Step-by-Step Implementation

### Step 4.1: Create Patient Record Number Forms

**File**: `apps/patients/forms.py` - Add record number forms

```python
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Patient, PatientRecordNumber, PatientAdmission
from .validators import validate_record_number_format

class PatientRecordNumberForm(forms.ModelForm):
    """Form for creating/updating patient record numbers"""
    
    class Meta:
        model = PatientRecordNumber
        fields = ['record_number', 'change_reason', 'effective_date']
        widgets = {
            'record_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: REC001, 123456, etc.'
            }),
            'change_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Motivo da alteração do número do prontuário...'
            }),
            'effective_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop('patient', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default effective date to now
        if not self.instance.pk:
            self.fields['effective_date'].initial = timezone.now()
    
    def clean_record_number(self):
        record_number = self.cleaned_data.get('record_number')
        if record_number:
            validate_record_number_format(record_number)
        return record_number
    
    def clean_effective_date(self):
        effective_date = self.cleaned_data.get('effective_date')
        if effective_date and effective_date > timezone.now():
            raise ValidationError("Data de vigência não pode ser no futuro")
        return effective_date
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.patient:
            instance.patient = self.patient
        if self.user:
            instance.created_by = self.user
            instance.updated_by = self.user
        
        # Always set as current when creating new record
        if not instance.pk:
            instance.is_current = True
            
            # Get previous record number for history
            current_record = self.patient.record_numbers.filter(is_current=True).first()
            if current_record:
                instance.previous_record_number = current_record.record_number
        
        if commit:
            instance.save()
        return instance

class QuickRecordNumberUpdateForm(forms.Form):
    """Quick form for updating just the record number"""
    
    record_number = forms.CharField(
        max_length=50,
        label="Novo Número do Prontuário",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite o novo número...'
        })
    )
    change_reason = forms.CharField(
        required=False,
        label="Motivo (opcional)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Motivo da alteração...'
        })
    )
    
    def clean_record_number(self):
        record_number = self.cleaned_data.get('record_number')
        if record_number:
            validate_record_number_format(record_number)
        return record_number
```

### Step 4.2: Create Admission/Discharge Forms

**File**: `apps/patients/forms.py` - Add admission forms

```python
class PatientAdmissionForm(forms.ModelForm):
    """Form for creating patient admissions"""
    
    class Meta:
        model = PatientAdmission
        fields = [
            'admission_datetime', 'admission_type', 'initial_bed',
            'admission_diagnosis'
        ]
        widgets = {
            'admission_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'admission_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'initial_bed': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: A101, UTI-02, etc.'
            }),
            'admission_diagnosis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Diagnóstico principal da admissão...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop('patient', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default admission time to now
        if not self.instance.pk:
            self.fields['admission_datetime'].initial = timezone.now()
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Check if patient is already admitted
        if self.patient and self.patient.is_currently_admitted():
            raise ValidationError("Paciente já está internado")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.patient:
            instance.patient = self.patient
        if self.user:
            instance.created_by = self.user
            instance.updated_by = self.user
        
        if commit:
            instance.save()
        return instance

class PatientDischargeForm(forms.ModelForm):
    """Form for discharging patients"""
    
    class Meta:
        model = PatientAdmission
        fields = [
            'discharge_datetime', 'discharge_type', 'final_bed',
            'discharge_diagnosis'
        ]
        widgets = {
            'discharge_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'discharge_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'final_bed': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: A101, UTI-02, etc.'
            }),
            'discharge_diagnosis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Diagnóstico final e condições da alta...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default discharge time to now
        if not self.instance.discharge_datetime:
            self.fields['discharge_datetime'].initial = timezone.now()
        
        # Pre-fill final bed with initial bed
        if self.instance.initial_bed and not self.instance.final_bed:
            self.fields['final_bed'].initial = self.instance.initial_bed
    
    def clean(self):
        cleaned_data = super().clean()
        
        if not self.instance.can_discharge():
            raise ValidationError("Esta internação não pode ser finalizada")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.updated_by = self.user
        
        if commit:
            instance.save()
        return instance

class QuickAdmissionForm(forms.Form):
    """Quick admission form for common scenarios"""
    
    admission_type = forms.ChoiceField(
        choices=PatientAdmission.AdmissionType.choices,
        label="Tipo de Admissão",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    initial_bed = forms.CharField(
        max_length=20,
        required=False,
        label="Leito",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: A101, UTI-02, etc.'
        })
    )
    admission_diagnosis = forms.CharField(
        required=False,
        label="Diagnóstico",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Diagnóstico principal...'
        })
    )

class QuickDischargeForm(forms.Form):
    """Quick discharge form for common scenarios"""
    
    discharge_type = forms.ChoiceField(
        choices=PatientAdmission.DischargeType.choices,
        label="Tipo de Alta",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    discharge_diagnosis = forms.CharField(
        required=False,
        label="Diagnóstico de Alta",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Condições da alta...'
        })
    )
```

### Step 4.3: Update Patient Form with Record Number

**File**: `apps/patients/forms.py` - Update existing PatientForm

```python
class PatientForm(forms.ModelForm):
    # ... existing fields ...
    
    # Add record number field to patient form
    initial_record_number = forms.CharField(
        max_length=50,
        required=False,
        label="Número do Prontuário",
        help_text="Número inicial do prontuário (pode ser alterado posteriormente)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: REC001, 123456, etc.'
        })
    )
    
    class Meta:
        model = Patient
        fields = [
            'name', 'birthday', 'healthcard_number', 'id_number', 'fiscal_number',
            'phone', 'address', 'city', 'state', 'zip_code', 'status', 'bed'
        ]
        # ... existing widget configuration ...
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If editing existing patient, show current record number
        if self.instance.pk:
            current_record = self.instance.record_numbers.filter(is_current=True).first()
            if current_record:
                self.fields['initial_record_number'].initial = current_record.record_number
    
    def save(self, commit=True):
        instance = super().save(commit=commit)
        
        # Handle initial record number for new patients
        if commit and self.cleaned_data.get('initial_record_number'):
            record_number = self.cleaned_data['initial_record_number']
            
            # Check if patient already has a current record number
            if not instance.record_numbers.filter(is_current=True).exists():
                PatientRecordNumber.objects.create(
                    patient=instance,
                    record_number=record_number,
                    change_reason="Registro inicial",
                    is_current=True,
                    created_by=getattr(instance, '_current_user', None),
                    updated_by=getattr(instance, '_current_user', None)
                )
        
        return instance
```

### Step 4.4: Create Record Number Management Templates

**File**: `apps/patients/templates/patients/record_number_form.html`

```html
{% extends "base_app.html" %}
{% load hospital_tags %}

{% block title %}{% if form.instance.pk %}Editar{% else %}Novo{% endif %} Número de Prontuário - {% hospital_name %}{% endblock %}

{% block app_content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h2>{% if form.instance.pk %}Editar{% else %}Novo{% endif %} Número de Prontuário</h2>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item"><a href="{% url 'apps.core:dashboard' %}">Dashboard</a></li>
                            <li class="breadcrumb-item"><a href="{% url 'apps.patients:patient_list' %}">Pacientes</a></li>
                            <li class="breadcrumb-item"><a href="{% url 'apps.patients:patient_detail' patient.pk %}">{{ patient.name }}</a></li>
                            <li class="breadcrumb-item active">Número de Prontuário</li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <a href="{% url 'apps.patients:patient_detail' patient.pk %}" class="btn btn-outline-secondary">
                        <i class="fas fa-arrow-left"></i> Voltar
                    </a>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-file-medical"></i>
                        Informações do Prontuário
                    </h5>
                </div>
                <div class="card-body">
                    <form method="post">
                        {% csrf_token %}
                        
                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label for="{{ form.record_number.id_for_label }}" class="form-label">
                                        {{ form.record_number.label }}
                                        {% if form.record_number.field.required %}<span class="text-danger">*</span>{% endif %}
                                    </label>
                                    {{ form.record_number }}
                                    {% if form.record_number.help_text %}
                                        <div class="form-text">{{ form.record_number.help_text }}</div>
                                    {% endif %}
                                    {% if form.record_number.errors %}
                                        <div class="invalid-feedback d-block">{{ form.record_number.errors.0 }}</div>
                                    {% endif %}
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label for="{{ form.effective_date.id_for_label }}" class="form-label">
                                        {{ form.effective_date.label }}
                                        {% if form.effective_date.field.required %}<span class="text-danger">*</span>{% endif %}
                                    </label>
                                    {{ form.effective_date }}
                                    {% if form.effective_date.help_text %}
                                        <div class="form-text">{{ form.effective_date.help_text }}</div>
                                    {% endif %}
                                    {% if form.effective_date.errors %}
                                        <div class="invalid-feedback d-block">{{ form.effective_date.errors.0 }}</div>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <label for="{{ form.change_reason.id_for_label }}" class="form-label">
                                {{ form.change_reason.label }}
                            </label>
                            {{ form.change_reason }}
                            {% if form.change_reason.help_text %}
                                <div class="form-text">{{ form.change_reason.help_text }}</div>
                            {% endif %}
                            {% if form.change_reason.errors %}
                                <div class="invalid-feedback d-block">{{ form.change_reason.errors.0 }}</div>
                            {% endif %}
                        </div>
                        
                        <div class="d-flex justify-content-end gap-2">
                            <a href="{% url 'apps.patients:patient_detail' patient.pk %}" class="btn btn-outline-secondary">
                                Cancelar
                            </a>
                            <button type="submit" class="btn btn-medical-primary">
                                <i class="fas fa-save"></i>
                                {% if form.instance.pk %}Atualizar{% else %}Criar{% endif %}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h6 class="card-title mb-0">
                        <i class="fas fa-info-circle"></i>
                        Informações do Paciente
                    </h6>
                </div>
                <div class="card-body">
                    <p><strong>Nome:</strong> {{ patient.name }}</p>
                    <p><strong>Status:</strong> {% include "patients/partials/patient_status_badge.html" %}</p>
                    {% if patient.current_record_number %}
                        <p><strong>Prontuário Atual:</strong> 
                            <span class="badge bg-primary">{{ patient.current_record_number }}</span>
                        </p>
                    {% endif %}
                    {% if patient.bed %}
                        <p><strong>Leito:</strong> {{ patient.bed }}</p>
                    {% endif %}
                </div>
            </div>
            
            {% if patient.record_numbers.all %}
            <div class="card mt-3">
                <div class="card-header">
                    <h6 class="card-title mb-0">
                        <i class="fas fa-history"></i>
                        Histórico de Prontuários
                    </h6>
                </div>
                <div class="card-body">
                    {% for record in patient.record_numbers.all %}
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <div>
                                <span class="badge {% if record.is_current %}bg-primary{% else %}bg-secondary{% endif %}">
                                    {{ record.record_number }}
                                </span>
                                {% if record.is_current %}<small class="text-muted">(atual)</small>{% endif %}
                            </div>
                            <small class="text-muted">
                                {{ record.effective_date|date:"d/m/Y H:i" }}
                            </small>
                        </div>
                        {% if record.change_reason %}
                            <small class="text-muted d-block mb-2">{{ record.change_reason }}</small>
                        {% endif %}
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock app_content %}
```

### Step 4.5: Create Admission/Discharge Templates

**File**: `apps/patients/templates/patients/admission_form.html`

```html
{% extends "base_app.html" %}
{% load hospital_tags %}

{% block title %}{% if form.instance.pk %}Editar{% else %}Nova{% endif %} Internação - {% hospital_name %}{% endblock %}

{% block app_content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h2>{% if form.instance.pk %}Editar{% else %}Nova{% endif %} Internação</h2>
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item"><a href="{% url 'apps.core:dashboard' %}">Dashboard</a></li>
                            <li class="breadcrumb-item"><a href="{% url 'apps.patients:patient_list' %}">Pacientes</a></li>
                            <li class="breadcrumb-item"><a href="{% url 'apps.patients:patient_detail' patient.pk %}">{{ patient.name }}</a></li>
                            <li class="breadcrumb-item active">Internação</li>
                        </ol>
                    </nav>
                </div>
                <div>
                    <a href="{% url 'apps.patients:patient_detail' patient.pk %}" class="btn btn-outline-secondary">
                        <i class="fas fa-arrow-left"></i> Voltar
                    </a>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-bed"></i>
                        Informações da Internação
                    </h5>
                </div>
                <div class="card-body">
                    <form method="post">
                        {% csrf_token %}
                        
                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label for="{{ form.admission_datetime.id_for_label }}" class="form-label">
                                        {{ form.admission_datetime.label }}
                                        <span class="text-danger">*</span>
                                    </label>
                                    {{ form.admission_datetime }}
                                    {% if form.admission_datetime.errors %}
                                        <div class="invalid-feedback d-block">{{ form.admission_datetime.errors.0 }}</div>
                                    {% endif %}
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label for="{{ form.admission_type.id_for_label }}" class="form-label">
                                        {{ form.admission_type.label }}
                                        <span class="text-danger">*</span>
                                    </label>
                                    {{ form.admission_type }}
                                    {% if form.admission_type.errors %}
                                        <div class="invalid-feedback d-block">{{ form.admission_type.errors.0 }}</div>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <label for="{{ form.initial_bed.id_for_label }}" class="form-label">
                                {{ form.initial_bed.label }}
                            </label>
                            {{ form.initial_bed }}
                            {% if form.initial_bed.help_text %}
                                <div class="form-text">{{ form.initial_bed.help_text }}</div>
                            {% endif %}
                            {% if form.initial_bed.errors %}
                                <div class="invalid-feedback d-block">{{ form.initial_bed.errors.0 }}</div>
                            {% endif %}
                        </div>
                        
                        <div class="mb-3">
                            <label for="{{ form.admission_diagnosis.id_for_label }}" class="form-label">
                                {{ form.admission_diagnosis.label }}
                            </label>
                            {{ form.admission_diagnosis }}
                            {% if form.admission_diagnosis.help_text %}
                                <div class="form-text">{{ form.admission_diagnosis.help_text }}</div>
                            {% endif %}
                            {% if form.admission_diagnosis.errors %}
                                <div class="invalid-feedback d-block">{{ form.admission_diagnosis.errors.0 }}</div>
                            {% endif %}
                        </div>
                        
                        <div class="d-flex justify-content-end gap-2">
                            <a href="{% url 'apps.patients:patient_detail' patient.pk %}" class="btn btn-outline-secondary">
                                Cancelar
                            </a>
                            <button type="submit" class="btn btn-medical-primary">
                                <i class="fas fa-save"></i>
                                {% if form.instance.pk %}Atualizar{% else %}Internar{% endif %}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            {% include "patients/partials/patient_info_sidebar.html" %}
        </div>
    </div>
</div>
{% endblock app_content %}
```

### Step 4.6: Update Patient Detail Template

**File**: `apps/patients/templates/patients/patient_detail.html` - Add record tracking sections

```html
<!-- Add to existing patient detail template -->

<!-- Record Number Section -->
<div class="row mb-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0">
                    <i class="fas fa-file-medical"></i>
                    Número do Prontuário
                </h5>
                {% if perms.patients.add_patientrecordnumber %}
                    <a href="{% url 'apps.patients:record_number_create' patient.pk %}" class="btn btn-medical-outline-primary btn-sm">
                        <i class="fas fa-plus"></i> Alterar Número
                    </a>
                {% endif %}
            </div>
            <div class="card-body">
                {% if patient.current_record_number %}
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">Número Atual</h6>
                            <span class="badge bg-primary fs-6">{{ patient.current_record_number }}</span>
                        </div>
                        <div class="text-end">
                            {% with current_record=patient.record_numbers.filter:is_current=True|first %}
                                {% if current_record %}
                                    <small class="text-muted">
                                        Vigente desde {{ current_record.effective_date|date:"d/m/Y H:i" }}
                                    </small>
                                {% endif %}
                            {% endwith %}
                        </div>
                    </div>
                    
                    {% if patient.record_numbers.count > 1 %}
                        <hr>
                        <h6 class="mb-2">Histórico de Alterações</h6>
                        <div class="row">
                            {% for record in patient.record_numbers.all %}
                                {% if not record.is_current %}
                                    <div class="col-md-6 mb-2">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <span class="badge bg-secondary">{{ record.record_number }}</span>
                                            <small class="text-muted">{{ record.effective_date|date:"d/m/Y" }}</small>
                                        </div>
                                        {% if record.change_reason %}
                                            <small class="text-muted">{{ record.change_reason|truncatewords:10 }}</small>
                                        {% endif %}
                                    </div>
                                {% endif %}
                            {% endfor %}
                        </div>
                    {% endif %}
                {% else %}
                    <div class="text-center text-muted py-3">
                        <i class="fas fa-file-medical fa-2x mb-2"></i>
                        <p>Nenhum número de prontuário registrado</p>
                        {% if perms.patients.add_patientrecordnumber %}
                            <a href="{% url 'apps.patients:record_number_create' patient.pk %}" class="btn btn-medical-primary btn-sm">
                                <i class="fas fa-plus"></i> Adicionar Número
                            </a>
                        {% endif %}
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<!-- Admission Status Section -->
<div class="row mb-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0">
                    <i class="fas fa-bed"></i>
                    Status de Internação
                </h5>
                <div>
                    {% if patient.is_currently_admitted %}
                        {% if perms.patients.change_patientadmission %}
                            <a href="{% url 'apps.patients:discharge_patient' patient.current_admission_id %}" class="btn btn-outline-warning btn-sm">
                                <i class="fas fa-sign-out-alt"></i> Dar Alta
                            </a>
                        {% endif %}
                    {% else %}
                        {% if perms.patients.add_patientadmission %}
                            <a href="{% url 'apps.patients:admit_patient' patient.pk %}" class="btn btn-medical-primary btn-sm">
                                <i class="fas fa-bed"></i> Internar
                            </a>
                        {% endif %}
                    {% endif %}
                </div>
            </div>
            <div class="card-body">
                {% if patient.is_currently_admitted %}
                    {% with current_admission=patient.get_current_admission %}
                        <div class="row">
                            <div class="col-md-6">
                                <h6 class="text-success mb-1">
                                    <i class="fas fa-bed"></i> Paciente Internado
                                </h6>
                                <p class="mb-1">
                                    <strong>Desde:</strong> {{ current_admission.admission_datetime|date:"d/m/Y H:i" }}
                                </p>
                                <p class="mb-1">
                                    <strong>Tipo:</strong> {{ current_admission.get_admission_type_display }}
                                </p>
                                {% if current_admission.initial_bed %}
                                    <p class="mb-1">
                                        <strong>Leito:</strong> {{ current_admission.initial_bed }}
                                    </p>
                                {% endif %}
                            </div>
                            <div class="col-md-6">
                                {% with duration=current_admission.calculate_current_duration %}
                                    {% if duration %}
                                        <h6 class="mb-1">Duração da Internação</h6>
                                        <p class="mb-1">
                                            <span class="badge bg-info">{{ duration.days }} dias</span>
                                            <span class="badge bg-outline-info">{{ duration.hours }} horas</span>
                                        </p>
                                    {% endif %}
                                {% endwith %}
                                {% if current_admission.admission_diagnosis %}
                                    <p class="mb-1">
                                        <strong>Diagnóstico:</strong> {{ current_admission.admission_diagnosis|truncatewords:15 }}
                                    </p>
                                {% endif %}
                            </div>
                        </div>
                    {% endwith %}
                {% else %}
                    <div class="text-center text-muted py-3">
                        <i class="fas fa-home fa-2x mb-2"></i>
                        <p>Paciente não está internado</p>
                        {% if patient.last_discharge_date %}
                            <small>Última alta: {{ patient.last_discharge_date|date:"d/m/Y" }}</small>
                        {% endif %}
                    </div>
                {% endif %}
                
                <!-- Admission Statistics -->
                {% if patient.total_admissions_count > 0 %}
                    <hr>
                    <div class="row text-center">
                        <div class="col-md-4">
                            <h6 class="text-muted mb-1">Total de Internações</h6>
                            <span class="badge bg-primary fs-6">{{ patient.total_admissions_count }}</span>
                        </div>
                        <div class="col-md-4">
                            <h6 class="text-muted mb-1">Total de Dias</h6>
                            <span class="badge bg-secondary fs-6">{{ patient.total_inpatient_days }}</span>
                        </div>
                        <div class="col-md-4">
                            <h6 class="text-muted mb-1">Média por Internação</h6>
                            <span class="badge bg-outline-primary fs-6">
                                {% widthratio patient.total_inpatient_days patient.total_admissions_count 1 %} dias
                            </span>
                        </div>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<!-- Admission History Section -->
{% if patient.admissions.all %}
<div class="row mb-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">
                    <i class="fas fa-history"></i>
                    Histórico de Internações
                </h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Admissão</th>
                                <th>Alta</th>
                                <th>Tipo</th>
                                <th>Duração</th>
                                <th>Leito</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for admission in patient.admissions.all %}
                                <tr {% if admission.is_active %}class="table-success"{% endif %}>
                                    <td>
                                        {{ admission.admission_datetime|date:"d/m/Y H:i" }}
                                        <br>
                                        <small class="text-muted">{{ admission.get_admission_type_display }}</small>
                                    </td>
                                    <td>
                                        {% if admission.discharge_datetime %}
                                            {{ admission.discharge_datetime|date:"d/m/Y H:i" }}
                                            <br>
                                            <small class="text-muted">{{ admission.get_discharge_type_display }}</small>
                                        {% else %}
                                            <span class="badge bg-success">Ativo</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        <span class="badge {% if admission.admission_type == 'emergency' %}bg-danger{% elif admission.admission_type == 'scheduled' %}bg-primary{% else %}bg-secondary{% endif %}">
                                            {{ admission.get_admission_type_display }}
                                        </span>
                                    </td>
                                    <td>
                                        {% if admission.stay_duration_days %}
                                            {{ admission.stay_duration_days }} dias
                                        {% elif admission.is_active %}
                                            {% with duration=admission.calculate_current_duration %}
                                                {{ duration.days }} dias (ativo)
                                            {% endwith %}
                                        {% else %}
                                            -
                                        {% endif %}
                                    </td>
                                    <td>
                                        {% if admission.initial_bed %}
                                            {{ admission.initial_bed }}
                                            {% if admission.final_bed and admission.final_bed != admission.initial_bed %}
                                                → {{ admission.final_bed }}
                                            {% endif %}
                                        {% else %}
                                            -
                                        {% endif %}
                                    </td>
                                    <td>
                                        {% if admission.is_active and perms.patients.change_patientadmission %}
                                            <a href="{% url 'apps.patients:discharge_patient' admission.pk %}" 
                                               class="btn btn-outline-warning btn-sm" title="Dar Alta">
                                                <i class="fas fa-sign-out-alt"></i>
                                            </a>
                                        {% endif %}
                                        {% if perms.patients.change_patientadmission %}
                                            <a href="{% url 'apps.patients:admission_update' admission.pk %}" 
                                               class="btn btn-outline-secondary btn-sm" title="Editar">
                                                <i class="fas fa-edit"></i>
                                            </a>
                                        {% endif %}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
{% endif %}
```

### Step 4.7: Create Quick Action Components

**File**: `apps/patients/templates/patients/partials/quick_actions.html`

```html
<!-- Quick Actions Component for Patient Detail -->
<div class="card">
    <div class="card-header">
        <h6 class="card-title mb-0">
            <i class="fas fa-bolt"></i>
            Ações Rápidas
        </h6>
    </div>
    <div class="card-body">
        <!-- Record Number Quick Update -->
        {% if perms.patients.add_patientrecordnumber %}
            <div class="mb-3">
                <form method="post" action="{% url 'apps.patients:quick_record_number_update' patient.pk %}" class="quick-form">
                    {% csrf_token %}
                    <label class="form-label">Atualizar Prontuário</label>
                    <div class="input-group input-group-sm">
                        <input type="text" name="record_number" class="form-control" 
                               placeholder="Novo número..." maxlength="50" required>
                        <button type="submit" class="btn btn-medical-outline-primary">
                            <i class="fas fa-save"></i>
                        </button>
                    </div>
                </form>
            </div>
        {% endif %}
        
        <!-- Quick Admission -->
        {% if not patient.is_currently_admitted and perms.patients.add_patientadmission %}
            <div class="mb-3">
                <form method="post" action="{% url 'apps.patients:quick_admit_patient' patient.pk %}" class="quick-form">
                    {% csrf_token %}
                    <label class="form-label">Internação Rápida</label>
                    <div class="row g-1">
                        <div class="col-8">
                            <select name="admission_type" class="form-select form-select-sm" required>
                                <option value="">Tipo...</option>
                                <option value="emergency">Emergência</option>
                                <option value="scheduled">Programada</option>
                                <option value="transfer">Transferência</option>
                            </select>
                        </div>
                        <div class="col-4">
                            <button type="submit" class="btn btn-medical-primary btn-sm w-100">
                                <i class="fas fa-bed"></i>
                            </button>
                        </div>
                    </div>
                    <input type="text" name="initial_bed" class="form-control form-control-sm mt-1" 
                           placeholder="Leito (opcional)">
                </form>
            </div>
        {% endif %}
        
        <!-- Quick Discharge -->
        {% if patient.is_currently_admitted and perms.patients.change_patientadmission %}
            <div class="mb-3">
                <form method="post" action="{% url 'apps.patients:quick_discharge_patient' patient.current_admission_id %}" class="quick-form">
                    {% csrf_token %}
                    <label class="form-label">Alta Rápida</label>
                    <div class="row g-1">
                        <div class="col-8">
                            <select name="discharge_type" class="form-select form-select-sm" required>
                                <option value="">Tipo...</option>
                                <option value="medical">Alta Médica</option>
                                <option value="administrative">Administrativa</option>
                                <option value="transfer_out">Transferência</option>
                                <option value="request">A Pedido</option>
                            </select>
                        </div>
                        <div class="col-4">
                            <button type="submit" class="btn btn-outline-warning btn-sm w-100">
                                <i class="fas fa-sign-out-alt"></i>
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        {% endif %}
        
        <hr>
        
        <!-- Links to Full Forms -->
        <div class="d-grid gap-1">
            {% if perms.patients.add_patientrecordnumber %}
                <a href="{% url 'apps.patients:record_number_create' patient.pk %}" class="btn btn-outline-primary btn-sm">
                    <i class="fas fa-file-medical"></i> Alterar Prontuário
                </a>
            {% endif %}
            
            {% if not patient.is_currently_admitted and perms.patients.add_patientadmission %}
                <a href="{% url 'apps.patients:admit_patient' patient.pk %}" class="btn btn-medical-outline-primary btn-sm">
                    <i class="fas fa-bed"></i> Internar Paciente
                </a>
            {% endif %}
            
            {% if patient.is_currently_admitted and perms.patients.change_patientadmission %}
                <a href="{% url 'apps.patients:discharge_patient' patient.current_admission_id %}" class="btn btn-outline-warning btn-sm">
                    <i class="fas fa-sign-out-alt"></i> Dar Alta
                </a>
            {% endif %}
        </div>
    </div>
</div>

<style>
.quick-form {
    margin: 0;
}

.quick-form .form-control:focus,
.quick-form .form-select:focus {
    box-shadow: 0 0 0 0.1rem rgba(var(--bs-primary-rgb), 0.25);
}
</style>
```

## Success Criteria

- ✅ Comprehensive forms for record number management
- ✅ Forms for admission and discharge processes
- ✅ Updated patient form with initial record number support
- ✅ Professional templates matching existing UI patterns
- ✅ Patient detail template enhanced with record tracking sections
- ✅ Quick action components for common operations
- ✅ Proper form validation and error handling
- ✅ Responsive design working on mobile devices
- ✅ Integration with existing permission system
- ✅ User-friendly interfaces with clear navigation
- ✅ Historical data display and management

## Next Phase

Continue to **Phase 5: API and Integration** to restore and update the API endpoints and integrate with existing search and listing functionality.