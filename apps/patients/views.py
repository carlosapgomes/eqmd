from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q, Case, When, IntegerField
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views import View

from .models import Patient, PatientHospitalRecord, AllowedTag
from .forms import PatientForm, PatientHospitalRecordForm, AllowedTagForm
from apps.hospitals.models import Hospital
from apps.core.permissions.utils import can_access_patient, can_change_patient_personal_data


class PatientListView(LoginRequiredMixin, ListView):
    model = Patient
    paginate_by = 10

    def get_queryset(self):
        from apps.core.permissions.utils import get_user_accessible_patients
        from apps.core.permissions.constants import INPATIENT, EMERGENCY, TRANSFERRED, OUTPATIENT, DISCHARGED
        
        # Check hospital filter parameters first to determine filtering strategy
        hospital_filter = self.request.GET.get('hospital')
        has_hospital_param = 'hospital' in self.request.GET
        
        if hospital_filter or has_hospital_param:
            # User has explicitly selected a hospital filter - use simple permission checking
            if not self.request.user.is_authenticated:
                return super().get_queryset().none()
            
            # Get user's accessible hospitals
            user_hospitals = []
            if hasattr(self.request.user, 'hospitals'):
                user_hospitals = list(self.request.user.hospitals.values_list('id', flat=True))
            elif self.request.user.is_superuser:
                from apps.hospitals.models import Hospital
                user_hospitals = list(Hospital.objects.values_list('id', flat=True))
            
            if not user_hospitals:
                return super().get_queryset().none()
            
            # Start with base queryset that respects user's hospital access
            from apps.patients.models import Patient
            queryset = Patient.objects.filter(
                Q(current_hospital_id__in=user_hospitals) |
                Q(hospital_records__hospital_id__in=user_hospitals)
            ).distinct()
            
            # Apply specific hospital filter if provided
            if hospital_filter:
                try:
                    # Handle both UUID strings and integer IDs
                    from uuid import UUID
                    if len(hospital_filter) > 10:  # Likely a UUID string
                        hospital_id = UUID(hospital_filter)
                    else:
                        hospital_id = int(hospital_filter)
                    
                    if hospital_id in user_hospitals:  # Security check
                        # Different filtering logic for inpatients vs outpatients
                        from apps.core.permissions.constants import INPATIENT, EMERGENCY, TRANSFERRED, OUTPATIENT, DISCHARGED
                        inpatient_statuses = [INPATIENT, EMERGENCY, TRANSFERRED]
                        outpatient_statuses = [OUTPATIENT, DISCHARGED]
                        
                        queryset = queryset.filter(
                            Q(status__in=inpatient_statuses, current_hospital_id=hospital_id) |
                            Q(status__in=outpatient_statuses)  # All outpatients, no hospital restriction
                        ).distinct()
                    else:
                        return super().get_queryset().none()
                except (ValueError, TypeError):
                    pass
        else:
            # No explicit hospital filter - use default permission-based filtering
            queryset = get_user_accessible_patients(self.request.user)
            if queryset is None:
                queryset = super().get_queryset().none()
            
            # Apply default context filtering for current hospital
            if (hasattr(self.request.user, 'has_hospital_context') and 
                self.request.user.has_hospital_context and 
                hasattr(self.request.user, 'current_hospital') and 
                self.request.user.current_hospital):
                
                user_hospital = self.request.user.current_hospital
                admitted_statuses = [INPATIENT, EMERGENCY, TRANSFERRED]
                
                # Only filter admitted patients to current hospital
                queryset = queryset.filter(
                    Q(status__in=admitted_statuses, current_hospital=user_hospital) |
                    Q(status__in=[OUTPATIENT, DISCHARGED])
                )
        
        # Add optimized select_related and prefetch_related
        queryset = queryset.select_related('current_hospital').prefetch_related('tags__allowed_tag', 'hospital_records__hospital')
        
        # Search functionality
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(id_number__icontains=search_query) |
                Q(fiscal_number__icontains=search_query) |
                Q(healthcard_number__icontains=search_query)
            )

        # Status filter
        status_filter = self.request.GET.get('status')
        if status_filter:
            try:
                status_value = int(status_filter)
                queryset = queryset.filter(status=status_value)
            except (ValueError, TypeError):
                pass

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
        # Use available hospitals from context processor (which respects user permissions)
        from apps.hospitals.middleware import HospitalContextMiddleware
        context['available_hospitals'] = HospitalContextMiddleware.get_available_hospitals(self.request.user)
        
        # Add current hospital and default filter information for template logic
        context['current_hospital'] = getattr(self.request.user, 'current_hospital', None)
        context['using_default_hospital_filter'] = (
            'hospital' not in self.request.GET and 
            getattr(self.request.user, 'has_hospital_context', False) and
            getattr(self.request.user, 'current_hospital', None)
        )
        return context


class PatientDetailView(LoginRequiredMixin, DetailView):
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
        ).select_subclasses().select_related('created_by').order_by('-created_at')[:3]
        
        # Add events count
        context['total_events_count'] = Event.objects.filter(patient=patient).count()
        
        # Add permission context
        context['can_edit_patient'] = can_change_patient_personal_data(self.request.user, patient)
        
        return context


class PatientCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Patient
    form_class = PatientForm
    permission_required = 'patients.add_patient'

    def get_form_kwargs(self):
        """Pass hospital record data to form if provided"""
        kwargs = super().get_form_kwargs()
        if self.request.method == 'POST':
            # Extract hospital record data from POST
            hospital_record_data = {}
            for key, value in self.request.POST.items():
                if key.startswith('hospital_record-'):
                    field_name = key.replace('hospital_record-', '')
                    hospital_record_data[field_name] = value
            if hospital_record_data:
                kwargs['hospital_record_data'] = hospital_record_data
        return kwargs

    def get_context_data(self, **kwargs):
        """Add hospital record form and existing records to context"""
        context = super().get_context_data(**kwargs)
        if hasattr(self.get_form(), 'hospital_record_form'):
            context['hospital_record_form'] = self.get_form().hospital_record_form
        
        # No existing records for new patients
        context['existing_hospital_records'] = []
        context['patient_id'] = None
        return context

    def get_success_url(self):
        return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        # Store user for tag creation
        form.current_user = self.request.user
        
        response = super().form_valid(form)
        
        # Add success message with hospital record info if created
        if hasattr(form, 'hospital_record_form') and form.hospital_record_form.has_changed():
            hospital_data = form.hospital_record_form.cleaned_data
            if hospital_data.get('hospital'):
                messages.success(
                    self.request, 
                    f"Patient {form.instance.name} created successfully with hospital record at {hospital_data['hospital'].name}."
                )
            else:
                messages.success(self.request, f"Patient {form.instance.name} created successfully.")
        else:
            messages.success(self.request, f"Patient {form.instance.name} created successfully.")
        
        return response


class PatientUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Patient
    form_class = PatientForm
    permission_required = 'patients.change_patient'

    def get_form_kwargs(self):
        """Pass hospital record data to form if provided"""
        kwargs = super().get_form_kwargs()
        if self.request.method == 'POST':
            # Extract hospital record data from POST
            hospital_record_data = {}
            for key, value in self.request.POST.items():
                if key.startswith('hospital_record-'):
                    field_name = key.replace('hospital_record-', '')
                    hospital_record_data[field_name] = value
            if hospital_record_data:
                kwargs['hospital_record_data'] = hospital_record_data
        else:
            # For GET requests, pre-populate with existing hospital record if available
            patient = self.get_object()
            if patient.pk and patient.current_hospital:
                try:
                    hospital_record = PatientHospitalRecord.objects.get(
                        patient=patient,
                        hospital=patient.current_hospital
                    )
                    kwargs['hospital_record_data'] = {
                        'hospital': hospital_record.hospital.pk,
                        'record_number': hospital_record.record_number,
                        'first_admission_date': hospital_record.first_admission_date,
                        'last_admission_date': hospital_record.last_admission_date,
                        'last_discharge_date': hospital_record.last_discharge_date,
                    }
                except PatientHospitalRecord.DoesNotExist:
                    pass
        return kwargs

    def get_context_data(self, **kwargs):
        """Add hospital record form and existing records to context"""
        context = super().get_context_data(**kwargs)
        if hasattr(self.get_form(), 'hospital_record_form'):
            context['hospital_record_form'] = self.get_form().hospital_record_form
        
        # Add existing hospital records for the patient
        patient = self.get_object()
        context['existing_hospital_records'] = PatientHospitalRecord.objects.filter(
            patient=patient
        ).select_related('hospital').order_by('-last_admission_date')
        context['patient_id'] = str(patient.pk)
        return context

    def get_success_url(self):
        return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        # Store user for tag creation
        form.current_user = self.request.user
        
        response = super().form_valid(form)
        
        # Add success message with hospital record info if updated
        if hasattr(form, 'hospital_record_form') and form.hospital_record_form.has_changed():
            hospital_data = form.hospital_record_form.cleaned_data
            if hospital_data.get('hospital'):
                messages.success(
                    self.request, 
                    f"Patient {form.instance.name} updated successfully with hospital record at {hospital_data['hospital'].name}."
                )
            else:
                messages.success(self.request, f"Patient {form.instance.name} updated successfully.")
        else:
            messages.success(self.request, f"Patient {form.instance.name} updated successfully.")
        
        return response


class PatientDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Patient
    success_url = reverse_lazy('patients:patient_list')
    permission_required = 'patients.delete_patient'

    def delete(self, request, *args, **kwargs):
        patient = self.get_object()
        messages.success(request, f"Patient {patient.name} deleted successfully.")
        return super().delete(request, *args, **kwargs)


class HospitalRecordCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = PatientHospitalRecord
    form_class = PatientHospitalRecordForm
    template_name = 'patients/hospital_record_form.html'
    permission_required = 'patients.add_patienthospitalrecord'

    def get_initial(self):
        initial = super().get_initial()
        # Check for patient_id in URL kwargs first, then fallback to GET parameter
        patient_id = self.kwargs.get('patient_id') or self.request.GET.get('patient')
        if patient_id:
            initial['patient'] = get_object_or_404(Patient, pk=patient_id)
        return initial

    def get_success_url(self):
        # Use patient_id from URL kwargs if available, otherwise use the object's patient
        patient_id = self.kwargs.get('patient_id') or self.object.patient.pk
        return reverse_lazy('patients:patient_detail', kwargs={'pk': patient_id})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Hospital record created successfully.")
        return super().form_valid(form)


class HospitalRecordUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = PatientHospitalRecord
    form_class = PatientHospitalRecordForm
    template_name = 'patients/hospital_record_form.html'
    permission_required = 'patients.change_patienthospitalrecord'

    def get_success_url(self):
        return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.patient.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Hospital record updated successfully.")
        return super().form_valid(form)


class HospitalRecordDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = PatientHospitalRecord
    permission_required = 'patients.delete_patienthospitalrecord'

    def get_success_url(self):
        return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.patient.pk})

    def delete(self, request, *args, **kwargs):
        record = self.get_object()
        messages.success(request, f"Hospital record for {record.patient.name} deleted successfully.")
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


# API Views
class PatientHospitalRecordsAPIView(LoginRequiredMixin, View):
    """API view to get all hospital records for a patient"""
    
    def get(self, request, patient_id):
        try:
            patient = get_object_or_404(Patient, pk=patient_id)
            
            # Check permission
            if not can_access_patient(request.user, patient):
                return JsonResponse({'error': 'Permission denied'}, status=403)
            
            records = PatientHospitalRecord.objects.filter(
                patient=patient
            ).select_related('hospital').order_by('-last_admission_date')
            
            records_data = []
            for record in records:
                records_data.append({
                    'id': str(record.id),
                    'hospital': {
                        'id': str(record.hospital.id),
                        'name': record.hospital.name,
                    },
                    'record_number': record.record_number,
                    'first_admission_date': record.first_admission_date.isoformat() if record.first_admission_date else None,
                    'last_admission_date': record.last_admission_date.isoformat() if record.last_admission_date else None,
                    'last_discharge_date': record.last_discharge_date.isoformat() if record.last_discharge_date else None,
                })
            
            return JsonResponse({
                'records': records_data,
                'count': len(records_data)
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class HospitalRecordByHospitalAPIView(LoginRequiredMixin, View):
    """API view to get hospital record for a specific patient and hospital"""
    
    def get(self, request, hospital_id):
        try:
            patient_id = request.GET.get('patient_id')
            if not patient_id:
                return JsonResponse({'error': 'patient_id parameter required'}, status=400)
            
            patient = get_object_or_404(Patient, pk=patient_id)
            hospital = get_object_or_404(Hospital, pk=hospital_id)
            
            # Check permission
            if not can_access_patient(request.user, patient):
                return JsonResponse({'error': 'Permission denied'}, status=403)
            
            try:
                record = PatientHospitalRecord.objects.get(
                    patient=patient,
                    hospital=hospital
                )
                
                return JsonResponse({
                    'exists': True,
                    'record': {
                        'id': str(record.id),
                        'record_number': record.record_number,
                        'first_admission_date': record.first_admission_date.isoformat() if record.first_admission_date else '',
                        'last_admission_date': record.last_admission_date.isoformat() if record.last_admission_date else '',
                        'last_discharge_date': record.last_discharge_date.isoformat() if record.last_discharge_date else '',
                    }
                })
                
            except PatientHospitalRecord.DoesNotExist:
                return JsonResponse({
                    'exists': False,
                    'record': None
                })
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


