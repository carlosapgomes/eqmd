"""
Views for report CRUD.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView

from apps.patients.models import Patient
from apps.reports.models import Report, ReportTemplate
from apps.reports.forms import ReportCreateForm
from apps.reports.services.report_service import create_report_from_template
from apps.reports.services.context_builder import build_report_context
from apps.reports.services.renderer import render_template


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
            try:
                template = ReportTemplate.objects.get(pk=template_id)
                # Check access
                if template.is_public or template.created_by == self.request.user:
                    # Render template content
                    context = build_report_context(
                        patient=self.patient,
                        doctor=self.request.user,
                        document_date=initial.get('document_date') or __import__('datetime').date.today(),
                    )
                    initial['content'] = render_template(
                        template.markdown_body, context
                    )
                    initial['template'] = template
            except ReportTemplate.DoesNotExist:
                pass

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
