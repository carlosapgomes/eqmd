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

from .models import Photo, MediaFile
from .forms import PhotoCreateForm, PhotoUpdateForm
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
        file_path = Path(settings.MEDIA_ROOT) / media_file.file.name

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
        """Redirect to photo detail view after successful creation."""
        return reverse_lazy("mediafiles:photo_detail", kwargs={"pk": self.object.pk})

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
        """Redirect to photo detail view after successful update."""
        return reverse_lazy("mediafiles:photo_detail", kwargs={"pk": self.object.pk})

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
            "patients:patient_detail",
            kwargs={"pk": self.object.patient.pk}
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

    def get_queryset(self):
        """Optimize queryset with related objects."""
        return Photo.objects.select_related(
            "patient", "created_by", "updated_by", "media_file"
        )
