"""
Views for report template CRUD.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView

from apps.reports.models import ReportTemplate
from apps.reports.forms import ReportTemplateForm
from apps.reports.services.permissions import can_manage_report_templates


class TemplateListView(LoginRequiredMixin, ListView):
    """List view for report templates."""

    model = ReportTemplate
    template_name = 'reports/reporttemplate_list.html'
    context_object_name = 'templates'
    paginate_by = 20

    def get_queryset(self):
        """Filter to show public templates and user's own private templates."""
        queryset = ReportTemplate.objects.select_related('created_by', 'updated_by')
        return queryset.filter(is_public=True) | queryset.filter(created_by=self.request.user)


class TemplateCreateView(LoginRequiredMixin, CreateView):
    """Create view for report templates."""

    model = ReportTemplate
    form_class = ReportTemplateForm
    template_name = 'reports/reporttemplate_form.html'
    success_url = reverse_lazy('reports:template_list')

    def dispatch(self, request, *args, **kwargs):
        """Check if user can manage templates."""
        if not can_manage_report_templates(request.user):
            raise PermissionDenied("You don't have permission to manage report templates")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass user to form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Add success message on valid form."""
        messages.success(self.request, f'Template "{form.instance.name}" created successfully.')
        return super().form_valid(form)


class TemplateUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for report templates."""

    model = ReportTemplate
    form_class = ReportTemplateForm
    template_name = 'reports/reporttemplate_form.html'
    success_url = reverse_lazy('reports:template_list')

    def dispatch(self, request, *args, **kwargs):
        """Check if user can manage templates and is creator or admin."""
        if not can_manage_report_templates(request.user):
            raise PermissionDenied("You don't have permission to manage report templates")

        obj = self.get_object()
        is_creator = obj.created_by == request.user
        is_admin = request.user.is_staff or request.user.is_superuser

        if not is_creator and not is_admin:
            raise PermissionDenied("You can only edit your own templates")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass user to form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Add success message on valid form."""
        messages.success(self.request, f'Template "{form.instance.name}" updated successfully.')
        return super().form_valid(form)
