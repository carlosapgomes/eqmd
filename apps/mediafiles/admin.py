"""
MediaFiles Admin Configuration

This module provides comprehensive admin interface for media file management
with security features, thumbnails, and optimized queries.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import MediaFile, Photo


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    """Admin interface for MediaFile model."""

    list_display = [
        'thumbnail_preview',
        'original_filename',
        'get_display_size',
        'get_dimensions_display',
        'mime_type',
        'created_at',
    ]

    list_filter = [
        'mime_type',
        'created_at',
        'width',
        'height',
    ]

    search_fields = [
        'original_filename',
        'file_hash',
    ]

    readonly_fields = [
        'id',
        'file_hash',
        'file_size',
        'mime_type',
        'width',
        'height',
        'duration',
        'created_at',
        'updated_at',
        'thumbnail_preview_large',
        'metadata_display',
    ]

    fieldsets = (
        ('File Information', {
            'fields': (
                'id',
                'original_filename',
                'file',
                'thumbnail_preview_large',
            )
        }),
        ('File Metadata', {
            'fields': (
                'file_hash',
                'file_size',
                'mime_type',
                'width',
                'height',
                'duration',
            )
        }),
        ('Additional Data', {
            'fields': (
                'metadata_display',
            ),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )

    def thumbnail_preview(self, obj):
        """Display small thumbnail in list view."""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.thumbnail.url
            )
        return "No thumbnail"
    thumbnail_preview.short_description = "Preview"

    def thumbnail_preview_large(self, obj):
        """Display large thumbnail in detail view."""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 8px;" />',
                obj.thumbnail.url
            )
        return "No thumbnail available"
    thumbnail_preview_large.short_description = "Thumbnail Preview"

    def metadata_display(self, obj):
        """Display formatted metadata."""
        if obj.metadata:
            import json
            return format_html(
                '<pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 12px;">{}</pre>',
                json.dumps(obj.metadata, indent=2)
            )
        return "No metadata"
    metadata_display.short_description = "Metadata"

    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related()


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    """Admin interface for Photo model."""

    list_display = [
        'thumbnail_preview',
        'description',
        'patient_link',
        'event_datetime',
        'created_by',
        'get_file_info_display',
    ]

    list_filter = [
        'event_datetime',
        'created_by',
        'patient__current_hospital',
        'event_type',
    ]

    search_fields = [
        'description',
        'patient__name',
        'media_file__original_filename',
        'caption',
    ]

    readonly_fields = [
        'id',
        'event_type',
        'created_at',
        'updated_at',
        'thumbnail_preview_large',
        'file_info_display',
    ]

    fieldsets = (
        ('Event Information', {
            'fields': (
                'id',
                'event_type',
                'description',
                'event_datetime',
                'patient',
                'created_by',
                'updated_by',
            )
        }),
        ('Photo Details', {
            'fields': (
                'media_file',
                'caption',
                'thumbnail_preview_large',
                'file_info_display',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )

    def thumbnail_preview(self, obj):
        """Display small thumbnail in list view."""
        if obj.media_file and obj.media_file.thumbnail:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.media_file.thumbnail.url
            )
        return "No thumbnail"
    thumbnail_preview.short_description = "Preview"

    def thumbnail_preview_large(self, obj):
        """Display large thumbnail in detail view."""
        if obj.media_file and obj.media_file.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 400px; border-radius: 8px;" />',
                obj.media_file.thumbnail.url
            )
        return "No thumbnail available"
    thumbnail_preview_large.short_description = "Photo Preview"

    def patient_link(self, obj):
        """Display patient as clickable link."""
        if obj.patient:
            url = reverse('admin:patients_patient_change', args=[obj.patient.pk])
            return format_html('<a href="{}">{}</a>', url, obj.patient.name)
        return "No patient"
    patient_link.short_description = "Patient"

    def get_file_info_display(self, obj):
        """Display file information in list view."""
        if obj.media_file:
            return f"{obj.media_file.get_display_size()} • {obj.media_file.get_dimensions_display()}"
        return "No file"
    get_file_info_display.short_description = "File Info"

    def file_info_display(self, obj):
        """Display detailed file information."""
        if obj.media_file:
            return format_html(
                '''
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                    <h4 style="margin-top: 0;">File Details</h4>
                    <p><strong>Original Filename:</strong> {}</p>
                    <p><strong>File Size:</strong> {}</p>
                    <p><strong>Dimensions:</strong> {}</p>
                    <p><strong>MIME Type:</strong> {}</p>
                    <p><strong>File Hash:</strong> <code>{}</code></p>
                    <p><strong>Secure URL:</strong> <a href="{}" target="_blank">View File</a></p>
                </div>
                ''',
                obj.media_file.original_filename,
                obj.media_file.get_display_size(),
                obj.media_file.get_dimensions_display(),
                obj.media_file.mime_type,
                obj.media_file.file_hash[:16] + '...',
                obj.media_file.get_secure_url(),
            )
        return "No file information available"
    file_info_display.short_description = "File Information"

    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related(
            'media_file',
            'patient',
            'created_by',
            'updated_by'
        )

    def save_model(self, request, obj, form, change):
        """Override save to set updated_by field."""
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
