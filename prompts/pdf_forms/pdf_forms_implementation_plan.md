# PDF Forms Implementation Plan

## Overview

Implementation of PDF form overlay functionality for hospital-specific forms (transfusion requests, ICU transfer requests, etc.) as a dedicated Django app that integrates with the existing Event system.

**Key Approach: Manual Field Configuration with Coordinate-Based Positioning**

### Project Context

**EquipeMed** is a Django 5 medical team collaboration platform for single-hospital patient tracking and care management. This feature adds the ability to fill hospital-specific PDF forms through web interfaces and generate completed PDFs with precise data overlays using manual field positioning.

### Architecture Decision: Dedicated App vs. Extending Existing

**Decision: Create dedicated `pdf_forms` app**

**Why NOT extend sample_content app:**

- **sample_content is actively used**: Provides text templates for medical notes (dailynotes, simplenotes, historyandphysicals) via modal interfaces
- **Different purpose**: sample_content = text templates for insertion, pdf_forms = fillable form overlays with PDF generation
- **Different data models**: Text templates vs PDF files with field mappings
- **Different UI patterns**: Text insertion modals vs form filling workflows

**Benefits of dedicated app:**

- **Clean separation of concerns**: Follows Django single-responsibility principle
- **Hospital-specific customization**: Can be enabled/disabled per hospital without affecting core functionality
- **Independent evolution**: Can evolve PDF functionality without impacting text templates
- **Clear boundaries**: Easier maintenance and testing

### Manual Configuration vs. Auto-Extraction

**❌ Why NOT Auto-Extract PDF Fields:**

- **Unreliable**: Many hospital PDFs are scanned documents without fillable form fields
- **Limited Compatibility**: Only works with PDFs that have embedded form annotations
- **Positioning Issues**: Auto-detected positioning is often inaccurate
- **Format Variations**: Different PDF creation tools create inconsistent field structures

**✅ Why Manual Configuration is Better:**

- **Universal Compatibility**: Works with any PDF format (scanned, image-based, or form-based)
- **Precise Control**: Exact positioning using x,y coordinates in centimeters
- **Predictable Results**: No guessing about field detection or positioning
- **Hospital-Friendly**: Perfect for legacy scanned hospital forms
- **User Control**: Complete control over field appearance and formatting

## Phase 1: App Structure Creation

### 1.1 Create Django App

```bash
# Create the app
uv run python manage.py startapp pdf_forms apps/pdf_forms

# Add to settings
# config/settings.py - add 'apps.pdf_forms' to INSTALLED_APPS
```

### 1.2 Directory Structure

```
apps/pdf_forms/
├── __init__.py
├── apps.py                    # App configuration
├── models.py                  # Core models (PDFFormTemplate, PDFFormSubmission)
├── forms.py                   # Dynamic Django forms
├── views.py                   # CRUD views for forms and submissions
├── urls.py                    # URL routing
├── admin.py                   # Admin interface
├── services/                  # Business logic services
│   ├── __init__.py
│   ├── pdf_overlay.py         # PDF form filling logic
│   ├── field_mapping.py       # Form field mapping utilities
│   └── form_generator.py      # Dynamic Django form generation
├── templates/pdf_forms/       # Templates
│   ├── base.html             # Base template extending main base
│   ├── form_template_list.html
│   ├── form_select.html
│   ├── form_fill.html
│   ├── form_submission_detail.html
│   └── partials/
│       ├── pdf_form_event_card.html  # Timeline integration
│       └── form_field_widgets.html   # Custom form widgets
├── static/pdf_forms/          # Static assets
│   ├── css/
│   │   └── pdf_forms.css     # Form styling
│   ├── js/
│   │   └── pdf_forms.js      # Form interaction JavaScript
│   └── images/
│       └── pdf_icon.svg      # PDF icons and assets
├── migrations/                # Database migrations
│   └── __init__.py
├── tests/                     # Test modules
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_services.py
│   └── factories.py          # Test data factories
└── management/                # Management commands
    ├── __init__.py
    └── commands/
        ├── __init__.py
        └── create_sample_pdf_forms.py
```

## Phase 2: Models Implementation

### 2.1 Core Models

```python
# apps/pdf_forms/models.py
import uuid
import json
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from apps.events.models import Event

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

    # Form configuration with coordinate-based positioning
    form_fields = models.JSONField(
        default=dict,
        help_text="JSON configuration with field positions and properties",
        verbose_name="Configuração dos Campos"
    )

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

    class Meta:
        verbose_name = "Submissão de Formulário PDF"
        verbose_name_plural = "Submissões de Formulários PDF"
        indexes = [
            models.Index(fields=['form_template'], name='pdf_submission_template_idx'),
            models.Index(fields=['patient'], name='pdf_submission_patient_idx'),
        ]
```

### 2.2 Event System Integration

```python
# apps/events/models.py - Add to EVENT_TYPE_CHOICES
PDF_FORM_EVENT = 11

EVENT_TYPE_CHOICES = [
    # ... existing choices ...
    (PDF_FORM_EVENT, 'Formulário PDF'),
]
```

## Phase 3: Field Configuration Structure

### 3.1 Manual Field Configuration Format

The `form_fields` JSON in `PDFFormTemplate` uses coordinate-based positioning:

```json
{
  "patient_name": {
    "type": "text",
    "label": "Nome do Paciente",
    "x": 5.2,           // cm from left edge
    "y": 10.5,          // cm from top edge  
    "width": 8.0,       // cm width
    "height": 0.7,      // cm height
    "font_size": 12,
    "font_family": "Arial",
    "required": true,
    "max_length": 100
  },
  "blood_type": {
    "type": "choice",
    "label": "Tipo Sanguíneo", 
    "x": 15.0,
    "y": 10.5,
    "width": 3.0,
    "height": 0.7,
    "font_size": 12,
    "choices": ["A+", "A-", "B+", "B-", "O+", "O-"],
    "required": true
  },
  "urgency_checkbox": {
    "type": "boolean",
    "label": "Urgente",
    "x": 18.0,
    "y": 12.0,
    "width": 0.5,
    "height": 0.5,
    "required": false
  },
  "request_date": {
    "type": "date",
    "label": "Data da Solicitação",
    "x": 5.2,
    "y": 8.0,
    "width": 4.0,
    "height": 0.7,
    "font_size": 12,
    "required": true
  }
}
```

### Field Configuration Properties

- **Position**: `x`, `y` coordinates in centimeters from top-left
- **Dimensions**: `width`, `height` in centimeters
- **Typography**: `font_size`, `font_family`
- **Type-specific**: `choices` for select, `max_length` for text
- **Validation**: `required` flag

## Phase 4: Field Configuration Interface

### 4.1 Admin Interface for Field Configuration

```python
# apps/pdf_forms/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import PDFFormTemplate, PDFFormSubmission

@admin.register(PDFFormTemplate)
class PDFFormTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'hospital_specific', 'is_active', 'created_at', 'pdf_preview']
    list_filter = ['hospital_specific', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'pdf_file')
        }),
        ('Field Configuration', {
            'fields': ('form_fields',),
            'description': 'Configure field positions using x,y coordinates in centimeters'
        }),
        ('Settings', {
            'fields': ('hospital_specific', 'is_active')
        }),
        ('Audit', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    def pdf_preview(self, obj):
        if obj.pdf_file:
            return format_html('<a href="{}" target="_blank">View PDF</a>', obj.pdf_file.url)
        return "No PDF"
    pdf_preview.short_description = "PDF Preview"
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
```

### 4.2 Visual Field Configuration Interface (Future Enhancement)

For easier field configuration, consider adding a visual interface:

```html
<!-- Future enhancement: Visual field positioning -->
<div class="pdf-field-configurator">
    <div class="pdf-preview">
        <img src="pdf-preview.png" alt="PDF Preview" />
        <div class="field-overlay" data-field="patient_name" 
             style="left: 5.2cm; top: 10.5cm; width: 8cm; height: 0.7cm;">
        </div>
    </div>
    <div class="field-properties">
        <input type="text" name="field_name" />
        <input type="number" name="x" step="0.1" /> cm
        <input type="number" name="y" step="0.1" /> cm
        <select name="field_type">
            <option value="text">Text</option>
            <option value="choice">Choice</option>
            <option value="boolean">Checkbox</option>
            <option value="date">Date</option>
        </select>
    </div>
</div>
```

## Phase 5: PDF Processing Services

### 5.1 Coordinate-Based PDF Overlay Service

```python
# apps/pdf_forms/services/pdf_overlay.py
import os
import uuid
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

try:
    import pypdf
    from pypdf import PdfReader, PdfWriter
    PDF_LIBRARY_AVAILABLE = True
except ImportError:
    PDF_LIBRARY_AVAILABLE = False

class PDFFormOverlay:
    """
    Service for filling PDF forms with submitted data.
    Handles PDF form field mapping and overlay generation.
    """

    def __init__(self):
        if not PDF_LIBRARY_AVAILABLE:
            raise ImportError("pypdf library is required for PDF form processing")

    def fill_form(self, template_path, form_data, output_filename=None):
        """
        Fill PDF form fields with submitted data.

        Args:
            template_path (str): Path to blank PDF form template
            form_data (dict): Form data to fill
            output_filename (str): Optional output filename

        Returns:
            ContentFile: Filled PDF as Django ContentFile
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"PDF template not found: {template_path}")

        try:
            # Read the original PDF
            reader = PdfReader(template_path)
            writer = PdfWriter()

            # Process each page
            for page_num, page in enumerate(reader.pages):
                # Fill form fields on this page
                if '/Annots' in page:
                    annotations = page['/Annots']
                    if annotations:
                        self._fill_page_fields(page, form_data)

                # Add page to writer
                writer.add_page(page)

            # Generate output filename if not provided
            if not output_filename:
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                output_filename = f"filled_form_{timestamp}.pdf"

            # Write to bytes
            output_buffer = BytesIO()
            writer.write(output_buffer)
            output_buffer.seek(0)

            # Return as ContentFile
            return ContentFile(
                output_buffer.getvalue(),
                name=output_filename
            )

        except Exception as e:
            raise Exception(f"Error filling PDF form: {str(e)}")

    def _fill_page_fields(self, page, form_data):
        """Fill form fields on a specific page."""
        # Implementation depends on pypdf version and PDF structure
        # This is a simplified version - real implementation needs
        # to handle different field types (text, checkbox, radio, etc.)
        pass

    def extract_form_fields(self, pdf_path):
        """
        Extract fillable fields from PDF form.

        Args:
            pdf_path (str): Path to PDF file

        Returns:
            dict: Dictionary of field names and their properties
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            reader = PdfReader(pdf_path)
            fields = {}

            for page in reader.pages:
                if '/Annots' in page:
                    annotations = page['/Annots']
                    if annotations:
                        page_fields = self._extract_page_fields(page)
                        fields.update(page_fields)

            return fields

        except Exception as e:
            raise Exception(f"Error extracting PDF fields: {str(e)}")

    def _extract_page_fields(self, page):
        """Extract fields from a specific page."""
        # Implementation depends on PDF structure
        # Should return dict of field_name: field_properties
        return {}

    def validate_pdf_form(self, pdf_path):
        """
        Validate that PDF contains fillable form fields.

        Args:
            pdf_path (str): Path to PDF file

        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            fields = self.extract_form_fields(pdf_path)
            if not fields:
                return False, "PDF does not contain fillable form fields"
            return True, None
        except Exception as e:
            return False, str(e)
```

### 5.2 Dynamic Form Generator

```python
# apps/pdf_forms/services/form_generator.py
from django import forms
from django.core.exceptions import ValidationError

class DynamicFormGenerator:
    """
    Generate Django forms based on PDF field configuration.
    Creates form classes dynamically from PDF field mappings.
    """

    FIELD_TYPE_MAPPING = {
        'text': forms.CharField,
        'textarea': forms.CharField,
        'email': forms.EmailField,
        'number': forms.IntegerField,
        'decimal': forms.DecimalField,
        'date': forms.DateField,
        'datetime': forms.DateTimeField,
        'boolean': forms.BooleanField,
        'choice': forms.ChoiceField,
        'multiple_choice': forms.MultipleChoiceField,
    }

    def generate_form_class(self, pdf_template):
        """
        Create Django form class from PDF template field configuration.

        Args:
            pdf_template (PDFFormTemplate): Template with field configuration

        Returns:
            type: Django form class
        """
        form_fields = {}
        field_config = pdf_template.form_fields

        for field_name, config in field_config.items():
            django_field = self._create_django_field(field_name, config)
            if django_field:
                form_fields[field_name] = django_field

        # Create form class dynamically
        form_class_name = f"{pdf_template.name.replace(' ', '')}Form"

        # Add custom validation method
        def clean(self):
            cleaned_data = super().clean()
            # Add custom validation logic here
            return cleaned_data

        form_fields['clean'] = clean

        # Create the form class
        return type(form_class_name, (forms.Form,), form_fields)

    def _create_django_field(self, field_name, config):
        """
        Create Django form field from configuration.

        Args:
            field_name (str): Name of the field
            config (dict): Field configuration

        Returns:
            forms.Field: Django form field instance
        """
        field_type = config.get('type', 'text')
        required = config.get('required', False)
        label = config.get('label', field_name.replace('_', ' ').title())
        help_text = config.get('help_text', '')
        max_length = config.get('max_length')
        choices = config.get('choices', [])

        # Get the Django field class
        field_class = self.FIELD_TYPE_MAPPING.get(field_type, forms.CharField)

        # Build field kwargs
        field_kwargs = {
            'required': required,
            'label': label,
            'help_text': help_text,
        }

        # Add type-specific kwargs
        if field_type == 'textarea':
            field_kwargs['widget'] = forms.Textarea(attrs={'rows': 3})
        elif field_type == 'choice' and choices:
            field_kwargs['choices'] = [(c, c) for c in choices]
        elif field_type == 'multiple_choice' and choices:
            field_kwargs['choices'] = [(c, c) for c in choices]
            field_kwargs['widget'] = forms.CheckboxSelectMultiple()
        elif max_length and field_type in ['text', 'textarea']:
            field_kwargs['max_length'] = max_length

        return field_class(**field_kwargs)
```

## Phase 4: Views Implementation

### 4.1 Core Views

```python
# apps/pdf_forms/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, FormView, View
from django.http import HttpResponse, Http404, FileResponse
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from apps.core.permissions.decorators import patient_access_required
from apps.core.permissions.utils import can_access_patient
from .models import PDFFormTemplate, PDFFormSubmission
from .services.form_generator import DynamicFormGenerator
from .services.pdf_overlay import PDFFormOverlay

class PDFFormTemplateListView(LoginRequiredMixin, ListView):
    """List available PDF form templates for current hospital."""

    model = PDFFormTemplate
    template_name = 'pdf_forms/form_template_list.html'
    context_object_name = 'form_templates'
    paginate_by = 20

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

        if not can_access_patient(request.user, patient):
            raise PermissionDenied("You don't have permission to access this patient")

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

        # Check permissions
        if not can_access_patient(request.user, self.patient):
            raise PermissionDenied("You don't have permission to access this patient")

        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        """Generate form class dynamically based on PDF template."""
        generator = DynamicFormGenerator()
        return generator.generate_form_class(self.form_template)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form_template': self.form_template,
            'patient': self.patient,
        })
        return context

    def form_valid(self, form):
        """Process form submission and generate PDF."""
        try:
            # Create PDF overlay service
            pdf_service = PDFFormOverlay()

            # Fill PDF form using coordinate-based overlay
            filled_pdf = pdf_service.fill_form(
                template_path=self.form_template.pdf_file.path,
                form_data=form.cleaned_data,
                field_config=self.form_template.form_fields
            )

            # Create submission record
            submission = PDFFormSubmission(
                form_template=self.form_template,
                patient=self.patient,
                created_by=self.request.user,
                event_datetime=timezone.now(),
                event_type=PDFFormSubmission.PDF_FORM_EVENT,
                description=f"Formulário PDF: {self.form_template.name}",
                form_data=form.cleaned_data,
                original_filename=f"{self.form_template.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                file_size=len(filled_pdf.read())
            )

            # Save the filled PDF
            submission.generated_pdf.save(
                submission.original_filename,
                filled_pdf,
                save=False
            )

            submission.save()

            messages.success(
                self.request,
                f"Formulário '{self.form_template.name}' preenchido com sucesso!"
            )

            return redirect('pdf_forms:submission_detail', pk=submission.pk)

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

        # Check permissions
        if not can_access_patient(self.request.user, submission.patient):
            raise PermissionDenied("You don't have permission to access this submission")

        return submission

class PDFFormDownloadView(LoginRequiredMixin, View):
    """Download generated PDF file."""

    def get(self, request, submission_id):
        submission = get_object_or_404(PDFFormSubmission, id=submission_id)

        # Check permissions
        if not can_access_patient(request.user, submission.patient):
            raise PermissionDenied("You don't have permission to download this file")

        if not submission.generated_pdf:
            raise Http404("Generated PDF file not found")

        try:
            response = FileResponse(
                submission.generated_pdf.open('rb'),
                content_type='application/pdf',
                as_attachment=True,
                filename=submission.original_filename
            )
            return response
        except IOError:
            raise Http404("PDF file not found on disk")
```

## Phase 5: URL Configuration

### 5.1 App URLs

```python
# apps/pdf_forms/urls.py
from django.urls import path
from . import views

app_name = 'pdf_forms'

urlpatterns = [
    # Template management
    path('templates/', views.PDFFormTemplateListView.as_view(), name='template_list'),

    # Form workflow
    path('select/<uuid:patient_id>/', views.PDFFormSelectView.as_view(), name='form_select'),
    path('fill/<uuid:template_id>/<uuid:patient_id>/', views.PDFFormFillView.as_view(), name='form_fill'),

    # Submissions
    path('submission/<uuid:pk>/', views.PDFFormSubmissionDetailView.as_view(), name='submission_detail'),
    path('download/<uuid:submission_id>/', views.PDFFormDownloadView.as_view(), name='pdf_download'),
]
```

### 5.2 Main URLs Integration

```python
# config/urls.py - Add to urlpatterns
path('pdf-forms/', include('apps.pdf_forms.urls')),
```

## Phase 6: Templates Implementation

### 6.1 Base Template

```html
<!-- apps/pdf_forms/templates/pdf_forms/base.html -->
{% extends "base_app.html" %} {% load static %} {% block extra_head %} {{
block.super }}
<link href="{% static 'pdf_forms/css/pdf_forms.css' %}" rel="stylesheet" />
{% endblock %} {% block extra_js %} {{ block.super }}
<script src="{% static 'pdf_forms/js/pdf_forms.js' %}"></script>
{% endblock %}
```

### 6.2 Form Selection Template

```html
<!-- apps/pdf_forms/templates/pdf_forms/form_select.html -->
{% extends "pdf_forms/base.html" %} {% load static %} {% block page_title
%}Selecionar Formulário PDF - {{ patient.name }}{% endblock %} {% block content
%}
<div class="container-fluid">
  <div class="row">
    <div class="col-12">
      <!-- Patient header -->
      <div class="card mb-4">
        <div class="card-header bg-primary text-white">
          <h5 class="mb-0">
            <i class="bi bi-file-earmark-pdf me-2"></i>
            Formulários PDF - {{ patient.name }}
          </h5>
        </div>
        <div class="card-body">
          <p class="mb-0">
            Selecione o formulário PDF que deseja preencher para este paciente.
          </p>
        </div>
      </div>

      <!-- Form templates -->
      {% if form_templates %}
      <div class="row">
        {% for template in form_templates %}
        <div class="col-md-6 col-lg-4 mb-3">
          <div class="card h-100">
            <div class="card-body">
              <h6 class="card-title">
                <i class="bi bi-file-earmark-pdf text-danger me-2"></i>
                {{ template.name }}
              </h6>
              {% if template.description %}
              <p class="card-text text-muted small">
                {{ template.description }}
              </p>
              {% endif %}
            </div>
            <div class="card-footer">
              <a
                href="{% url 'pdf_forms:form_fill' template.id patient.id %}"
                class="btn btn-primary btn-sm"
              >
                <i class="bi bi-pencil me-1"></i>
                Preencher Formulário
              </a>
            </div>
          </div>
        </div>
        {% endfor %}
      </div>
      {% else %}
      <div class="alert alert-info">
        <i class="bi bi-info-circle me-2"></i>
        Nenhum formulário PDF disponível no momento.
      </div>
      {% endif %}
    </div>
  </div>
</div>
{% endblock %}
```

### 6.3 Form Fill Template

```html
<!-- apps/pdf_forms/templates/pdf_forms/form_fill.html -->
{% extends "pdf_forms/base.html" %} {% load static %} {% block page_title %}{{
form_template.name }} - {{ patient.name }}{% endblock %} {% block content %}
<div class="container-fluid">
  <div class="row">
    <div class="col-12">
      <!-- Header -->
      <div class="card mb-4">
        <div class="card-header bg-primary text-white">
          <h5 class="mb-0">
            <i class="bi bi-file-earmark-pdf me-2"></i>
            {{ form_template.name }}
          </h5>
          <small>Paciente: {{ patient.name }}</small>
        </div>
        {% if form_template.description %}
        <div class="card-body">
          <p class="mb-0">{{ form_template.description }}</p>
        </div>
        {% endif %}
      </div>

      <!-- Form -->
      <div class="card">
        <div class="card-body">
          <form method="post" class="pdf-form">
            {% csrf_token %} {% if form.non_field_errors %}
            <div class="alert alert-danger">{{ form.non_field_errors }}</div>
            {% endif %}

            <div class="row">
              {% for field in form %}
              <div class="col-md-6 mb-3">
                <label for="{{ field.id_for_label }}" class="form-label">
                  {{ field.label }} {% if field.field.required %}
                  <span class="text-danger">*</span>
                  {% endif %}
                </label>

                {{ field }} {% if field.help_text %}
                <div class="form-text">{{ field.help_text }}</div>
                {% endif %} {% if field.errors %}
                <div class="invalid-feedback d-block">{{ field.errors }}</div>
                {% endif %}
              </div>
              {% endfor %}
            </div>

            <div class="d-flex justify-content-between">
              <a
                href="{% url 'pdf_forms:form_select' patient.id %}"
                class="btn btn-secondary"
              >
                <i class="bi bi-arrow-left me-1"></i>
                Voltar
              </a>

              <button type="submit" class="btn btn-primary">
                <i class="bi bi-file-earmark-pdf me-1"></i>
                Gerar PDF
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

### 6.4 Timeline Integration Template

```html
<!-- apps/pdf_forms/templates/pdf_forms/partials/pdf_form_event_card.html -->
<!-- Event card template for timeline integration -->
{% load static %}

<div class="event-card pdf-form-event" data-event-id="{{ event.id }}">
  <div class="event-header">
    <div class="event-icon">
      <i class="bi bi-file-earmark-pdf text-danger"></i>
    </div>
    <div class="event-info">
      <h6 class="event-title">{{ event.form_template.name }}</h6>
      <small class="event-meta">
        Por {{ event.created_by.get_full_name }} em {{
        event.event_datetime|date:"d/m/Y H:i" }}
      </small>
    </div>
    <div class="event-actions">
      <a
        href="{% url 'pdf_forms:submission_detail' event.id %}"
        class="btn btn-sm btn-outline-primary"
        title="Ver detalhes"
      >
        <i class="bi bi-eye"></i>
      </a>
      <a
        href="{% url 'pdf_forms:pdf_download' event.id %}"
        class="btn btn-sm btn-outline-success"
        title="Baixar PDF"
      >
        <i class="bi bi-download"></i>
      </a>
    </div>
  </div>

  <div class="event-content">
    {% if event.description %}
    <p class="mb-2">{{ event.description }}</p>
    {% endif %}

    <div class="pdf-info">
      <small class="text-muted">
        <i class="bi bi-file-earmark me-1"></i>
        {{ event.original_filename }} ({{ event.file_size|filesizeformat }})
      </small>
    </div>
  </div>
</div>
```

## Phase 7: Hospital Configuration Integration

### 7.1 Settings Configuration

```python
# config/settings.py

# PDF Forms Configuration
PDF_FORMS_CONFIG = {
    'enabled': os.getenv('HOSPITAL_PDF_FORMS_ENABLED', 'false').lower() == 'true',
    'templates_path': os.getenv('HOSPITAL_PDF_FORMS_PATH', ''),
    'max_file_size': int(os.getenv('PDF_FORMS_MAX_FILE_SIZE', 10 * 1024 * 1024)),  # 10MB
    'allowed_extensions': ['.pdf'],
    'require_form_validation': os.getenv('PDF_FORMS_REQUIRE_VALIDATION', 'true').lower() == 'true',
}

# File upload settings for PDF forms
if PDF_FORMS_CONFIG['enabled']:
    # Ensure media directories exist
    PDF_FORMS_MEDIA_ROOT = MEDIA_ROOT / 'pdf_forms'
    PDF_FORMS_MEDIA_ROOT.mkdir(exist_ok=True)
    (PDF_FORMS_MEDIA_ROOT / 'templates').mkdir(exist_ok=True)
    (PDF_FORMS_MEDIA_ROOT / 'completed').mkdir(exist_ok=True)
```

### 7.2 Environment Variables

```bash
# .env file additions

# PDF Forms Configuration
HOSPITAL_PDF_FORMS_ENABLED=true
HOSPITAL_PDF_FORMS_PATH=/path/to/hospital/pdf/templates
PDF_FORMS_MAX_FILE_SIZE=10485760  # 10MB
PDF_FORMS_REQUIRE_VALIDATION=true
```

### 7.3 Template Tags Integration

```python
# apps/pdf_forms/templatetags/pdf_forms_tags.py
from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def pdf_forms_enabled():
    """Check if PDF forms are enabled for this hospital."""
    return getattr(settings, 'PDF_FORMS_CONFIG', {}).get('enabled', False)

@register.inclusion_tag('pdf_forms/partials/pdf_forms_menu.html', takes_context=True)
def pdf_forms_menu(context):
    """Render PDF forms menu items."""
    request = context['request']
    return {
        'user': request.user,
        'enabled': pdf_forms_enabled(),
    }
```

## Phase 8: Dependencies and Installation

### 8.1 Updated Python Dependencies

```bash
# Core dependencies for coordinate-based PDF overlay
uv add reportlab        # For precise text positioning and overlay creation
uv add PyPDF2          # For PDF manipulation and merging

# Alternative PyPDF library (if PyPDF2 has issues)
# uv add pypdf
```

**Why These Libraries:**

- **ReportLab**: Professional PDF generation with precise coordinate positioning
- **PyPDF2**: Reliable PDF manipulation for merging overlay onto original
- **Coordinate-based approach**: No dependency on PDF form field detection

### 8.2 Settings Updates

```python
# config/settings.py
INSTALLED_APPS = [
    # ... existing apps ...
    'apps.pdf_forms',
]

# Ensure proper ordering after events app
```

### 8.3 Database Migrations

```bash
# Create and run migrations
uv run python manage.py makemigrations pdf_forms
uv run python manage.py migrate
```

## Phase 9: Security Implementation

### 9.1 File Security

```python
# Security utilities in apps/pdf_forms/security.py
import os
import uuid
from pathlib import Path
from django.core.exceptions import ValidationError
from django.conf import settings

class PDFFormSecurity:
    """Security utilities for PDF form handling."""

    ALLOWED_EXTENSIONS = ['.pdf']
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def validate_pdf_file(uploaded_file):
        """Validate uploaded PDF file."""
        # Check file extension
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        if file_extension not in PDFFormSecurity.ALLOWED_EXTENSIONS:
            raise ValidationError(f"Only PDF files are allowed. Got: {file_extension}")

        # Check file size
        if uploaded_file.size > PDFFormSecurity.MAX_FILE_SIZE:
            raise ValidationError(f"File too large. Maximum size: {PDFFormSecurity.MAX_FILE_SIZE} bytes")

        # Check MIME type
        if uploaded_file.content_type != 'application/pdf':
            raise ValidationError(f"Invalid file type. Expected PDF, got: {uploaded_file.content_type}")

        return True

    @staticmethod
    def generate_secure_filename(original_filename, prefix=''):
        """Generate secure filename with UUID."""
        file_extension = os.path.splitext(original_filename)[1].lower()
        secure_name = f"{prefix}{uuid.uuid4()}{file_extension}"
        return secure_name

    @staticmethod
    def validate_file_path(file_path):
        """Validate file path for security."""
        # Resolve path and check it's within allowed directories
        resolved_path = Path(file_path).resolve()
        media_root = Path(settings.MEDIA_ROOT).resolve()

        if not str(resolved_path).startswith(str(media_root)):
            raise ValidationError("Invalid file path")

        return True
```

### 9.2 Permission Integration

```python
# apps/pdf_forms/permissions.py
from apps.core.permissions.utils import can_access_patient
from django.core.exceptions import PermissionDenied

def check_pdf_form_access(user, patient):
    """Check if user can access PDF forms for patient."""
    if not can_access_patient(user, patient):
        raise PermissionDenied("You don't have permission to access this patient's PDF forms")

    return True

def check_pdf_form_creation(user, patient):
    """Check if user can create PDF forms for patient."""
    # Add any additional checks for PDF form creation
    return check_pdf_form_access(user, patient)
```

## Phase 10: Testing Strategy

### 10.1 Unit Tests

```python
# apps/pdf_forms/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.patients.models import Patient
from apps.pdf_forms.models import PDFFormTemplate, PDFFormSubmission
from apps.pdf_forms.tests.factories import PDFFormTemplateFactory

User = get_user_model()

class PDFFormTemplateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

    def test_create_pdf_form_template(self):
        """Test creating a PDF form template."""
        template = PDFFormTemplateFactory(created_by=self.user)
        self.assertTrue(template.is_active)
        self.assertEqual(template.created_by, self.user)

    def test_pdf_form_submission_creation(self):
        """Test creating a PDF form submission."""
        template = PDFFormTemplateFactory(created_by=self.user)
        patient = Patient.objects.create(
            name="Test Patient",
            created_by=self.user
        )

        submission = PDFFormSubmission.objects.create(
            form_template=template,
            patient=patient,
            created_by=self.user,
            form_data={'field1': 'value1'},
            original_filename='test.pdf',
            file_size=1024
        )

        self.assertEqual(submission.form_template, template)
        self.assertEqual(submission.patient, patient)
```

### 10.2 Integration Tests

```python
# apps/pdf_forms/tests/test_views.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.patients.models import Patient
from apps.pdf_forms.tests.factories import PDFFormTemplateFactory

User = get_user_model()

class PDFFormViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            name="Test Patient",
            created_by=self.user
        )
        self.template = PDFFormTemplateFactory(created_by=self.user)

    def test_form_select_view(self):
        """Test PDF form selection view."""
        self.client.login(email='test@example.com', password='testpass123')

        url = reverse('pdf_forms:form_select', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.template.name)
        self.assertContains(response, self.patient.name)
```

### 10.3 Service Tests

```python
# apps/pdf_forms/tests/test_services.py
from django.test import TestCase
from unittest.mock import patch, MagicMock
from apps.pdf_forms.services.form_generator import DynamicFormGenerator
from apps.pdf_forms.tests.factories import PDFFormTemplateFactory

class FormGeneratorTests(TestCase):

    def setUp(self):
        self.generator = DynamicFormGenerator()

    def test_generate_form_class(self):
        """Test dynamic form class generation."""
        template = PDFFormTemplateFactory(
            form_fields={
                'patient_name': {
                    'type': 'text',
                    'required': True,
                    'label': 'Patient Name',
                    'max_length': 100
                },
                'date_of_birth': {
                    'type': 'date',
                    'required': True,
                    'label': 'Date of Birth'
                }
            }
        )

        form_class = self.generator.generate_form_class(template)
        form_instance = form_class()

        self.assertIn('patient_name', form_instance.fields)
        self.assertIn('date_of_birth', form_instance.fields)
        self.assertTrue(form_instance.fields['patient_name'].required)
```

## Phase 11: Management Commands

### 11.1 Sample Data Command

```python
# apps/pdf_forms/management/commands/create_sample_pdf_forms.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.pdf_forms.models import PDFFormTemplate

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample PDF form templates for testing'

    def handle(self, *args, **options):
        # Get or create superuser
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR('No superuser found. Create one first.')
            )
            return

        # Sample form configurations
        sample_forms = [
            {
                'name': 'Solicitação de Transfusão',
                'description': 'Formulário para solicitação de transfusão sanguínea',
                'form_fields': {
                    'patient_name': {
                        'type': 'text',
                        'required': True,
                        'label': 'Nome do Paciente',
                        'max_length': 200
                    },
                    'blood_type': {
                        'type': 'choice',
                        'required': True,
                        'label': 'Tipo Sanguíneo',
                        'choices': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
                    },
                    'units_requested': {
                        'type': 'number',
                        'required': True,
                        'label': 'Unidades Solicitadas'
                    },
                    'urgency': {
                        'type': 'choice',
                        'required': True,
                        'label': 'Urgência',
                        'choices': ['Rotina', 'Urgente', 'Emergência']
                    },
                    'clinical_indication': {
                        'type': 'textarea',
                        'required': True,
                        'label': 'Indicação Clínica'
                    }
                }
            },
            {
                'name': 'Transferência para UTI',
                'description': 'Formulário para solicitação de transferência para UTI',
                'form_fields': {
                    'patient_name': {
                        'type': 'text',
                        'required': True,
                        'label': 'Nome do Paciente'
                    },
                    'current_location': {
                        'type': 'text',
                        'required': True,
                        'label': 'Localização Atual'
                    },
                    'requested_icu': {
                        'type': 'choice',
                        'required': True,
                        'label': 'UTI Solicitada',
                        'choices': ['UTI Geral', 'UTI Cardiológica', 'UTI Neurológica']
                    },
                    'clinical_condition': {
                        'type': 'textarea',
                        'required': True,
                        'label': 'Condição Clínica'
                    },
                    'life_support': {
                        'type': 'boolean',
                        'required': False,
                        'label': 'Necessita Suporte Vida'
                    }
                }
            }
        ]

        created_count = 0
        for form_data in sample_forms:
            template, created = PDFFormTemplate.objects.get_or_create(
                name=form_data['name'],
                defaults={
                    'description': form_data['description'],
                    'form_fields': form_data['form_fields'],
                    'created_by': admin_user,
                    'hospital_specific': True,
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Template already exists: {template.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Created {created_count} new PDF form templates')
        )
```

## Phase 12: Documentation and Deployment

### 12.1 README Update

Add to main CLAUDE.md:

````markdown
### PDF Forms App

**Hospital-specific PDF form overlay functionality**

- Models: PDFFormTemplate, PDFFormSubmission
- Dynamic form generation from PDF field configuration
- Integration with Event system for timeline display
- Hospital-specific form templates with secure file handling
- Permission-based access control
- URL structure: `/pdf-forms/select/<patient_id>/`, `/pdf-forms/fill/<template_id>/<patient_id>/`

#### Key Features

- **Dynamic Forms**: Generate Django forms from PDF field mappings
- **PDF Overlay**: Fill PDF forms with submitted data using pypdf
- **Event Integration**: PDF submissions appear in patient timeline
- **Hospital Configuration**: Enable/disable per hospital
- **Security**: UUID-based file storage, permission checks, file validation

#### Usage Examples

```bash
# Enable PDF forms for hospital
export HOSPITAL_PDF_FORMS_ENABLED=true

# Management commands
uv run python manage.py create_sample_pdf_forms
```
````

````

### 12.2 Deployment Checklist

1. **Dependencies**: Ensure pypdf is installed
2. **Media Directories**: Verify media/pdf_forms directories exist
3. **Environment Variables**: Set PDF forms configuration
4. **Migrations**: Run database migrations
5. **Static Files**: Collect static files for CSS/JS
6. **Permissions**: Verify file system permissions for media storage
7. **PDF Templates**: Upload hospital-specific PDF templates
8. **Testing**: Run test suite to verify functionality

### 12.3 Configuration Template

```python
# Example production configuration
PDF_FORMS_CONFIG = {
    'enabled': True,
    'templates_path': '/app/media/pdf_forms/templates/',
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'allowed_extensions': ['.pdf'],
    'require_form_validation': True,
}
````

## Summary

This comprehensive implementation plan provides:

1. **Isolated Architecture**: Dedicated app that doesn't interfere with existing functionality
2. **Hospital-Specific**: Configurable per hospital installation
3. **Event Integration**: Natural fit with existing patient timeline
4. **Security Focus**: Comprehensive file validation and permission checks
5. **Extensible Design**: Easy to add new form types and features
6. **Production Ready**: Complete testing, documentation, and deployment guidance

The modular approach ensures that the PDF forms functionality can be developed, tested, and deployed independently while maintaining consistency with the existing EquipeMed architecture and design patterns.

## Key Improvements: Manual Configuration Approach

### Why This Approach is Superior

1. **Reliability**: Works with any PDF format - scanned, image-based, or digitally created
2. **Precision**: Exact positioning using centimeter coordinates for predictable results  
3. **Hospital-Friendly**: Perfect for legacy hospital forms that are often scanned documents
4. **User Control**: Complete control over field positioning, formatting, and appearance
5. **No Dependency Issues**: Doesn't rely on PDF form field detection or specific PDF structures

### Implementation Benefits

- **ReportLab Integration**: Professional-grade PDF generation with precise coordinate positioning
- **Coordinate System**: Intuitive centimeter-based positioning from top-left origin
- **Multi-Format Support**: Handles text, choice, boolean, and date fields with proper formatting
- **Visual Configuration**: Admin interface allows easy field configuration with PDF preview
- **Merge Strategy**: Clean overlay approach that preserves original PDF appearance

### Comparison with Auto-Extraction

| Aspect | Manual Configuration | Auto-Extraction |
|--------|---------------------|------------------|
| **Compatibility** | Any PDF format | Only fillable PDFs |
| **Reliability** | 100% predictable | Unreliable detection |
| **Hospital Forms** | Perfect for scanned forms | Limited to digital forms |
| **Positioning** | Precise cm coordinates | Approximate detection |
| **Maintenance** | Simple JSON config | Complex field mapping |
| **Setup Time** | One-time configuration | Ongoing detection issues |

This approach ensures that the PDF forms feature will work reliably in real hospital environments where forms are often legacy scanned documents rather than modern fillable PDFs.
