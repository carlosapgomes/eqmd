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


# Photo-specific template tags (Step 3.7)

@register.simple_tag
def photo_thumbnail(photo, size="medium", css_class=""):
    """
    Display photo thumbnail with appropriate styling.

    Args:
        photo: Photo instance
        size: Thumbnail size ('small', 'medium', 'large')
        css_class: Additional CSS classes

    Returns:
        HTML for photo thumbnail display
    """
    if not photo or not hasattr(photo, 'media_file'):
        return ""

    # Size mappings for photos
    size_classes = {
        'small': 'photo-thumbnail-sm',
        'medium': 'photo-thumbnail-md',
        'large': 'photo-thumbnail-lg'
    }

    size_class = size_classes.get(size, 'photo-thumbnail-md')
    all_classes = f"photo-thumbnail {size_class} {css_class}".strip()

    # Get thumbnail URL
    if hasattr(photo.media_file, 'thumbnail_path') and photo.media_file.thumbnail_path:
        thumbnail_url = f"{settings.MEDIA_URL}{photo.media_file.thumbnail_path}"
    else:
        # Fallback to original file
        thumbnail_url = f"{settings.MEDIA_URL}{photo.media_file.file.name}"

    alt_text = f"Foto: {photo.description or photo.media_file.original_filename}"

    return format_html(
        '<img src="{}" alt="{}" class="{}" loading="lazy">',
        thumbnail_url,
        alt_text,
        all_classes
    )


@register.simple_tag
def photo_modal_trigger(photo, trigger_text="Ver foto", css_class=""):
    """
    Create modal trigger button for photo viewing.

    Args:
        photo: Photo instance
        trigger_text: Text for the trigger button
        css_class: Additional CSS classes

    Returns:
        HTML for modal trigger button
    """
    if not photo or not hasattr(photo, 'media_file'):
        return ""

    # Get photo data for modal
    photo_url = f"{settings.MEDIA_URL}{photo.media_file.file.name}"

    dimensions = ""
    if photo.media_file.width and photo.media_file.height:
        dimensions = f"{photo.media_file.width}x{photo.media_file.height}"

    file_size = format_file_size(photo.media_file.file_size) if photo.media_file.file_size else ""

    created_date = photo.event_datetime.strftime("%d/%m/%Y %H:%M") if photo.event_datetime else ""
    author = photo.created_by.get_full_name() if photo.created_by else ""

    button_classes = f"btn btn-outline-primary {css_class}".strip()

    return format_html(
        '''<button type="button" class="{}" data-bs-toggle="modal" data-bs-target="#photoModal"
           data-photo-id="{}" data-photo-url="{}" data-photo-title="{}"
           data-photo-filename="{}" data-photo-size="{}" data-photo-dimensions="{}"
           data-photo-created="{}" data-photo-author="{}">
           <i class="bi bi-eye me-1"></i>{}
        </button>''',
        button_classes,
        photo.id,
        photo_url,
        photo.description or "Foto",
        photo.media_file.original_filename,
        file_size,
        dimensions,
        created_date,
        author,
        trigger_text
    )


@register.inclusion_tag('mediafiles/partials/photo_metadata.html')
def photo_metadata(photo, show_technical=True):
    """
    Display photo metadata in a formatted layout.

    Args:
        photo: Photo instance
        show_technical: Whether to show technical metadata

    Returns:
        Context for photo metadata template
    """
    if not photo or not hasattr(photo, 'media_file'):
        return {}

    metadata = {
        'photo': photo,
        'media_file': photo.media_file,
        'show_technical': show_technical,
        'file_size': format_file_size(photo.media_file.file_size) if photo.media_file.file_size else None,
        'dimensions': None,
        'created_date': photo.event_datetime.strftime("%d/%m/%Y %H:%M") if photo.event_datetime else None,
        'author': photo.created_by.get_full_name() if photo.created_by else None,
    }

    if photo.media_file.width and photo.media_file.height:
        metadata['dimensions'] = f"{photo.media_file.width}x{photo.media_file.height}"

    return metadata


@register.filter
def photo_file_size(photo):
    """
    Format photo file size display.

    Args:
        photo: Photo instance

    Returns:
        Formatted file size string
    """
    if not photo or not hasattr(photo, 'media_file') or not photo.media_file.file_size:
        return ""

    return format_file_size(photo.media_file.file_size)
