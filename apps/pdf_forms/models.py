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
        blank=True,
        help_text="JSON configuration with field positions and properties",
        verbose_name="Configuração dos Campos"
    )

    def clean_form_fields(self):
        """Validate form fields configuration."""
        if self.form_fields:
            PDFFormSecurity.validate_field_configuration(self.form_fields)
            return self.form_fields

    # Form type selection
    form_type = models.CharField(
        max_length=20,
        choices=[
            ('HOSPITAL', 'Hospital Specific'),
            ('APAC', 'APAC National'),
            ('AIH', 'AIH National'),
        ],
        default='HOSPITAL',
        verbose_name="Tipo de Formulário"
    )

    # Hospital customization (kept for backward compatibility)
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
        # Allow empty form_fields to enable saving templates before configuration
        if self.form_fields and len(self.form_fields) > 0:
            PDFFormSecurity.validate_field_configuration(self.form_fields)

    def save(self, *args, **kwargs):
        """Override save to ensure security validation."""
        # Skip full_clean in tests to avoid validation issues
        if not hasattr(self, '_skip_validation'):
            self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_configured(self):
        """Check if the template has field configuration."""
        return bool(self.form_fields and len(self.form_fields) > 0)

    @property
    def has_data_sources(self):
        """Check if template configuration includes data sources."""
        if not self.form_fields:
            return False
        return 'data_sources' in self.form_fields

    @property
    def is_national_form(self):
        """Check if this is a national form (APAC/AIH)."""
        return self.form_type in ['APAC', 'AIH']
    
    @property 
    def configuration_status(self):
        """Get human-readable configuration status."""
        if not self.pdf_file:
            return "Sem PDF"
        elif not self.is_configured:
            return "Não configurado"
        else:
            field_count = len(self.form_fields)
            return f"Configurado ({field_count} campo{'s' if field_count != 1 else ''})"

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = "Template de Formulário PDF"
        verbose_name_plural = "Templates de Formulários PDF"
        indexes = [
            models.Index(fields=['is_active'], name='pdf_form_template_active_idx'),
            models.Index(fields=['hospital_specific'], name='pdf_form_template_hospital_idx'),
            models.Index(fields=['form_type'], name='pdf_form_template_type_idx'),
        ]


class PDFFormSubmission(Event):
    """
    PDF Form submissions extending Event model for timeline integration.
    Stores submitted form data. PDFs are generated on-demand during downloads.
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
