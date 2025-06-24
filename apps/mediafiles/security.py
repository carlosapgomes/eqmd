# MediaFiles Security Configuration
# Security settings and utilities for media file handling

import logging
from typing import Dict, Any, List
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


# Security logger configuration
def configure_security_logging():
    """Configure security logging for media files."""
    logger = logging.getLogger('security.mediafiles')

    if not logger.handlers:
        try:
            # Create logs directory if it doesn't exist
            import os
            from django.conf import settings

            logs_dir = getattr(settings, 'LOGS_DIR', 'logs')
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir, exist_ok=True)

            # Create file handler for security logs
            log_file = os.path.join(logs_dir, 'security_mediafiles.log')
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter(
                '%(asctime)s %(levelname)s %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        except Exception:
            # Fall back to console logging if file logging fails
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s %(levelname)s %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

    return logger


# Rate limiting utilities
class RateLimiter:
    """Rate limiting utilities for media file operations."""
    
    @staticmethod
    def is_rate_limited(identifier: str, action: str, limit: int = 100, window: int = 3600) -> bool:
        """
        Check if identifier is rate limited for specific action.
        
        Args:
            identifier: User ID or IP address
            action: Action type (e.g., 'file_access', 'upload')
            limit: Maximum actions per window
            window: Time window in seconds
        
        Returns:
            bool: True if rate limited
        """
        cache_key = f"rate_limit:{identifier}:{action}"
        current_count = cache.get(cache_key, 0)
        
        if current_count >= limit:
            return True
        
        # Increment counter
        cache.set(cache_key, current_count + 1, window)
        return False
    
    @staticmethod
    def get_rate_limit_status(identifier: str, action: str, limit: int = 100) -> Dict[str, Any]:
        """
        Get current rate limit status for identifier.
        
        Args:
            identifier: User ID or IP address
            action: Action type
            limit: Maximum actions per window
        
        Returns:
            Dictionary with rate limit status
        """
        cache_key = f"rate_limit:{identifier}:{action}"
        current_count = cache.get(cache_key, 0)
        
        return {
            'current_count': current_count,
            'limit': limit,
            'remaining': max(0, limit - current_count),
            'is_limited': current_count >= limit
        }


# File validation utilities
class FileValidator:
    """File validation utilities for media files."""

    @staticmethod
    def validate_image_file(uploaded_file):
        """
        Validate uploaded image file for security and format.

        Args:
            uploaded_file: Django UploadedFile object

        Raises:
            ValidationError: If file validation fails
        """
        from django.core.exceptions import ValidationError
        from pathlib import Path

        # Check file size
        max_size = getattr(settings, 'MEDIA_IMAGE_MAX_SIZE', 5 * 1024 * 1024)
        if uploaded_file.size > max_size:
            raise ValidationError(f"File size ({uploaded_file.size} bytes) exceeds maximum allowed ({max_size} bytes)")

        # Check file extension
        ext = Path(uploaded_file.name).suffix.lower()
        allowed_extensions = getattr(settings, 'MEDIA_ALLOWED_IMAGE_EXTENSIONS', ['.jpg', '.jpeg', '.png', '.webp'])
        if ext not in allowed_extensions:
            raise ValidationError(f"File extension {ext} not allowed")

        # Check MIME type
        allowed_types = getattr(settings, 'MEDIA_ALLOWED_IMAGE_TYPES', ['image/jpeg', 'image/png', 'image/webp'])
        if uploaded_file.content_type not in allowed_types:
            raise ValidationError(f"File type {uploaded_file.content_type} not allowed")

        # Basic magic number validation
        uploaded_file.seek(0)
        header = uploaded_file.read(1024)
        uploaded_file.seek(0)

        # Check for common image magic numbers
        if not (
            header.startswith(b'\xff\xd8\xff') or  # JPEG
            header.startswith(b'\x89PNG\r\n\x1a\n') or  # PNG
            header.startswith(b'RIFF') and b'WEBP' in header[:12]  # WebP
        ):
            raise ValidationError("Invalid image file format")


# Security validation utilities
class SecurityValidator:
    """Security validation utilities for media files."""
    
    # Dangerous file patterns
    DANGEROUS_PATTERNS = [
        r'\.\./',  # Path traversal
        r'\\\.\\',  # Windows path traversal
        r'<script',  # Script injection
        r'javascript:',  # JavaScript protocol
        r'vbscript:',  # VBScript protocol
        r'data:',  # Data URLs (can be dangerous)
    ]
    
    # Suspicious user agents
    SUSPICIOUS_USER_AGENTS = [
        'curl',
        'wget',
        'python-requests',
        'bot',
        'crawler',
        'spider',
    ]
    
    @classmethod
    def validate_request_security(cls, request) -> Dict[str, Any]:
        """
        Validate request for security issues.
        
        Args:
            request: Django HttpRequest object
        
        Returns:
            Dictionary with validation results
        """
        issues = []
        
        # Check user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        for suspicious in cls.SUSPICIOUS_USER_AGENTS:
            if suspicious in user_agent:
                issues.append(f"Suspicious user agent: {user_agent}")
                break
        
        # Check for suspicious headers
        if 'HTTP_X_FORWARDED_FOR' in request.META:
            forwarded_ips = request.META['HTTP_X_FORWARDED_FOR'].split(',')
            if len(forwarded_ips) > 5:  # Too many proxy hops
                issues.append("Excessive proxy forwarding detected")
        
        # Check referer
        referer = request.META.get('HTTP_REFERER', '')
        if referer and not referer.startswith(('http://localhost', 'https://localhost')):
            # In production, check against allowed domains
            pass
        
        return {
            'is_secure': len(issues) == 0,
            'issues': issues
        }
    
    @classmethod
    def validate_file_path_security(cls, file_path: str) -> bool:
        """
        Validate file path for security issues.
        
        Args:
            file_path: File path to validate
        
        Returns:
            bool: True if path is secure
        """
        import re
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, file_path, re.IGNORECASE):
                return False
        
        # Check for absolute paths
        if file_path.startswith('/') or '\\' in file_path:
            return False
        
        # Check for null bytes
        if '\x00' in file_path:
            return False
        
        return True


# Access control utilities
class AccessController:
    """Access control utilities for media files."""
    
    @staticmethod
    def check_hospital_context(user, patient) -> bool:
        """
        Check if user has access to patient in current hospital context.
        
        Args:
            user: Django User object
            patient: Patient object
        
        Returns:
            bool: True if access is allowed
        """
        if not hasattr(user, 'current_hospital'):
            return True  # No hospital context restriction
        
        return user.current_hospital == patient.hospital
    
    @staticmethod
    def check_patient_permissions(user, patient) -> bool:
        """
        Check if user has permission to view patient data.
        
        Args:
            user: Django User object
            patient: Patient object
        
        Returns:
            bool: True if permission granted
        """
        return user.has_perm('patients.view_patient', patient)
    
    @staticmethod
    def check_event_permissions(user, event) -> bool:
        """
        Check if user has permission to view event data.
        
        Args:
            user: Django User object
            event: Event object
        
        Returns:
            bool: True if permission granted
        """
        return user.has_perm('events.view_event', event)
    
    @staticmethod
    def get_user_permissions_summary(user) -> Dict[str, Any]:
        """
        Get summary of user's media-related permissions.
        
        Args:
            user: Django User object
        
        Returns:
            Dictionary with permission summary
        """
        return {
            'can_view_patients': user.has_perm('patients.view_patient'),
            'can_view_events': user.has_perm('events.view_event'),
            'can_add_events': user.has_perm('events.add_event'),
            'can_change_events': user.has_perm('events.change_event'),
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'current_hospital': getattr(user, 'current_hospital', None)
        }


# Audit logging utilities
class AuditLogger:
    """Audit logging utilities for media file operations."""
    
    @staticmethod
    def log_file_access(user, file_id: str, action: str, success: bool = True, details: str = None):
        """
        Log file access for audit trail.
        
        Args:
            user: Django User object
            file_id: Media file ID
            action: Action performed
            success: Whether action was successful
            details: Additional details
        """
        logger = configure_security_logging()
        
        log_data = {
            'user': user.username if user else 'anonymous',
            'user_id': user.id if user else None,
            'file_id': file_id,
            'action': action,
            'success': success,
            'timestamp': timezone.now().isoformat(),
            'details': details or ''
        }
        
        if success:
            logger.info(f"File access: {log_data}")
        else:
            logger.warning(f"File access failed: {log_data}")
    
    @staticmethod
    def log_security_event(user, event_type: str, details: str, severity: str = 'warning'):
        """
        Log security-related events.
        
        Args:
            user: Django User object or None
            event_type: Type of security event
            details: Event details
            severity: Event severity ('info', 'warning', 'error')
        """
        logger = configure_security_logging()
        
        log_data = {
            'user': user.username if user else 'anonymous',
            'user_id': user.id if user else None,
            'event_type': event_type,
            'details': details,
            'timestamp': timezone.now().isoformat()
        }
        
        if severity == 'error':
            logger.error(f"Security event: {log_data}")
        elif severity == 'warning':
            logger.warning(f"Security event: {log_data}")
        else:
            logger.info(f"Security event: {log_data}")


# Security settings validation
def validate_security_settings() -> List[str]:
    """
    Validate security-related settings.
    
    Returns:
        List of validation warnings/errors
    """
    warnings = []
    
    # Check required settings
    required_settings = [
        'MEDIA_ALLOWED_IMAGE_EXTENSIONS',
        'MEDIA_ALLOWED_VIDEO_EXTENSIONS',
        'MEDIA_ALLOWED_IMAGE_TYPES',
        'MEDIA_ALLOWED_VIDEO_TYPES',
        'MEDIA_ALLOWED_VIDEO_CODECS',
        'MEDIA_ALLOWED_VIDEO_FORMATS',
        'MEDIA_IMAGE_MAX_SIZE',
        'MEDIA_VIDEO_MAX_SIZE',
        'MEDIA_VIDEO_MAX_DURATION',
        'MEDIA_VIDEO_MAX_DIMENSION',
        'MEDIA_VIDEO_MAX_RANGE_SIZE',
        'MEDIA_MAX_FILENAME_LENGTH',
        'MEDIA_USE_UUID_FILENAMES',
        'MEDIA_ENABLE_FILE_DEDUPLICATION',
    ]
    
    for setting in required_settings:
        if not hasattr(settings, setting):
            warnings.append(f"Missing security setting: {setting}")
    
    # Check file size limits
    if hasattr(settings, 'MEDIA_IMAGE_MAX_SIZE'):
        if settings.MEDIA_IMAGE_MAX_SIZE > 10 * 1024 * 1024:  # 10MB
            warnings.append("Image file size limit is very high (>10MB)")
    
    if hasattr(settings, 'MEDIA_VIDEO_MAX_SIZE'):
        if settings.MEDIA_VIDEO_MAX_SIZE > 100 * 1024 * 1024:  # 100MB
            warnings.append("Video file size limit is very high (>100MB)")
    
    # Check UUID filename setting
    if not getattr(settings, 'MEDIA_USE_UUID_FILENAMES', False):
        warnings.append("UUID-based filenames not enabled (security risk)")
    
    # Check video-specific settings
    if hasattr(settings, 'MEDIA_VIDEO_MAX_DURATION'):
        if settings.MEDIA_VIDEO_MAX_DURATION > 300:  # 5 minutes
            warnings.append("Video duration limit is very high (>5 minutes)")

    if hasattr(settings, 'MEDIA_VIDEO_MAX_DIMENSION'):
        if settings.MEDIA_VIDEO_MAX_DIMENSION > 8192:  # 8K
            warnings.append("Video dimension limit is very high (>8K)")

    if hasattr(settings, 'MEDIA_VIDEO_MAX_RANGE_SIZE'):
        if settings.MEDIA_VIDEO_MAX_RANGE_SIZE > 50 * 1024 * 1024:  # 50MB
            warnings.append("Video range request size limit is very high (>50MB)")

    # Check codec security
    if hasattr(settings, 'MEDIA_ALLOWED_VIDEO_CODECS'):
        dangerous_codecs = ['wmv', 'asf', 'rm', 'rmvb', 'flv']
        for codec in settings.MEDIA_ALLOWED_VIDEO_CODECS:
            if codec.lower() in dangerous_codecs:
                warnings.append(f"Potentially unsafe video codec allowed: {codec}")

    # Check container format security
    if hasattr(settings, 'MEDIA_ALLOWED_VIDEO_FORMATS'):
        dangerous_formats = ['asf', 'wmv', 'rm', 'rmvb', 'flv']
        for format_name in settings.MEDIA_ALLOWED_VIDEO_FORMATS:
            if format_name.lower() in dangerous_formats:
                warnings.append(f"Potentially unsafe video format allowed: {format_name}")

    # Check filename length
    if hasattr(settings, 'MEDIA_MAX_FILENAME_LENGTH'):
        if settings.MEDIA_MAX_FILENAME_LENGTH > 255:
            warnings.append("Maximum filename length is very high (>255 characters)")
        elif settings.MEDIA_MAX_FILENAME_LENGTH < 50:
            warnings.append("Maximum filename length is very low (<50 characters)")

    # Check debug mode
    if settings.DEBUG:
        warnings.append("DEBUG mode is enabled (not recommended for production)")

    return warnings


def validate_video_security_settings() -> List[str]:
    """
    Validate video-specific security settings.

    Returns:
        List of validation warnings/errors specific to video security
    """
    warnings = []

    # Check video file size limits
    video_max_size = getattr(settings, 'MEDIA_VIDEO_MAX_SIZE', 0)
    if video_max_size == 0:
        warnings.append("Video file size limit not set")
    elif video_max_size > 100 * 1024 * 1024:  # 100MB
        warnings.append(f"Video file size limit is very high: {video_max_size // (1024 * 1024)}MB")

    # Check video duration limits
    video_max_duration = getattr(settings, 'MEDIA_VIDEO_MAX_DURATION', 0)
    if video_max_duration == 0:
        warnings.append("Video duration limit not set")
    elif video_max_duration > 600:  # 10 minutes
        warnings.append(f"Video duration limit is very high: {video_max_duration} seconds")

    # Check video codec whitelist
    allowed_codecs = getattr(settings, 'MEDIA_ALLOWED_VIDEO_CODECS', [])
    if not allowed_codecs:
        warnings.append("No video codecs are allowed (video uploads will fail)")
    else:
        safe_codecs = ['h264', 'h265', 'vp8', 'vp9', 'av1']
        for codec in allowed_codecs:
            if codec.lower() not in safe_codecs:
                warnings.append(f"Video codec '{codec}' may not be secure")

    # Check video format whitelist
    allowed_formats = getattr(settings, 'MEDIA_ALLOWED_VIDEO_FORMATS', [])
    if not allowed_formats:
        warnings.append("No video formats are allowed (video uploads will fail)")
    else:
        safe_formats = ['mp4', 'webm', 'mov']
        for format_name in allowed_formats:
            if format_name.lower() not in safe_formats:
                warnings.append(f"Video format '{format_name}' may not be secure")

    # Check streaming security settings
    max_range_size = getattr(settings, 'MEDIA_VIDEO_MAX_RANGE_SIZE', 0)
    if max_range_size == 0:
        warnings.append("Video range request size limit not set (potential DoS risk)")
    elif max_range_size > 100 * 1024 * 1024:  # 100MB
        warnings.append(f"Video range request size limit is very high: {max_range_size // (1024 * 1024)}MB")

    # Check video dimension limits
    max_dimension = getattr(settings, 'MEDIA_VIDEO_MAX_DIMENSION', 0)
    if max_dimension == 0:
        warnings.append("Video dimension limit not set")
    elif max_dimension > 8192:  # 8K
        warnings.append(f"Video dimension limit is very high: {max_dimension}px")

    return warnings


# Initialize security logging on import
configure_security_logging()
