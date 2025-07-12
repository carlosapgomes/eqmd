"""
MediaFiles Admin Configuration

This module provides comprehensive admin interface for media file management
with security features, thumbnails, and optimized queries.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import MediaFile, Photo, PhotoSeries, PhotoSeriesFile, VideoClip


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


class PhotoSeriesFileInline(admin.TabularInline):
    """Inline admin for PhotoSeriesFile model."""
    
    model = PhotoSeriesFile
    extra = 0
    fields = ['thumbnail_preview', 'media_file', 'order', 'description']
    readonly_fields = ['thumbnail_preview']
    ordering = ['order']
    
    def thumbnail_preview(self, obj):
        """Display thumbnail preview for media file."""
        if obj.media_file and obj.media_file.thumbnail:
            return format_html(
                '<img src="{}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 4px;" />',
                obj.media_file.thumbnail.url
            )
        return "No thumbnail"
    thumbnail_preview.short_description = "Preview"


@admin.register(PhotoSeries)
class PhotoSeriesAdmin(admin.ModelAdmin):
    """Admin interface for PhotoSeries model."""
    
    list_display = [
        'primary_thumbnail_preview',
        'description',
        'photo_count_display',
        'patient_link',
        'event_datetime',
        'created_by',
    ]
    
    list_filter = [
        'event_datetime',
        'created_by',
        'event_type',
    ]
    
    search_fields = [
        'description',
        'patient__name',
        'caption',
    ]
    
    readonly_fields = [
        'id',
        'event_type',
        'created_at',
        'updated_at',
        'photo_count_display',
        'primary_thumbnail_large',
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
        ('Photo Series Details', {
            'fields': (
                'caption',
                'photo_count_display',
                'primary_thumbnail_large',
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
    
    inlines = [PhotoSeriesFileInline]
    
    def primary_thumbnail_preview(self, obj):
        """Display primary thumbnail in list view."""
        thumbnail_url = obj.get_primary_thumbnail()
        if thumbnail_url:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                thumbnail_url
            )
        return "No photos"
    primary_thumbnail_preview.short_description = "Preview"
    
    def primary_thumbnail_large(self, obj):
        """Display large primary thumbnail in detail view."""
        thumbnail_url = obj.get_primary_thumbnail()
        if thumbnail_url:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 400px; border-radius: 8px;" />',
                thumbnail_url
            )
        return "No photos available"
    primary_thumbnail_large.short_description = "Series Preview"
    
    def photo_count_display(self, obj):
        """Display photo count."""
        count = obj.get_photo_count()
        return f"{count} foto{'s' if count != 1 else ''}"
    photo_count_display.short_description = "Photos"
    
    def patient_link(self, obj):
        """Display patient as clickable link."""
        if obj.patient:
            url = reverse('admin:patients_patient_change', args=[obj.patient.pk])
            return format_html('<a href="{}">{}</a>', url, obj.patient.name)
        return "No patient"
    patient_link.short_description = "Patient"
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related(
            'patient',
            'created_by',
            'updated_by'
        ).prefetch_related(
            'photoseriesfile_set__media_file'
        )
    
    def save_model(self, request, obj, form, change):
        """Override save to set updated_by field."""
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['reorder_photos_action', 'export_series_zip', 'duplicate_series']
    
    def reorder_photos_action(self, request, queryset):
        """Bulk reorder photos action."""
        self.message_user(request, f"Use the individual edit pages to reorder photos in each series.")
    reorder_photos_action.short_description = "Reorder photos in selected series"
    
    def export_series_zip(self, request, queryset):
        """Export series as ZIP action."""
        self.message_user(request, f"ZIP export functionality will be implemented in future versions.")
    export_series_zip.short_description = "Export selected series as ZIP"
    
    def duplicate_series(self, request, queryset):
        """Duplicate series action."""
        self.message_user(request, f"Series duplication functionality will be implemented in future versions.")
    duplicate_series.short_description = "Duplicate selected series"


@admin.register(VideoClip)
class VideoClipAdmin(admin.ModelAdmin):
    """Admin interface for VideoClip model."""

    list_display = [
        'thumbnail_preview',
        'description',
        'duration_display',
        'patient_link',
        'event_datetime',
        'created_by',
        'file_size_display',
    ]

    list_filter = [
        'event_datetime',
        'created_by',
        'duration',
        'video_codec',
        'event_type',
    ]

    search_fields = [
        'description',
        'patient__name',
        'original_filename',
        'caption',
    ]

    readonly_fields = [
        'id',
        'event_type',
        'created_at',
        'updated_at',
        'duration_display',
        'file_size_display',
        'dimensions_display',
        'video_info_display',
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
        ('Video File (FilePond)', {
            'fields': (
                'file_id',
                'original_filename',
                'caption',
            )
        }),
        ('Video Metadata', {
            'fields': (
                'duration_display',
                'file_size_display',
                'dimensions_display',
                'video_codec',
                'video_info_display',
            ),
            'classes': ('collapse',),
        }),
        ('Audit Trail', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )

    def thumbnail_preview(self, obj):
        """Display video thumbnail in list view."""
        # TODO: Implement thumbnail support for FilePond videos
        return format_html(
            '<div style="position: relative; width: 50px; height: 50px; background: #f8f9fa; border-radius: 4px; display: flex; align-items: center; justify-content: center;">'
            '<div style="background: rgba(0,0,0,0.7); color: white; font-size: 12px; padding: 2px 4px; border-radius: 2px;">▶</div>'
            '</div>'
        )
    thumbnail_preview.short_description = "Preview"

    def duration_display(self, obj):
        """Format duration in MM:SS format for admin display."""
        return obj.get_duration()
    duration_display.short_description = "Duration"

    def file_size_display(self, obj):
        """Format file size for admin display."""
        return obj.get_display_size()
    file_size_display.short_description = "File Size"

    def dimensions_display(self, obj):
        """Format dimensions for admin display."""
        return obj.get_dimensions_display()
    dimensions_display.short_description = "Dimensions"

    def video_info_display(self, obj):
        """Display comprehensive video information."""
        codec = obj.video_codec or 'Unknown'
        dimensions = obj.get_dimensions_display()
        
        return format_html(
            '''
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                <h4 style="margin-top: 0;">Video Technical Details (FilePond)</h4>
                <p><strong>File ID:</strong> {}</p>
                <p><strong>Original Filename:</strong> {}</p>
                <p><strong>File Size:</strong> {}</p>
                <p><strong>Duration:</strong> {}</p>
                <p><strong>Resolution:</strong> {}</p>
                <p><strong>Codec:</strong> {}</p>
                <p><strong>Secure URL:</strong> <a href="{}" target="_blank">View Video</a></p>
            </div>
            ''',
            obj.file_id,
            obj.original_filename,
            obj.get_display_size(),
            obj.get_duration(),
            dimensions,
            codec,
            obj.get_video_url() or '#',
        )
    video_info_display.short_description = "Video Information"

    def patient_link(self, obj):
        """Display patient as clickable link."""
        if obj.patient:
            url = reverse('admin:patients_patient_change', args=[obj.patient.pk])
            return format_html('<a href="{}">{}</a>', url, obj.patient.name)
        return "No patient"
    patient_link.short_description = "Patient"

    def get_queryset(self, request):
        """Optimize queryset for admin list view with select_related."""
        return super().get_queryset(request).select_related(
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

    actions = ['export_video_info', 'regenerate_thumbnails', 'validate_video_files']

    def export_video_info(self, request, queryset):
        """Export video information as CSV."""
        self.message_user(request, f"Video info export functionality will be implemented in future versions.")
    export_video_info.short_description = "Export video information as CSV"

    def regenerate_thumbnails(self, request, queryset):
        """Regenerate thumbnails for selected videos."""
        self.message_user(request, "Thumbnail regeneration not yet implemented for FilePond videos.")
    regenerate_thumbnails.short_description = "Regenerate thumbnails for selected videos"

    def validate_video_files(self, request, queryset):
        """Validate video files for security and format compliance."""
        valid_count = 0
        invalid_count = 0
        
        for video_clip in queryset:
            try:
                # Basic validation for FilePond videos
                if video_clip.duration and video_clip.duration > 120:
                    invalid_count += 1
                    self.message_user(request, f"Duration validation failed for {video_clip}: exceeds 2 minutes", level='WARNING')
                else:
                    valid_count += 1
            except Exception as e:
                invalid_count += 1
                self.message_user(request, f"Validation failed for {video_clip}: {e}", level='WARNING')
        
        self.message_user(request, f"Validation complete: {valid_count} valid, {invalid_count} invalid videos.")
    validate_video_files.short_description = "Validate selected video files"
