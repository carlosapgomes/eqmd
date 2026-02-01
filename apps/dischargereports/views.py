import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, UpdateView, DetailView, ListView, DeleteView
from .models import DischargeReport
from .services.pdf_generator import DischargeReportPDFGenerator
from .forms import DischargeReportCreateForm, DischargeReportUpdateForm
from apps.core.permissions import can_edit_event, can_delete_event, can_access_patient
from apps.core.permissions.constants import MEDICAL_DOCTOR, RESIDENT

logger = logging.getLogger(__name__)


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
    - Drafts: Creator or users with delete permission
    - Final reports: Follow system standards or delete permission override
    """
    if not can_access_patient(user, report.patient):
        return False
    
    # If it's a draft, allow creator or delete permission
    if report.is_draft:
        return report.created_by == user or user.has_perm('events.delete_event')

    # If it's final, follow system standards or delete permission override
    return can_delete_event(user, report) or user.has_perm('events.delete_event')


class DischargeReportListView(LoginRequiredMixin, ListView):
    """List all discharge reports"""
    model = DischargeReport
    template_name = 'dischargereports/dischargereport_list.html'
    context_object_name = 'reports'
    paginate_by = 20

    def get_queryset(self):
        return DischargeReport.all_objects.select_related('patient').order_by('-created_at')


class DischargeReportDetailView(LoginRequiredMixin, DetailView):
    """View discharge report details"""
    model = DischargeReport
    template_name = 'dischargereports/dischargereport_detail.html'
    context_object_name = 'report'

    def get_queryset(self):
        return DischargeReport.all_objects.select_related('patient', 'created_by', 'updated_by')

    def get_context_data(self, **kwargs):
        """Add additional context data including permission checks."""
        context = super().get_context_data(**kwargs)

        # Add permission context for template use
        context["can_edit_report"] = can_edit_discharge_report(self.request.user, self.object)
        context["can_delete_report"] = can_delete_discharge_report(self.request.user, self.object)

        return context


class DischargeReportCreateView(LoginRequiredMixin, CreateView):
    """Create new discharge report for a specific patient"""
    model = DischargeReport
    form_class = DischargeReportCreateForm
    template_name = 'dischargereports/dischargereport_create.html'

    def dispatch(self, request, *args, **kwargs):
        """Get patient and check permissions before processing request."""
        from django.shortcuts import get_object_or_404
        from apps.patients.models import Patient
        
        self.patient = get_object_or_404(Patient, pk=kwargs["patient_id"])

        # Check if user can access this patient
        if not can_access_patient(request.user, self.patient):
            raise PermissionDenied(
                "You don't have permission to create discharge reports for this patient"
            )

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass patient to form."""
        kwargs = super().get_form_kwargs()
        kwargs["patient"] = self.patient
        return kwargs

    def get_context_data(self, **kwargs):
        """Add patient context."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.patient
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful creation."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )

    def form_valid(self, form):
        """Handle successful form submission."""
        is_draft = 'save_final' not in self.request.POST

        # Handle draft vs final save
        if is_draft:
            messages.success(self.request, f'Relatório de alta para {self.patient.name} salvo como rascunho.')
        else:
            messages.success(self.request, f'Relatório de alta para {self.patient.name} salvo definitivamente.')

        self.object = form.save(commit=False)
        self.object.patient = self.patient
        self.object.created_by = self.request.user
        self.object.updated_by = self.request.user
        self.object.event_datetime = self.object.event_datetime or timezone.now()
        self.object.is_draft = is_draft
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class DischargeReportUpdateView(LoginRequiredMixin, UpdateView):
    """Update discharge report - separate template"""
    model = DischargeReport
    form_class = DischargeReportUpdateForm
    template_name = 'dischargereports/dischargereport_update.html'
    context_object_name = 'report'

    def get_queryset(self):
        return DischargeReport.all_objects.select_related('patient', 'created_by', 'updated_by')

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

    def get_success_url(self):
        """Redirect to patient timeline after successful update."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.object.patient.pk},
        )

    def form_valid(self, form):
        is_draft = self.object.is_draft

        # Handle draft vs final save
        if 'save_final' in self.request.POST and self.object.is_draft:
            is_draft = False
            messages.success(self.request, 'Relatório de alta finalizado com sucesso.')
        elif 'save_draft' in self.request.POST:
            is_draft = True
            messages.success(self.request, 'Rascunho do relatório atualizado.')
        else:
            messages.success(self.request, 'Relatório de alta atualizado.')

        self.object = form.save(commit=False)
        self.object.updated_by = self.request.user
        self.object.is_draft = is_draft
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class DischargeReportDeleteView(LoginRequiredMixin, DeleteView):
    """Delete discharge report when permitted."""
    model = DischargeReport
    template_name = 'dischargereports/dischargereport_confirm_delete.html'
    context_object_name = 'report'

    def get_queryset(self):
        return DischargeReport.all_objects.select_related('patient', 'created_by', 'updated_by')

    def get_object(self):
        obj = super().get_object()
        if not obj.can_be_deleted_by_user(self.request.user):
            raise PermissionDenied("Este relatório não pode ser excluído.")
        return obj

    def get_success_url(self):
        """Redirect to patient timeline after successful deletion."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.object.patient.pk},
        )

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Relatório de alta excluído com sucesso.')
        return super().delete(request, *args, **kwargs)


class DischargeReportPDFView(LoginRequiredMixin, View):
    """Generate and return PDF for discharge reports."""

    def get(self, request, *args, **kwargs):
        try:
            report = get_object_or_404(DischargeReport.all_objects, pk=kwargs["pk"])

            if not can_access_patient(request.user, report.patient):
                raise PermissionDenied("You don't have permission to access this patient")

            pdf_generator = DischargeReportPDFGenerator()
            pdf_buffer = pdf_generator.generate_from_report(report)

            response = HttpResponse(pdf_buffer.read(), content_type="application/pdf")
            safe_name = "".join(
                c for c in report.patient.name if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            date_str = report.discharge_date.strftime("%Y%m%d")
            filename = f"Relatorio_Alta_{safe_name}_{date_str}.pdf"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        except PermissionDenied:
            raise
        except Exception as exc:
            logger.error("Discharge report PDF generation error: %s", str(exc), exc_info=True)
            return HttpResponse(f"Erro ao gerar PDF: {str(exc)}", status=500)
