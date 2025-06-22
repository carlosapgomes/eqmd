# MediaFiles Template Tags
# Template tags for media display and formatting

from django import template
from django.utils.html import format_html
from django.conf import settings
from pathlib import Path

from ..utils import format_file_size, format_duration

register = template.Library()


@register.simple_tag
def mediafiles_thumbnail(media_file, size="medium", css_class=""):
    """
    Display media thumbnails with appropriate fallbacks.

    Args:
        media_file: MediaFile instance
        size: Thumbnail size ('small', 'medium', 'large')
        css_class: Additional CSS classes

    Returns:
        HTML for thumbnail display
    """
    if not media_file:
        return ""

    # Size mappings
    size_classes = {
        'small': 'thumbnail-sm',
        'medium': 'thumbnail-md',
        'large': 'thumbnail-lg'
    }

    size_class = size_classes.get(size, 'thumbnail-md')
    all_classes = f"{size_class} {css_class}".strip()

    # Check if thumbnail exists
    if hasattr(media_file, 'thumbnail_path') and media_file.thumbnail_path:
        thumbnail_url = f"{settings.MEDIA_URL}{media_file.thumbnail_path}"
        alt_text = f"Thumbnail for {media_file.original_filename}"

        return format_html(
            '<img src="{}" alt="{}" class="{}" loading="lazy">',
            thumbnail_url,
            alt_text,
            all_classes
        )

    # Fallback to file type icon
    icon_class = mediafiles_type_icon(media_file.file_type)
    return format_html(
        '<div class="thumbnail-placeholder {}"><i class="{}"></i></div>',
        all_classes,
        icon_class
    )


@register.filter
def mediafiles_duration(seconds):
    """
    Format video duration in human-readable format.

    Args:
        seconds: Duration in seconds (float or int)

    Returns:
        Formatted duration string
    """
    if seconds is None:
        return ""

    try:
        return format_duration(float(seconds))
    except (ValueError, TypeError):
        return ""


@register.filter
def mediafiles_file_size(bytes_size):
    """
    Format file sizes in human-readable format.

    Args:
        bytes_size: File size in bytes

    Returns:
        Formatted file size string
    """
    if bytes_size is None:
        return ""

    try:
        return format_file_size(int(bytes_size))
    except (ValueError, TypeError):
        return ""


@register.simple_tag
def mediafiles_type_icon(file_type):
    """
    Get appropriate Bootstrap Icons for file types.

    Args:
        file_type: File type ('image' or 'video')

    Returns:
        Bootstrap icon class string
    """
    icon_map = {
        'image': 'bi bi-image',
        'video': 'bi bi-play-circle',
        'photo': 'bi bi-camera',
        'photo_series': 'bi bi-images',
        'video_clip': 'bi bi-play-circle-fill'
    }

    return icon_map.get(file_type, 'bi bi-file-earmark')


@register.inclusion_tag('mediafiles/partials/media_card.html', takes_context=True)
def media_card(context, media_object, show_patient=True, show_actions=True):
    """
    Render a media card for Photo, PhotoSeries, or VideoClip.

    Args:
        context: Template context
        media_object: Photo, PhotoSeries, or VideoClip instance
        show_patient: Whether to show patient information
        show_actions: Whether to show action buttons

    Returns:
        Context for media card template
    """
    request = context.get('request')
    user = request.user if request else None

    # Determine media type
    media_type = 'unknown'
    if hasattr(media_object, 'event_type'):
        from apps.events.models import Event
        if media_object.event_type == Event.PHOTO_EVENT:
            media_type = 'photo'
        elif media_object.event_type == Event.PHOTO_SERIES_EVENT:
            media_type = 'photo_series'
        elif media_object.event_type == Event.VIDEO_CLIP_EVENT:
            media_type = 'video_clip'

    return {
        'media_object': media_object,
        'media_type': media_type,
        'show_patient': show_patient,
        'show_actions': show_actions,
        'user': user,
        'request': request,
    }


@register.simple_tag
def mediafiles_count_for_patient(patient, media_type=None):
    """
    Get count of media files for a patient.

    Args:
        patient: Patient instance
        media_type: Optional media type filter ('photo', 'photo_series', 'video')

    Returns:
        Count of media files
    """
    if not patient:
        return 0

    from apps.events.models import Event

    # Build queryset
    queryset = Event.objects.filter(patient=patient)

    if media_type == 'photo':
        queryset = queryset.filter(event_type=Event.PHOTO_EVENT)
    elif media_type == 'photo_series':
        queryset = queryset.filter(event_type=Event.PHOTO_SERIES_EVENT)
    elif media_type == 'video':
        queryset = queryset.filter(event_type=Event.VIDEO_CLIP_EVENT)
    else:
        # All media types
        queryset = queryset.filter(
            event_type__in=[Event.PHOTO_EVENT, Event.PHOTO_SERIES_EVENT, Event.VIDEO_CLIP_EVENT]
        )

    return queryset.count()


@register.filter
def file_extension(filename):
    """
    Get file extension from filename.

    Args:
        filename: Name of the file

    Returns:
        File extension (e.g., '.jpg', '.mp4')
    """
    if not filename:
        return ""

    return Path(filename).suffix.lower()


@register.filter
def is_image_file(filename):
    """
    Check if filename represents an image file.

    Args:
        filename: Name of the file

    Returns:
        True if it's an image file extension
    """
    if not filename:
        return False

    image_extensions = getattr(settings, 'MEDIA_ALLOWED_IMAGE_EXTENSIONS', ['.jpg', '.jpeg', '.png', '.webp'])
    return Path(filename).suffix.lower() in image_extensions


@register.filter
def is_video_file(filename):
    """
    Check if filename represents a video file.

    Args:
        filename: Name of the file

    Returns:
        True if it's a video file extension
    """
    if not filename:
        return False

    video_extensions = getattr(settings, 'MEDIA_ALLOWED_VIDEO_EXTENSIONS', ['.mp4', '.webm', '.mov'])
    return Path(filename).suffix.lower() in video_extensions


@register.inclusion_tag('mediafiles/partials/media_gallery.html')
def media_gallery(media_files, columns=3):
    """
    Render media gallery with responsive grid.

    Args:
        media_files: QuerySet or list of media objects
        columns: Number of columns for the grid (default: 3)

    Returns:
        Context for media gallery template
    """
    return {
        'media_files': media_files,
        'columns': columns,
        'grid_class': f'row-cols-1 row-cols-md-{columns}'
    }
