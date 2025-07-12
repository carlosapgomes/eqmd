from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q, Case, When, IntegerField
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views import View

from .models import Patient, AllowedTag
from .forms import PatientForm, AllowedTagForm
# from apps.hospitals.models import Hospital  # Removed for single-hospital refactor
from apps.core.permissions.utils import can_access_patient, can_change_patient_personal_data


class PatientListView(LoginRequiredMixin, ListView):
    model = Patient
    paginate_by = 10

    def get_queryset(self):
        from apps.core.permissions.utils import get_user_accessible_patients
        
        # Use simplified permission-based filtering (no hospital context)
        queryset = get_user_accessible_patients(self.request.user)
        if queryset is None:
            queryset = super().get_queryset().none()
        
        # Add optimized select_related and prefetch_related (no hospital fields)
        queryset = queryset.select_related('created_by').prefetch_related('tags__allowed_tag')
        
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
        # Simple context without hospital-related logic
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
        """Pass form kwargs without hospital record data"""
        kwargs = super().get_form_kwargs()
        # No hospital record data processing needed
        return kwargs

    def get_context_data(self, **kwargs):
        """Add simple context without hospital record forms"""
        context = super().get_context_data(**kwargs)
        # No hospital record context needed
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
    permission_required = 'patients.change_patient'

    def get_form_kwargs(self):
        """Pass form kwargs without hospital record data"""
        kwargs = super().get_form_kwargs()
        # No hospital record data processing needed
        return kwargs

    def get_context_data(self, **kwargs):
        """Add simple context without hospital record forms"""
        context = super().get_context_data(**kwargs)
        # No hospital record context needed
        return context

    def get_success_url(self):
        return reverse_lazy('patients:patient_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        # Store user for tag creation
        form.current_user = self.request.user
        
        response = super().form_valid(form)
        
        # Add simple success message
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
# (Hospital record API views removed for single-hospital refactor)


