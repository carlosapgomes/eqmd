from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
import json
from .models import PDFFormTemplate, PDFFormSubmission
from .services.field_mapping import PatientFieldMapper


@admin.register(PDFFormTemplate)
class PDFFormTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'configuration_status_display', 'hospital_specific', 'is_active', 'created_at', 'pdf_preview', 'configure_fields']
    list_filter = ['hospital_specific', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'pdf_file'),
            'description': 'Upload a PDF file and provide basic information. You can save the template and configure fields using the visual configurator later.'
        }),
        ('Field Configuration', {
            'fields': ('form_fields',),
            'description': 'Optional: Manually configure field positions using JSON, or leave empty and use the visual configurator after saving.',
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('hospital_specific', 'is_active')
        }),
        ('Audit', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    def get_urls(self):
        """Add custom URLs for the visual field configurator."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/configure-fields/',
                self.admin_site.admin_view(self.configure_fields_view),
                name='pdf_forms_pdfformtemplate_configure_fields'
            ),
            path(
                '<path:object_id>/api/pdf-preview/',
                self.admin_site.admin_view(self.pdf_preview_api),
                name='pdf_forms_pdfformtemplate_pdf_preview_api'
            ),
            path(
                '<path:object_id>/api/save-fields/',
                self.admin_site.admin_view(self.save_fields_api),
                name='pdf_forms_pdfformtemplate_save_fields_api'
            ),
        ]
        return custom_urls + urls
    
    def configure_fields_view(self, request, object_id):
        """Visual field configuration view."""
        template = get_object_or_404(PDFFormTemplate, id=object_id)
        
        # Ensure user has permission to change this template
        if not self.has_change_permission(request, template):
            raise PermissionDenied("You don't have permission to configure fields for this template")
        
        # Get available patient fields for mapping
        patient_fields = PatientFieldMapper.get_available_patient_fields()
        patient_field_options = [
            {'value': '', 'label': '-- No Auto-Population --'}
        ]
        for field_path, field_info in patient_fields.items():
            patient_field_options.append({
                'value': field_path,
                'label': f"{field_info['label']} ({field_path})",
                'type': field_info['type']
            })

        context = {
            'template': template,
            'title': f'Configure Fields: {template.name}',
            'opts': self.model._meta,
            'original': template,
            'has_change_permission': True,
            'has_view_permission': True,
            'field_types': [
                {'value': 'text', 'label': 'Text Field'},
                {'value': 'textarea', 'label': 'Text Area'},
                {'value': 'number', 'label': 'Number'},
                {'value': 'date', 'label': 'Date'},
                {'value': 'choice', 'label': 'Choice (Dropdown)'},
                {'value': 'boolean', 'label': 'Checkbox'},
                {'value': 'email', 'label': 'Email'},
            ],
            'patient_field_options': patient_field_options,
            'current_fields_json': json.dumps(template.form_fields or {}),
            'admin_media_prefix': '/static/admin/',
        }
        
        return render(request, 'admin/pdf_forms/pdfformtemplate/configure_fields.html', context)
    
    def pdf_preview_api(self, request, object_id):
        """API endpoint to get PDF preview as base64 image."""
        template = get_object_or_404(PDFFormTemplate, id=object_id)
        
        if not template.pdf_file:
            return JsonResponse({'error': 'No PDF file uploaded'}, status=400)
        
        try:
            # Import PDF processing libraries
            from pdf2image import convert_from_path
            import base64
            from io import BytesIO
            
            # Convert first page of PDF to image
            images = convert_from_path(template.pdf_file.path, first_page=1, last_page=1, dpi=150)
            
            if images:
                # Convert PIL image to base64
                img_buffer = BytesIO()
                images[0].save(img_buffer, format='PNG')
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
                
                return JsonResponse({
                    'success': True,
                    'image': f'data:image/png;base64,{img_base64}',
                    'width': images[0].width,
                    'height': images[0].height
                })
            else:
                return JsonResponse({'error': 'Could not convert PDF to image'}, status=500)
                
        except ImportError:
            return JsonResponse({
                'error': 'PDF preview requires pdf2image library. Install with: uv add pdf2image',
                'solution': 'Run: uv add pdf2image'
            }, status=500)
        except Exception as e:
            error_message = str(e).lower()
            if 'poppler' in error_message:
                return JsonResponse({
                    'error': 'PDF preview requires Poppler to be installed on the system.',
                    'solution': 'Install Poppler:\n• Ubuntu/Debian: sudo apt install poppler-utils\n• macOS: brew install poppler\n• Windows: Download from https://blog.alivate.com.au/poppler-windows/',
                    'alternative': 'You can still configure fields manually using the JSON editor below the PDF preview area.'
                }, status=500)
            else:
                return JsonResponse({
                    'error': f'Error processing PDF: {str(e)}',
                    'alternative': 'You can still configure fields manually using the JSON editor.'
                }, status=500)
    
    def save_fields_api(self, request, object_id):
        """API endpoint to save field configuration from visual editor."""
        if request.method != 'POST':
            return JsonResponse({'error': 'POST required'}, status=405)
        
        template = get_object_or_404(PDFFormTemplate, id=object_id)
        
        # Ensure user has permission to change this template
        if not self.has_change_permission(request, template):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        try:
            # Parse JSON data from request
            data = json.loads(request.body)
            fields_config = data.get('fields', {})
            
            # Validate field configuration
            self.validate_fields_config(fields_config)
            
            # Save the configuration
            template.form_fields = fields_config
            template.updated_by = request.user
            template.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Field configuration saved successfully for {template.name}'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Error saving fields: {str(e)}'}, status=500)
    
    def validate_fields_config(self, fields_config):
        """Validate the field configuration structure."""
        if not isinstance(fields_config, dict):
            raise ValidationError("Fields configuration must be a dictionary")
        
        # Check if this is the new sectioned format
        if 'sections' in fields_config and 'fields' in fields_config:
            # New sectioned format - validate sections and fields separately
            sections = fields_config.get('sections', {})
            fields = fields_config.get('fields', {})
            
            # Validate sections structure
            if not isinstance(sections, dict):
                raise ValidationError("Sections configuration must be a dictionary")
            
            for section_key, section_config in sections.items():
                if not isinstance(section_config, dict):
                    raise ValidationError(f"Section '{section_key}' configuration must be a dictionary")
                
                # Required section fields
                if not section_config.get('label'):
                    raise ValidationError(f"Section '{section_key}' missing required 'label'")
            
            # Validate fields using existing validation
            from .services.field_mapping import FieldMappingUtils
            is_valid, errors = FieldMappingUtils.validate_field_config(fields)
            
            if not is_valid:
                raise ValidationError('; '.join(errors))
                
        else:
            # Legacy format - validate as before
            from .services.field_mapping import FieldMappingUtils
            is_valid, errors = FieldMappingUtils.validate_field_config(fields_config)
            
            if not is_valid:
                raise ValidationError('; '.join(errors))
    
    def pdf_preview(self, obj):
        if obj.pdf_file:
            return format_html('<a href="{}" target="_blank">View PDF</a>', obj.pdf_file.url)
        return "No PDF"
    pdf_preview.short_description = "PDF Preview"
    
    def configuration_status_display(self, obj):
        """Display configuration status with styling."""
        status = obj.configuration_status
        if status == "Sem PDF":
            return format_html('<span style="color: red;">📄 {}</span>', status)
        elif status == "Não configurado":
            return format_html('<span style="color: orange;">⚠️ {}</span>', status)
        else:
            return format_html('<span style="color: green;">✅ {}</span>', status)
    configuration_status_display.short_description = "Status"
    
    def configure_fields(self, obj):
        """Link to visual field configurator."""
        if obj.pk and obj.pdf_file:
            url = reverse('admin:pdf_forms_pdfformtemplate_configure_fields', args=[obj.pk])
            if obj.is_configured:
                return format_html('<a href="{}" class="button">Editar Campos</a>', url)
            else:
                return format_html('<a href="{}" class="button" style="background-color: #ffc107; color: #000;">Configurar Campos</a>', url)
        return "Upload PDF first"
    configure_fields.short_description = "Configuração"
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PDFFormSubmission)
class PDFFormSubmissionAdmin(admin.ModelAdmin):
    list_display = ['form_template', 'patient', 'created_by', 'event_datetime', 'form_data_preview']
    list_filter = ['form_template', 'event_datetime', 'created_by']
    search_fields = ['form_template__name', 'patient__name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'event_type']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('form_template', 'patient', 'event_datetime', 'description', 'event_type')
        }),
        ('Form Data', {
            'fields': ('form_data',),
            'description': 'JSON data containing form field values. PDFs are generated on-demand from this data.'
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def form_data_preview(self, obj):
        """Display a preview of the form data."""
        if not obj.form_data:
            return format_html('<span style="color: #666;">No data</span>')
        
        # Get field count and show a preview of field names
        field_count = len(obj.form_data)
        if field_count == 0:
            return format_html('<span style="color: #666;">Empty</span>')
        
        # Show first few field names as preview
        field_names = list(obj.form_data.keys())[:3]
        preview_text = ', '.join(field_names)
        if len(obj.form_data) > 3:
            preview_text += f' (+{len(obj.form_data) - 3} more)'
        
        return format_html(
            '<span title="{}"><strong>{} fields:</strong> {}</span>',
            ', '.join(obj.form_data.keys()),
            field_count,
            preview_text
        )
    form_data_preview.short_description = "Form Data"
