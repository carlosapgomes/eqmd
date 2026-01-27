from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, FormView, View, DeleteView
from django.http import HttpResponse, Http404, FileResponse
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from io import BytesIO

from apps.core.permissions.decorators import patient_access_required
from apps.core.permissions.utils import can_access_patient, can_delete_event
from ..models import PDFFormTemplate, PDFFormSubmission
from ..services.form_generator import DynamicFormGenerator
from ..services.pdf_overlay import PDFFormOverlay
from ..permissions import (
    check_pdf_form_access, 
    check_pdf_form_creation,
    check_pdf_form_template_access,
    check_pdf_download_access
)
from ..security import PDFFormSecurity


class PDFFormTemplateListView(LoginRequiredMixin, ListView):
    """List available PDF form templates for current hospital."""

    model = PDFFormTemplate
    template_name = 'pdf_forms/form_template_list.html'
    context_object_name = 'form_templates'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Check if user can access PDF form templates
        check_pdf_form_template_access(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return PDFFormTemplate.objects.filter(
            is_active=True,
            hospital_specific=True  # Only hospital-specific forms
        ).exclude(
            form_fields__isnull=True  # Exclude templates without any configuration
        ).exclude(
            form_fields__exact={}  # Exclude templates with empty configuration
        ).order_by('name')


class PDFFormSelectView(LoginRequiredMixin, View):
    """Select PDF form for a specific patient - supports both hospital and national forms."""

    def get(self, request, patient_id):
        # Check patient access
        from apps.patients.models import Patient
        patient = get_object_or_404(Patient, id=patient_id)

        # Use security permission check
        check_pdf_form_access(request.user, patient)

        # Get available forms (both hospital and national forms)
        form_templates = PDFFormTemplate.objects.filter(
            is_active=True
        ).exclude(
            form_fields__isnull=True  # Exclude templates without any configuration
        ).exclude(
            form_fields__exact={}  # Exclude templates with empty configuration
        ).order_by('form_type', 'name')

        # Group forms by type
        hospital_forms = [f for f in form_templates if f.form_type == 'HOSPITAL']
        national_forms = [f for f in form_templates if f.is_national_form]

        context = {
            'patient': patient,
            'hospital_forms': hospital_forms,
            'national_forms': national_forms,
        }
        return render(request, 'pdf_forms/form_select.html', context)


class PDFFormFillView(LoginRequiredMixin, FormView):
    """Display and handle PDF form filling."""

    template_name = 'pdf_forms/form_fill.html'

    def dispatch(self, request, *args, **kwargs):
        # Check authentication first - if not authenticated, LoginRequiredMixin will redirect
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
            
        # Get template and patient
        self.form_template = get_object_or_404(
            PDFFormTemplate,
            id=kwargs['template_id'],
            is_active=True
        )

        from apps.patients.models import Patient
        self.patient = get_object_or_404(Patient, id=kwargs['patient_id'])

        # Check permissions using security module
        check_pdf_form_creation(request.user, self.patient)

        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        """Generate form class dynamically based on PDF template."""
        generator = DynamicFormGenerator()
        return generator.generate_form_class(self.form_template, self.patient, self.request.user)

    def get_initial(self):
        """Get initial data for the form, including auto-fill values."""
        initial = super().get_initial()
        
        # Generate form class to get auto-fill initial values  
        from ..services.form_generator import DynamicFormGenerator
        generator = DynamicFormGenerator()
        form_class = generator.generate_form_class(self.form_template, self.patient, self.request.user)
        
        # Add patient/hospital auto-fill initial values
        if hasattr(form_class, '_patient_initial_values'):
            initial.update(form_class._patient_initial_values)
            
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form_template': self.form_template,
            'patient': self.patient,
        })

        # Add linked fields map if available for JavaScript initialization
        form = context.get('form')
        if form and hasattr(form.__class__, '_linked_fields_map'):
            context['linked_fields_map'] = form.__class__._linked_fields_map

        return context

    def post(self, request, *args, **kwargs):
        """Handle POST request with exception handling."""
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            messages.error(
                request,
                f"Erro ao processar formulário: {str(e)}"
            )
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
                f"Formulário '{self.form_template.name}' preenchido com sucesso!"
            )

            return redirect('pdf_forms:submission_detail', pk=submission.pk)

        except ValidationError as e:
            messages.error(
                self.request,
                f"Erro de validação: {str(e)}"
            )
            return self.form_invalid(form)
        except Exception as e:
            messages.error(
                self.request,
                f"Erro ao processar formulário: {str(e)}"
            )
            return self.form_invalid(form)


class PDFFormSubmissionDetailView(LoginRequiredMixin, DetailView):
    """View completed PDF form submission."""

    model = PDFFormSubmission
    template_name = 'pdf_forms/form_submission_detail.html'
    context_object_name = 'submission'

    def get_object(self):
        submission = super().get_object()

        # Check permissions using security module
        check_pdf_form_access(self.request.user, submission.patient)

        return submission

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_delete_submission'] = can_delete_event(self.request.user, self.object)
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
            timestamp = submission.event_datetime.strftime('%Y%m%d_%H%M%S')
            secure_filename = PDFFormSecurity.generate_secure_filename(
                f"{submission.form_template.name}_{timestamp}.pdf",
                prefix="pdf_form_"
            )

            # Generate PDF response directly from form data
            response = pdf_service.generate_pdf_response(
                template_path=submission.form_template.pdf_file.path,
                form_data=submission.form_data,
                field_config=submission.form_template.form_fields,
                filename=secure_filename
            )

            return response

        except ValidationError as e:
            raise PermissionDenied(f"Security validation failed: {str(e)}")
        except FileNotFoundError as e:
            raise Http404(f"Template file not found: {str(e)}")
        except Exception as e:
            # Log the error for debugging while showing generic message to user
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"PDF generation failed for submission {submission_id}: {str(e)}")
            raise Http404("Erro ao gerar PDF. Tente novamente ou contacte o suporte.")


class PDFFormSubmissionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Delete view for PDF form submissions with permission checking."""

    model = PDFFormSubmission
    template_name = 'pdf_forms/submission_confirm_delete.html'
    context_object_name = 'submission'
    permission_required = 'events.delete_event'

    def get_success_url(self):
        """Redirect to patient timeline after successful deletion."""
        return reverse_lazy(
            'apps.patients:patient_events_timeline',
            kwargs={'patient_id': self.object.patient.pk}
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
        """Optimize queryset with related objects."""
        return PDFFormSubmission.objects.select_related('patient', 'created_by', 'form_template')

    def delete(self, request, *args, **kwargs):
        """Handle successful deletion."""
        submission = self.get_object()
        patient_name = submission.patient.name
        form_name = submission.form_template.name
        messages.success(request, f"Formulário '{form_name}' para {patient_name} excluído com sucesso.")
        return super().delete(request, *args, **kwargs)