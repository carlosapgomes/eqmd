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
import uuid

from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponse
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
from apps.patients.services import tag_filters, tag_projection
from apps.reports.services import template_discovery
from apps.reports.services.report_service import get_template_for_initial_content
from apps.reports.services.template_tag_projection import template_tag_badges


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
        """Get patient, resolve discovery and reject malformed filters."""
        self.patient = get_object_or_404(
            Patient, pk=self.kwargs['patient_id']
        )
        if not request.user.is_authenticated:
            # Let LoginRequiredMixin issue the redirect before any
            # discovery query is built with an anonymous actor.
            return super().dispatch(request, *args, **kwargs)
        self.discovery = template_discovery.resolve_discovery_state(
            request.user, request.GET
        )
        if self.discovery.error:
            return HttpResponse(self.discovery.error, status=400)
        self._selection_page, self._selected_template = self._resolve_selection()
        return super().dispatch(request, *args, **kwargs)

    def _resolve_selection(self):
        """Page of selectable templates plus the separately pinned choice.

        The current choice comes from the GET prefill parameter on an
        unbound form and from the submitted value on a bound form. It
        is revalidated against current selectable eligibility on every
        request; an unavailable choice is reported generically.
        """
        base = template_discovery.selectable_base_queryset(self.request.user)
        filtered = template_discovery.apply_discovery_filters(
            base, self.discovery.selection, self.discovery.name_query
        )
        paginator = Paginator(filtered, template_discovery.PAGE_SIZE)
        page_obj = paginator.get_page(self.request.GET.get('page'))
        if self.request.method == 'POST':
            raw = self.request.POST.get('template')
        else:
            raw = self.request.GET.get('template')
        selected = None
        unavailable = False
        if raw:
            try:
                selected_uuid = uuid.UUID(str(raw))
            except (ValueError, AttributeError, TypeError):
                unavailable = True
            else:
                selected = base.filter(pk=selected_uuid).first()
                if selected is None:
                    unavailable = True
        self._selected_unavailable = unavailable
        self._selected_raw = str(raw or '')
        return page_obj, selected

    def get_form_kwargs(self):
        """Pass user, patient and bounded selector page to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['patient'] = self.patient
        kwargs['selection_templates'] = list(self._selection_page.object_list)
        kwargs['selected_template'] = self._selected_template
        kwargs['selected_template_id'] = self._selected_raw
        kwargs['selected_unavailable'] = self._selected_unavailable
        return kwargs

    def get_context_data(self, **kwargs):
        """Add patient, discovery state and bounded selection context."""
        context = super().get_context_data(**kwargs)
        context['patient'] = self.patient
        templates = list(self._selection_page.object_list)
        badges = template_tag_badges(
            actor=self.request.user, templates=templates
        )
        context['template_tag_badges'] = badges
        for template in templates:
            template.visible_tag_badges = badges.get(template.pk, [])
        selection = self.discovery.selection
        query = self.request.GET
        include_historical = template_discovery.parse_include_historical(query)
        page_ids = {template.pk for template in templates}
        selected = self._selected_template
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
                # S4 isolation: report creation keeps its accepted native
                # select (`selector_plain`, no `data-tag-selector` root, no
                # enhancement) + JSON controller (S4 starting point). The
                # shared filter form renders the native `discovery_tag_options`
                # select here, so the catalogue-only selector names below are
                # intentionally NOT computed (P2: skips two extra
                # `discovery_tag_options` calls per creation GET).
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
                'selection_templates': templates,
                'selection_page_obj': self._selection_page,
                'selection_count': self._selection_page.paginator.count,
                'selected_template': selected,
                'selected_template_badges': (
                    template_tag_badges(
                        actor=self.request.user, templates=[selected]
                    ).get(selected.pk, [])
                    if selected is not None
                    else []
                ),
                'selected_template_unavailable': self._selected_unavailable,
                'selected_template_outside_results': bool(
                    selected is not None and selected.pk not in page_ids
                ),
            }
        )
        return context

    def get_initial(self):
        """Set initial content if template is selected via GET.

        Only a currently selectable template (active public-or-own,
        the S2 selectable semantics) may prefill title/content. An
        unavailable identity is left for the generic-unavailable
        notice and the full validation queryset, revealing no name
        or rendered body and without clearing the submitted identity.
        """
        initial = super().get_initial()
        template_id = self.request.GET.get('template')

        if template_id:
            try:
                template_uuid = uuid.UUID(str(template_id))
            except (ValueError, AttributeError, TypeError):
                return initial
            selectable = template_discovery.selectable_base_queryset(
                self.request.user
            ).filter(pk=template_uuid)
            if not selectable.exists():
                return initial
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
