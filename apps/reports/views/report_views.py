"""
Views for report CRUD.
"""
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, DetailView, UpdateView, DeleteView
from django.utils import timezone

from apps.core.permissions import can_access_patient
from apps.patients.models import Patient
from apps.reports.models import Report
from apps.reports.forms import (
    ReportCreateForm,
    ReportDuplicateForm,
    ReportUpdateForm,
)
from apps.reports.services.report_service import get_template_for_initial_content


class ReportDetailView(LoginRequiredMixin, DetailView):
    """Detail view for reports."""

    model = Report
    template_name = 'reports/report_detail.html'
    context_object_name = 'report'

    def get_context_data(self, **kwargs):
        """Add markdown rendering context."""
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        return context


class ReportUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update view for reports."""

    model = Report
    form_class = ReportUpdateForm
    template_name = 'reports/report_update_form.html'
    context_object_name = 'report'

    def test_func(self):
        """Check if user can edit report (creator and within 24h)."""
        report = self.get_object()
        return (
            report.created_by == self.request.user
            and report.can_be_edited
        )

    def get_context_data(self, **kwargs):
        """Add patient to context."""
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        return context

    def form_valid(self, form):
        """Add success message on valid form."""
        messages.success(
            self.request,
            f'Report "{form.instance.title}" updated successfully.'
        )
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect to patient timeline after update."""
        return reverse(
            'patients:patient_events_timeline',
            kwargs={'patient_id': self.object.patient.pk}
        )


class ReportDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete view for reports."""

    model = Report
    template_name = 'reports/report_confirm_delete.html'
    context_object_name = 'report'

    def test_func(self):
        """Check if user can delete report (creator and within 24h)."""
        report = self.get_object()
        return (
            report.created_by == self.request.user
            and report.can_be_edited
        )

    def get_context_data(self, **kwargs):
        """Add patient to context."""
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        return context

    def delete(self, request, *args, **kwargs):
        """Add success message on delete."""
        messages.success(
            self.request,
            f'Report "{self.get_object().title}" deleted successfully.'
        )
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        """Redirect to patient timeline after deletion."""
        return reverse(
            'patients:patient_events_timeline',
            kwargs={'patient_id': self.object.patient.pk}
        )


class ReportCreateView(LoginRequiredMixin, CreateView):
    """Create view for reports."""

    model = Report
    form_class = ReportCreateForm
    template_name = 'reports/report_create_form.html'

    def dispatch(self, request, *args, **kwargs):
        """Get patient from URL and store it."""
        self.patient = get_object_or_404(
            Patient, pk=self.kwargs['patient_id']
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass user and patient to form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['patient'] = self.patient
        return kwargs

    def get_context_data(self, **kwargs):
        """Add patient to context."""
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        return context

    def get_initial(self):
        """Set initial content if template is selected via GET."""
        initial = super().get_initial()
        template_id = self.request.GET.get('template')

        if template_id:
            doc_date = initial.get('document_date')
            if isinstance(doc_date, str):
                try:
                    doc_date = datetime.strptime(doc_date, "%m-%d-%Y").date()
                except ValueError:
                    doc_date = None
            if not doc_date:
                doc_date = timezone.localdate()
            template, content = get_template_for_initial_content(
                template_id, self.request.user, self.patient, doc_date
            )
            if template:
                initial['content'] = content
                initial['template'] = template
                initial.setdefault('title', template.name)
                initial['document_date'] = doc_date

        return initial

    def form_valid(self, form):
        """Add success message on valid form."""
        messages.success(
            self.request,
            f'Report "{form.instance.title}" created successfully.'
        )
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect to patient timeline after creation."""
        return reverse(
            'patients:patient_events_timeline',
            kwargs={'patient_id': self.patient.pk}
        )


class ReportDuplicateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Duplicate an existing report into a new, independent report."""

    model = Report
    form_class = ReportDuplicateForm
    template_name = 'reports/report_duplicate_form.html'
    permission_required = 'events.add_event'

    def dispatch(self, request, *args, **kwargs):
        """Load the source report and check patient access."""
        self.source_report = get_object_or_404(Report, pk=kwargs['pk'])

        if not can_access_patient(request.user, self.source_report.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's reports"
            )

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pre-fill the form from the source report and bind the patient."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['patient'] = self.source_report.patient
        kwargs['initial'] = {
            'title': self.source_report.title,
            'content': self.source_report.content,
        }
        return kwargs

    def get_context_data(self, **kwargs):
        """Add source report and patient to the context."""
        context = super().get_context_data(**kwargs)
        context['source_report'] = self.source_report
        context['patient'] = self.source_report.patient
        return context

    def form_valid(self, form):
        """Create the copy for the source patient and report success."""
        form.instance.patient = self.source_report.patient
        messages.success(
            self.request,
            f'Relatório duplicado para {self.source_report.patient.name} criado com base no relatório anterior.',
        )
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect to the source patient's timeline after creation."""
        return reverse(
            'patients:patient_events_timeline',
            kwargs={'patient_id': self.source_report.patient.pk}
        )
