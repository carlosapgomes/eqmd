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
        # Create file handler for security logs
        handler = logging.FileHandler('logs/security_mediafiles.log')
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
        'MEDIA_IMAGE_MAX_SIZE',
        'MEDIA_VIDEO_MAX_SIZE',
        'MEDIA_USE_UUID_FILENAMES',
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
    
    # Check debug mode
    if settings.DEBUG:
        warnings.append("DEBUG mode is enabled (not recommended for production)")
    
    return warnings


# Initialize security logging on import
configure_security_logging()
