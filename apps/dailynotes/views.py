from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from .models import DailyNote
from .forms import DailyNoteForm
from apps.core.permissions import (
    patient_access_required,
    can_edit_event_required,
    can_delete_event_required,
    hospital_context_required,
    can_access_patient,
    can_edit_event,
    can_delete_event
)


@method_decorator(hospital_context_required, name='dispatch')
class DailyNoteListView(LoginRequiredMixin, ListView):
    """
    List view for DailyNote instances with search and filtering capabilities.
    """
    model = DailyNote
    template_name = 'dailynotes/dailynote_list.html'
    context_object_name = 'dailynotes'
    paginate_by = 20

    def get_queryset(self):
        """Filter queryset based on search parameters and user permissions."""
        queryset = DailyNote.objects.select_related('patient', 'created_by').all()

        # Filter by user's hospital context and patient access permissions
        if hasattr(self.request.user, 'current_hospital') and self.request.user.current_hospital:
            # Only show daily notes for patients in the user's current hospital
            queryset = queryset.filter(patient__current_hospital=self.request.user.current_hospital)

        # Further filter based on patient access permissions
        accessible_patients = []
        for dailynote in queryset:
            if can_access_patient(self.request.user, dailynote.patient):
                accessible_patients.append(dailynote.patient.id)

        if accessible_patients:
            queryset = queryset.filter(patient__id__in=accessible_patients)
        else:
            queryset = queryset.none()

        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(description__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(patient__name__icontains=search_query)
            )

        # Filter by patient if specified
        patient_id = self.request.GET.get('patient')
        if patient_id:
            queryset = queryset.filter(patient__id=patient_id)

        return queryset.order_by('-event_datetime')

    def get_context_data(self, **kwargs):
        """Add additional context data including permission checks for each daily note."""
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_patient'] = self.request.GET.get('patient', '')

        # Add permission information for each daily note
        if 'dailynote_list' in context:
            for dailynote in context['dailynote_list']:
                dailynote.can_edit = can_edit_event(self.request.user, dailynote)
                dailynote.can_delete = can_delete_event(self.request.user, dailynote)

        return context


@method_decorator(hospital_context_required, name='dispatch')
class DailyNoteDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detail view for DailyNote instances.
    """
    model = DailyNote
    template_name = 'dailynotes/dailynote_detail.html'
    context_object_name = 'dailynote'
    permission_required = 'events.view_event'

    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to access this patient's daily notes")

        return obj

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return DailyNote.objects.select_related('patient', 'created_by', 'updated_by')

    def get_context_data(self, **kwargs):
        """Add additional context data including permission checks."""
        context = super().get_context_data(**kwargs)

        # Add permission context for template use
        context['can_edit_dailynote'] = can_edit_event(self.request.user, self.object)
        context['can_delete_dailynote'] = can_delete_event(self.request.user, self.object)

        return context


@method_decorator(hospital_context_required, name='dispatch')
class DailyNoteCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Create view for DailyNote instances.
    """
    model = DailyNote
    form_class = DailyNoteForm
    template_name = 'dailynotes/dailynote_form.html'
    permission_required = 'events.add_event'

    def get_form_kwargs(self):
        """Pass current user to form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        """Redirect to detail view after successful creation."""
        return reverse_lazy('dailynotes:dailynote_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        """Handle successful form submission with patient access validation."""
        # Check if user can access the selected patient
        if not can_access_patient(self.request.user, form.instance.patient):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to create daily notes for this patient")

        messages.success(
            self.request,
            f"Evolução para {form.instance.patient.name} criada com sucesso."
        )
        return super().form_valid(form)


@method_decorator(hospital_context_required, name='dispatch')
class DailyNoteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Update view for DailyNote instances with permission checking.
    """
    model = DailyNote
    form_class = DailyNoteForm
    template_name = 'dailynotes/dailynote_form.html'
    permission_required = 'events.change_event'

    def get_object(self, queryset=None):
        """Get object and check patient access and edit permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to access this patient's daily notes")

        # Check if user can edit this event
        if not can_edit_event(self.request.user, obj):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to edit this daily note")

        return obj

    def get_form_kwargs(self):
        """Pass current user to form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        """Redirect to detail view after successful update."""
        return reverse_lazy('dailynotes:dailynote_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        """Handle successful form submission with patient access validation."""
        # Check if user can access the selected patient (in case patient was changed)
        if not can_access_patient(self.request.user, form.instance.patient):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to create daily notes for this patient")

        messages.success(
            self.request,
            f"Evolução para {form.instance.patient.name} atualizada com sucesso."
        )
        return super().form_valid(form)


@method_decorator(hospital_context_required, name='dispatch')
class DailyNoteDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Delete view for DailyNote instances with permission checking.
    """
    model = DailyNote
    template_name = 'dailynotes/dailynote_confirm_delete.html'
    context_object_name = 'dailynote'
    permission_required = 'events.delete_event'
    success_url = reverse_lazy('dailynotes:dailynote_list')

    def get_object(self, queryset=None):
        """Get object and check patient access and delete permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to access this patient's daily notes")

        # Check if user can delete this event
        if not can_delete_event(self.request.user, obj):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to delete this daily note")

        return obj

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return DailyNote.objects.select_related('patient', 'created_by')

    def delete(self, request, *args, **kwargs):
        """Handle successful deletion."""
        dailynote = self.get_object()
        patient_name = dailynote.patient.name
        messages.success(
            request,
            f"Evolução para {patient_name} excluída com sucesso."
        )
        return super().delete(request, *args, **kwargs)
