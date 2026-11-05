from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DeleteView, DetailView, FormView, ListView, View

from apps.core.permissions.utils import (
    can_access_patient,
    can_delete_event,
    can_edit_event,
    is_doctor_or_resident,
)
from apps.events.services.event_deletion import delete_event_record

from ..models import PDFFormSubmission, PDFFormTemplate
from ..permissions import (
    check_pdf_download_access,
    check_pdf_form_access,
    check_pdf_form_creation,
    check_pdf_form_template_access,
)
from ..security import PDFFormSecurity
from ..services.duplication import (
    build_duplicate_initial_data,
    can_duplicate_pdf_submission,
)
from ..services.form_generator import DynamicFormGenerator
from ..services.pdf_overlay import PDFFormOverlay

DRAFT_APPROVAL_DENIED_MESSAGE = (
    "Apenas médicos e residentes podem aprovar rascunhos de formulários PDF."
)


def visible_pdf_submissions():
    """Active submissions with human drafts, bot drafts excluded (design D3).

    The default manager hides every draft, and bot drafts must stay on their
    own botauth promotion path, so the queryset re-admits human drafts only.
    """
    return (
        PDFFormSubmission.objects.with_drafts()
        .filter(Q(is_draft=False) | Q(draft_created_by_bot=""))
        .select_related("patient", "created_by", "form_template")
    )


class PDFFormTemplateListView(LoginRequiredMixin, ListView):
    """List available PDF form templates for current hospital."""

    model = PDFFormTemplate
    template_name = "pdf_forms/form_template_list.html"
    context_object_name = "form_templates"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Check if user can access PDF form templates
        check_pdf_form_template_access(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            PDFFormTemplate.objects.filter(
                is_active=True,
                hospital_specific=True,  # Only hospital-specific forms
            )
            .exclude(
                form_fields__isnull=True  # Exclude templates without any configuration
            )
            .exclude(
                form_fields__exact={}  # Exclude templates with empty configuration
            )
            .order_by("name")
        )


class PDFFormSelectView(LoginRequiredMixin, View):
    """Select PDF form for a specific patient - supports both hospital and national forms."""

    def get(self, request, patient_id):
        # Check patient access
        from apps.patients.models import Patient

        patient = get_object_or_404(Patient, id=patient_id)

        # Use security permission check
        check_pdf_form_access(request.user, patient)

        # Get available forms (both hospital and national forms)
        form_templates = (
            PDFFormTemplate.objects.filter(is_active=True)
            .exclude(
                form_fields__isnull=True  # Exclude templates without any configuration
            )
            .exclude(
                form_fields__exact={}  # Exclude templates with empty configuration
            )
            .order_by("form_type", "name")
        )

        # Group forms by type
        hospital_forms = [f for f in form_templates if f.form_type == "HOSPITAL"]
        national_forms = [f for f in form_templates if f.is_national_form]

        context = {
            "patient": patient,
            "hospital_forms": hospital_forms,
            "national_forms": national_forms,
        }
        return render(request, "pdf_forms/form_select.html", context)


class PDFFormFillView(LoginRequiredMixin, FormView):
    """Display and handle PDF form filling."""

    template_name = "pdf_forms/form_fill.html"

    def dispatch(self, request, *args, **kwargs):
        # Check authentication first - if not authenticated, LoginRequiredMixin will redirect
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        # Get template and patient
        self.form_template = get_object_or_404(
            PDFFormTemplate, id=kwargs["template_id"], is_active=True
        )

        from apps.patients.models import Patient

        self.patient = get_object_or_404(Patient, id=kwargs["patient_id"])

        # Check permissions using security module
        check_pdf_form_creation(request.user, self.patient)

        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        """Generate form class dynamically based on PDF template."""
        generator = DynamicFormGenerator()
        return generator.generate_form_class(
            self.form_template, self.patient, self.request.user
        )

    def get_initial(self):
        """Get initial data for the form, including auto-fill values."""
        initial = super().get_initial()

        # Generate form class to get auto-fill initial values
        from ..services.form_generator import DynamicFormGenerator

        generator = DynamicFormGenerator()
        form_class = generator.generate_form_class(
            self.form_template, self.patient, self.request.user
        )

        # Add patient/hospital auto-fill initial values
        if hasattr(form_class, "_patient_initial_values"):
            initial.update(form_class._patient_initial_values)

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_template": self.form_template,
                "patient": self.patient,
            }
        )

        # Add linked fields map if available for JavaScript initialization
        form = context.get("form")
        if form and hasattr(form.__class__, "_linked_fields_map"):
            context["linked_fields_map"] = form.__class__._linked_fields_map

        return context

    def post(self, request, *args, **kwargs):
        """Handle POST request with exception handling."""
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:  # noqa: BLE001 - view error path
            messages.error(request, f"Erro ao processar formulário: {e!s}")
            # Return the form with error message
            form = self.get_form()
            return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        """Process form submission and save data only."""
        try:
            # Sanitize form data for security
            sanitized_data = PDFFormSecurity.sanitize_form_data(form.cleaned_data)

            # Create submission record with form data only
            submission = PDFFormSubmission(
                form_template=self.form_template,
                patient=self.patient,
                created_by=self.request.user,
                updated_by=self.request.user,
                event_datetime=timezone.now(),
                description=f"Formulário PDF: {self.form_template.name}",
                form_data=sanitized_data,
            )
            submission.save()

            messages.success(
                self.request,
                f"Formulário '{self.form_template.name}' preenchido com sucesso!",
            )

            return redirect("pdf_forms:submission_detail", pk=submission.pk)

        except ValidationError as e:
            messages.error(self.request, f"Erro de validação: {e!s}")
            return self.form_invalid(form)
        except Exception as e:  # noqa: BLE001 - view error path
            messages.error(self.request, f"Erro ao processar formulário: {e!s}")
            return self.form_invalid(form)


class PDFFormSubmissionUpdateView(LoginRequiredMixin, FormView):
    """Edit a hospital PDF form submission in place.

    Reuses the fill machinery, prefilled from the stored submission, and saves
    the same row. Saving a draft keeps it supervised; a doctor/resident flips
    it with the finalize action (design D5/D8).
    """

    template_name = "pdf_forms/form_fill.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        self.submission = get_object_or_404(
            visible_pdf_submissions(), pk=kwargs["pk"]
        )

        # Hospital dynamic forms only: national forms keep their own capture
        # flow, whose form class carries the real fields.
        if self.submission.form_template.is_national_form:
            raise Http404("Dynamic form submission not found")

        check_pdf_form_access(request.user, self.submission.patient)

        if not can_edit_event(request.user, self.submission):
            raise PermissionDenied(
                "You don't have permission to edit this PDF form submission"
            )

        self.form_template = self.submission.form_template
        self.patient = self.submission.patient

        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        generator = DynamicFormGenerator()
        return generator.generate_form_class(
            self.form_template, self.patient, self.request.user
        )

    def get_initial(self):
        """Prefill the form from the stored submission through the fill service."""
        initial = super().get_initial()

        generator = DynamicFormGenerator()
        form_class = generator.generate_form_class(
            self.form_template,
            self.patient,
            self.request.user,
        )
        initial.update(
            build_duplicate_initial_data(form_class, self.submission.form_data)
        )

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_template": self.form_template,
                "patient": self.patient,
                "submission": self.submission,
                "is_update": True,
                "is_draft_submission": self.submission.is_draft,
                "can_finalize": (
                    self.submission.is_draft
                    and is_doctor_or_resident(self.request.user)
                ),
            }
        )

        form = context.get("form")
        if form and hasattr(form.__class__, "_linked_fields_map"):
            context["linked_fields_map"] = form.__class__._linked_fields_map

        return context

    def _submitted_action(self):
        """Return the supervision action submitted by the form buttons."""
        if "save_final" in self.request.POST:
            return "save_final"
        if "save_draft" in self.request.POST:
            return "save_draft"
        return None

    def post(self, request, *args, **kwargs):
        """Reject a crafted student approval before the error guard."""
        if (
            self.submission.is_draft
            and self._submitted_action() == "save_final"
            and not is_doctor_or_resident(request.user)
        ):
            raise PermissionDenied(DRAFT_APPROVAL_DENIED_MESSAGE)

        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:  # noqa: BLE001 - view error path
            messages.error(request, f"Erro ao processar formulário: {e!s}")
            form = self.get_form()
            return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        """Persist the corrected submission, keeping or promoting its state."""
        action = self._submitted_action()
        was_draft = self.submission.is_draft

        try:
            sanitized_data = PDFFormSecurity.sanitize_form_data(form.cleaned_data)

            submission = self.submission
            submission.form_data = sanitized_data
            submission.updated_by = self.request.user

            if was_draft and action == "save_final":
                submission.is_draft = False
                submission.draft_promoted_at = timezone.now()
                submission.draft_promoted_by = self.request.user
            elif was_draft:
                submission.is_draft = True

            submission.save()

            messages.success(
                self.request,
                f"Formulário '{self.form_template.name}' atualizado com sucesso!",
            )

            return redirect("pdf_forms:submission_detail", pk=submission.pk)

        except ValidationError as e:
            messages.error(self.request, f"Erro de validação: {e!s}")
            return self.form_invalid(form)
        except Exception as e:  # noqa: BLE001 - view error path
            messages.error(self.request, f"Erro ao processar formulário: {e!s}")
            return self.form_invalid(form)


class PDFFormSubmissionDuplicateView(LoginRequiredMixin, FormView):
    """
    Duplicate an existing PDF form submission.

    On GET, renders a new form prefilled from the source submission.
    On valid POST, creates a new ``PDFFormSubmission`` for the same
    patient and template while leaving the source unchanged.
    """

    template_name = "pdf_forms/form_fill.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        self.source = get_object_or_404(
            PDFFormSubmission.objects.select_related(
                "patient",
                "created_by",
                "form_template",
            ),
            pk=kwargs["pk"],
        )

        if not can_duplicate_pdf_submission(request.user, self.source):
            raise PermissionDenied("This submission cannot be duplicated.")

        self.form_template = self.source.form_template
        self.patient = self.source.patient

        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        generator = DynamicFormGenerator()
        return generator.generate_form_class(
            self.form_template,
            self.patient,
            self.request.user,
        )

    def get_initial(self):
        initial = super().get_initial()

        # Start with normal auto-fill values from the form generator
        generator = DynamicFormGenerator()
        form_class = generator.generate_form_class(
            self.form_template,
            self.patient,
            self.request.user,
        )

        # Overlay source form_data values via service
        source_initial = build_duplicate_initial_data(
            form_class,
            self.source.form_data,
        )
        initial.update(source_initial)

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_template": self.form_template,
                "patient": self.patient,
                "is_duplicate": True,
                "source_submission": self.source,
            }
        )

        form = context.get("form")
        if form and hasattr(form.__class__, "_linked_fields_map"):
            context["linked_fields_map"] = form.__class__._linked_fields_map

        return context

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:  # noqa: BLE001 - view error path
            messages.error(
                request,
                f"Erro ao processar formulário: {e!s}",
            )
            form = self.get_form()
            return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        try:
            sanitized_data = PDFFormSecurity.sanitize_form_data(form.cleaned_data)

            submission = PDFFormSubmission(
                form_template=self.form_template,
                patient=self.patient,
                created_by=self.request.user,
                updated_by=self.request.user,
                event_datetime=timezone.now(),
                description=(
                    f"Duplicata: {self.form_template.name}"
                    f" (original: {self.source.event_datetime:%d/%m/%Y})"
                ),
                form_data=sanitized_data,
            )
            submission.save()

            messages.success(
                self.request,
                (
                    f"Duplicata do formulário '"
                    f"{self.form_template.name}' criada com sucesso!"
                ),
            )

            return redirect(
                "pdf_forms:submission_detail",
                pk=submission.pk,
            )

        except ValidationError as e:
            messages.error(
                self.request,
                f"Erro de validação: {e!s}",
            )
            return self.form_invalid(form)
        except Exception as e:  # noqa: BLE001 - view error path
            messages.error(
                self.request,
                f"Erro ao processar formulário: {e!s}",
            )
            return self.form_invalid(form)


class PDFFormSubmissionDetailView(LoginRequiredMixin, DetailView):
    """View completed PDF form submission.

    Human drafts resolve for review (design D8/D10); bot drafts keep their own
    promotion path and stay 404 (design D3).
    """

    model = PDFFormSubmission
    template_name = "pdf_forms/form_submission_detail.html"
    context_object_name = "submission"

    def get_queryset(self):
        return visible_pdf_submissions()

    def get_object(self):
        submission = super().get_object()

        # Check permissions using security module
        check_pdf_form_access(self.request.user, submission.patient)

        return submission

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_delete_submission"] = can_delete_event(
            self.request.user, self.object
        )
        return context


class PDFFormDownloadView(LoginRequiredMixin, View):
    """Generate and download PDF from form data on-the-fly."""

    def get(self, request, submission_id):
        submission = get_object_or_404(PDFFormSubmission, id=submission_id)

        # Check permissions using security module
        check_pdf_download_access(request.user, submission)

        # Validate that form_data exists
        if not submission.form_data:
            raise Http404("Form data not found for PDF generation")

        # Validate that form template and PDF file exist
        if not submission.form_template or not submission.form_template.pdf_file:
            raise Http404("PDF template not found")

        try:
            # Validate template file path for security
            PDFFormSecurity.validate_file_path(submission.form_template.pdf_file.path)

            # Create PDF overlay service
            pdf_service = PDFFormOverlay()

            # Generate secure filename
            timestamp = submission.event_datetime.strftime("%Y%m%d_%H%M%S")
            secure_filename = PDFFormSecurity.generate_secure_filename(
                f"{submission.form_template.name}_{timestamp}.pdf", prefix="pdf_form_"
            )

            # Generate PDF response directly from form data
            response = pdf_service.generate_pdf_response(
                template_path=submission.form_template.pdf_file.path,
                form_data=submission.form_data,
                field_config=submission.form_template.form_fields,
                filename=secure_filename,
            )

            return response

        except ValidationError as e:
            raise PermissionDenied(f"Security validation failed: {e!s}")
        except FileNotFoundError as e:
            raise Http404(f"Template file not found: {e!s}")
        except Exception as e:  # noqa: BLE001 - view error path
            # Log the error for debugging while showing generic message to user
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"PDF generation failed for submission {submission_id}: {e!s}")
            raise Http404("Erro ao gerar PDF. Tente novamente ou contacte o suporte.")


class PDFFormSubmissionDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, DeleteView
):
    """Delete view for PDF form submissions with permission checking."""

    model = PDFFormSubmission
    template_name = "pdf_forms/submission_confirm_delete.html"
    context_object_name = "submission"
    permission_required = "events.delete_event"

    def get_success_url(self):
        """Redirect to patient timeline after successful deletion."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.object.patient.pk},
        )

    def get_object(self, queryset=None):
        """Get object and check patient access and delete permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's PDF forms"
            )

        # Check if user can delete this event
        if not can_delete_event(self.request.user, obj):
            raise PermissionDenied(
                "You don't have permission to delete this PDF form submission"
            )

        return obj

    def get_queryset(self):
        """Resolve definitive submissions and human drafts (bot drafts 404)."""
        return visible_pdf_submissions()

    def form_valid(self, form):
        """Delete the submission by the path its state and history require.

        ``BaseDeleteView.form_valid`` would call ``self.object.delete()``
        directly, so the method decision lives here instead (design D7).
        """
        submission = self.object
        patient_name = submission.patient.name
        form_name = submission.form_template.name
        delete_event_record(submission, deleted_by=self.request.user)
        messages.success(
            self.request,
            f"Formulário '{form_name}' para {patient_name} excluído com sucesso.",
        )
        return redirect(self.get_success_url())
