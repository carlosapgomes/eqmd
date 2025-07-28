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
from .models import PDFFormTemplate, PDFFormSubmission
from .services.form_generator import DynamicFormGenerator
from .services.pdf_overlay import PDFFormOverlay
from .permissions import (
    check_pdf_form_access, 
    check_pdf_form_creation,
    check_pdf_form_template_access,
    check_pdf_download_access
)
from .security import PDFFormSecurity


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
        ).order_by('name')


class PDFFormSelectView(LoginRequiredMixin, View):
    """Select PDF form for a specific patient."""

    def get(self, request, patient_id):
        # Check patient access
        from apps.patients.models import Patient
        patient = get_object_or_404(Patient, id=patient_id)

        # Use security permission check
        check_pdf_form_access(request.user, patient)

        # Get available forms
        form_templates = PDFFormTemplate.objects.filter(
            is_active=True,
            hospital_specific=True
        ).order_by('name')

        context = {
            'patient': patient,
            'form_templates': form_templates,
        }
        return render(request, 'pdf_forms/form_select.html', context)


class PDFFormFillView(LoginRequiredMixin, FormView):
    """Display and handle PDF form filling."""

    template_name = 'pdf_forms/form_fill.html'

    def dispatch(self, request, *args, **kwargs):
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
        return generator.generate_form_class(self.form_template, self.patient)

    def get_form_kwargs(self):
        """Add initial values from patient data to form kwargs."""
        kwargs = super().get_form_kwargs()
        
        # Get the form class to access patient initial values
        form_class = self.get_form_class()
        if hasattr(form_class, '_patient_initial_values'):
            # Merge patient initial values with any existing initial values
            initial = kwargs.get('initial', {})
            initial.update(form_class._patient_initial_values)
            kwargs['initial'] = initial
            
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form_template': self.form_template,
            'patient': self.patient,
        })
        return context

    def form_valid(self, form):
        """Process form submission and generate PDF."""
        print(f"DEBUG: form_valid called with data: {form.cleaned_data}")
        try:
            # Sanitize form data for security
            sanitized_data = PDFFormSecurity.sanitize_form_data(form.cleaned_data)
            print(f"DEBUG: sanitized_data: {sanitized_data}")

            # Create PDF overlay service
            pdf_service = PDFFormOverlay()

            # Fill PDF form using coordinate-based overlay
            filled_pdf = pdf_service.fill_form(
                template_path=self.form_template.pdf_file.path,
                form_data=sanitized_data,
                field_config=self.form_template.form_fields
            )

            # Generate secure filename
            secure_filename = PDFFormSecurity.generate_secure_filename(
                f"{self.form_template.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                prefix="pdf_form_"
            )

            # Create submission record
            submission = PDFFormSubmission(
                form_template=self.form_template,
                patient=self.patient,
                created_by=self.request.user,
                updated_by=self.request.user,
                event_datetime=timezone.now(),
                description=f"Formulário PDF: {self.form_template.name}",
                form_data=sanitized_data,
                original_filename=secure_filename,
            )

            # Save the filled PDF
            submission.generated_pdf.save(
                secure_filename,
                filled_pdf,
                save=False
            )

            # Update file size
            submission.file_size = submission.generated_pdf.size
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
    """Download generated PDF file."""

    def get(self, request, submission_id):
        submission = get_object_or_404(PDFFormSubmission, id=submission_id)

        # Check permissions using security module
        check_pdf_download_access(request.user, submission)

        if not submission.generated_pdf:
            raise Http404("Generated PDF file not found")

        try:
            # Validate file path for security
            PDFFormSecurity.validate_file_path(submission.generated_pdf.path)
            
            response = FileResponse(
                submission.generated_pdf.open('rb'),
                content_type='application/pdf',
                as_attachment=True,
                filename=submission.original_filename
            )
            return response
        except ValidationError as e:
            raise PermissionDenied(f"Security validation failed: {str(e)}")
        except IOError:
            raise Http404("PDF file not found on disk")


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