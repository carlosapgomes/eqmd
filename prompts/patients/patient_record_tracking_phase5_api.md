# Phase 5: API and Integration

## Overview

Restore and update API endpoints, integrate with existing search functionality, update URL patterns, and create views for the new record tracking functionality.

## Step-by-Step Implementation

### Step 5.1: Create URL Patterns

**File**: `apps/patients/urls.py` - Restore and update URL patterns

```python
from django.urls import path
from . import views

app_name = 'apps.patients'

urlpatterns = [
    # Existing patient URLs
    path('', views.PatientListView.as_view(), name='patient_list'),
    path('<uuid:pk>/', views.PatientDetailView.as_view(), name='patient_detail'),
    path('create/', views.PatientCreateView.as_view(), name='patient_create'),
    path('<uuid:pk>/edit/', views.PatientUpdateView.as_view(), name='patient_update'),
    path('<uuid:pk>/delete/', views.PatientDeleteView.as_view(), name='patient_delete'),

    # Patient Record Number URLs
    path(
        '<uuid:patient_id>/record-number/create/',
        views.PatientRecordNumberCreateView.as_view(),
        name='record_number_create'
    ),
    path(
        'record-number/<uuid:pk>/edit/',
        views.PatientRecordNumberUpdateView.as_view(),
        name='record_number_update'
    ),
    path(
        'record-number/<uuid:pk>/delete/',
        views.PatientRecordNumberDeleteView.as_view(),
        name='record_number_delete'
    ),
    path(
        '<uuid:patient_id>/record-number/quick-update/',
        views.QuickRecordNumberUpdateView.as_view(),
        name='quick_record_number_update'
    ),

    # Patient Admission URLs
    path(
        '<uuid:patient_id>/admit/',
        views.PatientAdmissionCreateView.as_view(),
        name='admit_patient'
    ),
    path(
        'admission/<uuid:pk>/edit/',
        views.PatientAdmissionUpdateView.as_view(),
        name='admission_update'
    ),
    path(
        'admission/<uuid:pk>/discharge/',
        views.PatientDischargeView.as_view(),
        name='discharge_patient'
    ),
    path(
        '<uuid:patient_id>/quick-admit/',
        views.QuickAdmissionView.as_view(),
        name='quick_admit_patient'
    ),
    path(
        'admission/<uuid:admission_id>/quick-discharge/',
        views.QuickDischargeView.as_view(),
        name='quick_discharge_patient'
    ),

    # Tag management URLs (existing)
    path('tags/', views.AllowedTagListView.as_view(), name='tag_list'),
    path('tags/create/', views.AllowedTagCreateView.as_view(), name='tag_create'),
    path('tags/<int:pk>/edit/', views.AllowedTagUpdateView.as_view(), name='tag_update'),
    path('tags/<int:pk>/delete/', views.AllowedTagDeleteView.as_view(), name='tag_delete'),

    # API URLs - Restored and updated
    path(
        'api/<uuid:patient_id>/record-numbers/',
        views.PatientRecordNumbersAPIView.as_view(),
        name='api_patient_record_numbers'
    ),
    path(
        'api/<uuid:patient_id>/admissions/',
        views.PatientAdmissionsAPIView.as_view(),
        name='api_patient_admissions'
    ),
    path(
        'api/record-number/<str:record_number>/',
        views.RecordNumberLookupAPIView.as_view(),
        name='api_record_number_lookup'
    ),
    path(
        'api/admission/<uuid:admission_id>/',
        views.AdmissionDetailAPIView.as_view(),
        name='api_admission_detail'
    ),
    path(
        'api/patients/search/',
        views.PatientSearchAPIView.as_view(),
        name='api_patient_search'
    ),
]
```

### Step 5.2: Create Record Number Views

**File**: `apps/patients/views.py` - Add record number views

```python
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Patient, PatientRecordNumber, PatientAdmission
from .forms import (
    PatientRecordNumberForm, QuickRecordNumberUpdateForm,
    PatientAdmissionForm, PatientDischargeForm,
    QuickAdmissionForm, QuickDischargeForm
)

class PatientRecordNumberCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create new patient record number"""
    model = PatientRecordNumber
    form_class = PatientRecordNumberForm
    template_name = 'patients/record_number_form.html'
    permission_required = 'patients.add_patientrecordnumber'

    def dispatch(self, request, *args, **kwargs):
        self.patient = get_object_or_404(Patient, pk=kwargs['patient_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['patient'] = self.patient
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        return context

    def form_valid(self, form):
        try:
            # Use the patient model method for proper record number update
            record_number = form.cleaned_data['record_number']
            reason = form.cleaned_data.get('change_reason', '')
            effective_date = form.cleaned_data.get('effective_date', timezone.now())

            new_record = self.patient.update_current_record_number(
                record_number=record_number,
                user=self.request.user,
                reason=reason,
                effective_date=effective_date
            )

            messages.success(
                self.request,
                f'Número de prontuário atualizado para {record_number} com sucesso.'
            )
            return redirect('patients:patient_detail', pk=self.patient.pk)

        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)

class PatientRecordNumberUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Update existing patient record number"""
    model = PatientRecordNumber
    form_class = PatientRecordNumberForm
    template_name = 'patients/record_number_form.html'
    permission_required = 'patients.change_patientrecordnumber'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['patient'] = self.object.patient
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        return context

    def get_success_url(self):
        messages.success(self.request, 'Número de prontuário atualizado com sucesso.')
        return reverse('patients:patient_detail', kwargs={'pk': self.object.patient.pk})

class PatientRecordNumberDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Delete patient record number"""
    model = PatientRecordNumber
    template_name = 'patients/record_number_confirm_delete.html'
    permission_required = 'patients.delete_patientrecordnumber'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        return context

    def get_success_url(self):
        messages.success(self.request, 'Número de prontuário removido com sucesso.')
        return reverse('patients:patient_detail', kwargs={'pk': self.object.patient.pk})

class QuickRecordNumberUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Quick record number update via AJAX/form submission"""
    permission_required = 'patients.add_patientrecordnumber'

    def post(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id)
        form = QuickRecordNumberUpdateForm(request.POST)

        if form.is_valid():
            try:
                record_number = form.cleaned_data['record_number']
                reason = form.cleaned_data.get('change_reason', 'Atualização rápida')

                patient.update_current_record_number(
                    record_number=record_number,
                    user=request.user,
                    reason=reason
                )

                messages.success(request, f'Prontuário atualizado para {record_number}.')

            except ValidationError as e:
                messages.error(request, f'Erro ao atualizar prontuário: {str(e)}')
        else:
            messages.error(request, 'Dados inválidos para atualização do prontuário.')

        return redirect('patients:patient_detail', pk=patient_id)
```

### Step 5.3: Create Admission/Discharge Views

**File**: `apps/patients/views.py` - Add admission views

```python
class PatientAdmissionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create new patient admission"""
    model = PatientAdmission
    form_class = PatientAdmissionForm
    template_name = 'patients/admission_form.html'
    permission_required = 'patients.add_patientadmission'

    def dispatch(self, request, *args, **kwargs):
        self.patient = get_object_or_404(Patient, pk=kwargs['patient_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['patient'] = self.patient
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        return context

    def form_valid(self, form):
        try:
            # Use the patient model method for proper admission
            admission = self.patient.admit_patient(
                admission_datetime=form.cleaned_data['admission_datetime'],
                admission_type=form.cleaned_data['admission_type'],
                user=self.request.user,
                initial_bed=form.cleaned_data.get('initial_bed', ''),
                admission_diagnosis=form.cleaned_data.get('admission_diagnosis', '')
            )

            messages.success(
                self.request,
                f'Paciente internado com sucesso. Admissão registrada.'
            )
            return redirect('patients:patient_detail', pk=self.patient.pk)

        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)

class PatientAdmissionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Update existing patient admission"""
    model = PatientAdmission
    form_class = PatientAdmissionForm
    template_name = 'patients/admission_form.html'
    permission_required = 'patients.change_patientadmission'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['patient'] = self.object.patient
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        return context

    def get_success_url(self):
        messages.success(self.request, 'Internação atualizada com sucesso.')
        return reverse('patients:patient_detail', kwargs={'pk': self.object.patient.pk})

class PatientDischargeView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Discharge patient by updating admission record"""
    model = PatientAdmission
    form_class = PatientDischargeForm
    template_name = 'patients/discharge_form.html'
    permission_required = 'patients.change_patientadmission'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        context['admission'] = self.object
        return context

    def form_valid(self, form):
        try:
            # Use the patient model method for proper discharge
            discharge_datetime = form.cleaned_data['discharge_datetime']
            discharge_type = form.cleaned_data['discharge_type']

            self.object.patient.discharge_patient(
                discharge_datetime=discharge_datetime,
                discharge_type=discharge_type,
                user=self.request.user,
                final_bed=form.cleaned_data.get('final_bed', ''),
                discharge_diagnosis=form.cleaned_data.get('discharge_diagnosis', '')
            )

            messages.success(
                self.request,
                f'Paciente recebeu alta com sucesso. Tipo: {form.cleaned_data["discharge_type"]}'
            )
            return redirect('patients:patient_detail', pk=self.object.patient.pk)

        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)

class QuickAdmissionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Quick admission via form submission"""
    permission_required = 'patients.add_patientadmission'

    def post(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id)
        form = QuickAdmissionForm(request.POST)

        if form.is_valid():
            try:
                admission = patient.admit_patient(
                    admission_datetime=timezone.now(),
                    admission_type=form.cleaned_data['admission_type'],
                    user=request.user,
                    initial_bed=form.cleaned_data.get('initial_bed', ''),
                    admission_diagnosis=form.cleaned_data.get('admission_diagnosis', '')
                )

                messages.success(
                    request,
                    f'Paciente internado rapidamente. Tipo: {admission.get_admission_type_display()}'
                )

            except ValidationError as e:
                messages.error(request, f'Erro na internação: {str(e)}')
        else:
            messages.error(request, 'Dados inválidos para internação.')

        return redirect('patients:patient_detail', pk=patient_id)

class QuickDischargeView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Quick discharge via form submission"""
    permission_required = 'patients.change_patientadmission'

    def post(self, request, admission_id):
        admission = get_object_or_404(PatientAdmission, pk=admission_id)
        form = QuickDischargeForm(request.POST)

        if form.is_valid():
            try:
                admission.patient.discharge_patient(
                    discharge_datetime=timezone.now(),
                    discharge_type=form.cleaned_data['discharge_type'],
                    user=request.user,
                    discharge_diagnosis=form.cleaned_data.get('discharge_diagnosis', '')
                )

                messages.success(
                    request,
                    f'Alta rápida registrada. Tipo: {form.cleaned_data["discharge_type"]}'
                )

            except ValidationError as e:
                messages.error(request, f'Erro na alta: {str(e)}')
        else:
            messages.error(request, 'Dados inválidos para alta.')

        return redirect('patients:patient_detail', pk=admission.patient.pk)
```

### Step 5.4: Create API Views

**File**: `apps/patients/views.py` - Add API views

```python
from django.http import JsonResponse
from django.views import View
from django.core.serializers import serialize
from django.core.paginator import Paginator
from django.db.models import Q
import json

class PatientRecordNumbersAPIView(LoginRequiredMixin, View):
    """API view for patient record numbers"""

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id)

        # Check permissions
        if not request.user.has_perm('patients.view_patientrecordnumber'):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        records = patient.record_numbers.all().order_by('-effective_date')

        data = {
            'patient_id': str(patient.pk),
            'patient_name': patient.name,
            'current_record_number': patient.current_record_number,
            'records': []
        }

        for record in records:
            data['records'].append({
                'id': str(record.pk),
                'record_number': record.record_number,
                'is_current': record.is_current,
                'previous_record_number': record.previous_record_number,
                'change_reason': record.change_reason,
                'effective_date': record.effective_date.isoformat(),
                'created_at': record.created_at.isoformat(),
                'created_by': record.created_by.get_full_name() or record.created_by.username,
            })

        return JsonResponse(data)

class PatientAdmissionsAPIView(LoginRequiredMixin, View):
    """API view for patient admissions"""

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id)

        # Check permissions
        if not request.user.has_perm('patients.view_patientadmission'):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        admissions = patient.admissions.all().order_by('-admission_datetime')

        data = {
            'patient_id': str(patient.pk),
            'patient_name': patient.name,
            'is_currently_admitted': patient.is_currently_admitted(),
            'current_admission_id': str(patient.current_admission_id) if patient.current_admission_id else None,
            'total_admissions': patient.total_admissions_count,
            'total_inpatient_days': patient.total_inpatient_days,
            'admissions': []
        }

        for admission in admissions:
            admission_data = {
                'id': str(admission.pk),
                'admission_datetime': admission.admission_datetime.isoformat(),
                'admission_type': admission.admission_type,
                'admission_type_display': admission.get_admission_type_display(),
                'initial_bed': admission.initial_bed,
                'admission_diagnosis': admission.admission_diagnosis,
                'is_active': admission.is_active,
                'created_by': admission.created_by.get_full_name() or admission.created_by.username,
            }

            if admission.discharge_datetime:
                admission_data.update({
                    'discharge_datetime': admission.discharge_datetime.isoformat(),
                    'discharge_type': admission.discharge_type,
                    'discharge_type_display': admission.get_discharge_type_display(),
                    'final_bed': admission.final_bed,
                    'discharge_diagnosis': admission.discharge_diagnosis,
                    'stay_duration_days': admission.stay_duration_days,
                    'stay_duration_hours': admission.stay_duration_hours,
                })
            else:
                # Calculate current duration for active admission
                current_duration = admission.calculate_current_duration()
                if current_duration:
                    admission_data['current_duration'] = current_duration

            data['admissions'].append(admission_data)

        return JsonResponse(data)

class RecordNumberLookupAPIView(LoginRequiredMixin, View):
    """API view for looking up patients by record number"""

    def get(self, request, record_number):
        # Check permissions
        if not request.user.has_perm('patients.view_patient'):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        # Find current record with this number
        current_record = PatientRecordNumber.objects.filter(
            record_number=record_number,
            is_current=True
        ).select_related('patient').first()

        if current_record:
            patient = current_record.patient
            data = {
                'found': True,
                'patient': {
                    'id': str(patient.pk),
                    'name': patient.name,
                    'current_record_number': patient.current_record_number,
                    'status': patient.get_status_display(),
                    'is_currently_admitted': patient.is_currently_admitted(),
                    'bed': patient.bed,
                }
            }
        else:
            # Check historical records
            historical_record = PatientRecordNumber.objects.filter(
                record_number=record_number,
                is_current=False
            ).select_related('patient').first()

            if historical_record:
                patient = historical_record.patient
                data = {
                    'found': True,
                    'is_historical': True,
                    'patient': {
                        'id': str(patient.pk),
                        'name': patient.name,
                        'current_record_number': patient.current_record_number,
                        'historical_record_number': record_number,
                        'status': patient.get_status_display(),
                    }
                }
            else:
                data = {'found': False}

        return JsonResponse(data)

class AdmissionDetailAPIView(LoginRequiredMixin, View):
    """API view for admission details"""

    def get(self, request, admission_id):
        admission = get_object_or_404(PatientAdmission, pk=admission_id)

        # Check permissions
        if not request.user.has_perm('patients.view_patientadmission'):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        data = {
            'id': str(admission.pk),
            'patient': {
                'id': str(admission.patient.pk),
                'name': admission.patient.name,
            },
            'admission_datetime': admission.admission_datetime.isoformat(),
            'admission_type': admission.admission_type,
            'admission_type_display': admission.get_admission_type_display(),
            'initial_bed': admission.initial_bed,
            'admission_diagnosis': admission.admission_diagnosis,
            'is_active': admission.is_active,
        }

        if admission.discharge_datetime:
            data.update({
                'discharge_datetime': admission.discharge_datetime.isoformat(),
                'discharge_type': admission.discharge_type,
                'discharge_type_display': admission.get_discharge_type_display(),
                'final_bed': admission.final_bed,
                'discharge_diagnosis': admission.discharge_diagnosis,
                'stay_duration_days': admission.stay_duration_days,
                'stay_duration_hours': admission.stay_duration_hours,
            })
        else:
            current_duration = admission.calculate_current_duration()
            if current_duration:
                data['current_duration'] = current_duration

        return JsonResponse(data)

class PatientSearchAPIView(LoginRequiredMixin, View):
    """Enhanced patient search API with record number support"""

    def get(self, request):
        # Check permissions
        if not request.user.has_perm('patients.view_patient'):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        query = request.GET.get('q', '').strip()
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))

        if not query:
            return JsonResponse({'results': [], 'total': 0, 'page': page})

        # Search in multiple fields including record numbers
        patients = Patient.objects.filter(
            Q(name__icontains=query) |
            Q(healthcard_number__icontains=query) |
            Q(id_number__icontains=query) |
            Q(fiscal_number__icontains=query) |
            Q(current_record_number__icontains=query) |
            Q(record_numbers__record_number__icontains=query)
        ).distinct().order_by('name')

        # Pagination
        paginator = Paginator(patients, per_page)
        page_obj = paginator.get_page(page)

        results = []
        for patient in page_obj:
            results.append({
                'id': str(patient.pk),
                'name': patient.name,
                'current_record_number': patient.current_record_number,
                'status': patient.get_status_display(),
                'is_currently_admitted': patient.is_currently_admitted(),
                'bed': patient.bed,
                'healthcard_number': patient.healthcard_number,
                'phone': patient.phone,
            })

        data = {
            'results': results,
            'total': paginator.count,
            'page': page,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }

        return JsonResponse(data)
```

### Step 5.5: Update Patient List View with Record Number Search

**File**: `apps/patients/views.py` - Update existing PatientListView

```python
class PatientListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Enhanced patient list view with record number search"""
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 20
    permission_required = 'patients.view_patient'

    def get_queryset(self):
        queryset = super().get_queryset()

        # Search functionality
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(healthcard_number__icontains=search_query) |
                Q(id_number__icontains=search_query) |
                Q(fiscal_number__icontains=search_query) |
                Q(current_record_number__icontains=search_query) |
                Q(record_numbers__record_number__icontains=search_query)
            ).distinct()

        # Status filter
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Admission status filter
        admission_filter = self.request.GET.get('admission')
        if admission_filter == 'admitted':
            queryset = queryset.exclude(current_admission_id__isnull=True)
        elif admission_filter == 'not_admitted':
            queryset = queryset.filter(current_admission_id__isnull=True)

        return queryset.order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['admission_filter'] = self.request.GET.get('admission', '')
        context['status_choices'] = Patient.Status.choices
        return context
```

### Step 5.6: Update Patient Detail View

**File**: `apps/patients/views.py` - Update PatientDetailView with record tracking

```python
class PatientDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Enhanced patient detail view with record tracking"""
    model = Patient
    template_name = 'patients/patient_detail.html'
    context_object_name = 'patient'
    permission_required = 'patients.view_patient'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add record number history
        context['record_numbers'] = self.object.record_numbers.all().order_by('-effective_date')
        context['current_record'] = self.object.record_numbers.filter(is_current=True).first()

        # Add admission history
        context['admissions'] = self.object.admissions.all().order_by('-admission_datetime')
        context['current_admission'] = self.object.get_current_admission()

        # Add quick action forms
        context['quick_record_form'] = QuickRecordNumberUpdateForm()
        context['quick_admission_form'] = QuickAdmissionForm()
        context['quick_discharge_form'] = QuickDischargeForm()

        # Add statistics
        context['admission_stats'] = {
            'total_admissions': self.object.total_admissions_count,
            'total_days': self.object.total_inpatient_days,
            'average_stay': (
                self.object.total_inpatient_days / self.object.total_admissions_count
                if self.object.total_admissions_count > 0 else 0
            ),
            'is_currently_admitted': self.object.is_currently_admitted(),
        }

        return context
```

### Step 5.7: Create Confirmation Delete Template

**File**: `apps/patients/templates/patients/record_number_confirm_delete.html`

```html
{% extends "base_app.html" %} {% load hospital_tags %} {% block title %}Excluir
Número de Prontuário - {% hospital_name %}{% endblock %} {% block app_content %}
<div class="container-fluid">
  <div class="row">
    <div class="col-md-6 mx-auto">
      <div class="card">
        <div class="card-header bg-danger text-white">
          <h5 class="card-title mb-0">
            <i class="fas fa-trash"></i>
            Confirmar Exclusão
          </h5>
        </div>
        <div class="card-body">
          <div class="alert alert-warning">
            <i class="fas fa-exclamation-triangle"></i>
            <strong>Atenção!</strong> Esta ação não pode ser desfeita.
          </div>

          <p>Tem certeza que deseja excluir o número de prontuário abaixo?</p>

          <div class="card bg-light">
            <div class="card-body">
              <h6>Paciente: {{ patient.name }}</h6>
              <p class="mb-1">
                <strong>Número:</strong>
                <span class="badge bg-primary">{{ object.record_number }}</span>
                {% if object.is_current %}<span class="badge bg-success"
                  >Atual</span
                >{% endif %}
              </p>
              <p class="mb-1">
                <strong>Vigente desde:</strong> {{
                object.effective_date|date:"d/m/Y H:i" }}
              </p>
              {% if object.change_reason %}
              <p class="mb-0">
                <strong>Motivo:</strong> {{ object.change_reason }}
              </p>
              {% endif %}
            </div>
          </div>

          <form method="post" class="mt-3">
            {% csrf_token %}
            <div class="d-flex justify-content-end gap-2">
              <a
                href="{% url 'patients:patient_detail' patient.pk %}"
                class="btn btn-secondary"
              >
                <i class="fas fa-times"></i> Cancelar
              </a>
              <button type="submit" class="btn btn-danger">
                <i class="fas fa-trash"></i> Excluir
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

## Testing API Endpoints

### Step 5.8: Create API Tests

**File**: `apps/patients/tests/test_api_views.py`

```python
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json

from ..models import Patient, PatientRecordNumber, PatientAdmission

User = get_user_model()

class PatientAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            profession='doctor'
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )

    def test_patient_record_numbers_api(self):
        """Test patient record numbers API endpoint"""
        # Create record numbers
        record1 = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            is_current=False,
            created_by=self.user,
            updated_by=self.user
        )
        record2 = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC002',
            is_current=True,
            previous_record_number='REC001',
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:api_patient_record_numbers', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['patient_id'], str(self.patient.pk))
        self.assertEqual(data['current_record_number'], 'REC002')
        self.assertEqual(len(data['records']), 2)

        # Check current record is first
        self.assertTrue(data['records'][0]['is_current'])
        self.assertEqual(data['records'][0]['record_number'], 'REC002')

    def test_record_number_lookup_api(self):
        """Test record number lookup API"""
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='LOOKUP123',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:api_record_number_lookup', kwargs={'record_number': 'LOOKUP123'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['found'])
        self.assertEqual(data['patient']['id'], str(self.patient.pk))
        self.assertEqual(data['patient']['name'], self.patient.name)

    def test_patient_admissions_api(self):
        """Test patient admissions API endpoint"""
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=2),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            initial_bed='A101',
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:api_patient_admissions', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['patient_id'], str(self.patient.pk))
        self.assertTrue(data['is_currently_admitted'])
        self.assertEqual(len(data['admissions']), 1)

        admission_data = data['admissions'][0]
        self.assertEqual(admission_data['admission_type'], 'emergency')
        self.assertEqual(admission_data['initial_bed'], 'A101')
        self.assertTrue(admission_data['is_active'])

    def test_patient_search_api(self):
        """Test enhanced patient search API"""
        # Create record number for search
        PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='SEARCH456',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:api_patient_search')

        # Search by name
        response = self.client.get(url, {'q': 'Test Patient'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)

        # Search by record number
        response = self.client.get(url, {'q': 'SEARCH456'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['current_record_number'], 'SEARCH456')
```

## Success Criteria

- ✅ Complete URL patterns for record tracking functionality
- ✅ Views for creating, updating, deleting record numbers
- ✅ Views for admission and discharge processes
- ✅ Quick action views for common operations
- ✅ Comprehensive API endpoints for all functionality
- ✅ Enhanced patient search with record number support
- ✅ Updated patient list and detail views
- ✅ Proper permission checks on all views and APIs
- ✅ User-friendly error handling and messages
- ✅ API tests covering all endpoints
- ✅ Integration with existing permission system
- ✅ Backward compatibility with existing patient functionality

## Next Phase

Continue to **Phase 6: Testing and Validation** to create comprehensive tests, validate business logic, and ensure data integrity across the entire system.
