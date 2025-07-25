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
