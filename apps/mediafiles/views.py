# MediaFiles Views
# Secure file serving and access control views

import mimetypes
import time
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, FileResponse, Http404
from django.utils.decorators import method_decorator
from django.utils.http import http_date
from django.views import View
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods


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

        # Check patient access permissions
        if not user.has_perm('patients.view_patient', event.patient):
            raise PermissionDenied("No permission to view patient files")

        # Check hospital context
        if hasattr(user, 'current_hospital') and user.current_hospital != event.patient.hospital:
            raise PermissionDenied("File not accessible in current hospital context")

        # Check event-specific permissions
        if not user.has_perm('events.view_event', event):
            raise PermissionDenied("No permission to view this event")

        return media_file

    def _get_event_from_media_file(self, media_file):
        """
        Get the associated event from a media file.

        Args:
            media_file: MediaFile object

        Returns:
            Event object
        """
        # This will be implemented when models are created
        # Try to find associated Photo, PhotoSeries, or VideoClip
        try:
            if hasattr(media_file, 'photo'):
                return media_file.photo
            elif hasattr(media_file, 'videoclip'):
                return media_file.videoclip
            elif hasattr(media_file, 'photoseriesfile_set'):
                # Get first photo series that uses this file
                series_file = media_file.photoseriesfile_set.first()
                if series_file:
                    return series_file.photo_series
        except AttributeError:
            pass

        # Fallback - this should not happen in production
        raise PermissionDenied("Could not determine associated event")

    def _serve_file_securely(self, media_file) -> FileResponse:
        """
        Serve file with comprehensive security headers.

        Args:
            media_file: MediaFile object

        Returns:
            FileResponse with security headers

        Raises:
            Http404: If file not found on disk
        """
        file_path = Path(settings.MEDIA_ROOT) / media_file.file_path

        # Validate file exists and is readable
        if not file_path.exists() or not file_path.is_file():
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

        return response

    def _log_file_access(self, user, media_file, action: str) -> None:
        """Log file access for audit trail."""
        import logging
        security_logger = logging.getLogger('security.mediafiles')

        security_logger.info(
            f"File access: user={user.username} "
            f"file={media_file.id} "
            f"filename={media_file.original_filename} "
            f"action={action} "
            f"timestamp={time.time()}"
        )

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
        # Get thumbnail path
        if not media_file.thumbnail_path:
            raise Http404("Thumbnail not available")

        thumbnail_path = Path(settings.MEDIA_ROOT) / media_file.thumbnail_path

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
