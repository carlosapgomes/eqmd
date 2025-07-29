from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q, Case, When, IntegerField
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.views import View
from django.utils import timezone

from .models import Patient, AllowedTag, PatientRecordNumber, PatientAdmission, Ward
from .forms import (
    PatientForm, AllowedTagForm, 
    PatientRecordNumberForm, QuickRecordNumberUpdateForm,
    PatientAdmissionForm, PatientDischargeForm,
    QuickAdmissionForm, QuickDischargeForm, WardForm,
    # Status change forms
    AdmitPatientForm, DischargePatientForm, EmergencyAdmissionForm,
    TransferPatientForm, DeclareDeathForm, SetOutpatientForm
)
# from apps.hospitals.models import Hospital  # Removed for single-hospital refactor
from apps.core.permissions.utils import can_access_patient, can_change_patient_personal_data


class PatientListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Enhanced patient list view with record number search"""
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 20
    permission_required = 'patients.view_patient'

    def get_queryset(self):
        from apps.core.permissions.utils import get_user_accessible_patients
        
        # Use simplified permission-based filtering (no hospital context)
        queryset = get_user_accessible_patients(self.request.user)
        if queryset is None:
            queryset = super().get_queryset().none()
        
        # Add optimized select_related and prefetch_related
        queryset = queryset.select_related('created_by').prefetch_related('tags__allowed_tag')
        
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
            try:
                status_value = int(status_filter)
                queryset = queryset.filter(status=status_value)
            except (ValueError, TypeError):
                pass

        # Admission status filter
        admission_filter = self.request.GET.get('admission')
        if admission_filter == 'admitted':
            queryset = queryset.exclude(current_admission_id__isnull=True)
        elif admission_filter == 'not_admitted':
            queryset = queryset.filter(current_admission_id__isnull=True)

        # Apply priority ordering: inpatients first, then outpatients, both alphabetically
        from apps.core.permissions.constants import INPATIENT, EMERGENCY, TRANSFERRED, OUTPATIENT, DISCHARGED
        queryset = queryset.annotate(
            priority=Case(
                When(status__in=[INPATIENT, EMERGENCY, TRANSFERRED], then=1),  # Inpatients first
                When(status__in=[OUTPATIENT, DISCHARGED], then=2),            # Outpatients second
                default=3,
                output_field=IntegerField()
            )
        ).order_by('priority', 'name')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['admission_filter'] = self.request.GET.get('admission', '')
        context['status_choices'] = Patient.Status.choices
        context['wards'] = Ward.objects.filter(is_active=True).order_by('name')
        return context


class PatientDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Enhanced patient detail view with record tracking"""
    model = Patient
    template_name = 'patients/patient_detail.html'
    context_object_name = 'patient'
    permission_required = 'patients.view_patient'

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
        ).select_subclasses().select_related('created_by').order_by('-created_at')[:3]
        
        # Add events count
        context['total_events_count'] = Event.objects.filter(patient=patient).count()
        
        # Add permission context
        context['can_edit_patient'] = can_change_patient_personal_data(self.request.user, patient)

        # Add record number history
        context['record_numbers'] = patient.record_numbers.all().order_by('-effective_date')
        context['current_record'] = patient.record_numbers.filter(is_current=True).first()

        # Add admission history
        context['admissions'] = patient.admissions.all().order_by('-admission_datetime')
        context['current_admission'] = patient.get_current_admission()

        # Add quick action forms
        context['quick_record_form'] = QuickRecordNumberUpdateForm()
        context['quick_admission_form'] = QuickAdmissionForm()
        context['quick_discharge_form'] = QuickDischargeForm()
        
        # Add wards for status change modals
        context['wards'] = Ward.objects.filter(is_active=True).order_by('name')

        # Add statistics
        context['admission_stats'] = {
            'total_admissions': patient.total_admissions_count,
            'total_days': patient.total_inpatient_days,
            'average_stay': (
                patient.total_inpatient_days / patient.total_admissions_count
                if patient.total_admissions_count > 0 else 0
            ),
            'is_currently_admitted': patient.is_currently_admitted(),
        }
        
        return context


class PatientCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Patient
    form_class = PatientForm
    template_name = 'patients/patient_create.html'
    permission_required = 'patients.add_patient'

    def get_form_kwargs(self):
        """Pass form kwargs without hospital record data"""
        kwargs = super().get_form_kwargs()
        # No hospital record data processing needed
        return kwargs

    def get_context_data(self, **kwargs):
        """Add simple context without hospital record forms"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Criar Novo Paciente'
        return context

    def get_success_url(self):
        return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        # Store user for tag creation
        form.current_user = self.request.user
        
        response = super().form_valid(form)
        
        # Add simple success message
        messages.success(self.request, f"Patient {form.instance.name} created successfully.")
        
        return response


class PatientUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Patient
    form_class = PatientForm
    template_name = 'patients/patient_update.html'
    permission_required = 'patients.change_patient'

    def get_form_kwargs(self):
        """Pass form kwargs without hospital record data"""
        kwargs = super().get_form_kwargs()
        # Remove initial_record_number for update form
        if 'initial' in kwargs:
            kwargs['initial'] = kwargs['initial'].copy()
            kwargs['initial'].pop('initial_record_number', None)
        return kwargs

    def get_context_data(self, **kwargs):
        """Add simple context without hospital record forms"""
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Paciente: {self.object.name}'
        return context

    def get_success_url(self):
        return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        # Store user for tag creation
        form.current_user = self.request.user
        
        messages.success(self.request, f"Patient {form.instance.name} updated successfully.")
        
        response = super().form_valid(form)
        return response


class PatientDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Patient
    success_url = reverse_lazy('patients:patient_list')
    permission_required = 'patients.delete_patient'

    def delete(self, request, *args, **kwargs):
        patient = self.get_object()
        messages.success(request, f"Patient {patient.name} deleted successfully.")
        return super().delete(request, *args, **kwargs)




# AllowedTag views
class AllowedTagListView(LoginRequiredMixin, ListView):
    model = AllowedTag
    template_name = 'patients/tag_list.html'
    context_object_name = 'tags'
    paginate_by = 20


class AllowedTagCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = AllowedTag
    form_class = AllowedTagForm
    template_name = 'patients/tag_form.html'
    success_url = reverse_lazy('patients:tag_list')
    permission_required = 'patients.add_allowedtag'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Tag created successfully.')
        return super().form_valid(form)


class AllowedTagUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = AllowedTag
    form_class = AllowedTagForm
    template_name = 'patients/tag_form.html'
    success_url = reverse_lazy('patients:tag_list')
    permission_required = 'patients.change_allowedtag'

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Tag updated successfully.')
        return super().form_valid(form)


class AllowedTagDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = AllowedTag
    template_name = 'patients/tag_confirm_delete.html'
    success_url = reverse_lazy('patients:tag_list')
    permission_required = 'patients.delete_allowedtag'

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Tag deleted successfully.')
        return super().delete(request, *args, **kwargs)


# Record Tracking Views

from django.http import JsonResponse
from django.views import View
from django.core.serializers import serialize
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
import json

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
                ward=form.cleaned_data.get('ward'),
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
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"QuickDischargeView: Starting discharge for admission {admission_id}")
        logger.info(f"QuickDischargeView: POST data: {request.POST}")
        
        admission = get_object_or_404(PatientAdmission, pk=admission_id)
        logger.info(f"QuickDischargeView: Found admission for patient {admission.patient.name}")
        
        form = QuickDischargeForm(request.POST)
        logger.info(f"QuickDischargeView: Form is_valid: {form.is_valid()}")

        if form.is_valid():
            logger.info(f"QuickDischargeView: Form cleaned_data: {form.cleaned_data}")
            try:
                logger.info("QuickDischargeView: Calling discharge_patient method")
                admission.patient.discharge_patient(
                    discharge_datetime=timezone.now(),
                    discharge_type=form.cleaned_data['discharge_type'],
                    user=request.user,
                    discharge_diagnosis=form.cleaned_data.get('discharge_diagnosis', '')
                )
                logger.info("QuickDischargeView: discharge_patient completed successfully")

                messages.success(
                    request,
                    f'Alta rápida registrada. Tipo: {form.cleaned_data["discharge_type"]}'
                )

            except ValidationError as e:
                logger.error(f"QuickDischargeView: ValidationError in discharge_patient: {str(e)}")
                messages.error(request, f'Erro na alta: {str(e)}')
            except Exception as e:
                logger.error(f"QuickDischargeView: Unexpected error in discharge_patient: {str(e)}")
                messages.error(request, f'Erro inesperado: {str(e)}')
        else:
            logger.error(f"QuickDischargeView: Form validation failed. Errors: {form.errors}")
            messages.error(request, 'Dados inválidos para alta.')

        logger.info(f"QuickDischargeView: Redirecting to patient_detail for patient {admission.patient.pk}")
        return redirect('patients:patient_detail', pk=admission.patient.pk)

# API Views

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
            'gender': patient.gender,
            'gender_display': patient.get_gender_display(),
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
            'gender': patient.gender,
            'gender_display': patient.get_gender_display(),
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
                    'gender': patient.gender,
                    'gender_display': patient.get_gender_display(),
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
                        'gender': patient.gender,
                        'gender_display': patient.get_gender_display(),
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
                'gender': patient.gender,
                'gender_display': patient.get_gender_display(),
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


# Ward Management Views

class WardListView(LoginRequiredMixin, ListView):
    """View for listing all wards"""
    model = Ward
    template_name = 'patients/ward_list.html'
    context_object_name = 'wards'
    paginate_by = 20
    
    def get_queryset(self):
        return Ward.objects.filter(is_active=True).order_by('name')


class WardDetailView(LoginRequiredMixin, DetailView):
    """View for ward details with current patients"""
    model = Ward
    template_name = 'patients/ward_detail.html'
    context_object_name = 'ward'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ward = self.get_object()
        context['current_patients'] = ward.patients.filter(
            status__in=[Patient.Status.INPATIENT, Patient.Status.EMERGENCY]
        ).order_by('name')
        context['recent_admissions'] = ward.admissions.filter(
            is_active=True
        ).order_by('-admission_datetime')[:10]
        return context


class WardCreateView(LoginRequiredMixin, CreateView):
    """View for creating new wards"""
    model = Ward
    form_class = WardForm
    template_name = 'patients/ward_form.html'
    success_url = reverse_lazy('patients:ward_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class WardUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating existing wards"""
    model = Ward
    form_class = WardForm
    template_name = 'patients/ward_form.html'
    success_url = reverse_lazy('patients:ward_list')
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


# Status Change Views

class PatientStatusChangeView(LoginRequiredMixin, View):
    """Base view for patient status changes"""
    
    def get_patient(self, pk):
        """Get patient and check permissions"""
        patient = get_object_or_404(Patient, pk=pk)
        if not can_access_patient(self.request.user, patient):
            raise PermissionDenied("Você não tem permissão para alterar o status deste paciente")
        return patient
    
    def post(self, request, pk):
        patient = self.get_patient(pk)
        return self.handle_status_change(request, patient)
    
    def handle_status_change(self, request, patient):
        """Override in subclasses"""
        raise NotImplementedError


class AdmitPatientView(PatientStatusChangeView):
    """Change patient status to inpatient"""
    
    def handle_status_change(self, request, patient):
        form = AdmitPatientForm(request.POST)
        
        if form.is_valid():
            try:
                # Update patient status and related fields
                patient.status = Patient.Status.INPATIENT
                patient.ward = form.cleaned_data['ward']
                patient.bed = form.cleaned_data.get('bed', '')
                patient.updated_by = request.user
                patient.save()
                
                messages.success(
                    request,
                    f'Paciente {patient.name} foi internado com sucesso.'
                )
            except ValidationError as e:
                messages.error(request, f'Erro na internação: {str(e)}')
        else:
            messages.error(request, 'Dados inválidos para internação.')
        
        return redirect('patients:patient_detail', pk=patient.pk)


class DischargePatientView(PatientStatusChangeView):
    """Change patient status to discharged"""
    
    def handle_status_change(self, request, patient):
        form = DischargePatientForm(request.POST)
        
        if form.is_valid():
            try:
                # Update patient status and clear bed/ward
                patient.status = Patient.Status.DISCHARGED
                patient.bed = ''
                patient.updated_by = request.user
                patient.save()
                
                messages.success(
                    request,
                    f'Paciente {patient.name} recebeu alta com sucesso.'
                )
            except ValidationError as e:
                messages.error(request, f'Erro na alta: {str(e)}')
        else:
            messages.error(request, 'Dados inválidos para alta.')
        
        return redirect('patients:patient_detail', pk=patient.pk)


class EmergencyAdmissionView(PatientStatusChangeView):
    """Change patient status to emergency"""
    
    def handle_status_change(self, request, patient):
        form = EmergencyAdmissionForm(request.POST)
        
        if form.is_valid():
            try:
                # Update patient status for emergency
                patient.status = Patient.Status.EMERGENCY
                if form.cleaned_data.get('ward'):
                    patient.ward = form.cleaned_data['ward']
                patient.bed = form.cleaned_data.get('bed', '')
                patient.updated_by = request.user
                patient.save()
                
                messages.success(
                    request,
                    f'Paciente {patient.name} foi admitido em emergência.'
                )
            except ValidationError as e:
                messages.error(request, f'Erro na admissão de emergência: {str(e)}')
        else:
            messages.error(request, 'Dados inválidos para admissão de emergência.')
        
        return redirect('patients:patient_detail', pk=patient.pk)


class TransferPatientView(PatientStatusChangeView):
    """Change patient status to transferred"""
    
    def handle_status_change(self, request, patient):
        form = TransferPatientForm(request.POST)
        
        if form.is_valid():
            try:
                # Update patient status for transfer
                patient.status = Patient.Status.TRANSFERRED
                patient.bed = ''
                patient.updated_by = request.user
                patient.save()
                
                messages.success(
                    request,
                    f'Paciente {patient.name} foi transferido para {form.cleaned_data["destination"]}.'
                )
            except ValidationError as e:
                messages.error(request, f'Erro na transferência: {str(e)}')
        else:
            messages.error(request, 'Dados inválidos para transferência.')
        
        return redirect('patients:patient_detail', pk=patient.pk)


class DeclareDeathView(PatientStatusChangeView):
    """Change patient status to deceased"""
    
    def handle_status_change(self, request, patient):
        from apps.core.permissions.utils import can_change_patient_status
        
        # Check if user can declare death (doctors/residents only)
        if not can_change_patient_status(request.user, patient, Patient.Status.DECEASED):
            messages.error(request, 'Você não tem permissão para declarar óbito.')
            return redirect('patients:patient_detail', pk=patient.pk)
        
        form = DeclareDeathForm(request.POST)
        
        if form.is_valid():
            try:
                # Update patient status for death
                patient.status = Patient.Status.DECEASED
                patient.bed = ''
                patient.updated_by = request.user
                patient.save()
                
                messages.success(
                    request,
                    f'Óbito de {patient.name} foi declarado.'
                )
            except ValidationError as e:
                messages.error(request, f'Erro na declaração de óbito: {str(e)}')
        else:
            messages.error(request, 'Dados inválidos para declaração de óbito.')
        
        return redirect('patients:patient_detail', pk=patient.pk)


class SetOutpatientView(PatientStatusChangeView):
    """Change patient status to outpatient"""
    
    def handle_status_change(self, request, patient):
        form = SetOutpatientForm(request.POST)
        
        if form.is_valid():
            try:
                # Update patient status for outpatient care
                patient.status = Patient.Status.OUTPATIENT
                patient.bed = ''
                patient.updated_by = request.user
                patient.save()
                
                messages.success(
                    request,
                    f'Paciente {patient.name} foi definido para acompanhamento ambulatorial.'
                )
            except ValidationError as e:
                messages.error(request, f'Erro na alteração para ambulatorial: {str(e)}')
        else:
            messages.error(request, 'Dados inválidos para status ambulatorial.')
        
        return redirect('patients:patient_detail', pk=patient.pk)


