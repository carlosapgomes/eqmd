"""
Views for report template CRUD.
"""

from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from apps.reports.models import ReportTemplate
from apps.reports.forms import ReportTemplateForm
from apps.reports.services.permissions import can_manage_report_templates
from apps.reports.services.template_tag_projection import template_tag_badges
from apps.reports.services.template_tags import (
    GENERIC_TAG_ERROR_MESSAGE,
    parse_tag_submission,
    save_template_with_tags,
)


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

    def get_context_data(
        self, **kwargs: Any
    ) -> dict[str, Any]:  # Any: Django template context.
        """Attach requester-safe tag badges for the current page only."""
        context = super().get_context_data(**kwargs)
        badges = template_tag_badges(
            actor=self.request.user,
            templates=context['object_list'],
        )
        context['template_tag_badges'] = badges
        for template in context['object_list']:
            template.visible_tag_badges = badges.get(template.pk, [])
        return context


class _TemplateTagFormMixin:
    """Persist template fields and tag associations atomically (design D2)."""

    # Provided by the CreateView/UpdateView bases this mixin is used with.
    request: HttpRequest

    def form_valid(self, form: ReportTemplateForm) -> HttpResponse:
        """Save through the association service; surface a generic tag error."""
        # Capture newness before saving: the service persists the
        # instance, so form.instance is no longer adding afterwards.
        # (The UUID primary key is already assigned on an unsaved
        # instance, so ``pk is None`` cannot be used here.)
        is_new = form.instance._state.adding
        try:
            submitted = parse_tag_submission(self.request.POST)
            save_template_with_tags(
                actor=self.request.user,
                template=form.instance,
                submitted_tag_ids=submitted,
            )
        except ValidationError:
            form.add_error('tag_ids', GENERIC_TAG_ERROR_MESSAGE)
            return self.form_invalid(form)  # type: ignore[attr-defined]  # provided by the view base
        self.object = form.instance
        messages.success(
            self.request,
            f'Template "{form.instance.name}" '
            f'{"created" if is_new else "updated"} successfully.',
        )
        return HttpResponseRedirect(self.get_success_url())  # type: ignore[attr-defined]  # provided by the view base


class TemplateCreateView(LoginRequiredMixin, _TemplateTagFormMixin, CreateView):
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


class TemplateUpdateView(LoginRequiredMixin, _TemplateTagFormMixin, UpdateView):
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


class TemplateDeleteView(LoginRequiredMixin, DeleteView):
    """Delete view for report templates."""

    model = ReportTemplate
    template_name = 'reports/reporttemplate_confirm_delete.html'
    context_object_name = 'template'
    success_url = reverse_lazy('reports:template_list')

    def dispatch(self, request, *args, **kwargs):
        """Check if user can manage templates and is creator."""
        if not can_manage_report_templates(request.user):
            raise PermissionDenied("You don't have permission to manage report templates")

        obj = self.get_object()
        if obj.created_by != request.user:
            raise PermissionDenied("You can only delete your own templates")

        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """Add success message on delete."""
        template = self.get_object()
        messages.success(self.request, f'Template "{template.name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)
