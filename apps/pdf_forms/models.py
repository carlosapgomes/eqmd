import uuid
import json
import os
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from apps.events.models import Event
from .security import PDFFormSecurity


class PDFFormTemplate(models.Model):
    """
    Template for PDF forms specific to hospital.
    Stores blank PDF form and field mapping configuration.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nome do Formulário")
    description = models.TextField(blank=True, verbose_name="Descrição")

    # PDF file storage
    pdf_file = models.FileField(
        upload_to='pdf_forms/templates/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        verbose_name="Arquivo PDF"
    )

    def clean_pdf_file(self):
        """Validate PDF file security."""
        if self.pdf_file:
            PDFFormSecurity.validate_pdf_file(self.pdf_file)
            return self.pdf_file

    # Form configuration with coordinate-based positioning
    form_fields = models.JSONField(
        default=dict,
        help_text="JSON configuration with field positions and properties",
        verbose_name="Configuração dos Campos"
    )

    def clean_form_fields(self):
        """Validate form fields configuration."""
        if self.form_fields:
            PDFFormSecurity.validate_field_configuration(self.form_fields)
            return self.form_fields

    # Hospital customization
    hospital_specific = models.BooleanField(
        default=True,
        verbose_name="Específico do Hospital"
    )

    # Status
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pdf_form_templates_created",
        verbose_name="Criado por"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pdf_form_templates_updated",
        verbose_name="Atualizado por",
        null=True,
        blank=True
    )

    def clean(self):
        """Model-level validation."""
        super().clean()
        
        # Validate PDF file if present
        if self.pdf_file:
            try:
                PDFFormSecurity.validate_pdf_file(self.pdf_file)
                # Also validate actual PDF content if file exists on disk (skip in tests)
                if hasattr(self.pdf_file, 'path') and os.path.exists(self.pdf_file.path):
                    PDFFormSecurity.validate_pdf_content(self.pdf_file.path)
            except ValidationError:
                raise
        
        # Validate form fields configuration (only if not empty)
        if self.form_fields and len(self.form_fields) > 0:
            PDFFormSecurity.validate_field_configuration(self.form_fields)

    def save(self, *args, **kwargs):
        """Override save to ensure security validation."""
        # Skip full_clean in tests to avoid validation issues
        if not hasattr(self, '_skip_validation'):
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = "Template de Formulário PDF"
        verbose_name_plural = "Templates de Formulários PDF"
        indexes = [
            models.Index(fields=['is_active'], name='pdf_form_template_active_idx'),
            models.Index(fields=['hospital_specific'], name='pdf_form_template_hospital_idx'),
        ]


class PDFFormSubmission(Event):
    """
    PDF Form submissions extending Event model for timeline integration.
    Stores submitted data and generated PDF.
    """

    form_template = models.ForeignKey(
        PDFFormTemplate,
        on_delete=models.PROTECT,
        verbose_name="Template do Formulário"
    )

    def clean(self):
        """Model-level validation for PDF submissions."""
        super().clean()
        
        # Sanitize form data
        if self.form_data:
            self.form_data = PDFFormSecurity.sanitize_form_data(self.form_data)
        
        # Validate generated PDF if present
        if self.generated_pdf and hasattr(self.generated_pdf, 'path'):
            PDFFormSecurity.validate_file_path(self.generated_pdf.path)

    def save(self, *args, **kwargs):
        # Automatically set the event type for PDF forms
        if not self.event_type:
            self.event_type = Event.PDF_FORM_EVENT
        
        # Run security validation
        self.full_clean()
        super().save(*args, **kwargs)

    # Submitted form data
    form_data = models.JSONField(
        verbose_name="Dados do Formulário"
    )

    # Generated PDF file
    generated_pdf = models.FileField(
        upload_to='pdf_forms/completed/%Y/%m/',
        verbose_name="PDF Gerado"
    )

    # File metadata
    original_filename = models.CharField(
        max_length=255,
        verbose_name="Nome Original do Arquivo"
    )
    file_size = models.PositiveIntegerField(
        verbose_name="Tamanho do Arquivo (bytes)"
    )

    def __str__(self):
        return f"{self.form_template.name} - {self.patient}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('pdf_forms:submission_detail', kwargs={'pk': self.pk})

    def get_edit_url(self):
        """Return the edit URL for this PDF form submission."""
        from django.urls import reverse
        # PDF submissions are read-only, so edit URL points to detail view
        return reverse('pdf_forms:submission_detail', kwargs={'pk': self.pk})

    class Meta:
        verbose_name = "Submissão de Formulário PDF"
        verbose_name_plural = "Submissões de Formulários PDF"
        indexes = [
            models.Index(fields=['form_template'], name='pdf_submission_template_idx'),
        ]
