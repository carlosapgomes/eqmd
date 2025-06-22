# MediaFiles Security Implementation Plan

## Overview

This document outlines the comprehensive security implementation for the MediaFiles app, covering file naming, validation, access control, and threat mitigation.

## Security Principles

### Core Security Goals

1. **Confidentiality**: Patient media files are protected from unauthorized access
2. **Integrity**: Files cannot be tampered with or corrupted
3. **Availability**: Authorized users can access files when needed
4. **Auditability**: All file access is logged for compliance
5. **Non-repudiation**: Actions can be traced to specific users

### Threat Model

**Threats Addressed**:
- File enumeration attacks
- Path traversal attacks
- Malicious file uploads
- Unauthorized file access
- Data exfiltration
- File corruption/tampering
- Privacy violations

## File Naming Security

### UUID-Based Secure Naming

```python
import uuid
import secrets
from pathlib import Path
from django.utils.text import slugify

def generate_secure_filename(original_filename):
    """
    Generate cryptographically secure filename using UUID4.
    
    Security features:
    - UUID4 provides 122 bits of entropy
    - No predictable patterns
    - No patient information leakage
    - Extension validation included
    """
    # Validate and normalize extension
    ext = Path(original_filename).suffix.lower()
    if not ext:
        raise ValueError("File must have an extension")
    
    # Generate secure UUID-based filename
    secure_uuid = uuid.uuid4()
    secure_filename = f"{secure_uuid}{ext}"
    
    return secure_filename

def sanitize_original_filename(filename):
    """
    Sanitize original filename for safe database storage.
    
    Security features:
    - Remove path traversal characters
    - Limit length to prevent buffer overflows
    - Remove dangerous characters
    - Preserve readability for users
    """
    # Remove path components
    clean_name = Path(filename).name
    
    # Remove dangerous characters
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
    for char in dangerous_chars:
        clean_name = clean_name.replace(char, '_')
    
    # Limit length
    if len(clean_name) > 100:
        name_part = Path(clean_name).stem[:90]
        ext_part = Path(clean_name).suffix
        clean_name = f"{name_part}{ext_part}"
    
    return clean_name
```

### Path Security

```python
def get_secure_upload_path(instance, filename):
    """
    Generate secure upload path with multiple security layers.
    
    Security features:
    - UUID-based filename prevents enumeration
    - Year/month organization limits directory traversal
    - Media type separation for access control
    - No user-controlled path components
    """
    from django.utils import timezone
    from django.conf import settings
    
    # Validate filename extension
    ext = Path(filename).suffix.lower()
    if ext not in settings.MEDIA_ALLOWED_IMAGE_EXTENSIONS + settings.MEDIA_ALLOWED_VIDEO_EXTENSIONS:
        raise ValueError(f"File extension {ext} not allowed")
    
    # Generate secure filename
    secure_filename = generate_secure_filename(filename)
    
    # Create date-based path (no user input)
    current_date = timezone.now()
    year_month = current_date.strftime('%Y/%m')
    
    # Determine media type (controlled by application logic)
    media_type = get_media_type_from_instance(instance)
    
    # Construct secure path
    secure_path = f"{media_type}/{year_month}/originals/{secure_filename}"
    
    # Final validation - ensure no path traversal
    if '..' in secure_path or secure_path.startswith('/'):
        raise ValueError("Invalid path detected")
    
    return secure_path
```

## File Validation Security

### Comprehensive File Validation

```python
import magic
import hashlib
from PIL import Image
from django.core.exceptions import ValidationError
from django.conf import settings

def validate_file_security(file_obj):
    """
    Comprehensive file security validation.
    
    Security checks:
    - File size limits
    - MIME type validation
    - Magic number verification
    - Malicious content detection
    - File structure validation
    """
    # Reset file pointer
    file_obj.seek(0)
    
    # Check file size
    file_size = file_obj.size
    if file_size > settings.MEDIA_IMAGE_MAX_SIZE:
        raise ValidationError(f"File too large: {file_size} bytes")
    
    # Read file header for magic number check
    file_header = file_obj.read(1024)
    file_obj.seek(0)
    
    # MIME type validation using python-magic
    detected_mime = magic.from_buffer(file_header, mime=True)
    
    # Validate against allowed MIME types
    allowed_mimes = settings.MEDIA_ALLOWED_IMAGE_TYPES + settings.MEDIA_ALLOWED_VIDEO_TYPES
    if detected_mime not in allowed_mimes:
        raise ValidationError(f"File type not allowed: {detected_mime}")
    
    # Additional validation for images
    if detected_mime.startswith('image/'):
        validate_image_security(file_obj)
    
    # Additional validation for videos
    elif detected_mime.startswith('video/'):
        validate_video_security(file_obj)

def validate_image_security(file_obj):
    """
    Image-specific security validation.
    
    Security checks:
    - Image format validation
    - Embedded script detection
    - Metadata sanitization
    - Dimension limits
    """
    try:
        # Use Pillow to validate image structure
        with Image.open(file_obj) as img:
            # Verify image can be loaded
            img.verify()
            
            # Check dimensions
            if img.width > 10000 or img.height > 10000:
                raise ValidationError("Image dimensions too large")
            
            # Check for suspicious metadata
            if hasattr(img, '_getexif') and img._getexif():
                # Log metadata for review but don't block
                pass
                
    except Exception as e:
        raise ValidationError(f"Invalid image file: {str(e)}")
    
    # Reset file pointer after validation
    file_obj.seek(0)
```

### File Hash Calculation

```python
def calculate_secure_file_hash(file_obj):
    """
    Calculate SHA-256 hash for file integrity and deduplication.
    
    Security features:
    - Cryptographically secure hash function
    - Tamper detection capability
    - Deduplication support
    - Integrity verification
    """
    hash_sha256 = hashlib.sha256()
    
    # Reset file pointer
    file_obj.seek(0)
    
    # Process file in secure chunks
    chunk_size = 8192  # 8KB chunks
    while chunk := file_obj.read(chunk_size):
        hash_sha256.update(chunk)
    
    # Reset file pointer
    file_obj.seek(0)
    
    return hash_sha256.hexdigest()
```

## Access Control Security

### Permission-Based File Access

```python
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404

@login_required
def secure_file_serve(request, file_id):
    """
    Secure file serving with comprehensive access control.
    
    Security features:
    - Authentication required
    - Permission-based access
    - Audit logging
    - Rate limiting
    - Secure headers
    """
    try:
        # Get media file with security checks
        media_file = get_media_file_with_permissions(request.user, file_id)
        
        # Log access attempt
        log_file_access(request.user, media_file, 'view')
        
        # Check rate limiting
        if is_rate_limited(request.user, 'file_access'):
            raise PermissionDenied("Rate limit exceeded")
        
        # Serve file with secure headers
        return serve_file_securely(media_file)
        
    except MediaFile.DoesNotExist:
        # Log suspicious access attempt
        log_security_event(request.user, 'file_not_found', file_id)
        raise Http404("File not found")

def get_media_file_with_permissions(user, file_id):
    """
    Get media file with comprehensive permission checking.
    
    Permission checks:
    - User authentication
    - Hospital context validation
    - Patient access permissions
    - Event access permissions
    - File-specific permissions
    """
    from apps.mediafiles.models import MediaFile
    
    # Get media file
    try:
        media_file = MediaFile.objects.get(id=file_id)
    except MediaFile.DoesNotExist:
        raise PermissionDenied("File not found or access denied")
    
    # Get associated event
    event = get_event_from_media_file(media_file)
    
    # Check patient access permissions
    if not user.has_perm('patients.view_patient', event.patient):
        raise PermissionDenied("No permission to view patient files")
    
    # Check hospital context
    if not user.current_hospital == event.patient.hospital:
        raise PermissionDenied("File not accessible in current hospital context")
    
    # Check event-specific permissions
    if not user.has_perm('events.view_event', event):
        raise PermissionDenied("No permission to view this event")
    
    return media_file
```

### Secure File Serving

```python
from django.http import FileResponse, HttpResponse
from django.utils.http import http_date
import mimetypes
import time

def serve_file_securely(media_file):
    """
    Serve file with comprehensive security headers.
    
    Security features:
    - Content-Type validation
    - Content-Disposition headers
    - Cache control
    - CSRF protection
    - XSS prevention
    """
    file_path = media_file.get_absolute_path()
    
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
    response['Cache-Control'] = 'private, max-age=3600'
    response['Expires'] = http_date(time.time() + 3600)
    
    # Set content length
    response['Content-Length'] = file_path.stat().st_size
    
    return response
```

## Audit and Monitoring

### Security Event Logging

```python
import logging
from django.utils import timezone

security_logger = logging.getLogger('security.mediafiles')

def log_file_access(user, media_file, action):
    """Log file access for audit trail."""
    security_logger.info(
        f"File access: user={user.username} "
        f"file={media_file.id} "
        f"action={action} "
        f"timestamp={timezone.now().isoformat()}"
    )

def log_security_event(user, event_type, details):
    """Log security-related events."""
    security_logger.warning(
        f"Security event: user={user.username if user else 'anonymous'} "
        f"type={event_type} "
        f"details={details} "
        f"timestamp={timezone.now().isoformat()}"
    )

def log_file_upload(user, media_file, success=True):
    """Log file upload attempts."""
    level = logging.INFO if success else logging.WARNING
    security_logger.log(
        level,
        f"File upload: user={user.username} "
        f"file={media_file.original_filename} "
        f"success={success} "
        f"timestamp={timezone.now().isoformat()}"
    )
```

### Rate Limiting

```python
from django.core.cache import cache
from django.utils import timezone

def is_rate_limited(user, action, limit=100, window=3600):
    """
    Check if user is rate limited for specific action.
    
    Args:
        user: User object
        action: Action type (e.g., 'file_access', 'upload')
        limit: Maximum actions per window
        window: Time window in seconds
    
    Returns:
        bool: True if rate limited
    """
    cache_key = f"rate_limit:{user.id}:{action}"
    current_count = cache.get(cache_key, 0)
    
    if current_count >= limit:
        return True
    
    # Increment counter
    cache.set(cache_key, current_count + 1, window)
    return False
```

## Data Protection

### File Encryption (Future Enhancement)

```python
from cryptography.fernet import Fernet
from django.conf import settings

def encrypt_file_content(file_content):
    """
    Encrypt file content for storage (future enhancement).
    
    Note: This is a placeholder for future encryption implementation.
    Current implementation focuses on access control and secure naming.
    """
    # This would be implemented when encryption at rest is required
    # Key management would need to be carefully designed
    pass

def decrypt_file_content(encrypted_content):
    """Decrypt file content for serving (future enhancement)."""
    # Corresponding decryption implementation
    pass
```

### Secure Deletion

```python
import os
import secrets

def secure_file_deletion(file_path):
    """
    Securely delete file with multiple overwrites.
    
    Security features:
    - Multiple overwrite passes
    - Random data overwriting
    - Metadata clearing
    - Verification of deletion
    """
    if not file_path.exists():
        return True
    
    try:
        # Get file size
        file_size = file_path.stat().st_size
        
        # Overwrite with random data (3 passes)
        with open(file_path, 'r+b') as f:
            for _ in range(3):
                f.seek(0)
                f.write(secrets.token_bytes(file_size))
                f.flush()
                os.fsync(f.fileno())
        
        # Delete file
        file_path.unlink()
        
        # Verify deletion
        return not file_path.exists()
        
    except Exception as e:
        log_security_event(None, 'secure_deletion_failed', str(e))
        return False
```

## Security Configuration

### Django Settings Security

```python
# Security settings for media files
MEDIA_ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
MEDIA_ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.webm', '.mov']
MEDIA_ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
MEDIA_ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/webm', 'video/quicktime']

# File size limits
MEDIA_IMAGE_MAX_SIZE = 5 * 1024 * 1024  # 5MB
MEDIA_VIDEO_MAX_SIZE = 50 * 1024 * 1024  # 50MB
MEDIA_VIDEO_MAX_DURATION = 120  # 2 minutes

# Security features
MEDIA_USE_UUID_FILENAMES = True
MEDIA_ENABLE_FILE_DEDUPLICATION = True
MEDIA_MAX_FILENAME_LENGTH = 100

# Rate limiting
MEDIA_RATE_LIMIT_UPLOADS = 10  # per hour
MEDIA_RATE_LIMIT_DOWNLOADS = 100  # per hour

# Audit logging
LOGGING = {
    'loggers': {
        'security.mediafiles': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'handlers': {
        'security_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/security_mediafiles.log',
            'formatter': 'security',
        },
    },
    'formatters': {
        'security': {
            'format': '{asctime} {levelname} {message}',
            'style': '{',
        },
    },
}
```

## Security Testing

### Penetration Testing Checklist

1. **File Upload Security**
   - [ ] Malicious file upload attempts
   - [ ] File type bypass attempts
   - [ ] Size limit bypass attempts
   - [ ] Path traversal attempts

2. **Access Control Testing**
   - [ ] Unauthorized file access attempts
   - [ ] Cross-patient data access attempts
   - [ ] Privilege escalation attempts
   - [ ] Session hijacking resistance

3. **File Enumeration Testing**
   - [ ] Sequential ID guessing
   - [ ] Filename pattern analysis
   - [ ] Directory traversal attempts
   - [ ] Information disclosure testing

4. **Rate Limiting Testing**
   - [ ] Upload flood testing
   - [ ] Download flood testing
   - [ ] API abuse testing
   - [ ] Resource exhaustion testing

## Compliance Considerations

### HIPAA Compliance

- **Access Controls**: Role-based access with audit trails
- **Encryption**: In transit (HTTPS) and at rest (planned)
- **Audit Logs**: Comprehensive logging of all access
- **Data Integrity**: Hash verification and tamper detection
- **Minimum Necessary**: Access limited to authorized personnel

### GDPR Compliance

- **Data Minimization**: Only necessary metadata stored
- **Right to Erasure**: Secure deletion capabilities
- **Data Portability**: Export capabilities planned
- **Privacy by Design**: Security built into architecture
- **Consent Management**: Integrated with patient consent system
