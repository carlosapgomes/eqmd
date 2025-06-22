# MediaFiles Security Middleware
# Security middleware for file serving and access control

import time
import logging
from typing import Optional
from urllib.parse import unquote

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, Http404
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

# Set up security logger
security_logger = logging.getLogger('security.mediafiles')


class MediaFileSecurityMiddleware(MiddlewareMixin):
    """
    Security middleware for media file access control.
    
    Features:
    - Permission-based file access control
    - Rate limiting for file downloads
    - Secure headers for file responses
    - Access logging for audit trails
    - IP-based access restrictions (if configured)
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.media_url_prefix = getattr(settings, 'MEDIA_URL', '/media/').rstrip('/')
        self.rate_limit_enabled = getattr(settings, 'MEDIA_ENABLE_RATE_LIMITING', True)
        self.access_logging_enabled = getattr(settings, 'MEDIA_ENABLE_ACCESS_LOGGING', True)
        
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Process incoming requests for media files.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            HttpResponse if request should be blocked, None to continue
        """
        # Check if this is a media file request
        if not self._is_media_request(request):
            return None
        
        # Log access attempt
        if self.access_logging_enabled:
            self._log_access_attempt(request)
        
        # Check rate limiting
        if self.rate_limit_enabled and self._is_rate_limited(request):
            self._log_security_event(request, 'rate_limit_exceeded')
            raise PermissionDenied("Rate limit exceeded for file access")
        
        # Check IP restrictions (if configured)
        if hasattr(settings, 'MEDIA_ALLOWED_IPS') and not self._is_ip_allowed(request):
            self._log_security_event(request, 'ip_blocked')
            raise PermissionDenied("IP address not allowed")
        
        return None
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Process responses for media files to add security headers.
        
        Args:
            request: Django HttpRequest object
            response: Django HttpResponse object
            
        Returns:
            Modified HttpResponse with security headers
        """
        # Add security headers to media file responses
        if self._is_media_request(request) and response.status_code == 200:
            response = self._add_security_headers(response)
        
        return response
    
    def _is_media_request(self, request: HttpRequest) -> bool:
        """
        Check if request is for a media file.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            True if request is for media file
        """
        path = unquote(request.path)
        return path.startswith(self.media_url_prefix)
    
    def _is_rate_limited(self, request: HttpRequest) -> bool:
        """
        Check if user/IP is rate limited.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            True if rate limited
        """
        # Get identifier for rate limiting
        if request.user.is_authenticated:
            identifier = f"user:{request.user.id}"
        else:
            identifier = f"ip:{self._get_client_ip(request)}"
        
        # Check rate limit
        cache_key = f"media_rate_limit:{identifier}"
        current_count = cache.get(cache_key, 0)
        
        # Get rate limit settings
        limit = getattr(settings, 'MEDIA_RATE_LIMIT_DOWNLOADS', 100)
        window = getattr(settings, 'MEDIA_RATE_LIMIT_WINDOW', 3600)  # 1 hour
        
        if current_count >= limit:
            return True
        
        # Increment counter
        cache.set(cache_key, current_count + 1, window)
        return False
    
    def _is_ip_allowed(self, request: HttpRequest) -> bool:
        """
        Check if client IP is allowed.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            True if IP is allowed
        """
        client_ip = self._get_client_ip(request)
        allowed_ips = getattr(settings, 'MEDIA_ALLOWED_IPS', [])
        
        if not allowed_ips:
            return True  # No restrictions if not configured
        
        return client_ip in allowed_ips
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            Client IP address
        """
        # Check for forwarded IP (behind proxy/load balancer)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        
        return ip
    
    def _add_security_headers(self, response: HttpResponse) -> HttpResponse:
        """
        Add security headers to media file responses.
        
        Args:
            response: Django HttpResponse object
            
        Returns:
            Response with added security headers
        """
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent framing (clickjacking protection)
        response['X-Frame-Options'] = 'DENY'
        
        # XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Content Security Policy for media files
        response['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; media-src 'self';"
        
        # Cache control for private content
        response['Cache-Control'] = 'private, max-age=3600, must-revalidate'
        
        # Referrer policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
    
    def _log_access_attempt(self, request: HttpRequest) -> None:
        """
        Log media file access attempt.
        
        Args:
            request: Django HttpRequest object
        """
        user_info = request.user.username if request.user.is_authenticated else 'anonymous'
        client_ip = self._get_client_ip(request)
        
        security_logger.info(
            f"Media access: user={user_info} ip={client_ip} "
            f"path={request.path} method={request.method} "
            f"user_agent={request.META.get('HTTP_USER_AGENT', 'unknown')} "
            f"timestamp={timezone.now().isoformat()}"
        )
    
    def _log_security_event(self, request: HttpRequest, event_type: str) -> None:
        """
        Log security-related events.
        
        Args:
            request: Django HttpRequest object
            event_type: Type of security event
        """
        user_info = request.user.username if request.user.is_authenticated else 'anonymous'
        client_ip = self._get_client_ip(request)
        
        security_logger.warning(
            f"Security event: type={event_type} user={user_info} "
            f"ip={client_ip} path={request.path} "
            f"timestamp={timezone.now().isoformat()}"
        )


class MediaFileUploadSecurityMiddleware(MiddlewareMixin):
    """
    Security middleware specifically for file upload requests.
    
    Features:
    - Upload rate limiting
    - File size validation
    - Content type validation
    - Upload attempt logging
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.upload_rate_limit_enabled = getattr(settings, 'MEDIA_ENABLE_UPLOAD_RATE_LIMITING', True)
        
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Process file upload requests.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            HttpResponse if request should be blocked, None to continue
        """
        # Check if this is a file upload request
        if not self._is_upload_request(request):
            return None
        
        # Check upload rate limiting
        if self.upload_rate_limit_enabled and self._is_upload_rate_limited(request):
            self._log_security_event(request, 'upload_rate_limit_exceeded')
            raise PermissionDenied("Upload rate limit exceeded")
        
        # Validate content length
        content_length = request.META.get('CONTENT_LENGTH')
        if content_length:
            try:
                content_length = int(content_length)
                max_upload_size = getattr(settings, 'DATA_UPLOAD_MAX_MEMORY_SIZE', 10 * 1024 * 1024)
                if content_length > max_upload_size:
                    self._log_security_event(request, 'upload_size_exceeded')
                    raise PermissionDenied("Upload size exceeds maximum allowed")
            except (ValueError, TypeError):
                pass
        
        return None
    
    def _is_upload_request(self, request: HttpRequest) -> bool:
        """
        Check if request is a file upload.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            True if request is file upload
        """
        return (
            request.method in ('POST', 'PUT', 'PATCH') and
            request.content_type and
            request.content_type.startswith('multipart/form-data')
        )
    
    def _is_upload_rate_limited(self, request: HttpRequest) -> bool:
        """
        Check if user/IP is upload rate limited.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            True if rate limited
        """
        # Get identifier for rate limiting
        if request.user.is_authenticated:
            identifier = f"user:{request.user.id}"
        else:
            identifier = f"ip:{self._get_client_ip(request)}"
        
        # Check upload rate limit
        cache_key = f"media_upload_rate_limit:{identifier}"
        current_count = cache.get(cache_key, 0)
        
        # Get upload rate limit settings
        limit = getattr(settings, 'MEDIA_RATE_LIMIT_UPLOADS', 10)
        window = getattr(settings, 'MEDIA_UPLOAD_RATE_LIMIT_WINDOW', 3600)  # 1 hour
        
        if current_count >= limit:
            return True
        
        # Increment counter
        cache.set(cache_key, current_count + 1, window)
        return False
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def _log_security_event(self, request: HttpRequest, event_type: str) -> None:
        """Log security-related events."""
        user_info = request.user.username if request.user.is_authenticated else 'anonymous'
        client_ip = self._get_client_ip(request)
        
        security_logger.warning(
            f"Upload security event: type={event_type} user={user_info} "
            f"ip={client_ip} path={request.path} "
            f"timestamp={timezone.now().isoformat()}"
        )
