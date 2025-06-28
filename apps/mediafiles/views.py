"""
MediaFiles Views

This module implements views for media file management in EquipeMed.
It provides secure file serving, photo CRUD operations, and access control.

Views:
- SecureFileServeView: Secure file serving with permission checks
- SecureThumbnailServeView: Secure thumbnail serving
- PhotoCreateView: Create new photo events
- PhotoDetailView: Display photo details
- PhotoUpdateView: Update photo metadata
- PhotoDeleteView: Delete photos with confirmation
"""

import mimetypes
import time
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import http_date
from django.views import View
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, DetailView, UpdateView, DeleteView
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import re

from .models import Photo, MediaFile, PhotoSeries, VideoClip
from .forms import PhotoCreateForm, PhotoUpdateForm, PhotoSeriesCreateForm, PhotoSeriesUpdateForm, PhotoSeriesPhotoForm, VideoClipCreateForm, VideoClipUpdateForm
from apps.patients.models import Patient
from apps.core.permissions import (
    hospital_context_required,
    can_access_patient,
    can_edit_event,
    can_delete_event,
)


class SecureFileServeView(View):
    """
    Secure file serving view with comprehensive access control.

    Security features:
    - Authentication required
    - Permission-based access
    - Audit logging
    - Rate limiting (handled by middleware)
    - Secure headers
    """

    @method_decorator(login_required)
    @method_decorator(cache_control(private=True, max_age=3600))
    def get(self, request: HttpRequest, file_id: str) -> HttpResponse:
        """
        Serve media file with security checks.

        Args:
            request: Django HttpRequest object
            file_id: UUID of the media file

        Returns:
            FileResponse with the requested file

        Raises:
            Http404: If file not found or access denied
            PermissionDenied: If user lacks permission
        """
        try:
            # Get media file with permission checks
            media_file = self._get_media_file_with_permissions(request.user, file_id)

            # Log access attempt
            self._log_file_access(request.user, media_file, 'view')

            # Serve file securely
            return self._serve_file_securely(media_file)

        except Exception as e:
            # Log suspicious access attempt
            self._log_security_event(request.user, 'file_access_error', str(e))
            raise Http404("File not found")

    def _get_media_file_with_permissions(self, user, file_id):
        """
        Get media file with comprehensive permission checking.

        Args:
            user: Django User object
            file_id: UUID of the media file

        Returns:
            MediaFile object if access is allowed

        Raises:
            PermissionDenied: If access is not allowed
        """
        # Import here to avoid circular imports
        from .models import MediaFile

        try:
            media_file = MediaFile.objects.get(id=file_id)
        except MediaFile.DoesNotExist:
            raise PermissionDenied("File not found or access denied")

        # Get associated event
        event = self._get_event_from_media_file(media_file)

        # Check patient access permissions using custom permission system
        from apps.core.permissions import can_access_patient
        if not can_access_patient(user, event.patient):
            raise PermissionDenied("No permission to view patient files")

        return media_file

    def _get_event_from_media_file(self, media_file):
        """
        Get the associated event from a media file.

        Args:
            media_file: MediaFile object

        Returns:
            Event object
        """
        # Import here to avoid circular imports
        from .models import Photo

        # Try to find associated Photo, PhotoSeries, or VideoClip using correct relationships
        try:
            # For Photo: Use reverse OneToOneField relationship
            try:
                photo = Photo.objects.get(media_file=media_file)
                return photo
            except Photo.DoesNotExist:
                pass

            # For VideoClip: Legacy support for old MediaFile-based videos
            # Note: New FilePond-based videos don't use MediaFile relationship
            try:
                # This will only work for old VideoClip instances created before FilePond migration
                videoclip = VideoClip.objects.get(media_file=media_file)
                return videoclip
            except (VideoClip.DoesNotExist, AttributeError):
                # AttributeError can occur if VideoClip model no longer has media_file field
                pass

            # For PhotoSeries: Use through model relationship
            if hasattr(media_file, 'photoseriesfile_set'):
                series_file = media_file.photoseriesfile_set.first()
                if series_file:
                    return series_file.photo_series

        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger('mediafiles.security')
            logger.error(f"Error finding event for media_file {media_file.id}: {str(e)}")

        # Fallback - this should not happen in production
        raise PermissionDenied("Could not determine associated event")

    def _serve_file_securely(self, media_file) -> FileResponse:
        """
        Serve file with comprehensive security headers.

        Includes fallback logic to handle both old (random UUID) and new (MediaFile.id) naming strategies.

        Args:
            media_file: MediaFile object

        Returns:
            FileResponse with security headers

        Raises:
            Http404: If file not found on disk
        """
        file_path = Path(settings.MEDIA_ROOT) / media_file.file.name

        # Check if file exists with current naming strategy
        if not file_path.exists() or not file_path.is_file():
            # FALLBACK: Try to find file with old naming strategy (random UUID)
            file_path = self._find_file_with_fallback(media_file, file_path)

            if not file_path or not file_path.exists():
                raise Http404("File not found on disk")

        # Get MIME type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = 'application/octet-stream'

        # Create secure response
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type,
            as_attachment=False  # Display inline for images/videos
        )

        # Set security headers
        response['Content-Disposition'] = f'inline; filename="{media_file.original_filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Cache-Control'] = 'private, max-age=3600, must-revalidate'
        response['Expires'] = http_date(time.time() + 3600)

        # Set content length
        response['Content-Length'] = file_path.stat().st_size

        # Add video-specific headers for streaming
        if media_file.is_video():
            response['Accept-Ranges'] = 'bytes'
            response['Content-Type'] = content_type

        return response

    def _find_file_with_fallback(self, media_file, expected_path):
        """
        Find file using fallback strategy for old naming convention.

        Args:
            media_file: MediaFile object
            expected_path: Path where file should be with new naming

        Returns:
            Path object if file found, None otherwise
        """
        # Get the directory where the file should be
        file_dir = expected_path.parent
        if not file_dir.exists():
            return None

        # Get the expected file extension
        file_extension = expected_path.suffix

        # Look for any file with the same extension in the directory
        # This handles the case where file was saved with random UUID
        matching_files = list(file_dir.glob(f'*{file_extension}'))

        if len(matching_files) == 1:
            # Found exactly one file with matching extension - likely our file
            return matching_files[0]
        elif len(matching_files) > 1:
            # Multiple files found - log this for investigation
            import logging
            logger = logging.getLogger('mediafiles.serving')
            logger.warning(f"Multiple files found for MediaFile {media_file.id} in {file_dir}: {[f.name for f in matching_files]}")

        return None

    def _log_file_access(self, user, media_file, action: str, extra_data: dict = None) -> None:
        """Log file access for audit trail."""
        import logging
        security_logger = logging.getLogger('security.mediafiles')

        log_message = (
            f"File access: user={user.username} "
            f"file={media_file.id} "
            f"filename={media_file.original_filename} "
            f"action={action} "
            f"timestamp={time.time()}"
        )
        
        if extra_data:
            extra_info = " ".join([f"{k}={v}" for k, v in extra_data.items()])
            log_message += f" {extra_info}"

        security_logger.info(log_message)

    def _log_security_event(self, user, event_type: str, details: str) -> None:
        """Log security-related events."""
        import logging
        security_logger = logging.getLogger('security.mediafiles')

        security_logger.warning(
            f"Security event: user={user.username if user else 'anonymous'} "
            f"type={event_type} "
            f"details={details} "
            f"timestamp={time.time()}"
        )


class SecureThumbnailServeView(SecureFileServeView):
    """
    Secure thumbnail serving view.

    Extends SecureFileServeView with thumbnail-specific logic.
    """

    @method_decorator(login_required)
    @method_decorator(cache_control(private=True, max_age=7200))  # Longer cache for thumbnails
    def get(self, request: HttpRequest, file_id: str) -> HttpResponse:
        """
        Serve thumbnail with security checks.

        Args:
            request: Django HttpRequest object
            file_id: UUID of the media file

        Returns:
            FileResponse with the requested thumbnail
        """
        try:
            # Get media file with permission checks
            media_file = self._get_media_file_with_permissions(request.user, file_id)

            # Log thumbnail access
            self._log_file_access(request.user, media_file, 'thumbnail')

            # Serve thumbnail securely
            return self._serve_thumbnail_securely(media_file)

        except Exception as e:
            # Log suspicious access attempt
            self._log_security_event(request.user, 'thumbnail_access_error', str(e))
            raise Http404("Thumbnail not found")

    def _serve_thumbnail_securely(self, media_file) -> FileResponse:
        """
        Serve thumbnail with security headers.

        Args:
            media_file: MediaFile object

        Returns:
            FileResponse with thumbnail

        Raises:
            Http404: If thumbnail not found
        """
        # Get thumbnail path - use the thumbnail ImageField
        if not media_file.thumbnail:
            raise Http404("Thumbnail not available")

        try:
            thumbnail_path = Path(media_file.thumbnail.path)
        except ValueError:
            # Handle case where thumbnail field exists but file path is invalid
            raise Http404("Thumbnail path not available")

        # Validate thumbnail exists
        if not thumbnail_path.exists() or not thumbnail_path.is_file():
            raise Http404("Thumbnail not found on disk")

        # Create secure response
        response = FileResponse(
            open(thumbnail_path, 'rb'),
            content_type='image/jpeg',  # Thumbnails are always JPEG
            as_attachment=False
        )

        # Set security headers (optimized for thumbnails)
        response['Content-Disposition'] = f'inline; filename="thumb_{media_file.original_filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'  # Allow framing for thumbnails
        response['Cache-Control'] = 'private, max-age=7200, must-revalidate'
        response['Expires'] = http_date(time.time() + 7200)

        # Set content length
        response['Content-Length'] = thumbnail_path.stat().st_size

        return response


@require_http_methods(["GET"])
@login_required
def serve_media_file(request: HttpRequest, file_id: str) -> HttpResponse:
    """
    Function-based view for serving media files.

    Args:
        request: Django HttpRequest object
        file_id: UUID of the media file

    Returns:
        FileResponse with the requested file
    """
    view = SecureFileServeView()
    return view.get(request, file_id)


@require_http_methods(["GET"])
@login_required
def serve_thumbnail(request: HttpRequest, file_id: str) -> HttpResponse:
    """
    Function-based view for serving thumbnails.

    Args:
        request: Django HttpRequest object
        file_id: UUID of the media file

    Returns:
        FileResponse with the requested thumbnail
    """
    view = SecureThumbnailServeView()
    return view.get(request, file_id)


class SecureVideoStreamView(SecureFileServeView):
    """
    Secure video streaming view with HTTP range request support.

    Extends SecureFileServeView with video-specific optimizations:
    - HTTP range request support for video seeking
    - Video-specific security headers
    - Bandwidth optimization
    - Enhanced access logging for video streams
    """

    def get(self, request: HttpRequest, file_id: str) -> HttpResponse:
        """
        Serve video file with range request support.

        Args:
            request: Django HttpRequest object
            file_id: UUID of the media file

        Returns:
            StreamingHttpResponse or FileResponse with video content

        Raises:
            Http404: If file not found or access denied
            PermissionDenied: If user lacks permission
        """
        try:
            # Get media file with permission checks
            media_file = self._get_media_file_with_permissions(request.user, file_id)

            # Validate it's a video file
            if not media_file.is_video():
                raise Http404("Requested file is not a video")

            # Enhanced logging for video access
            self._log_video_access(request.user, media_file, request)

            # Check for range request
            range_header = request.META.get('HTTP_RANGE')
            if range_header:
                return self._serve_video_range(media_file, range_header)
            else:
                return self._serve_video_complete(media_file)

        except Exception as e:
            # Log security incidents
            self._log_security_incident(request.user, file_id, str(e))
            raise

    def _serve_video_range(self, media_file, range_header: str) -> HttpResponse:
        """
        Serve video with HTTP range request support.

        Args:
            media_file: MediaFile object
            range_header: HTTP Range header value

        Returns:
            HttpResponse with partial content
        """
        file_path = Path(settings.MEDIA_ROOT) / media_file.file.name

        if not file_path.exists():
            raise Http404("Video file not found on disk")

        file_size = file_path.stat().st_size

        # Parse range header
        try:
            range_start, range_end = self._parse_range_header(range_header, file_size)
        except ValueError as e:
            # Log the actual range header for debugging
            import logging
            logger = logging.getLogger('mediafiles.debug')
            logger.warning(f"Failed to parse range header: '{range_header}', error: {e}")
            
            # Invalid range request
            response = HttpResponse(status=416)  # Range Not Satisfiable
            response['Content-Range'] = f'bytes */{file_size}'
            return response

        # Validate range for security
        if not self._validate_range_security(range_start, range_end, file_size):
            # Log the actual range values for debugging
            import logging
            logger = logging.getLogger('mediafiles.debug')
            logger.warning(f"Range validation failed: start={range_start}, end={range_end}, file_size={file_size}")
            raise PermissionDenied("Invalid range request")

        # Create partial content response
        content_length = range_end - range_start + 1

        response = HttpResponse(
            self._get_file_chunk(file_path, range_start, content_length),
            status=206,  # Partial Content
            content_type=self._get_video_content_type(media_file)
        )

        # Set range headers
        response['Content-Range'] = f'bytes {range_start}-{range_end}/{file_size}'
        response['Content-Length'] = str(content_length)
        response['Accept-Ranges'] = 'bytes'

        # Set video streaming security headers
        self._set_video_security_headers(response, media_file)

        return response

    def _serve_video_complete(self, media_file) -> FileResponse:
        """
        Serve complete video file.

        Args:
            media_file: MediaFile object

        Returns:
            FileResponse with complete video
        """
        file_path = Path(settings.MEDIA_ROOT) / media_file.file.name

        if not file_path.exists():
            raise Http404("Video file not found on disk")

        # Create response with video-specific optimizations
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=self._get_video_content_type(media_file),
            as_attachment=False
        )

        # Set video streaming headers
        response['Accept-Ranges'] = 'bytes'
        response['Content-Length'] = file_path.stat().st_size

        # Set video streaming security headers
        self._set_video_security_headers(response, media_file)

        return response

    def _parse_range_header(self, range_header: str, file_size: int) -> tuple:
        """
        Parse HTTP Range header.

        Args:
            range_header: Range header value (e.g., "bytes=0-1023")
            file_size: Total file size

        Returns:
            Tuple of (start, end) byte positions

        Raises:
            ValueError: If range header is invalid
        """
        if not range_header.startswith('bytes='):
            raise ValueError("Invalid range header format")

        range_spec = range_header[6:]  # Remove "bytes="

        if ',' in range_spec:
            # Multiple ranges not supported for security
            raise ValueError("Multiple ranges not supported")

        if '-' not in range_spec:
            raise ValueError("Invalid range specification")

        start_str, end_str = range_spec.split('-', 1)

        # Parse start position
        if start_str:
            range_start = int(start_str)
            if range_start < 0 or range_start >= file_size:
                raise ValueError("Invalid start position")
        else:
            # Suffix range (e.g., "-500" for last 500 bytes)
            if not end_str:
                raise ValueError("Invalid suffix range")
            suffix_length = int(end_str)
            range_start = max(0, file_size - suffix_length)

        # Parse end position
        if end_str and start_str:
            range_end = int(end_str)
            if range_end >= file_size:
                range_end = file_size - 1
        else:
            range_end = file_size - 1

        if range_start > range_end:
            raise ValueError("Invalid range: start > end")

        return range_start, range_end

    def _validate_range_security(self, start: int, end: int, file_size: int) -> bool:
        """
        Validate range request for security issues.

        Args:
            start: Start byte position
            end: End byte position
            file_size: Total file size

        Returns:
            True if range is valid and secure
        """
        # Check for reasonable range size (prevent DoS)
        # For video streaming, be more permissive with range requests
        range_size = end - start + 1
        
        # Allow full file requests or large chunks for video streaming
        if range_size == file_size or range_size >= file_size * 0.8:
            # Browser requesting entire file or most of it - always allow for video streaming
            return True
            
        # For video files, allow much larger ranges (up to 100MB)
        max_range_size = getattr(settings, 'MEDIA_VIDEO_MAX_RANGE_SIZE', 100 * 1024 * 1024)  # 100MB

        if range_size > max_range_size:
            import logging
            logger = logging.getLogger('mediafiles.debug')
            logger.warning(f"Range size too large: {range_size} > {max_range_size}")
            return False

        # Check for valid bounds
        if start < 0 or end >= file_size or start > end:
            import logging
            logger = logging.getLogger('mediafiles.debug')
            logger.warning(f"Invalid bounds: start={start}, end={end}, file_size={file_size}")
            return False

        return True

    def _get_file_chunk(self, file_path: Path, start: int, length: int):
        """
        Generator to read file chunk.

        Args:
            file_path: Path to file
            start: Start byte position
            length: Number of bytes to read

        Yields:
            File chunks
        """
        chunk_size = 8192  # 8KB chunks

        with open(file_path, 'rb') as f:
            f.seek(start)
            remaining = length

            while remaining > 0:
                chunk_length = min(chunk_size, remaining)
                chunk = f.read(chunk_length)

                if not chunk:
                    break

                remaining -= len(chunk)
                yield chunk

    def _get_video_content_type(self, media_file) -> str:
        """Get appropriate content type for video file."""
        content_type, _ = mimetypes.guess_type(media_file.original_filename)

        if not content_type or not content_type.startswith('video/'):
            # Fallback based on file extension
            ext = Path(media_file.original_filename).suffix.lower()
            content_type_map = {
                '.mp4': 'video/mp4',
                '.webm': 'video/webm',
                '.mov': 'video/quicktime',
            }
            content_type = content_type_map.get(ext, 'video/mp4')

        return content_type

    def _set_video_security_headers(self, response: HttpResponse, media_file) -> None:
        """Set video-specific security headers."""
        # Basic security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'  # Allow embedding in same origin
        response['X-XSS-Protection'] = '1; mode=block'

        # Video streaming headers
        response['Cache-Control'] = 'private, max-age=3600, must-revalidate'
        response['Content-Disposition'] = f'inline; filename="{media_file.original_filename}"'

        # CORS headers for video streaming (if needed)
        # response['Access-Control-Allow-Origin'] = 'same-origin'

    def _log_video_access(self, user, media_file, request) -> None:
        """Enhanced logging for video access."""
        # Get additional context for video streaming
        range_header = request.META.get('HTTP_RANGE', 'full')
        user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')

        # Log with video-specific information
        self._log_file_access(user, media_file, 'video_stream', {
            'range_request': range_header,
            'user_agent': user_agent,
            'video_duration': media_file.get_duration_display() if hasattr(media_file, 'get_duration_display') else 'unknown',
            'video_codec': getattr(media_file, 'video_codec', 'unknown'),
        })

    def _log_security_incident(self, user, file_id: str, error: str) -> None:
        """Log security incidents for video streaming."""
        import logging

        logger = logging.getLogger('mediafiles.security')
        logger.warning(
            f"Video streaming security incident - User: {user.id if user.is_authenticated else 'anonymous'}, "
            f"File: {file_id}, Error: {error}"
        )


@require_http_methods(["GET"])
@login_required
def serve_video_stream(request: HttpRequest, file_id: str) -> HttpResponse:
    """
    Function-based view for video streaming with range request support.

    Args:
        request: Django HttpRequest object
        file_id: UUID of the media file

    Returns:
        StreamingHttpResponse or FileResponse with video content
    """
    view = SecureVideoStreamView()
    return view.get(request, file_id)


# Photo CRUD Views

@method_decorator(hospital_context_required, name="dispatch")
class PhotoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Create view for Photo instances for a specific patient.

    Handles secure file upload and photo event creation.
    """

    model = Photo
    form_class = PhotoCreateForm
    template_name = "mediafiles/photo_form.html"
    permission_required = "events.add_event"

    def dispatch(self, request, *args, **kwargs):
        """Get patient and check permissions before processing request."""
        self.patient = get_object_or_404(Patient, pk=kwargs["patient_id"])

        # Check if user can access this patient
        if not can_access_patient(request.user, self.patient):
            raise PermissionDenied(
                "You don't have permission to create photos for this patient"
            )

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass current user and patient to form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["patient"] = self.patient
        return kwargs

    def get_context_data(self, **kwargs):
        """Add patient to context."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.patient
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful creation."""
        return reverse_lazy("apps.patients:patient_events_timeline", kwargs={"patient_id": self.object.patient.pk})

    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Foto adicionada com sucesso para {self.patient.name}."
        )
        return response


@method_decorator(hospital_context_required, name="dispatch")
class PhotoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detail view for Photo instances.

    Displays full-size photo with metadata and action buttons.
    """

    model = Photo
    template_name = "mediafiles/photo_detail.html"
    context_object_name = "photo"
    permission_required = "events.view_event"

    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's photos"
            )

        return obj

    def get_context_data(self, **kwargs):
        """Add permission context."""
        context = super().get_context_data(**kwargs)
        photo = self.get_object()

        # Add permission flags
        context["can_edit"] = can_edit_event(self.request.user, photo)
        context["can_delete"] = can_delete_event(self.request.user, photo)

        return context

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return Photo.objects.select_related(
            "patient", "created_by", "updated_by", "media_file"
        )


@method_decorator(hospital_context_required, name="dispatch")
class PhotoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Update view for Photo instances.

    Allows editing photo metadata within the 24-hour window.
    """

    model = Photo
    form_class = PhotoUpdateForm
    template_name = "mediafiles/photo_form.html"
    context_object_name = "photo"
    permission_required = "events.change_event"

    def get_object(self, queryset=None):
        """Get object and check patient access and edit permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's photos"
            )

        # Check if user can edit this event
        if not can_edit_event(self.request.user, obj):
            raise PermissionDenied(
                "You don't have permission to edit this photo"
            )

        return obj

    def get_form_kwargs(self):
        """Pass current user to form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Add context for update view."""
        context = super().get_context_data(**kwargs)
        context["is_update"] = True
        context["patient"] = self.object.patient
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful update."""
        return reverse_lazy("apps.patients:patient_events_timeline", kwargs={"patient_id": self.object.patient.pk})

    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Foto atualizada com sucesso."
        )
        return response

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return Photo.objects.select_related(
            "patient", "created_by", "updated_by", "media_file"
        )


@method_decorator(hospital_context_required, name="dispatch")
class PhotoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Delete view for Photo instances with permission checking.

    Requires confirmation and handles file cleanup.
    """

    model = Photo
    template_name = "mediafiles/photo_confirm_delete.html"
    context_object_name = "photo"
    permission_required = "events.delete_event"

    def get_object(self, queryset=None):
        """Get object and check patient access and delete permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's photos"
            )

        # Check if user can delete this event
        if not can_delete_event(self.request.user, obj):
            raise PermissionDenied(
                "You don't have permission to delete this photo"
            )

        return obj

    def get_success_url(self):
        """Redirect to patient timeline after successful deletion."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.object.patient.pk}
        )

    def delete(self, request, *args, **kwargs):
        """Handle deletion with success message."""
        photo = self.get_object()
        patient_name = photo.patient.name

        # Perform deletion
        response = super().delete(request, *args, **kwargs)

        messages.success(
            request,
            f"Foto removida com sucesso do prontuário de {patient_name}."
        )

        return response

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return Photo.objects.select_related(
            "patient", "created_by", "updated_by", "media_file"
        )


@method_decorator(hospital_context_required, name="dispatch")
class PhotoDownloadView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Download view for Photo instances.

    Serves photo file as download with proper headers.
    """

    model = Photo
    permission_required = "events.view_event"

    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's photos"
            )

        return obj

    def get(self, request, *args, **kwargs):
        """Serve photo file as download."""
        photo = self.get_object()
        media_file = photo.media_file

        # Log download access
        self._log_file_access(request.user, media_file, 'download')

        # Serve file as download
        file_path = Path(settings.MEDIA_ROOT) / media_file.file.name

        if not file_path.exists():
            raise Http404("File not found on disk")

        # Create download response
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=media_file.mime_type,
            as_attachment=True
        )

        # Set download filename
        response['Content-Disposition'] = f'attachment; filename="{media_file.original_filename}"'

        return response

    def _log_file_access(self, user, media_file, action: str, extra_data: dict = None) -> None:
        """Log file access for audit trail."""
        import logging
        security_logger = logging.getLogger('security.mediafiles')

        log_message = (
            f"File access: user={user.username} "
            f"file={media_file.id} "
            f"filename={media_file.original_filename} "
            f"action={action} "
            f"timestamp={time.time()}"
        )
        
        if extra_data:
            extra_info = " ".join([f"{k}={v}" for k, v in extra_data.items()])
            log_message += f" {extra_info}"

        security_logger.info(log_message)

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return Photo.objects.select_related(
            "patient", "created_by", "updated_by", "media_file"
        )


# PhotoSeries CRUD Views

@method_decorator(hospital_context_required, name="dispatch")
class PhotoSeriesCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Create view for PhotoSeries instances for a specific patient.

    Handles multiple file upload with batch processing and series creation.
    Features advanced multi-upload interface with drag-and-drop, progress tracking,
    and file management capabilities.
    """

    model = PhotoSeries
    form_class = PhotoSeriesCreateForm
    template_name = "mediafiles/photoseries_create.html"
    permission_required = "events.add_event"

    def dispatch(self, request, *args, **kwargs):
        """Get patient and check permissions before processing request."""
        self.patient = get_object_or_404(Patient, pk=kwargs["patient_id"])

        # Check if user can access this patient
        if not can_access_patient(request.user, self.patient):
            raise PermissionDenied(
                "You don't have permission to create photo series for this patient"
            )

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass current user and patient to form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["patient"] = self.patient
        return kwargs

    def get_context_data(self, **kwargs):
        """Add patient to context."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.patient
        context["is_series"] = True
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful creation."""
        return reverse_lazy("apps.patients:patient_events_timeline", kwargs={"patient_id": self.object.patient.pk})

    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        photo_count = self.object.get_photo_count()
        messages.success(
            self.request,
            f"Série de fotos com {photo_count} imagem(ns) adicionada com sucesso para {self.patient.name}."
        )
        return response

    def form_invalid(self, form):
        """Handle form validation errors."""
        messages.error(
            self.request,
            "Erro ao criar série de fotos. Verifique os dados e tente novamente."
        )
        return super().form_invalid(form)


@method_decorator(hospital_context_required, name="dispatch")
class PhotoSeriesDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detail view for PhotoSeries instances.

    Displays carousel with navigation between photos per extra requirements.
    """

    model = PhotoSeries
    template_name = "mediafiles/photoseries_detail.html"
    context_object_name = "photoseries"
    permission_required = "events.view_event"

    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's photo series"
            )

        return obj

    def get_context_data(self, **kwargs):
        """Add permission context and ordered photos."""
        context = super().get_context_data(**kwargs)
        photoseries = self.get_object()

        # Add permission flags
        context["can_edit"] = can_edit_event(self.request.user, photoseries)
        context["can_delete"] = can_delete_event(self.request.user, photoseries)

        # Add ordered photos for carousel
        context["ordered_photos"] = photoseries.get_ordered_photos()
        context["photo_count"] = photoseries.get_photo_count()

        return context

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return PhotoSeries.objects.select_related(
            "patient", "created_by", "updated_by"
        ).prefetch_related(
            "photoseriesfile_set__media_file"
        )


@method_decorator(hospital_context_required, name="dispatch")
class PhotoSeriesUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Update view for PhotoSeries instances.

    Limited editing per extra requirements: only description, datetime, and caption.
    Features streamlined interface focused on metadata editing with current photos display.
    """

    model = PhotoSeries
    form_class = PhotoSeriesUpdateForm
    template_name = "mediafiles/photoseries_update.html"
    context_object_name = "photoseries"
    permission_required = "events.change_event"

    def get_object(self, queryset=None):
        """Get object and check patient access and edit permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's photo series"
            )

        # Check if user can edit this event
        if not can_edit_event(self.request.user, obj):
            raise PermissionDenied(
                "You don't have permission to edit this photo series"
            )

        return obj

    def get_form_kwargs(self):
        """Pass current user to form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Add context for update view."""
        context = super().get_context_data(**kwargs)
        context["is_update"] = True
        context["is_series"] = True
        context["patient"] = self.object.patient
        context["ordered_photos"] = self.object.get_ordered_photos()
        context["photo_count"] = self.object.get_photo_count()
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful update."""
        return reverse_lazy("apps.patients:patient_events_timeline", kwargs={"patient_id": self.object.patient.pk})

    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Série de fotos atualizada com sucesso."
        )
        return response

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return PhotoSeries.objects.select_related(
            "patient", "created_by", "updated_by"
        ).prefetch_related(
            "photoseriesfile_set__media_file"
        )


@method_decorator(hospital_context_required, name="dispatch")
class PhotoSeriesDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Delete view for PhotoSeries instances with permission checking.

    Requires confirmation and handles batch file cleanup.
    """

    model = PhotoSeries
    template_name = "mediafiles/photoseries_confirm_delete.html"
    context_object_name = "photoseries"
    permission_required = "events.delete_event"

    def get_object(self, queryset=None):
        """Get object and check patient access and delete permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's photo series"
            )

        # Check if user can delete this event
        if not can_delete_event(self.request.user, obj):
            raise PermissionDenied(
                "You don't have permission to delete this photo series"
            )

        return obj

    def get_context_data(self, **kwargs):
        """Add photos for confirmation display."""
        context = super().get_context_data(**kwargs)
        context["ordered_photos"] = self.object.get_ordered_photos()
        context["photo_count"] = self.object.get_photo_count()
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful deletion."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.object.patient.pk}
        )

    def delete(self, request, *args, **kwargs):
        """Handle deletion with success message."""
        photoseries = self.get_object()
        patient_name = photoseries.patient.name
        photo_count = photoseries.get_photo_count()

        # Perform deletion
        response = super().delete(request, *args, **kwargs)

        messages.success(
            request,
            f"Série de fotos com {photo_count} imagem(ns) removida com sucesso do prontuário de {patient_name}."
        )

        return response

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return PhotoSeries.objects.select_related(
            "patient", "created_by", "updated_by"
        ).prefetch_related(
            "photoseriesfile_set__media_file"
        )


# AJAX Views for PhotoSeries Dynamic Management

@login_required
@require_POST
@hospital_context_required
def photoseries_add_photo(request, pk):
    """
    AJAX view for adding photos to existing series.
    
    Returns JSON response with new photo data.
    """
    try:
        # Get photo series and check permissions
        photoseries = get_object_or_404(PhotoSeries, pk=pk)
        
        # Check if user can access this patient
        if not can_access_patient(request.user, photoseries.patient):
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        # Check if user can edit this event
        if not can_edit_event(request.user, photoseries):
            return JsonResponse({
                'success': False,
                'error': 'You cannot edit this photo series anymore'
            }, status=403)
        
        # Process form
        form = PhotoSeriesPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            # Create MediaFile from uploaded image
            image = form.cleaned_data['image']
            description = form.cleaned_data.get('description', '')
            order = form.cleaned_data.get('order')
            
            media_file = MediaFile.objects.create_from_upload(image)
            
            # Add to series
            photoseries.add_photo(media_file, order=order, description=description)
            
            return JsonResponse({
                'success': True,
                'photo_id': str(media_file.id),
                'photo_url': media_file.get_secure_url(),
                'thumbnail_url': media_file.get_thumbnail_url(),
                'filename': media_file.original_filename,
                'order': photoseries.photoseriesfile_set.filter(media_file=media_file).first().order,
                'description': description,
                'photo_count': photoseries.get_photo_count()
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
@hospital_context_required
def photoseries_remove_photo(request, pk, photo_id):
    """
    AJAX view for removing photos from series.
    
    Returns JSON response with success/error status.
    """
    try:
        # Get photo series and check permissions
        photoseries = get_object_or_404(PhotoSeries, pk=pk)
        
        # Check if user can access this patient
        if not can_access_patient(request.user, photoseries.patient):
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        # Check if user can edit this event
        if not can_edit_event(request.user, photoseries):
            return JsonResponse({
                'success': False,
                'error': 'You cannot edit this photo series anymore'
            }, status=403)
        
        # Get media file
        media_file = get_object_or_404(MediaFile, pk=photo_id)
        
        # Remove from series
        photoseries.remove_photo(media_file)
        
        # Check if series still has photos
        if photoseries.get_photo_count() == 0:
            return JsonResponse({
                'success': False,
                'error': 'Cannot remove last photo from series'
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'photo_count': photoseries.get_photo_count(),
            'message': 'Photo removed successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
@hospital_context_required
def photoseries_reorder(request, pk):
    """
    AJAX view for reordering photos in series.
    
    Accepts new order array and returns updated order.
    """
    try:
        # Get photo series and check permissions
        photoseries = get_object_or_404(PhotoSeries, pk=pk)
        
        # Check if user can access this patient
        if not can_access_patient(request.user, photoseries.patient):
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
        
        # Check if user can edit this event
        if not can_edit_event(request.user, photoseries):
            return JsonResponse({
                'success': False,
                'error': 'You cannot edit this photo series anymore'
            }, status=403)
        
        # Parse JSON data
        data = json.loads(request.body)
        photo_order_list = data.get('photo_order', [])
        
        if not photo_order_list:
            return JsonResponse({
                'success': False,
                'error': 'Photo order list is required'
            }, status=400)
        
        # Reorder photos
        photoseries.reorder_photos(photo_order_list)
        
        # Return updated order
        ordered_photos = []
        for photo_file in photoseries.photoseriesfile_set.all().order_by('order'):
            ordered_photos.append({
                'photo_id': str(photo_file.media_file.id),
                'order': photo_file.order,
                'description': photo_file.description
            })
        
        return JsonResponse({
            'success': True,
            'ordered_photos': ordered_photos,
            'message': 'Photos reordered successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@hospital_context_required
def photoseries_download(request, pk):
    """
    Download view for PhotoSeries instances.
    
    Serves all photos in series as ZIP file.
    """
    try:
        # Get photo series and check permissions
        photoseries = get_object_or_404(PhotoSeries, pk=pk)
        
        # Check if user can access this patient
        if not can_access_patient(request.user, photoseries.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's photo series"
            )
        
        import zipfile
        import tempfile
        from django.http import FileResponse
        
        # Create temporary ZIP file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for photo_file in photoseries.photoseriesfile_set.all().order_by('order'):
                media_file = photo_file.media_file
                
                # Create filename with order prefix
                zip_filename = f"{photo_file.order:02d}_{media_file.original_filename}"
                
                # Add file to ZIP
                file_path = Path(settings.MEDIA_ROOT) / media_file.file.name
                if file_path.exists():
                    zip_file.write(file_path, zip_filename)
        
        temp_file.close()
        
        # Log download access
        import logging
        security_logger = logging.getLogger('security.mediafiles')
        security_logger.info(
            f"PhotoSeries ZIP download: user={request.user.username} "
            f"series={photoseries.id} "
            f"patient={photoseries.patient.id} "
            f"photo_count={photoseries.get_photo_count()}"
        )
        
        # Serve ZIP file
        response = FileResponse(
            open(temp_file.name, 'rb'),
            content_type='application/zip',
            as_attachment=True
        )
        
        # Create descriptive filename
        safe_patient_name = re.sub(r'[^\w\s-]', '', photoseries.patient.name)[:20]
        zip_filename = f"fotos_{safe_patient_name}_{photoseries.event_datetime.strftime('%Y%m%d')}.zip"
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        return response
        
    except Exception as e:
        # Log error
        import logging
        logger = logging.getLogger('mediafiles.downloads')
        logger.error(f"Error creating ZIP for PhotoSeries {pk}: {str(e)}")
        
        messages.error(request, "Erro ao gerar arquivo ZIP. Tente novamente.")
        return redirect('mediafiles:photoseries_detail', pk=pk)


# VideoClip CRUD Views

@method_decorator(hospital_context_required, name="dispatch")
class VideoClipCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Create view for VideoClip instances for a specific patient.

    Handles secure video upload and video clip event creation.
    """

    model = VideoClip
    form_class = VideoClipCreateForm
    template_name = "mediafiles/videoclip_form.html"
    permission_required = "events.add_event"

    def dispatch(self, request, *args, **kwargs):
        """Get patient and check permissions before processing request."""
        self.patient = get_object_or_404(Patient, pk=kwargs["patient_id"])

        # Check if user can access this patient
        if not can_access_patient(request.user, self.patient):
            raise PermissionDenied(
                "You don't have permission to create video clips for this patient"
            )

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass current user and patient to form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["patient"] = self.patient
        return kwargs

    def get_context_data(self, **kwargs):
        """Add patient to context."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.patient
        context["is_video"] = True
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful creation."""
        return reverse_lazy("apps.patients:patient_events_timeline", kwargs={"patient_id": self.object.patient.pk})

    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        duration = self.object.get_duration()
        messages.success(
            self.request,
            f"Vídeo de {duration} adicionado com sucesso para {self.patient.name}."
        )
        return response

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return VideoClip.objects.select_related(
            "patient", "created_by", "updated_by"
        )


@method_decorator(hospital_context_required, name="dispatch")
class VideoClipDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detail view for VideoClip instances.

    Displays video player with controls and metadata.
    """

    model = VideoClip
    template_name = "mediafiles/videoclip_detail.html"
    context_object_name = "videoclip"
    permission_required = "events.view_event"

    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's video clips"
            )

        return obj

    def get_context_data(self, **kwargs):
        """Add permission context."""
        context = super().get_context_data(**kwargs)
        videoclip = self.get_object()

        # Add permission flags
        context["can_edit"] = can_edit_event(self.request.user, videoclip)
        context["can_delete"] = can_delete_event(self.request.user, videoclip)

        return context

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return VideoClip.objects.select_related(
            "patient", "created_by", "updated_by"
        )


@method_decorator(hospital_context_required, name="dispatch")
class VideoClipUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Update view for VideoClip instances.

    Allows editing video metadata within the 24-hour window.
    """

    model = VideoClip
    form_class = VideoClipUpdateForm
    template_name = "mediafiles/videoclip_form.html"
    context_object_name = "videoclip"
    permission_required = "events.change_event"

    def get_object(self, queryset=None):
        """Get object and check patient access and edit permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's video clips"
            )

        # Check if user can edit this event
        if not can_edit_event(self.request.user, obj):
            raise PermissionDenied(
                "You don't have permission to edit this video clip"
            )

        return obj

    def get_form_kwargs(self):
        """Pass current user to form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Add context for update view."""
        context = super().get_context_data(**kwargs)
        context["is_update"] = True
        context["is_video"] = True
        context["patient"] = self.object.patient
        return context

    def get_success_url(self):
        """Redirect to patient timeline after successful update."""
        return reverse_lazy("apps.patients:patient_events_timeline", kwargs={"patient_id": self.object.patient.pk})

    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Vídeo atualizado com sucesso."
        )
        return response

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return VideoClip.objects.select_related(
            "patient", "created_by", "updated_by"
        )


@method_decorator(hospital_context_required, name="dispatch")
class VideoClipDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Delete view for VideoClip instances.

    Handles video clip deletion with confirmation and file cleanup.
    """

    model = VideoClip
    template_name = "mediafiles/videoclip_confirm_delete.html"
    context_object_name = "videoclip"
    permission_required = "events.delete_event"

    def get_object(self, queryset=None):
        """Get object and check patient access and delete permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's video clips"
            )

        # Check if user can delete this event
        if not can_delete_event(self.request.user, obj):
            raise PermissionDenied(
                "You don't have permission to delete this video clip"
            )

        return obj

    def get_success_url(self):
        """Redirect to patient timeline after successful deletion."""
        return reverse_lazy(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.object.patient.pk}
        )

    def delete(self, request, *args, **kwargs):
        """Handle deletion with success message."""
        videoclip = self.get_object()
        patient_name = videoclip.patient.name

        # Perform deletion
        response = super().delete(request, *args, **kwargs)

        messages.success(
            request,
            f"Vídeo removido com sucesso do prontuário de {patient_name}."
        )

        return response

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return VideoClip.objects.select_related(
            "patient", "created_by", "updated_by"
        )


@method_decorator(hospital_context_required, name="dispatch")
class VideoClipDownloadView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Download view for VideoClip instances.

    Serves video file as download with proper headers.
    """

    model = VideoClip
    permission_required = "events.view_event"

    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's video clips"
            )

        return obj

    def get(self, request, *args, **kwargs):
        """Serve video file as download."""
        videoclip = self.get_object()
        
        # Build file path from UUID and date structure
        from django.conf import settings
        from pathlib import Path
        
        # The file_id contains the UUID
        file_uuid = videoclip.file_id
        
        # Find the actual file by searching in the videos directory
        videos_dir = Path(settings.MEDIA_ROOT) / "videos"
        
        # Search for the file (it should be in the same year/month as creation date)
        creation_date = videoclip.created_at
        expected_path = videos_dir / creation_date.strftime('%Y/%m/originals') / f"{file_uuid}.mp4"
        
        if not expected_path.exists():
            # Fallback: search all possible locations
            for file_path in videos_dir.rglob(f"{file_uuid}.*"):
                expected_path = file_path
                break
            else:
                from django.http import Http404
                raise Http404("Video file not found")

        # Create download response
        response = FileResponse(
            open(expected_path, 'rb'),
            as_attachment=True,
            filename=videoclip.original_filename or f"video_{file_uuid}.mp4"
        )

        # Set download headers
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Length'] = expected_path.stat().st_size

        return response

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return VideoClip.objects.select_related(
            "patient", "created_by", "updated_by"
        )


@method_decorator(hospital_context_required, name="dispatch")
class VideoClipStreamView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Streaming view for VideoClip instances.

    Serves video file for streaming with range request support.
    """

    model = VideoClip
    permission_required = "events.view_event"

    def get_object(self, queryset=None):
        """Get object and check patient access permissions."""
        obj = super().get_object(queryset)

        # Check if user can access this patient
        if not can_access_patient(self.request.user, obj.patient):
            raise PermissionDenied(
                "You don't have permission to access this patient's video clips"
            )

        return obj

    def get(self, request, *args, **kwargs):
        """Serve video file for streaming."""
        videoclip = self.get_object()
        
        # Build file path from UUID and date structure
        from django.conf import settings
        from pathlib import Path
        
        # The file_id contains the UUID
        file_uuid = videoclip.file_id
        
        # Find the actual file by searching in the videos directory
        # Since we know the structure: videos/YYYY/MM/originals/UUID.mp4
        videos_dir = Path(settings.MEDIA_ROOT) / "videos"
        
        # Search for the file (it should be in the same year/month as creation date)
        creation_date = videoclip.created_at
        expected_path = videos_dir / creation_date.strftime('%Y/%m/originals') / f"{file_uuid}.mp4"
        
        if not expected_path.exists():
            # Fallback: search all possible locations
            for file_path in videos_dir.rglob(f"{file_uuid}.*"):
                expected_path = file_path
                break
            else:
                from django.http import Http404
                raise Http404("Video file not found")
        
        # Use the existing SecureVideoStreamView for streaming
        from django.http import FileResponse
        import mimetypes
        
        # Get content type
        content_type, _ = mimetypes.guess_type(str(expected_path))
        if not content_type:
            content_type = 'video/mp4'
        
        # Serve the file
        response = FileResponse(
            open(expected_path, 'rb'),
            content_type=content_type,
            as_attachment=False
        )
        
        # Add headers for video streaming
        response['Accept-Ranges'] = 'bytes'
        response['Content-Length'] = expected_path.stat().st_size
        
        return response

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return VideoClip.objects.select_related(
            "patient", "created_by", "updated_by"
        )


# Placeholder view for backward compatibility during transition
def placeholder_view(request, *args, **kwargs):
    """
    Placeholder view for backward compatibility.

    This should not be called anymore as all VideoClip views are implemented.
    """
    from django.http import HttpResponse
    return HttpResponse("VideoClip views are now implemented", status=200)