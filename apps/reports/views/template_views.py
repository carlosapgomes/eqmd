"""
Views for report template CRUD.
"""

from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from apps.patients.services import tag_filters, tag_projection
from apps.reports.models import ReportTemplate
from apps.reports.forms import ReportTemplateForm
from apps.reports.services.permissions import can_manage_report_templates
from apps.reports.services import template_discovery
from apps.reports.services.template_tag_projection import template_tag_badges
from apps.reports.services.template_tags import (
    GENERIC_TAG_ERROR_MESSAGE,
    parse_tag_submission,
    save_template_with_tags,
)


class TemplateListView(LoginRequiredMixin, ListView):
    """Catalogue of report templates with tag/name discovery (S2, D4/D5)."""

    model = ReportTemplate
    template_name = 'reports/reporttemplate_list.html'
    results_partial = 'reports/partials/_reporttemplate_results.html'
    context_object_name = 'templates'
    paginate_by = template_discovery.PAGE_SIZE

    discovery: template_discovery.DiscoveryState

    def dispatch(self, request, *args, **kwargs):
        """Resolve discovery state first; malformed filters never query results."""
        self.discovery = template_discovery.resolve_discovery_state(
            request.user, request.GET
        )
        if self.discovery.error:
            return HttpResponse(self.discovery.error, status=400)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Render the full page or the results fragment at the same URL."""
        if template_discovery.is_fragment_request(request.GET):
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            return render(request, self.results_partial, context)
        return super().get(request, *args, **kwargs)

    def paginate_queryset(self, queryset, page_size):
        """Forgiving page normalization: out-of-range pages clamp, not 404."""
        paginator = self.get_paginator(queryset, page_size)
        page_obj = paginator.get_page(self.request.GET.get(self.page_kwarg))
        return (
            paginator,
            page_obj,
            page_obj.object_list,
            page_obj.has_other_pages(),
        )

    def get_queryset(self):
        """Public-or-own base plus the resolved tag/name predicates."""
        base = template_discovery.catalogue_base_queryset(self.request.user)
        return template_discovery.apply_discovery_filters(
            base, self.discovery.selection, self.discovery.name_query
        )

    def get_context_data(
        self, **kwargs: Any
    ) -> dict[str, Any]:  # Any: Django template context.
        """Attach requester-safe badges and the canonical discovery state."""
        context = super().get_context_data(**kwargs)
        badges = template_tag_badges(
            actor=self.request.user,
            templates=context['object_list'],
        )
        context['template_tag_badges'] = badges
        for template in context['object_list']:
            template.visible_tag_badges = badges.get(template.pk, [])
        selection = self.discovery.selection
        query = self.request.GET
        include_historical = template_discovery.parse_include_historical(query)
        context.update(
            {
                'discovery_selection': selection,
                'discovery_name_query': self.discovery.name_query,
                'discovery_warning': self.discovery.warning,
                'discovery_specialty': self.discovery.specialty,
                'discovery_has_saved_preference': (
                    self.discovery.has_saved_preference
                ),
                'discovery_is_manual': selection.is_manual,
                'discovery_state_label': selection.state_label,
                'discovery_mode_label': selection.mode_label,
                'discovery_include_historical': include_historical,
                # S3 selector contract: the reports-owned selector
                # partial consumes the same names as the patient
                # surface (``available_tags``/``selected_tags``) with
                # requester-safe rows plus visible historical identities.
                # All visible identities (historical included) stay in
                # the native fallback select: enhancement disables it and
                # the selector owns lookup-only refreshes from there.
                'tag_selection': selection,
                'selected_tag_ids': list(selection.tag_ids),
                'available_tags': template_discovery.discovery_tag_options(
                    self.request.user,
                    selected_ids=selection.tag_ids,
                    include_historical=True,
                ),
                'available_tag_ids': [
                    option.tag_id
                    for option in template_discovery.discovery_tag_options(
                        self.request.user,
                        selected_ids=selection.tag_ids,
                        include_historical=True,
                    )
                ],
                'selected_tags': [
                    {
                        'badge': tag_projection.tag_badge(tag),
                        'remove_querystring': tag_filters.remove_tag_query(
                            query, selection, tag.pk
                        ),
                    }
                    for tag in selection.tags
                ],
                'clear_tags_querystring': tag_filters.manual_empty_query(
                    query, selection
                ),
                'discovery_tag_options': template_discovery.discovery_tag_options(
                    self.request.user,
                    selected_ids=selection.tag_ids,
                    include_historical=include_historical,
                ),
                'discovery_selected_tags': [
                    {
                        'badge': tag_projection.tag_badge(tag),
                        'remove_querystring': tag_filters.remove_tag_query(
                            query, selection, tag.pk
                        ),
                    }
                    for tag in selection.tags
                ],
                'discovery_filter_querystring': tag_filters.encoded_query(
                    query, selection
                ),
                'discovery_clear_querystring': tag_filters.manual_empty_query(
                    query, selection
                ),
                'discovery_reapply_querystring': tag_filters.effective_query(
                    query, tag_filters.TagFilterSelection()
                ).urlencode(),
            }
        )
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
