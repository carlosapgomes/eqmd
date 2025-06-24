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
        'patient__current_hospital',
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
        'patient__current_hospital',
        'media_file__duration',
        'media_file__video_codec',
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
        'duration_display',
        'video_codec',
        'video_bitrate',
        'fps',
        'thumbnail_preview_large',
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
        ('Video File', {
            'fields': (
                'media_file',
                'caption',
                'thumbnail_preview_large',
            )
        }),
        ('Video Metadata', {
            'fields': (
                'duration_display',
                'video_codec',
                'video_bitrate',
                'fps',
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
        if obj.media_file and obj.media_file.thumbnail:
            return format_html(
                '<div style="position: relative;">'
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />'
                '<div style="position: absolute; top: 2px; right: 2px; background: rgba(0,0,0,0.7); color: white; font-size: 10px; padding: 1px 3px; border-radius: 2px;">▶</div>'
                '</div>',
                obj.media_file.thumbnail.url
            )
        return "No thumbnail"
    thumbnail_preview.short_description = "Preview"

    def thumbnail_preview_large(self, obj):
        """Display large video thumbnail in detail view."""
        if obj.media_file and obj.media_file.thumbnail:
            video_url = obj.get_video_url()
            return format_html(
                '''
                <div style="position: relative; display: inline-block;">
                    <img src="{}" style="max-width: 400px; max-height: 400px; border-radius: 8px;" />
                    <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                                background: rgba(0,0,0,0.8); color: white; padding: 10px; border-radius: 50%;">
                        <span style="font-size: 24px;">▶</span>
                    </div>
                    <div style="position: absolute; bottom: 5px; left: 5px; background: rgba(0,0,0,0.8); 
                                color: white; padding: 2px 6px; border-radius: 4px; font-size: 12px;">
                        {}
                    </div>
                    <div style="margin-top: 10px;">
                        <a href="{}" target="_blank" style="color: #007cba; text-decoration: none;">
                            🎥 Watch Video
                        </a>
                    </div>
                </div>
                ''',
                obj.media_file.thumbnail.url,
                obj.get_duration(),
                video_url if video_url else '#'
            )
        return "No thumbnail available"
    thumbnail_preview_large.short_description = "Video Preview"

    def duration_display(self, obj):
        """Format duration in MM:SS format for admin display."""
        if obj.media_file and obj.media_file.duration:
            return obj.media_file.get_duration_display()
        return "0:00"
    duration_display.short_description = "Duration"

    def file_size_display(self, obj):
        """Format file size for admin display."""
        if obj.media_file:
            return obj.media_file.get_display_size()
        return "Unknown"
    file_size_display.short_description = "File Size"

    def video_info_display(self, obj):
        """Display comprehensive video information."""
        if obj.media_file:
            codec = obj.media_file.video_codec or 'Unknown'
            bitrate = f"{obj.media_file.video_bitrate:,} bps" if obj.media_file.video_bitrate else 'Unknown'
            fps = f"{obj.media_file.fps:.1f} fps" if obj.media_file.fps else 'Unknown'
            dimensions = obj.media_file.get_dimensions_display()
            
            return format_html(
                '''
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                    <h4 style="margin-top: 0;">Video Technical Details</h4>
                    <p><strong>Original Filename:</strong> {}</p>
                    <p><strong>File Size:</strong> {}</p>
                    <p><strong>Duration:</strong> {}</p>
                    <p><strong>Resolution:</strong> {}</p>
                    <p><strong>Codec:</strong> {}</p>
                    <p><strong>Bitrate:</strong> {}</p>
                    <p><strong>Frame Rate:</strong> {}</p>
                    <p><strong>MIME Type:</strong> {}</p>
                    <p><strong>File Hash:</strong> <code>{}</code></p>
                    <p><strong>Secure URL:</strong> <a href="{}" target="_blank">View Video</a></p>
                </div>
                ''',
                obj.media_file.original_filename,
                obj.media_file.get_display_size(),
                obj.get_duration(),
                dimensions,
                codec,
                bitrate,
                fps,
                obj.media_file.mime_type,
                obj.media_file.file_hash[:16] + '...',
                obj.get_video_url() or '#',
            )
        return "No video information available"
    video_info_display.short_description = "Video Information"

    def patient_link(self, obj):
        """Display patient as clickable link."""
        if obj.patient:
            url = reverse('admin:patients_patient_change', args=[obj.patient.pk])
            return format_html('<a href="{}">{}</a>', url, obj.patient.name)
        return "No patient"
    patient_link.short_description = "Patient"

    def video_codec(self, obj):
        """Display video codec."""
        return obj.media_file.video_codec if obj.media_file else 'Unknown'
    video_codec.short_description = "Codec"

    def video_bitrate(self, obj):
        """Display video bitrate."""
        if obj.media_file and obj.media_file.video_bitrate:
            return f"{obj.media_file.video_bitrate:,} bps"
        return 'Unknown'
    video_bitrate.short_description = "Bitrate"

    def fps(self, obj):
        """Display frame rate."""
        if obj.media_file and obj.media_file.fps:
            return f"{obj.media_file.fps:.1f} fps"
        return 'Unknown'
    fps.short_description = "FPS"

    def get_queryset(self, request):
        """Optimize queryset for admin list view with select_related."""
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

    actions = ['export_video_info', 'regenerate_thumbnails', 'validate_video_files']

    def export_video_info(self, request, queryset):
        """Export video information as CSV."""
        self.message_user(request, f"Video info export functionality will be implemented in future versions.")
    export_video_info.short_description = "Export video information as CSV"

    def regenerate_thumbnails(self, request, queryset):
        """Regenerate thumbnails for selected videos."""
        count = 0
        for video_clip in queryset:
            if video_clip.media_file:
                try:
                    # Clear existing thumbnail
                    if video_clip.media_file.thumbnail:
                        video_clip.media_file.thumbnail.delete(save=False)
                    
                    # Generate new thumbnail
                    video_clip.media_file.generate_video_thumbnail()
                    video_clip.media_file.save(update_fields=['thumbnail'])
                    count += 1
                except Exception as e:
                    self.message_user(request, f"Error regenerating thumbnail for {video_clip}: {e}", level='ERROR')
        
        self.message_user(request, f"Successfully regenerated {count} video thumbnails.")
    regenerate_thumbnails.short_description = "Regenerate thumbnails for selected videos"

    def validate_video_files(self, request, queryset):
        """Validate video files for security and format compliance."""
        valid_count = 0
        invalid_count = 0
        
        for video_clip in queryset:
            if video_clip.media_file:
                try:
                    video_clip.media_file.validate_video_security()
                    video_clip.media_file.validate_video_duration()
                    valid_count += 1
                except Exception as e:
                    invalid_count += 1
                    self.message_user(request, f"Validation failed for {video_clip}: {e}", level='WARNING')
        
        self.message_user(request, f"Validation complete: {valid_count} valid, {invalid_count} invalid videos.")
    validate_video_files.short_description = "Validate selected video files"
