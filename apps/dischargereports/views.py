from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, UpdateView, DetailView, ListView, DeleteView
from .models import DischargeReport
from .forms import DischargeReportForm
from apps.core.permissions import can_edit_event, can_delete_event, can_access_patient
from apps.core.permissions.constants import MEDICAL_DOCTOR, RESIDENT


def can_edit_discharge_report(user, report):
    """
    Check if user can edit discharge report based on business logic:
    - Drafts: Any doctor/resident can edit anytime
    - Final reports: Follow system standards (24h window, creator-only)
    """
    if not can_access_patient(user, report.patient):
        return False
    
    # If it's a draft, any doctor/resident can edit
    if report.is_draft:
        user_profession = getattr(user, 'profession', None)
        return user_profession in [MEDICAL_DOCTOR, RESIDENT]
    
    # If it's final, follow system standards
    return can_edit_event(user, report)


def can_delete_discharge_report(user, report):
    """
    Check if user can delete discharge report based on business logic:
    - Drafts: Any doctor/resident can delete anytime
    - Final reports: Follow system standards (24h window, creator-only)
    """
    if not can_access_patient(user, report.patient):
        return False
    
    # If it's a draft, any doctor/resident can delete
    if report.is_draft:
        user_profession = getattr(user, 'profession', None)
        return user_profession in [MEDICAL_DOCTOR, RESIDENT]
    
    # If it's final, follow system standards
    return can_delete_event(user, report)


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

    def get_initial(self):
        initial = super().get_initial()
        # If patient_id is provided in URL, set the patient
        patient_id = self.kwargs.get('patient_id')
        if patient_id:
            from apps.patients.models import Patient
            try:
                patient = Patient.objects.get(pk=patient_id)
                initial['patient'] = patient
            except Patient.DoesNotExist:
                pass
        return initial

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


class DischargeReportPrintView(LoginRequiredMixin, DetailView):
    """Print-friendly view for discharge reports"""
    model = DischargeReport
    template_name = 'dischargereports/dischargereport_print.html'
    context_object_name = 'report'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        context['user'] = self.request.user
        return context