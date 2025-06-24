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


# PhotoSeries-specific template tags (Step 3.7)

@register.inclusion_tag('mediafiles/partials/photoseries_carousel.html')
def photoseries_carousel(series):
    """
    Display photo carousel for PhotoSeries (per extra requirements).

    Args:
        series: PhotoSeries instance

    Returns:
        Context for photoseries carousel template
    """
    if not series:
        return {}

    ordered_photos = series.get_ordered_photos()

    return {
        'series': series,
        'photos': ordered_photos,
        'photo_count': len(ordered_photos),
        'carousel_id': f'photoCarousel_{series.id}'
    }


@register.simple_tag
def photoseries_thumbnail(series, css_class=""):
    """
    Display first photo thumbnail for PhotoSeries (per extra requirements).

    Args:
        series: PhotoSeries instance
        css_class: Additional CSS classes

    Returns:
        HTML for first photo thumbnail display
    """
    if not series:
        return ""

    primary_thumbnail = series.get_primary_thumbnail()
    if not primary_thumbnail:
        # Fallback to placeholder
        return format_html(
            '<div class="photoseries-thumbnail-placeholder {}"><i class="bi bi-images"></i></div>',
            css_class
        )

    # Get thumbnail URL
    if hasattr(primary_thumbnail, 'thumbnail_path') and primary_thumbnail.thumbnail_path:
        thumbnail_url = f"{settings.MEDIA_URL}{primary_thumbnail.thumbnail_path}"
    else:
        # Fallback to original file
        thumbnail_url = f"{settings.MEDIA_URL}{primary_thumbnail.file.name}"

    alt_text = f"Série de fotos: {series.description or 'Sem descrição'}"
    all_classes = f"photoseries-thumbnail {css_class}".strip()

    return format_html(
        '<img src="{}" alt="{}" class="{}" loading="lazy">',
        thumbnail_url,
        alt_text,
        all_classes
    )


@register.simple_tag
def photoseries_count(series):
    """
    Display photo count badge for PhotoSeries (per extra requirements).

    Args:
        series: PhotoSeries instance

    Returns:
        HTML for photo count badge
    """
    if not series:
        return ""

    count = series.get_photo_count()

    return format_html(
        '<span class="photoseries-count-badge badge bg-primary">{} foto{}</span>',
        count,
        's' if count != 1 else ''
    )


@register.inclusion_tag('mediafiles/partials/photoseries_action_buttons.html', takes_context=True)
def photoseries_action_buttons(context, photo, series):
    """
    Create action buttons for each photo in PhotoSeries.

    Args:
        context: Template context
        photo: Individual MediaFile instance
        series: PhotoSeries instance

    Returns:
        Context for action buttons template
    """
    request = context.get('request')
    user = request.user if request else None

    # Check permissions
    from apps.core.permissions import can_edit_event, can_delete_event
    can_edit = can_edit_event(user, series) if user and series else False
    can_delete = can_delete_event(user, series) if user and series else False

    return {
        'photo': photo,
        'series': series,
        'can_edit': can_edit,
        'can_delete': can_delete,
        'user': user,
        'request': request,
    }


@register.inclusion_tag('mediafiles/partials/photoseries_breadcrumb.html')
def photoseries_breadcrumb(series):
    """
    Generate breadcrumb navigation for PhotoSeries.

    Args:
        series: PhotoSeries instance

    Returns:
        Context for breadcrumb navigation template
    """
    if not series or not hasattr(series, 'patient'):
        return {}

    return {
        'series': series,
        'patient': series.patient,
        'timeline_url': series.get_timeline_return_url(),
    }


@register.simple_tag
def photoseries_metadata_item(label, value, icon_class=""):
    """
    Create a metadata item for PhotoSeries display.

    Args:
        label: Label for the metadata
        value: Value to display
        icon_class: Bootstrap icon class

    Returns:
        HTML for metadata item
    """
    if not value:
        return ""

    icon_html = f'<i class="{icon_class} me-1"></i>' if icon_class else ''

    return format_html(
        '<div class="metadata-item"><span class="metadata-label">{}{}</span><span class="metadata-value">{}</span></div>',
        icon_html,
        label,
        value
    )


@register.filter
def photoseries_photo_position(photo, series):
    """
    Get position of photo in PhotoSeries.

    Args:
        photo: MediaFile instance
        series: PhotoSeries instance

    Returns:
        Position number (1-based) or empty string
    """
    if not photo or not series:
        return ""

    try:
        from ..models import PhotoSeriesFile
        series_file = PhotoSeriesFile.objects.get(
            photo_series=series,
            media_file=photo
        )
        return series_file.order
    except PhotoSeriesFile.DoesNotExist:
        return ""


@register.simple_tag
def photoseries_download_url(series):
    """
    Generate ZIP download URL for PhotoSeries.

    Args:
        series: PhotoSeries instance

    Returns:
        Download URL for the series
    """
    if not series:
        return ""

    from django.urls import reverse
    return reverse('mediafiles:photoseries_download', kwargs={'pk': series.pk})


@register.filter
def photoseries_total_size(series):
    """
    Calculate total file size of all photos in PhotoSeries.

    Args:
        series: PhotoSeries instance

    Returns:
        Formatted total file size
    """
    if not series:
        return ""

    total_bytes = 0
    for photo in series.get_ordered_photos():
        if photo.file_size:
            total_bytes += photo.file_size

    return format_file_size(total_bytes) if total_bytes > 0 else ""


# VideoClip-specific template tags

@register.simple_tag
def video_player(videoclip, controls=True, autoplay=False, muted=False, css_class=""):
    """
    Display video player for VideoClip.

    Args:
        videoclip: VideoClip instance
        controls: Whether to show video controls
        autoplay: Whether to autoplay video
        muted: Whether to start muted
        css_class: Additional CSS classes

    Returns:
        HTML for video player
    """
    if not videoclip or not hasattr(videoclip, 'media_file'):
        return ""

    from django.urls import reverse

    video_url = reverse('mediafiles:videoclip_stream', kwargs={'pk': videoclip.pk})

    controls_attr = 'controls' if controls else ''
    autoplay_attr = 'autoplay' if autoplay else ''
    muted_attr = 'muted' if muted else ''

    all_classes = f"video-player {css_class}".strip()

    poster_attr = ""
    if hasattr(videoclip.media_file, 'get_thumbnail_url'):
        poster_url = videoclip.media_file.get_thumbnail_url()
        if poster_url:
            poster_attr = f'poster="{poster_url}"'

    return format_html(
        '''<video class="{}" {} {} {} {} preload="metadata" data-video-id="{}">
           <source src="{}" type="{}">
           Seu navegador não suporta o elemento de vídeo.
           </video>''',
        all_classes,
        controls_attr,
        autoplay_attr,
        muted_attr,
        poster_attr,
        videoclip.id,
        video_url,
        videoclip.media_file.mime_type or 'video/mp4'
    )


@register.simple_tag
def video_thumbnail(videoclip, size="medium", css_class=""):
    """
    Display video thumbnail with duration badge.

    Args:
        videoclip: VideoClip instance
        size: Thumbnail size ('small', 'medium', 'large')
        css_class: Additional CSS classes

    Returns:
        HTML for video thumbnail display
    """
    if not videoclip or not hasattr(videoclip, 'media_file'):
        return ""

    # Size mappings for videos
    size_classes = {
        'small': 'video-thumbnail-sm',
        'medium': 'video-thumbnail-md',
        'large': 'video-thumbnail-lg'
    }

    size_class = size_classes.get(size, 'video-thumbnail-md')
    all_classes = f"video-thumbnail {size_class} {css_class}".strip()

    # Get thumbnail URL
    thumbnail_url = ""
    if hasattr(videoclip.media_file, 'get_thumbnail_url'):
        thumbnail_url = videoclip.media_file.get_thumbnail_url()

    if not thumbnail_url:
        # Fallback to placeholder
        return format_html(
            '<div class="video-thumbnail-placeholder {}"><i class="bi bi-camera-video"></i></div>',
            all_classes
        )

    alt_text = f"Vídeo: {videoclip.description or videoclip.media_file.original_filename}"

    # Duration badge
    duration_badge = ""
    if videoclip.media_file.duration:
        duration_display = format_duration(videoclip.media_file.duration)
        duration_badge = format_html(
            '<div class="video-duration-overlay"><div class="video-duration-badge"><i class="bi bi-clock me-1"></i>{}</div></div>',
            duration_display
        )

    return format_html(
        '''<div class="video-thumbnail-wrapper position-relative">
           <img src="{}" alt="{}" class="{}" loading="lazy">
           {}
           <div class="video-play-overlay position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center opacity-0">
               <div class="bg-dark bg-opacity-75 rounded-circle p-3">
                   <i class="bi bi-play-fill text-white fs-2"></i>
               </div>
           </div>
           </div>''',
        thumbnail_url,
        alt_text,
        all_classes,
        duration_badge
    )


@register.simple_tag
def video_duration(videoclip):
    """
    Display formatted video duration.

    Args:
        videoclip: VideoClip instance

    Returns:
        Formatted duration string
    """
    if not videoclip or not hasattr(videoclip, 'media_file') or not videoclip.media_file.duration:
        return ""

    return format_duration(videoclip.media_file.duration)


@register.simple_tag
def video_modal_trigger(videoclip, trigger_text="Reproduzir vídeo", css_class=""):
    """
    Create modal trigger button for video viewing.

    Args:
        videoclip: VideoClip instance
        trigger_text: Text for the trigger button
        css_class: Additional CSS classes

    Returns:
        HTML for modal trigger button
    """
    if not videoclip or not hasattr(videoclip, 'media_file'):
        return ""

    from django.urls import reverse

    # Get video data for modal
    video_url = reverse('mediafiles:videoclip_stream', kwargs={'pk': videoclip.pk})

    duration_display = ""
    if videoclip.media_file.duration:
        duration_display = format_duration(videoclip.media_file.duration)

    file_size = format_file_size(videoclip.media_file.file_size) if videoclip.media_file.file_size else ""

    created_date = videoclip.event_datetime.strftime("%d/%m/%Y %H:%M") if videoclip.event_datetime else ""
    author = videoclip.created_by.get_full_name() if videoclip.created_by else ""

    button_classes = f"btn btn-outline-primary {css_class}".strip()

    return format_html(
        '''<button type="button" class="{}" data-bs-toggle="modal" data-bs-target="#videoModal"
           data-video-id="{}" data-video-url="{}" data-video-title="{}"
           data-video-filename="{}" data-video-size="{}" data-video-duration="{}"
           data-video-created="{}" data-video-author="{}">
           <i class="bi bi-play-circle me-1"></i>{}
        </button>''',
        button_classes,
        videoclip.id,
        video_url,
        videoclip.description or "Vídeo",
        videoclip.media_file.original_filename,
        file_size,
        duration_display,
        created_date,
        author,
        trigger_text
    )


@register.inclusion_tag('mediafiles/partials/video_metadata.html')
def video_metadata(videoclip, show_technical=True):
    """
    Display video metadata in a formatted layout.

    Args:
        videoclip: VideoClip instance
        show_technical: Whether to show technical metadata

    Returns:
        Context for video metadata template
    """
    if not videoclip or not hasattr(videoclip, 'media_file'):
        return {}

    metadata = {
        'videoclip': videoclip,
        'media_file': videoclip.media_file,
        'show_technical': show_technical,
        'file_size': format_file_size(videoclip.media_file.file_size) if videoclip.media_file.file_size else None,
        'duration': format_duration(videoclip.media_file.duration) if videoclip.media_file.duration else None,
        'created_date': videoclip.event_datetime.strftime("%d/%m/%Y %H:%M") if videoclip.event_datetime else None,
        'author': videoclip.created_by.get_full_name() if videoclip.created_by else None,
        'codec': videoclip.media_file.video_codec if hasattr(videoclip.media_file, 'video_codec') else None,
        'fps': videoclip.media_file.fps if hasattr(videoclip.media_file, 'fps') else None,
        'bitrate': videoclip.media_file.video_bitrate if hasattr(videoclip.media_file, 'video_bitrate') else None,
    }

    return metadata


@register.filter
def video_file_size(videoclip):
    """
    Format video file size display.

    Args:
        videoclip: VideoClip instance

    Returns:
        Formatted file size string
    """
    if not videoclip or not hasattr(videoclip, 'media_file') or not videoclip.media_file.file_size:
        return ""

    return format_file_size(videoclip.media_file.file_size)


@register.simple_tag
def video_download_url(videoclip):
    """
    Generate download URL for VideoClip.

    Args:
        videoclip: VideoClip instance

    Returns:
        Download URL for the video
    """
    if not videoclip:
        return ""

    from django.urls import reverse
    return reverse('mediafiles:videoclip_download', kwargs={'pk': videoclip.pk})


@register.simple_tag
def video_stream_url(videoclip):
    """
    Generate streaming URL for VideoClip.

    Args:
        videoclip: VideoClip instance

    Returns:
        Streaming URL for the video
    """
    if not videoclip:
        return ""

    from django.urls import reverse
    return reverse('mediafiles:videoclip_stream', kwargs={'pk': videoclip.pk})


@register.filter
def is_video_duration_valid(duration):
    """
    Check if video duration is within allowed limits.

    Args:
        duration: Duration in seconds

    Returns:
        True if duration is valid (≤ 2 minutes)
    """
    if duration is None:
        return True  # Allow None values

    try:
        max_duration = getattr(settings, 'MEDIA_VIDEO_MAX_DURATION', 120)  # 2 minutes
        return float(duration) <= max_duration
    except (ValueError, TypeError):
        return False


@register.simple_tag
def video_controls_overlay(videoclip, show_download=True):
    """
    Generate video controls overlay for video player.

    Args:
        videoclip: VideoClip instance
        show_download: Whether to show download button

    Returns:
        HTML for video controls overlay
    """
    if not videoclip:
        return ""

    from django.urls import reverse

    download_url = reverse('mediafiles:videoclip_download', kwargs={'pk': videoclip.pk})

    download_button = ""
    if show_download:
        download_button = format_html(
            '<a href="{}" class="btn btn-primary btn-sm" title="Baixar vídeo" download><i class="bi bi-download"></i></a>',
            download_url
        )

    return format_html(
        '''<div class="video-controls position-absolute top-0 end-0 p-3">
           <div class="btn-group-vertical">
               <button type="button" class="btn btn-dark btn-sm mb-1" id="videoPlayPause" title="Reproduzir/Pausar">
                   <i class="bi bi-play-fill"></i>
               </button>
               <button type="button" class="btn btn-dark btn-sm mb-1" id="videoBackward" title="Voltar 10s">
                   <i class="bi bi-skip-backward"></i>
               </button>
               <button type="button" class="btn btn-dark btn-sm mb-1" id="videoForward" title="Avançar 10s">
                   <i class="bi bi-skip-forward"></i>
               </button>
               <button type="button" class="btn btn-dark btn-sm mb-1" id="videoReplay" title="Reiniciar">
                   <i class="bi bi-arrow-clockwise"></i>
               </button>
               {}
           </div>
           </div>''',
        download_button
    )
