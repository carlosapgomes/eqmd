from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q
from django.core.exceptions import PermissionDenied

from .models import Patient, PatientHospitalRecord, AllowedTag
from .forms import PatientForm, PatientHospitalRecordForm, AllowedTagForm
from apps.hospitals.models import Hospital
from apps.core.permissions.utils import can_access_patient, can_change_patient_personal_data


class PatientListView(LoginRequiredMixin, ListView):
    model = Patient
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('current_hospital').prefetch_related('tags__allowed_tag')
        
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

        # Hospital filter - explicit parameter overrides default context
        hospital_filter = self.request.GET.get('hospital')
        if hospital_filter:
            queryset = queryset.filter(current_hospital_id=hospital_filter)
        else:
            # Default to current hospital context if user has one and no explicit filter
            if (hasattr(self.request.user, 'has_hospital_context') and 
                self.request.user.has_hospital_context and 
                hasattr(self.request.user, 'current_hospital') and 
                self.request.user.current_hospital):
                queryset = queryset.filter(current_hospital=self.request.user.current_hospital)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Use available hospitals from context processor (which respects user permissions)
        from apps.hospitals.middleware import HospitalContextMiddleware
        context['available_hospitals'] = HospitalContextMiddleware.get_available_hospitals(self.request.user)
        
        # Add current hospital and default filter information for template logic
        context['current_hospital'] = getattr(self.request.user, 'current_hospital', None)
        context['using_default_hospital_filter'] = (
            not self.request.GET.get('hospital') and 
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

    def get_success_url(self):
        return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        # Store user for tag creation
        form.current_user = self.request.user
        messages.success(self.request, f"Patient {form.instance.name} created successfully.")
        return super().form_valid(form)


class PatientUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Patient
    form_class = PatientForm
    permission_required = 'patients.change_patient'

    def get_success_url(self):
        return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        # Store user for tag creation
        form.current_user = self.request.user
        messages.success(self.request, f"Patient {form.instance.name} updated successfully.")
        return super().form_valid(form)


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


