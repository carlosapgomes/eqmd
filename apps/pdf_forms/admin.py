from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
import json
from .models import PDFFormTemplate, PDFFormSubmission


@admin.register(PDFFormTemplate)
class PDFFormTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'hospital_specific', 'is_active', 'created_at', 'pdf_preview', 'configure_fields']
    list_filter = ['hospital_specific', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'pdf_file')
        }),
        ('Field Configuration', {
            'fields': ('form_fields',),
            'description': 'Configure field positions using x,y coordinates in centimeters or use the visual configurator'
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
        
        required_field_props = ['type', 'label', 'x', 'y', 'width', 'height']
        valid_field_types = ['text', 'textarea', 'number', 'date', 'choice', 'boolean', 'email']
        
        for field_name, field_config in fields_config.items():
            if not isinstance(field_config, dict):
                raise ValidationError(f"Field '{field_name}' configuration must be a dictionary")
            
            # Check required properties
            for prop in required_field_props:
                if prop not in field_config:
                    raise ValidationError(f"Field '{field_name}' missing required property: {prop}")
            
            # Validate field type
            if field_config['type'] not in valid_field_types:
                raise ValidationError(f"Field '{field_name}' has invalid type: {field_config['type']}")
            
            # Validate numeric properties
            numeric_props = ['x', 'y', 'width', 'height']
            for prop in numeric_props:
                try:
                    float(field_config[prop])
                except (ValueError, TypeError):
                    raise ValidationError(f"Field '{field_name}' property '{prop}' must be numeric")
            
            # Validate choices for choice fields
            if field_config['type'] == 'choice':
                if 'choices' not in field_config or not isinstance(field_config['choices'], list):
                    raise ValidationError(f"Choice field '{field_name}' must have a 'choices' list")
    
    def pdf_preview(self, obj):
        if obj.pdf_file:
            return format_html('<a href="{}" target="_blank">View PDF</a>', obj.pdf_file.url)
        return "No PDF"
    pdf_preview.short_description = "PDF Preview"
    
    def configure_fields(self, obj):
        """Link to visual field configurator."""
        if obj.pk and obj.pdf_file:
            url = reverse('admin:pdf_forms_pdfformtemplate_configure_fields', args=[obj.pk])
            return format_html('<a href="{}" class="button">Configure Fields</a>', url)
        return "Upload PDF first"
    configure_fields.short_description = "Visual Config"
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PDFFormSubmission)
class PDFFormSubmissionAdmin(admin.ModelAdmin):
    list_display = ['form_template', 'patient', 'created_by', 'event_datetime', 'file_size_display']
    list_filter = ['form_template', 'event_datetime', 'created_by']
    search_fields = ['form_template__name', 'patient__name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'event_type', 'file_size', 'original_filename']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('form_template', 'patient', 'event_datetime', 'description', 'event_type')
        }),
        ('Form Data', {
            'fields': ('form_data',),
            'classes': ('collapse',)
        }),
        ('Generated PDF', {
            'fields': ('generated_pdf', 'original_filename', 'file_size')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def file_size_display(self, obj):
        if obj.file_size:
            # Convert bytes to human readable format
            if obj.file_size < 1024:
                return f"{obj.file_size} bytes"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "Unknown"
    file_size_display.short_description = "File Size"
