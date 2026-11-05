import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.core.permissions import can_access_patient
from apps.core.permissions.utils import is_doctor_or_resident
from apps.events.services.event_deletion import delete_event_record

from .forms import (
    DischargeReportCreateForm,
    DischargeReportDuplicateForm,
    DischargeReportUpdateForm,
)
from .models import DischargeReport
from .services.pdf_generator import DischargeReportPDFGenerator
from .services.permissions import (
    can_delete_discharge_report,
    can_edit_discharge_report,
)

logger = logging.getLogger(__name__)

FINALIZE_DENIED_MESSAGE = (
    "Apenas médicos e residentes podem finalizar ou reverter relatórios de alta."
)


def _deny_non_physician_finalization(user, *, finalizing=False, reverting=False):
    """Server gate for finalize and revert-finalize actions (design D5).

    Template hiding is role-aware UX only; this predicate is the authorization
    boundary on the create, duplicate and update paths.
    """
    if not (finalizing or reverting):
        return
    if not is_doctor_or_resident(user):
        raise PermissionDenied(FINALIZE_DENIED_MESSAGE)


def visible_discharge_reports():
    """Active discharge reports with human drafts, bot drafts excluded (D3).

    The default manager hides every draft, and bot drafts must stay on their
    own botauth promotion path, so the queryset re-admits human drafts only.
    """
    return (
        DischargeReport.objects.with_drafts()
        .filter(Q(is_draft=False) | Q(draft_created_by_bot=""))
        .select_related("patient", "created_by", "updated_by")
    )


class DischargeReportListView(LoginRequiredMixin, ListView):
    """List all discharge reports"""

    model = DischargeReport
    template_name = "dischargereports/dischargereport_list.html"
    context_object_name = "reports"
    paginate_by = 20

    def get_queryset(self):
        # with_drafts(): drafts are visible in the UI, but soft-deleted reports
        # must stay hidden (soft-delete retention contract).
        return (
            DischargeReport.objects.with_drafts()
            .select_related("patient")
            .order_by("-created_at")
        )


class DischargeReportDetailView(LoginRequiredMixin, DetailView):
    """View discharge report details"""

    model = DischargeReport
    template_name = "dischargereports/dischargereport_detail.html"
    context_object_name = "report"

    def get_queryset(self):
        """Resolve finals and human drafts (bot drafts stay 404)."""
        return visible_discharge_reports()

    def get_context_data(self, **kwargs):
        """Add additional context data including permission checks."""
        context = super().get_context_data(**kwargs)

        # Add permission context for template use
        context["can_edit_report"] = can_edit_discharge_report(
            self.request.user, self.object
        )
        context["can_delete_report"] = can_delete_discharge_report(
            self.request.user, self.object
        )

        return context


class DischargeReportCreateView(LoginRequiredMixin, CreateView):
    """Create new discharge report for a specific patient"""

    model = DischargeReport
    form_class = DischargeReportCreateForm
    template_name = "dischargereports/dischargereport_create.html"

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
        context["can_finalize"] = is_doctor_or_resident(self.request.user)
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful creation."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )

    def form_valid(self, form):
        """Handle successful form submission."""
        _deny_non_physician_finalization(
            self.request.user, finalizing="save_final" in self.request.POST
        )
        is_draft = "save_final" not in self.request.POST

        # Handle draft vs final save
        if is_draft:
            messages.success(
                self.request,
                f"Relatório de alta para {self.patient.name} salvo como rascunho.",
            )
        else:
            messages.success(
                self.request,
                f"Relatório de alta para {self.patient.name} salvo definitivamente.",
            )

        self.object = form.save(commit=False)
        self.object.patient = self.patient
        self.object.created_by = self.request.user
        self.object.updated_by = self.request.user
        self.object.event_datetime = self.object.event_datetime or timezone.now()
        self.object.is_draft = is_draft
        if not is_draft:
            # A report finalized straight from the create form records the same
            # metadata as a draft-to-final flip (spec R7/"finalizing SHALL
            # record"); only the access gate in ``dispatch`` decides who may
            # create it.
            self.object.finalized_at = timezone.now()
            self.object.finalized_by = self.request.user
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class DischargeReportDuplicateView(LoginRequiredMixin, CreateView):
    """Duplicate an existing discharge report into a new, independent report."""

    model = DischargeReport
    form_class = DischargeReportDuplicateForm
    template_name = "dischargereports/dischargereport_duplicate.html"

    def dispatch(self, request, *args, **kwargs):
        """Load the source report and check patient access (design D1)."""
        self.source = get_object_or_404(
            visible_discharge_reports(), pk=kwargs["pk"]
        )
        self.patient = self.source.patient

        if not can_access_patient(request.user, self.patient):
            raise PermissionDenied(
                "You don't have permission to create discharge reports for this patient"
            )

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Bind the patient and hand the source to the duplication form."""
        kwargs = super().get_form_kwargs()
        kwargs["patient"] = self.patient
        kwargs["source"] = self.source
        return kwargs

    def get_context_data(self, **kwargs):
        """Add the patient and the duplicated report to the context."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.patient
        context["source"] = self.source
        context["can_finalize"] = is_doctor_or_resident(self.request.user)
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful duplication."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )

    def form_valid(self, form):
        """Create the copy with the create-form draft/final semantics (D2)."""
        _deny_non_physician_finalization(
            self.request.user, finalizing="save_final" in self.request.POST
        )
        is_draft = "save_final" not in self.request.POST

        if is_draft:
            messages.success(
                self.request,
                f"Relatório de alta para {self.patient.name} duplicado como rascunho.",
            )
        else:
            messages.success(
                self.request,
                f"Relatório de alta para {self.patient.name} duplicado e salvo definitivamente.",
            )

        self.object = form.save(commit=False)
        self.object.patient = self.patient
        self.object.created_by = self.request.user
        self.object.updated_by = self.request.user
        self.object.event_datetime = self.object.event_datetime or timezone.now()
        self.object.is_draft = is_draft
        if not is_draft:
            # The copy records its own finalization; the source's metadata is
            # never carried over (D2).
            self.object.finalized_at = timezone.now()
            self.object.finalized_by = self.request.user
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class DischargeReportUpdateView(LoginRequiredMixin, UpdateView):
    """Update discharge report - separate template"""

    model = DischargeReport
    form_class = DischargeReportUpdateForm
    template_name = "dischargereports/dischargereport_update.html"
    context_object_name = "report"

    def get_queryset(self):
        """Resolve finals and human drafts (bot drafts stay 404)."""
        return visible_discharge_reports()

    def get_object(self):
        obj = super().get_object()
        # The bound form copies the hidden ``is_draft`` field onto this
        # instance during validation; keep the persisted status for the
        # action dispatch and the re-rendered form.
        self.was_draft = obj.is_draft
        # Check if user can edit this specific report
        if not obj.can_be_edited_by_user(self.request.user):
            if obj.is_draft:
                raise PermissionDenied(
                    "Você não tem permissão para editar este rascunho."
                )
            else:
                raise PermissionDenied("Este relatório não pode mais ser editado.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_finalize"] = self.object.is_draft and is_doctor_or_resident(
            self.request.user
        )
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful update."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.object.patient.pk},
        )

    def _submitted_action(self):
        """Return the update action submitted by the form buttons.

        ``save_draft``/``save_final`` come from the draft form;
        ``update_final`` from the finalized-report form, whose single button
        keeps the report finalized.
        """
        if "save_final" in self.request.POST:
            return "save_final"
        if "save_draft" in self.request.POST:
            return "save_draft"
        if "update_final" in self.request.POST:
            return "update_final"
        return None

    def _invalid_action_message(self):
        """Name the actions the update form offers for the stored status."""
        if self.was_draft:
            return "Ação inválida. Use 'Salvar Rascunho' ou 'Salvar Definitivo'."
        return "Ação inválida. Use 'Atualizar'."

    def form_valid(self, form):
        action = self._submitted_action()
        is_draft = self.was_draft

        # Finalizing a draft and reverting a final are physician acts; the
        # template hides the buttons, this gate enforces it (design D5).
        _deny_non_physician_finalization(
            self.request.user,
            finalizing=action == "save_final" and is_draft,
            reverting=action == "save_draft" and not is_draft,
        )

        if action is None:
            # Restore the persisted status the bound form copied onto the
            # shared instance, so the error page keeps the matching actions.
            self.object.is_draft = is_draft
            form.add_error(None, self._invalid_action_message())
            return self.form_invalid(form)

        # Handle draft vs final save
        finalized_now = False
        if action == "save_final" and is_draft:
            is_draft = False
            finalized_now = True
            messages.success(self.request, "Relatório de alta finalizado com sucesso.")
        elif action == "save_draft":
            is_draft = True
            messages.success(self.request, "Rascunho do relatório atualizado.")
        else:
            messages.success(self.request, "Relatório de alta atualizado.")

        self.object = form.save(commit=False)
        self.object.updated_by = self.request.user
        self.object.is_draft = is_draft
        if finalized_now:
            # Draft-to-final flip anchors the correction window at finalization.
            self.object.finalized_at = timezone.now()
            self.object.finalized_by = self.request.user
        # Reverting to draft RETAINS ``finalized_at/by`` untouched as the
        # last-finalization record (design D5): the loaded values pass through
        # ``form.save`` unchanged, so ever-finalized state stays derivable for
        # the deletion method (design D7) without new persistence.
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class DischargeReportDeleteView(LoginRequiredMixin, DeleteView):
    """Delete discharge report when permitted."""

    model = DischargeReport
    template_name = "dischargereports/dischargereport_confirm_delete.html"
    context_object_name = "report"

    def get_queryset(self):
        """Resolve finals and human drafts (bot drafts stay 404)."""
        return visible_discharge_reports()

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

    def form_valid(self, form):
        """Delete by the path the record's history requires (design D7).

        ``BaseDeleteView.form_valid`` would call ``self.object.delete()``
        directly, so the method decision lives here instead: never-finalized
        drafts lose the row, finals and reverted drafts keep soft-delete.
        """
        report = self.object
        delete_event_record(report, deleted_by=self.request.user)
        messages.success(self.request, "Relatório de alta excluído com sucesso.")
        return HttpResponseRedirect(self.get_success_url())


class DischargeReportPDFView(LoginRequiredMixin, View):
    """Generate and return PDF for discharge reports."""

    def get(self, request, *args, **kwargs):
        try:
            report = get_object_or_404(DischargeReport.objects, pk=kwargs["pk"])

            if not can_access_patient(request.user, report.patient):
                raise PermissionDenied(
                    "You don't have permission to access this patient"
                )

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
        except (PermissionDenied, Http404):
            raise
        except Exception as exc:
            logger.exception("Discharge report PDF generation error")
            return HttpResponse(f"Erro ao gerar PDF: {exc!s}", status=500)
