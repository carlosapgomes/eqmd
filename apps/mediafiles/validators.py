# MediaFiles Validators
# Comprehensive file validation for security and integrity

import os
import re
import mimetypes
from pathlib import Path
from typing import Dict, Any, List

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

try:
    import magic
    PYTHON_MAGIC_AVAILABLE = True
except ImportError:
    PYTHON_MAGIC_AVAILABLE = False

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False


class FileSecurityValidator:
    """Comprehensive file security validation."""
    
    # Known malicious file signatures (magic numbers)
    MALICIOUS_SIGNATURES = [
        b'\x4d\x5a',  # PE executable
        b'\x7f\x45\x4c\x46',  # ELF executable
        b'\xca\xfe\xba\xbe',  # Mach-O executable
        b'\xfe\xed\xfa\xce',  # Mach-O executable (reverse)
        b'\x50\x4b\x03\x04',  # ZIP (could contain executables)
    ]
    
    # Dangerous file extensions
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar',
        '.app', '.deb', '.pkg', '.dmg', '.sh', '.ps1', '.php', '.asp', '.jsp'
    }

    @classmethod
    def validate_file_size(cls, file_obj: UploadedFile, file_type: str) -> None:
        """
        Validate file size against configured limits.
        
        Args:
            file_obj: Django UploadedFile object
            file_type: Type of file ('image' or 'video')
            
        Raises:
            ValidationError: If file size exceeds limits
        """
        if file_type == 'image':
            max_size = getattr(settings, 'MEDIA_IMAGE_MAX_SIZE', 5 * 1024 * 1024)
        elif file_type == 'video':
            max_size = getattr(settings, 'MEDIA_VIDEO_MAX_SIZE', 50 * 1024 * 1024)
        else:
            raise ValidationError("Invalid file type specified")
        
        if file_obj.size > max_size:
            raise ValidationError(
                f"File size ({file_obj.size:,} bytes) exceeds maximum allowed "
                f"({max_size:,} bytes) for {file_type} files"
            )

    @classmethod
    def validate_file_extension(cls, filename: str, file_type: str) -> None:
        """
        Validate file extension against allowed types.
        
        Args:
            filename: Name of the file
            file_type: Type of file ('image' or 'video')
            
        Raises:
            ValidationError: If extension is not allowed
        """
        if not filename:
            raise ValidationError("Filename cannot be empty")
        
        ext = Path(filename).suffix.lower()
        if not ext:
            raise ValidationError("File must have an extension")
        
        # Check against dangerous extensions
        if ext in cls.DANGEROUS_EXTENSIONS:
            raise ValidationError(f"File extension {ext} is not allowed for security reasons")
        
        # Check against allowed extensions
        if file_type == 'image':
            allowed = getattr(settings, 'MEDIA_ALLOWED_IMAGE_EXTENSIONS', ['.jpg', '.jpeg', '.png', '.webp'])
        elif file_type == 'video':
            allowed = getattr(settings, 'MEDIA_ALLOWED_VIDEO_EXTENSIONS', ['.mp4', '.webm', '.mov'])
        else:
            raise ValidationError("Invalid file type specified")
        
        if ext not in allowed:
            raise ValidationError(f"File extension {ext} is not allowed for {file_type} files")

    @classmethod
    def validate_mime_type(cls, file_obj: UploadedFile, file_type: str) -> str:
        """
        Validate MIME type using multiple methods.
        
        Args:
            file_obj: Django UploadedFile object
            file_type: Type of file ('image' or 'video')
            
        Returns:
            Validated MIME type
            
        Raises:
            ValidationError: If MIME type is invalid or dangerous
        """
        # Get MIME type from file content if python-magic is available
        detected_mime = None
        if PYTHON_MAGIC_AVAILABLE:
            try:
                file_obj.seek(0)
                file_header = file_obj.read(1024)
                file_obj.seek(0)
                detected_mime = magic.from_buffer(file_header, mime=True)
            except Exception:
                pass
        
        # Fallback to Django's content_type or mimetypes
        declared_mime = file_obj.content_type
        if not declared_mime:
            declared_mime, _ = mimetypes.guess_type(file_obj.name)
        
        # Use detected MIME type if available, otherwise use declared
        mime_type = detected_mime or declared_mime
        
        if not mime_type:
            raise ValidationError("Could not determine file MIME type")
        
        # Validate against allowed MIME types
        if file_type == 'image':
            allowed = getattr(settings, 'MEDIA_ALLOWED_IMAGE_TYPES', 
                            ['image/jpeg', 'image/png', 'image/webp'])
        elif file_type == 'video':
            allowed = getattr(settings, 'MEDIA_ALLOWED_VIDEO_TYPES', 
                            ['video/mp4', 'video/webm', 'video/quicktime'])
        else:
            raise ValidationError("Invalid file type specified")
        
        if mime_type not in allowed:
            raise ValidationError(f"MIME type {mime_type} is not allowed for {file_type} files")
        
        # Check for MIME type spoofing
        if detected_mime and declared_mime and detected_mime != declared_mime:
            raise ValidationError(
                f"MIME type mismatch: detected {detected_mime}, declared {declared_mime}"
            )
        
        return mime_type

    @classmethod
    def validate_file_content(cls, file_obj: UploadedFile) -> None:
        """
        Validate file content for malicious signatures.
        
        Args:
            file_obj: Django UploadedFile object
            
        Raises:
            ValidationError: If malicious content is detected
        """
        file_obj.seek(0)
        file_header = file_obj.read(1024)
        file_obj.seek(0)
        
        # Check for malicious file signatures
        for signature in cls.MALICIOUS_SIGNATURES:
            if file_header.startswith(signature):
                raise ValidationError("File contains potentially malicious content")
        
        # Check for embedded scripts in file names or content
        dangerous_patterns = [
            rb'<script',
            rb'javascript:',
            rb'vbscript:',
            rb'onload=',
            rb'onerror=',
        ]
        
        for pattern in dangerous_patterns:
            if pattern in file_header.lower():
                raise ValidationError("File contains potentially dangerous script content")

    @classmethod
    def validate_filename_security(cls, filename: str) -> None:
        """
        Validate filename for security issues.
        
        Args:
            filename: Original filename
            
        Raises:
            ValidationError: If filename contains security issues
        """
        if not filename:
            raise ValidationError("Filename cannot be empty")
        
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            raise ValidationError("Filename contains path traversal characters")
        
        # Check for null bytes
        if '\x00' in filename:
            raise ValidationError("Filename contains null bytes")
        
        # Check for control characters
        if any(ord(c) < 32 for c in filename):
            raise ValidationError("Filename contains control characters")
        
        # Check length
        max_length = getattr(settings, 'MEDIA_MAX_FILENAME_LENGTH', 100)
        if len(filename) > max_length:
            raise ValidationError(f"Filename too long (max {max_length} characters)")
        
        # Check for reserved names (Windows)
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
            'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4',
            'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            raise ValidationError(f"Filename '{filename}' uses a reserved system name")


class ImageValidator:
    """Specialized validator for image files."""
    
    @classmethod
    def validate_image_format(cls, file_obj: UploadedFile) -> Dict[str, Any]:
        """
        Validate image format and extract metadata.
        
        Args:
            file_obj: Django UploadedFile object
            
        Returns:
            Dictionary with validation results and metadata
            
        Raises:
            ValidationError: If image is invalid or dangerous
        """
        if not PILLOW_AVAILABLE:
            raise ValidationError("Image validation not available (Pillow not installed)")
        
        try:
            file_obj.seek(0)
            
            # Open and verify image
            with Image.open(file_obj) as img:
                # Verify it's a valid image
                img.verify()
            
            # Reset and get metadata
            file_obj.seek(0)
            with Image.open(file_obj) as img:
                metadata = {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode
                }
                
                # Check for reasonable dimensions
                max_dimension = 10000  # 10k pixels max
                if img.width > max_dimension or img.height > max_dimension:
                    raise ValidationError(
                        f"Image dimensions too large: {img.width}x{img.height} "
                        f"(max {max_dimension}x{max_dimension})"
                    )
                
                # Check for suspicious metadata
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    if exif:
                        # Log EXIF data for review but don't block
                        # In production, you might want to strip EXIF data
                        pass
            
            file_obj.seek(0)
            return metadata
            
        except Exception as e:
            file_obj.seek(0)
            raise ValidationError(f"Invalid image file: {str(e)}")


class VideoValidator:
    """Specialized validator for video files."""
    
    @classmethod
    def validate_video_format(cls, file_obj: UploadedFile) -> Dict[str, Any]:
        """
        Validate video format and extract metadata.
        
        Args:
            file_obj: Django UploadedFile object
            
        Returns:
            Dictionary with validation results and metadata
            
        Raises:
            ValidationError: If video is invalid or exceeds limits
        """
        if not FFMPEG_AVAILABLE:
            # Basic validation without ffmpeg
            return {'basic_validation': True}
        
        import tempfile
        
        # Create temporary file for ffmpeg analysis
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_obj.name).suffix) as temp_file:
            file_obj.seek(0)
            for chunk in file_obj.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        try:
            # Probe video file
            probe = ffmpeg.probe(temp_file_path)
            video_stream = next((stream for stream in probe['streams']
                               if stream['codec_type'] == 'video'), None)
            
            if not video_stream:
                raise ValidationError("No video stream found in file")
            
            duration = float(video_stream.get('duration', 0))
            max_duration = getattr(settings, 'MEDIA_VIDEO_MAX_DURATION', 120)
            
            if duration > max_duration:
                raise ValidationError(
                    f"Video duration ({duration:.1f}s) exceeds maximum allowed ({max_duration}s)"
                )
            
            metadata = {
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'duration': duration,
                'codec': video_stream.get('codec_name'),
                'format': probe.get('format', {}).get('format_name')
            }
            
            file_obj.seek(0)
            return metadata
            
        except Exception as e:
            file_obj.seek(0)
            raise ValidationError(f"Video validation error: {str(e)}")
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass


def validate_media_file(file_obj: UploadedFile, file_type: str) -> Dict[str, Any]:
    """
    Comprehensive media file validation.
    
    Args:
        file_obj: Django UploadedFile object
        file_type: Type of file ('image' or 'video')
        
    Returns:
        Dictionary with validation results and metadata
        
    Raises:
        ValidationError: If file fails any validation checks
    """
    # Security validations
    FileSecurityValidator.validate_filename_security(file_obj.name)
    FileSecurityValidator.validate_file_size(file_obj, file_type)
    FileSecurityValidator.validate_file_extension(file_obj.name, file_type)
    mime_type = FileSecurityValidator.validate_mime_type(file_obj, file_type)
    FileSecurityValidator.validate_file_content(file_obj)
    
    # Format-specific validations
    metadata = {'mime_type': mime_type}
    
    if file_type == 'image':
        image_metadata = ImageValidator.validate_image_format(file_obj)
        metadata.update(image_metadata)
    elif file_type == 'video':
        video_metadata = VideoValidator.validate_video_format(file_obj)
        metadata.update(video_metadata)
    
    return {
        'is_valid': True,
        'metadata': metadata,
        'mime_type': mime_type
    }
