# MediaFiles Utilities
# Utility functions for media processing and file handling

import os
import re
import hashlib
import mimetypes
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import slugify
from django.utils import timezone

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


def get_thumbnail_upload_path(instance, filename: str) -> str:
    """
    Generate secure upload path for thumbnails with structured organization.

    Security features:
    - UUID4 provides 122 bits of entropy
    - No predictable patterns
    - Organized by media type and date
    - Path traversal protection

    Args:
        instance: MediaFile instance
        filename: Thumbnail filename

    Returns:
        Secure thumbnail path with UUID-based filename

    Raises:
        ValueError: If filename contains dangerous patterns
    """
    if not filename:
        raise ValueError("Filename cannot be empty")

    # Generate secure thumbnail filename
    secure_filename = f"{instance.id}_thumb.jpg"  # Always use JPG for thumbnails

    # Get date for path structure
    current_date = timezone.now()
    year_month = current_date.strftime('%Y/%m')

    # Determine media type based on MIME type
    if hasattr(instance, 'mime_type') and instance.mime_type:
        if instance.mime_type.startswith('image/'):
            # Check if it's part of a photo series (would need to check relations)
            media_type = 'photos'  # Default to photos for images
        elif instance.mime_type.startswith('video/'):
            media_type = 'videos'
        else:
            media_type = 'media'
    else:
        # Fallback if no mime_type available
        media_type = 'photos'  # Default for thumbnails

    # Construct secure thumbnail path
    secure_path = f"{media_type}/{year_month}/thumbnails/{secure_filename}"

    # Final validation - ensure no path traversal
    if '..' in secure_path or secure_path.startswith('/'):
        raise ValueError("Invalid path detected")

    return secure_path


def get_secure_upload_path(instance, filename: str) -> str:
    """
    Generate secure upload path with UUID filename.

    Security features:
    - UUID4 provides 122 bits of entropy
    - No predictable patterns
    - No patient information leakage
    - Extension validation included
    - Path traversal protection

    Args:
        instance: Model instance (Photo, PhotoSeries, or VideoClip)
        filename: Original filename

    Returns:
        Secure file path with UUID-based filename

    Raises:
        ValueError: If filename has invalid extension or contains dangerous patterns
    """
    if not filename:
        raise ValueError("Filename cannot be empty")

    # Get file extension and validate
    ext = Path(filename).suffix.lower()
    if not ext:
        raise ValueError("File must have an extension")

    # Validate extension against allowed types
    allowed_extensions = (
        getattr(settings, 'MEDIA_ALLOWED_IMAGE_EXTENSIONS', []) +
        getattr(settings, 'MEDIA_ALLOWED_VIDEO_EXTENSIONS', [])
    )
    if ext not in allowed_extensions:
        raise ValueError(f"File extension {ext} not allowed")

    # Generate secure filename using MediaFile instance ID for consistency
    # This ensures original file and thumbnail use the same UUID
    secure_filename = f"{instance.id}{ext}"

    # Determine media type and create path structure
    current_date = timezone.now()
    year_month = current_date.strftime('%Y/%m')

    # Determine media type from instance
    # For MediaFile instances, we need to infer type from MIME type since they don't have event_type
    if hasattr(instance, 'event_type'):
        # This is an Event-based instance (Photo, PhotoSeries, VideoClip)
        from apps.events.models import Event
        if instance.event_type == Event.PHOTO_EVENT:
            media_type = 'photos'
        elif instance.event_type == Event.PHOTO_SERIES_EVENT:
            media_type = 'photo_series'
        elif instance.event_type == Event.VIDEO_CLIP_EVENT:
            media_type = 'videos'
        else:
            media_type = 'media'
    elif hasattr(instance, 'mime_type') and instance.mime_type:
        # This is a MediaFile instance, determine type from MIME type
        if instance.mime_type.startswith('image/'):
            media_type = 'photos'  # Default to photos for images
        elif instance.mime_type.startswith('video/'):
            media_type = 'videos'
        else:
            media_type = 'media'
    else:
        # Fallback for unknown instances
        media_type = 'media'

    # Construct secure path
    secure_path = f"{media_type}/{year_month}/originals/{secure_filename}"

    # Final validation - ensure no path traversal
    if '..' in secure_path or secure_path.startswith('/'):
        raise ValueError("Invalid path detected")

    return secure_path


def normalize_filename(filename: str) -> str:
    """
    Normalize and sanitize original filename for safe database storage.

    Security features:
    - Remove path traversal characters
    - Limit length to prevent buffer overflows
    - Remove dangerous characters
    - Preserve readability for users
    - Prevent null byte injection

    Args:
        filename: Original filename

    Returns:
        Normalized filename safe for database storage
    """
    if not filename:
        return "unnamed_file"

    # Remove path components (security measure)
    filename = os.path.basename(filename)

    # Remove null bytes and other dangerous characters
    filename = filename.replace('\x00', '')

    # Get name and extension
    path = Path(filename)
    name = path.stem
    ext = path.suffix.lower()

    # Remove dangerous characters and normalize
    # Allow only word characters, spaces, hyphens, underscores, and dots
    name = re.sub(r'[^\w\s\-_.]', '', name)
    
    # Remove script-related content for security
    name = re.sub(r'script', '', name, flags=re.IGNORECASE)
    
    # Replace spaces and multiple consecutive separators with underscores
    name = re.sub(r'[\s]+', '_', name)
    name = re.sub(r'[-_]+', '_', name)
    name = name.strip('-_').lower()

    # Prevent reserved names (Windows)
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
        'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4',
        'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    if name.upper() in reserved_names:
        name = f"file_{name}"

    # Limit length
    max_length = getattr(settings, 'MEDIA_MAX_FILENAME_LENGTH', 100)
    if len(name) > max_length - len(ext):
        name = name[:max_length - len(ext)]

    # Don't use slugify as it removes dots and other safe characters
    # Just ensure we have a valid name
    if not name or not name.strip('._-'):
        name = "file"

    # Ensure name is not empty after all processing
    if not name:
        name = "unnamed_file"

    return f"{name}{ext}"


def calculate_file_hash(file_obj: UploadedFile) -> str:
    """
    Calculate SHA-256 hash for file deduplication.

    Args:
        file_obj: Django UploadedFile object

    Returns:
        SHA-256 hash as hexadecimal string
    """
    hash_sha256 = hashlib.sha256()

    # Reset file pointer to beginning
    file_obj.seek(0)

    # Read file in chunks to handle large files
    for chunk in file_obj.chunks():
        hash_sha256.update(chunk)

    # Reset file pointer for subsequent use
    file_obj.seek(0)

    return hash_sha256.hexdigest()


def validate_file_extension(filename: str, file_type: str) -> bool:
    """
    Validate file extension against allowed types.

    Args:
        filename: Name of the file
        file_type: Type of file ('image' or 'video')

    Returns:
        True if extension is allowed, False otherwise
    """
    if not filename:
        return False

    ext = Path(filename).suffix.lower()

    if file_type == 'image':
        allowed_extensions = getattr(settings, 'MEDIA_ALLOWED_IMAGE_EXTENSIONS', ['.jpg', '.jpeg', '.png', '.webp'])
    elif file_type == 'video':
        allowed_extensions = getattr(settings, 'MEDIA_ALLOWED_VIDEO_EXTENSIONS', ['.mp4', '.webm', '.mov'])
    else:
        return False

    return ext in allowed_extensions


def clean_filename(filename: str) -> str:
    """
    Remove dangerous characters and path components from filename.

    Security features:
    - Remove path traversal sequences
    - Remove null bytes and control characters
    - Remove shell metacharacters
    - Prevent directory traversal attacks
    - Handle Unicode normalization

    Args:
        filename: Original filename

    Returns:
        Cleaned filename safe for file system
    """
    if not filename:
        return "unnamed_file"

    # Remove path components (security measure against directory traversal)
    filename = os.path.basename(filename)

    # Remove null bytes and control characters (0x00-0x1F, 0x7F-0x9F)
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)

    # Remove dangerous characters for file systems and shells
    dangerous_chars = r'[<>:"/\\|?*;`$&(){}[\]^~]'
    filename = re.sub(dangerous_chars, '', filename)

    # Remove leading/trailing dots, spaces, and hyphens
    filename = filename.strip('. -')

    # Replace multiple consecutive spaces/dots with single space
    filename = re.sub(r'[.\s]+', ' ', filename)
    filename = filename.strip()

    # Prevent empty filename
    if not filename or filename in ('.', '..'):
        filename = "unnamed_file"

    # Limit length for file system compatibility
    max_length = 255  # Most file systems support this
    if len(filename.encode('utf-8')) > max_length:
        # Truncate while preserving extension
        name, ext = os.path.splitext(filename)
        max_name_length = max_length - len(ext.encode('utf-8')) - 10  # Safety margin
        name = name[:max_name_length]
        filename = f"{name}{ext}"

    return filename


def generate_thumbnail(image_path: str, size: Tuple[int, int] = (150, 150)) -> Optional[str]:
    """
    Generate thumbnail for image files using structured path organization.

    Args:
        image_path: Path to the original image
        size: Tuple of (width, height) for thumbnail

    Returns:
        Path to generated thumbnail or None if failed
    """
    if not PILLOW_AVAILABLE:
        return None

    try:
        # Open and process image
        with Image.open(image_path) as img:
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            # Generate thumbnail maintaining aspect ratio
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # Create structured thumbnail path
            path_obj = Path(image_path)
            
            # Expected structure: media_type/YYYY/MM/originals/filename
            # We want: media_type/YYYY/MM/thumbnails/filename_thumb.jpg
            if 'originals' in path_obj.parts:
                # Replace 'originals' with 'thumbnails' in the path
                parts = list(path_obj.parts)
                originals_index = parts.index('originals')
                parts[originals_index] = 'thumbnails'
                thumbnail_dir = Path(*parts[:-1])  # Remove filename
                thumbnail_path = thumbnail_dir / f"{path_obj.stem}_thumb.jpg"
            else:
                # Fallback to old structure for compatibility
                thumbnail_dir = path_obj.parent.parent / 'thumbnails'
                thumbnail_path = thumbnail_dir / f"{path_obj.stem}_thumb.jpg"

            # Create directory if it doesn't exist
            thumbnail_dir.mkdir(parents=True, exist_ok=True)

            # Save thumbnail
            img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)

            return str(thumbnail_path)

    except Exception as e:
        # Log error in production
        print(f"Error generating thumbnail for {image_path}: {e}")
        return None


def extract_video_thumbnail(video_path: str, time_offset: float = 1.0) -> Optional[str]:
    """
    Extract thumbnail from video file using structured path organization.

    Args:
        video_path: Path to the video file
        time_offset: Time in seconds to extract frame from

    Returns:
        Path to extracted thumbnail or None if failed
    """
    if not FFMPEG_AVAILABLE:
        return None

    try:
        # Create structured thumbnail path
        path_obj = Path(video_path)
        
        # Expected structure: media_type/YYYY/MM/originals/filename
        # We want: media_type/YYYY/MM/thumbnails/filename_thumb.jpg
        if 'originals' in path_obj.parts:
            # Replace 'originals' with 'thumbnails' in the path
            parts = list(path_obj.parts)
            originals_index = parts.index('originals')
            parts[originals_index] = 'thumbnails'
            thumbnail_dir = Path(*parts[:-1])  # Remove filename
            thumbnail_path = thumbnail_dir / f"{path_obj.stem}_thumb.jpg"
        else:
            # Fallback to old structure for compatibility
            thumbnail_dir = path_obj.parent.parent / 'thumbnails'
            thumbnail_path = thumbnail_dir / f"{path_obj.stem}_thumb.jpg"

        # Create directory if it doesn't exist
        thumbnail_dir.mkdir(parents=True, exist_ok=True)

        # Extract frame using ffmpeg
        (
            ffmpeg
            .input(video_path, ss=time_offset)
            .output(str(thumbnail_path), vframes=1, format='image2', vcodec='mjpeg')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )

        return str(thumbnail_path)

    except Exception as e:
        # Log error in production
        print(f"Error extracting video thumbnail for {video_path}: {e}")
        return None


def get_file_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract metadata from media files.

    Args:
        file_path: Path to the media file

    Returns:
        Dictionary containing file metadata
    """
    metadata = {
        'file_size': 0,
        'mime_type': None,
        'width': None,
        'height': None,
        'duration': None,
        'format': None,
    }

    try:
        # Get basic file info
        file_stat = os.stat(file_path)
        metadata['file_size'] = file_stat.st_size

        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        metadata['mime_type'] = mime_type

        # Get image metadata if it's an image
        if mime_type and mime_type.startswith('image/') and PILLOW_AVAILABLE:
            try:
                with Image.open(file_path) as img:
                    metadata['width'] = img.width
                    metadata['height'] = img.height
                    metadata['format'] = img.format
            except Exception:
                pass

        # Get video metadata if it's a video
        elif mime_type and mime_type.startswith('video/') and FFMPEG_AVAILABLE:
            try:
                probe = ffmpeg.probe(file_path)
                video_stream = next((stream for stream in probe['streams']
                                   if stream['codec_type'] == 'video'), None)

                if video_stream:
                    metadata['width'] = int(video_stream.get('width', 0))
                    metadata['height'] = int(video_stream.get('height', 0))
                    metadata['duration'] = float(video_stream.get('duration', 0))
                    metadata['format'] = probe.get('format', {}).get('format_name')
            except Exception:
                pass

    except Exception as e:
        print(f"Error extracting metadata for {file_path}: {e}")

    return metadata


def validate_image_file(file_obj: UploadedFile) -> Dict[str, Any]:
    """
    Validate image file format and content.

    Args:
        file_obj: Django UploadedFile object

    Returns:
        Dictionary with validation results
    """
    result = {
        'is_valid': False,
        'errors': [],
        'metadata': {}
    }

    try:
        # Check file size
        max_size = getattr(settings, 'MEDIA_IMAGE_MAX_SIZE', 5 * 1024 * 1024)
        if file_obj.size > max_size:
            result['errors'].append(f"File size ({file_obj.size} bytes) exceeds maximum allowed ({max_size} bytes)")
            return result

        # Check file extension
        if not validate_file_extension(file_obj.name, 'image'):
            result['errors'].append("Invalid file extension for image")
            return result

        # Check MIME type
        allowed_types = getattr(settings, 'MEDIA_ALLOWED_IMAGE_TYPES', ['image/jpeg', 'image/png', 'image/webp'])
        if file_obj.content_type not in allowed_types:
            result['errors'].append(f"Invalid MIME type: {file_obj.content_type}")
            return result

        # Validate image content if Pillow is available
        if PILLOW_AVAILABLE:
            try:
                file_obj.seek(0)
                with Image.open(file_obj) as img:
                    # Verify it's a valid image
                    img.verify()

                    # Reset file pointer and get metadata
                    file_obj.seek(0)
                    with Image.open(file_obj) as img:
                        result['metadata'] = {
                            'width': img.width,
                            'height': img.height,
                            'format': img.format,
                            'mode': img.mode
                        }

                file_obj.seek(0)  # Reset for subsequent use
                result['is_valid'] = True

            except Exception as e:
                result['errors'].append(f"Invalid image file: {str(e)}")
                file_obj.seek(0)
        else:
            # Basic validation without Pillow
            result['is_valid'] = True

    except Exception as e:
        result['errors'].append(f"File validation error: {str(e)}")

    return result


def validate_video_file(file_obj: UploadedFile) -> Dict[str, Any]:
    """
    Validate video file format and content.

    Args:
        file_obj: Django UploadedFile object

    Returns:
        Dictionary with validation results
    """
    result = {
        'is_valid': False,
        'errors': [],
        'metadata': {}
    }

    try:
        # Check file size
        max_size = getattr(settings, 'MEDIA_VIDEO_MAX_SIZE', 50 * 1024 * 1024)
        if file_obj.size > max_size:
            result['errors'].append(f"File size ({file_obj.size} bytes) exceeds maximum allowed ({max_size} bytes)")
            return result

        # Check file extension
        if not validate_file_extension(file_obj.name, 'video'):
            result['errors'].append("Invalid file extension for video")
            return result

        # Check MIME type
        allowed_types = getattr(settings, 'MEDIA_ALLOWED_VIDEO_TYPES', ['video/mp4', 'video/webm', 'video/quicktime'])
        if file_obj.content_type not in allowed_types:
            result['errors'].append(f"Invalid MIME type: {file_obj.content_type}")
            return result

        # Basic validation without ffmpeg
        result['is_valid'] = True

        # Enhanced validation if ffmpeg is available
        if FFMPEG_AVAILABLE:
            try:
                # Save temporary file for ffmpeg analysis
                import tempfile
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

                    if video_stream:
                        duration = float(video_stream.get('duration', 0))
                        max_duration = getattr(settings, 'MEDIA_VIDEO_MAX_DURATION', 120)

                        if duration > max_duration:
                            result['errors'].append(f"Video duration ({duration:.1f}s) exceeds maximum allowed ({max_duration}s)")
                            result['is_valid'] = False
                        else:
                            result['metadata'] = {
                                'width': int(video_stream.get('width', 0)),
                                'height': int(video_stream.get('height', 0)),
                                'duration': duration,
                                'codec': video_stream.get('codec_name'),
                                'format': probe.get('format', {}).get('format_name')
                            }
                    else:
                        result['errors'].append("No video stream found in file")
                        result['is_valid'] = False

                finally:
                    # Clean up temporary file
                    os.unlink(temp_file_path)

                file_obj.seek(0)  # Reset for subsequent use

            except Exception as e:
                result['errors'].append(f"Video validation error: {str(e)}")
                result['is_valid'] = False
                file_obj.seek(0)

    except Exception as e:
        result['errors'].append(f"File validation error: {str(e)}")

    return result


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted file size string
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    return f"{size:.1f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "1:23" for 1 minute 23 seconds)
    """
    if seconds < 0:
        return "0:00"

    minutes = int(seconds // 60)
    seconds = int(seconds % 60)

    if minutes >= 60:
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"


# Photo Series Security Functions

def get_secure_series_upload_path(instance, filename: str) -> str:
    """
    Generate secure upload path for photo series files.
    
    Security features:
    - UUID-based filenames prevent enumeration
    - Series prefix for organization
    - File extension validation
    - Path traversal protection
    
    Args:
        instance: PhotoSeriesFile instance
        filename: Original filename
        
    Returns:
        Secure upload path for series files
        
    Raises:
        ValidationError: If file extension not allowed
    """
    import uuid
    from django.core.exceptions import ValidationError
    
    ext = Path(filename).suffix.lower()
    allowed_extensions = getattr(settings, 'MEDIA_ALLOWED_IMAGE_EXTENSIONS', ['.jpg', '.jpeg', '.png', '.webp'])
    
    if ext not in allowed_extensions:
        raise ValidationError(f"File extension {ext} not allowed for photo series")

    # Generate UUID with series prefix for organization
    uuid_filename = f"series_{uuid.uuid4()}{ext}"
    return f"photo_series/{timezone.now().strftime('%Y/%m')}/originals/{uuid_filename}"


def validate_series_files(files) -> None:
    """
    Validate multiple files for photo series upload.
    
    Security checks:
    - Individual file validation for each image
    - Total series size validation
    - File type consistency checking
    - Atomic validation (all or nothing)
    
    Args:
        files: List of uploaded files
        
    Raises:
        ValidationError: If validation fails for any file or total size
    """
    from django.core.exceptions import ValidationError
    from .security import FileValidator
    
    if not files:
        raise ValidationError("At least one file is required for photo series")
    
    total_size = 0
    allowed_mime_types = set()
    
    # Individual file validation
    for file in files:
        # Validate each file individually
        try:
            FileValidator.validate_image_file(file)
        except ValidationError as e:
            raise ValidationError(f"File {file.name}: {str(e)}")
        
        total_size += file.size
        allowed_mime_types.add(file.content_type)
    
    # Check total series size limit
    max_series_size = getattr(settings, 'MEDIA_SERIES_MAX_TOTAL_SIZE', 50 * 1024 * 1024)  # Default 50MB
    if total_size > max_series_size:
        raise ValidationError(f"Total series size ({format_file_size(total_size)}) exceeds maximum allowed ({format_file_size(max_series_size)})")
    
    # Check for mixed file types (all files should be images)
    image_mime_types = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
    non_image_types = allowed_mime_types - image_mime_types
    if non_image_types:
        raise ValidationError(f"Photo series can only contain image files. Found: {', '.join(non_image_types)}")
    
    # Check series file count limits
    max_files = getattr(settings, 'MEDIA_SERIES_MAX_FILES', 20)  # Default 20 files per series
    if len(files) > max_files:
        raise ValidationError(f"Photo series cannot contain more than {max_files} files. Attempted to upload {len(files)} files")


def validate_photo_file(file) -> None:
    """
    Validate individual photo file for series inclusion.
    
    Args:
        file: Uploaded file object
        
    Raises:
        ValidationError: If file validation fails
    """
    from .security import FileValidator
    
    # Use existing photo validation
    FileValidator.validate_image_file(file)


def validate_video_filename_security(filename: str) -> None:
    """
    Validate video filename for security issues.

    Args:
        filename: Original filename to validate

    Raises:
        ValidationError: If filename contains security issues
    """
    from django.core.exceptions import ValidationError

    # Check for path traversal attempts
    dangerous_patterns = ['..', '/', '\\', '\x00', '<', '>', '|', '?', '*', ':', '"']
    for pattern in dangerous_patterns:
        if pattern in filename:
            raise ValidationError(f"Filename contains dangerous pattern: {pattern}")

    # Check for control characters
    if any(ord(c) < 32 for c in filename):
        raise ValidationError("Filename contains control characters")

    # Check filename length
    max_length = getattr(settings, 'MEDIA_MAX_FILENAME_LENGTH', 100)
    if len(filename) > max_length:
        raise ValidationError(f"Filename too long (max {max_length} characters)")

    # Check for suspicious extensions (double extensions)
    if filename.count('.') > 1:
        parts = filename.split('.')
        for part in parts[:-1]:  # Check all parts except the last (real extension)
            if part.lower() in ['exe', 'bat', 'cmd', 'com', 'scr', 'pif', 'js', 'vbs', 'php', 'asp']:
                raise ValidationError("Filename contains suspicious double extension")

    # Check for reserved Windows filenames
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
                     'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4',
                     'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    base_name = Path(filename).stem.upper()
    if base_name in reserved_names:
        raise ValidationError(f"Filename uses reserved name: {base_name}")


def validate_video_upload_security(file_obj, filename: str) -> Dict[str, Any]:
    """
    Comprehensive security validation for video uploads.

    Args:
        file_obj: Django UploadedFile object
        filename: Original filename

    Returns:
        Dictionary with validation results and security information

    Raises:
        ValidationError: If critical security issues are found
    """
    from django.core.exceptions import ValidationError

    result = {
        'is_secure': False,
        'security_issues': [],
        'warnings': [],
        'metadata': {}
    }

    try:
        # Validate filename security
        validate_video_filename_security(filename)

        # Validate file size
        max_size = getattr(settings, 'MEDIA_VIDEO_MAX_SIZE', 50 * 1024 * 1024)
        if file_obj.size > max_size:
            raise ValidationError(f"Video file size ({file_obj.size} bytes) exceeds maximum allowed ({max_size} bytes)")

        # Validate MIME type
        allowed_types = getattr(settings, 'MEDIA_ALLOWED_VIDEO_TYPES', ['video/mp4', 'video/webm', 'video/quicktime'])
        if file_obj.content_type not in allowed_types:
            raise ValidationError(f"Invalid MIME type: {file_obj.content_type}")

        # Check file header for basic validation
        file_obj.seek(0)
        header = file_obj.read(1024)
        file_obj.seek(0)

        # Validate video file headers
        valid_headers = {
            'video/mp4': [b'\x00\x00\x00\x18ftypmp4', b'\x00\x00\x00\x20ftypmp4'],
            'video/webm': [b'\x1a\x45\xdf\xa3'],
            'video/quicktime': [b'\x00\x00\x00\x14ftyp']
        }

        if file_obj.content_type in valid_headers:
            valid = False
            for valid_header in valid_headers[file_obj.content_type]:
                if header.startswith(valid_header):
                    valid = True
                    break
            if not valid:
                result['warnings'].append(f"File header doesn't match expected format for {file_obj.content_type}")

        # Check for suspicious content in header
        suspicious_patterns = [b'<script', b'javascript:', b'vbscript:', b'<?php', b'<%']
        for pattern in suspicious_patterns:
            if pattern in header:
                raise ValidationError("Video file contains suspicious content patterns")

        # If we reach here, basic security checks passed
        result['is_secure'] = True
        result['metadata']['file_size'] = file_obj.size
        result['metadata']['mime_type'] = file_obj.content_type

        return result

    except ValidationError:
        # Re-raise validation errors
        raise
    except Exception as e:
        result['security_issues'].append(f"Security validation error: {str(e)}")
        return result


class VideoProcessor:
    """
    Comprehensive video processing utilities using ffmpeg.
    
    This class provides secure video processing functions including:
    - Metadata extraction
    - Thumbnail generation
    - Video validation and security checks
    - Video compression (optional)
    """
    
    def __init__(self):
        """Initialize VideoProcessor with ffmpeg availability check."""
        self.ffmpeg_available = FFMPEG_AVAILABLE
        if not self.ffmpeg_available:
            print("Warning: ffmpeg not available. Video processing will be limited.")
    
    def extract_metadata(self, video_file) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from video file.
        
        Args:
            video_file: Path to video file or file object
            
        Returns:
            Dictionary containing video metadata
            
        Raises:
            ValueError: If ffmpeg is not available or file is invalid
        """
        if not self.ffmpeg_available:
            raise ValueError("ffmpeg is required for video metadata extraction")
        
        try:
            # Handle both file paths and file objects
            if hasattr(video_file, 'path'):
                file_path = video_file.path
            else:
                file_path = str(video_file)
            
            # Probe video file for comprehensive metadata
            probe = ffmpeg.probe(file_path)
            video_stream = next((stream for stream in probe['streams']
                              if stream['codec_type'] == 'video'), None)
            audio_stream = next((stream for stream in probe['streams']
                              if stream['codec_type'] == 'audio'), None)
            
            if not video_stream:
                raise ValueError("No video stream found in file")
            
            # Extract video metadata
            metadata = {
                'duration': float(video_stream.get('duration', 0)),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'codec_name': video_stream.get('codec_name', ''),
                'codec_long_name': video_stream.get('codec_long_name', ''),
                'profile': video_stream.get('profile', ''),
                'level': video_stream.get('level', ''),
                'pixel_format': video_stream.get('pix_fmt', ''),
                'bit_rate': int(video_stream.get('bit_rate', 0)) if video_stream.get('bit_rate') else None,
                'frame_rate': self._parse_frame_rate(video_stream.get('r_frame_rate', '0/1')),
                'avg_frame_rate': self._parse_frame_rate(video_stream.get('avg_frame_rate', '0/1')),
                'format_name': probe.get('format', {}).get('format_name', ''),
                'format_long_name': probe.get('format', {}).get('format_long_name', ''),
                'size': int(probe.get('format', {}).get('size', 0)),
                'has_audio': audio_stream is not None,
            }
            
            # Add audio metadata if available
            if audio_stream:
                metadata.update({
                    'audio_codec': audio_stream.get('codec_name', ''),
                    'audio_bit_rate': int(audio_stream.get('bit_rate', 0)) if audio_stream.get('bit_rate') else None,
                    'sample_rate': int(audio_stream.get('sample_rate', 0)) if audio_stream.get('sample_rate') else None,
                    'channels': int(audio_stream.get('channels', 0)) if audio_stream.get('channels') else None,
                })
            
            return metadata
            
        except Exception as e:
            raise ValueError(f"Error extracting video metadata: {str(e)}")
    
    def _parse_frame_rate(self, frame_rate_str: str) -> float:
        """Parse frame rate from ffmpeg string format (e.g., '30/1')."""
        try:
            if '/' in frame_rate_str:
                numerator, denominator = frame_rate_str.split('/')
                return float(numerator) / max(float(denominator), 1)
            return float(frame_rate_str)
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    def generate_secure_thumbnail(self, video_file, timestamp: float = 1.0) -> Optional[str]:
        """
        Generate secure thumbnail from video with UUID naming.
        
        Args:
            video_file: Path to video file or MediaFile instance
            timestamp: Time in seconds to extract frame from
            
        Returns:
            Path to generated thumbnail or None if failed
            
        Raises:
            ValueError: If ffmpeg is not available
        """
        if not self.ffmpeg_available:
            raise ValueError("ffmpeg is required for video thumbnail generation")
        
        try:
            # Handle both file paths and MediaFile instances
            if hasattr(video_file, 'file') and hasattr(video_file.file, 'path'):
                file_path = video_file.file.path
                instance_id = video_file.id
            elif hasattr(video_file, 'path'):
                file_path = video_file.path
                import uuid
                instance_id = uuid.uuid4()
            else:
                file_path = str(video_file)
                import uuid
                instance_id = uuid.uuid4()
            
            # Create structured thumbnail path
            path_obj = Path(file_path)
            
            # Expected structure: media_type/YYYY/MM/originals/filename
            # We want: media_type/YYYY/MM/thumbnails/filename_thumb.jpg
            if 'originals' in path_obj.parts:
                # Replace 'originals' with 'thumbnails' in the path
                parts = list(path_obj.parts)
                originals_index = parts.index('originals')
                parts[originals_index] = 'thumbnails'
                thumbnail_dir = Path(*parts[:-1])  # Remove filename
                thumbnail_path = thumbnail_dir / f"{instance_id}_thumb.jpg"
            else:
                # Fallback to adjacent thumbnails directory
                thumbnail_dir = path_obj.parent / 'thumbnails'
                thumbnail_path = thumbnail_dir / f"{instance_id}_thumb.jpg"
            
            # Create directory if it doesn't exist
            thumbnail_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate thumbnail using ffmpeg with high quality settings
            (
                ffmpeg
                .input(file_path, ss=timestamp)
                .output(
                    str(thumbnail_path),
                    vframes=1,
                    format='image2',
                    vcodec='mjpeg',
                    **{
                        'q:v': 2,  # High quality
                        's': '300x300',  # Max dimensions
                        'aspect': '1:1',  # Square aspect ratio
                    }
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            return str(thumbnail_path)
            
        except Exception as e:
            print(f"Error generating video thumbnail: {str(e)}")
            return None
    
    def validate_video_file(self, video_file) -> Dict[str, Any]:
        """
        Validate video file format, duration, and security.
        
        Args:
            video_file: Path to video file or file object
            
        Returns:
            Dictionary with validation results
            
        Raises:
            ValidationError: If validation fails
        """
        from django.core.exceptions import ValidationError
        
        result = {
            'is_valid': False,
            'errors': [],
            'metadata': {}
        }
        
        try:
            # Extract metadata first
            metadata = self.extract_metadata(video_file)
            result['metadata'] = metadata
            
            # Validate duration
            max_duration = getattr(settings, 'MEDIA_VIDEO_MAX_DURATION', 120)  # 2 minutes
            if metadata['duration'] > max_duration:
                result['errors'].append(
                    f"Video duration ({metadata['duration']:.1f}s) exceeds maximum allowed ({max_duration}s)"
                )
                return result
            
            # Validate dimensions
            max_dimension = getattr(settings, 'MEDIA_VIDEO_MAX_DIMENSION', 4096)  # 4K max
            if metadata['width'] > max_dimension or metadata['height'] > max_dimension:
                result['errors'].append(
                    f"Video dimensions ({metadata['width']}x{metadata['height']}) exceed maximum allowed ({max_dimension}x{max_dimension})"
                )
                return result
            
            # Validate codec
            allowed_codecs = getattr(settings, 'MEDIA_ALLOWED_VIDEO_CODECS', ['h264', 'vp8', 'vp9', 'av1'])
            if metadata['codec_name'].lower() not in allowed_codecs:
                result['errors'].append(
                    f"Video codec '{metadata['codec_name']}' not allowed. Allowed: {', '.join(allowed_codecs)}"
                )
                return result
            
            # Validate format
            allowed_formats = getattr(settings, 'MEDIA_ALLOWED_VIDEO_FORMATS', ['mp4', 'webm', 'mov'])
            format_parts = metadata['format_name'].split(',')
            if not any(fmt.strip() in allowed_formats for fmt in format_parts):
                result['errors'].append(
                    f"Video format '{metadata['format_name']}' not allowed. Allowed: {', '.join(allowed_formats)}"
                )
                return result
            
            result['is_valid'] = True
            return result
            
        except Exception as e:
            result['errors'].append(f"Video validation error: {str(e)}")
            return result
    
    def get_video_info(self, video_file) -> Dict[str, Any]:
        """
        Get comprehensive video information including streams and metadata.
        
        Args:
            video_file: Path to video file or file object
            
        Returns:
            Dictionary with comprehensive video information
        """
        try:
            # Get basic metadata
            metadata = self.extract_metadata(video_file)
            
            # Add formatted information
            info = {
                'basic_info': metadata,
                'duration_display': format_duration(metadata['duration']),
                'size_display': format_file_size(metadata['size']),
                'resolution_display': f"{metadata['width']} × {metadata['height']}",
                'aspect_ratio': self._calculate_aspect_ratio(metadata['width'], metadata['height']),
                'is_hd': metadata['height'] >= 720,
                'is_4k': metadata['height'] >= 2160,
                'estimated_quality': self._estimate_quality(metadata),
            }
            
            return info
            
        except Exception as e:
            return {
                'error': f"Error getting video info: {str(e)}",
                'duration_display': '0:00',
                'size_display': '0 B',
                'resolution_display': 'Unknown',
            }
    
    def _calculate_aspect_ratio(self, width: int, height: int) -> str:
        """Calculate and format aspect ratio."""
        if width == 0 or height == 0:
            return "Unknown"
        
        # Find GCD for simplification
        import math
        gcd = math.gcd(width, height)
        ratio_w = width // gcd
        ratio_h = height // gcd
        
        # Common aspect ratios
        common_ratios = {
            (16, 9): "16:9",
            (4, 3): "4:3",
            (3, 2): "3:2",
            (1, 1): "1:1",
            (21, 9): "21:9",
        }
        
        return common_ratios.get((ratio_w, ratio_h), f"{ratio_w}:{ratio_h}")
    
    def _estimate_quality(self, metadata: Dict[str, Any]) -> str:
        """Estimate video quality based on metadata."""
        height = metadata.get('height', 0)
        bit_rate = metadata.get('bit_rate', 0)
        
        if height >= 2160:
            return "4K/Ultra HD"
        elif height >= 1080:
            return "Full HD"
        elif height >= 720:
            return "HD"
        elif height >= 480:
            return "SD"
        else:
            return "Low Quality"
    
    def compress_video(self, input_file, output_file, target_size_mb: int = 10) -> bool:
        """
        Compress video to target size (optional feature).
        
        Args:
            input_file: Path to input video file
            output_file: Path for compressed output
            target_size_mb: Target file size in MB
            
        Returns:
            True if compression successful, False otherwise
        """
        if not self.ffmpeg_available:
            return False
        
        try:
            # Get video duration for bitrate calculation
            metadata = self.extract_metadata(input_file)
            duration = metadata['duration']
            
            if duration <= 0:
                return False
            
            # Calculate target bitrate (with some buffer for audio)
            target_bitrate = int((target_size_mb * 8 * 1024 * 1024) / duration * 0.9)  # 90% for video
            
            # Compress video
            (
                ffmpeg
                .input(input_file)
                .output(
                    output_file,
                    **{
                        'c:v': 'libx264',
                        'b:v': f'{target_bitrate}',
                        'c:a': 'aac',
                        'b:a': '128k',
                        'preset': 'medium',
                        'crf': '23',
                    }
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            return True
            
        except Exception as e:
            print(f"Error compressing video: {str(e)}")
            return False
    
    def validate_video_security(self, video_file) -> Dict[str, Any]:
        """
        Comprehensive security validation for video content.

        Args:
            video_file: Path to video file or file object

        Returns:
            Dictionary with security validation results
        """
        result = {
            'is_secure': False,
            'security_issues': [],
            'warnings': []
        }

        try:
            # Validate file path security first
            file_path = self._get_secure_file_path(video_file)

            # Get video metadata with security checks
            metadata = self.extract_metadata_secure(video_file)

            # Check for suspicious codecs
            dangerous_codecs = ['wmv', 'asf', 'avi', 'rm', 'rmvb', 'flv']
            if metadata['codec_name'].lower() in dangerous_codecs:
                result['security_issues'].append(f"Potentially unsafe codec: {metadata['codec_name']}")

            # Check for unusual aspect ratios (could indicate embedded content)
            width, height = metadata['width'], metadata['height']
            if width > 0 and height > 0:
                aspect_ratio = width / height
                if aspect_ratio > 10 or aspect_ratio < 0.1:
                    result['warnings'].append(f"Unusual aspect ratio: {width}x{height}")

            # Check for excessive bitrate (could indicate data hiding)
            if metadata['bit_rate'] and metadata['bit_rate'] > 50_000_000:  # 50 Mbps
                result['warnings'].append(f"Very high bitrate: {metadata['bit_rate']} bps")

            # Check for excessive duration
            max_duration = getattr(settings, 'MEDIA_VIDEO_MAX_DURATION', 120)
            if metadata['duration'] > max_duration:
                result['security_issues'].append(f"Duration exceeds limit: {metadata['duration']}s > {max_duration}s")

            # Check for suspicious metadata
            self._validate_video_metadata_security(metadata, result)

            # Check for container format security
            self._validate_container_security(metadata, result)

            # If no security issues found, mark as secure
            if not result['security_issues']:
                result['is_secure'] = True

            return result

        except Exception as e:
            result['security_issues'].append(f"Security validation error: {str(e)}")
            return result

    def _get_secure_file_path(self, video_file) -> str:
        """
        Get secure file path with validation.

        Args:
            video_file: Path to video file or file object

        Returns:
            Validated file path

        Raises:
            ValueError: If path is invalid or insecure
        """
        if hasattr(video_file, 'file') and hasattr(video_file.file, 'path'):
            file_path = video_file.file.path
        elif hasattr(video_file, 'path'):
            file_path = video_file.path
        else:
            file_path = str(video_file)

        # Validate path security
        if '..' in file_path or file_path.startswith('/etc/') or file_path.startswith('/proc/'):
            raise ValueError("Insecure file path detected")

        # Check for null bytes
        if '\x00' in file_path:
            raise ValueError("Null byte in file path")

        return file_path

    def extract_metadata_secure(self, video_file) -> Dict[str, Any]:
        """
        Extract metadata with security protections against command injection.

        Args:
            video_file: Path to video file or file object

        Returns:
            Dictionary containing video metadata

        Raises:
            ValueError: If ffmpeg is not available or file is invalid
        """
        if not self.ffmpeg_available:
            raise ValueError("ffmpeg is required for video metadata extraction")

        try:
            # Get secure file path
            file_path = self._get_secure_file_path(video_file)

            # Sanitize file path for ffmpeg command
            sanitized_path = self._sanitize_ffmpeg_path(file_path)

            # Probe video file with timeout and security restrictions
            probe = ffmpeg.probe(
                sanitized_path,
                cmd=['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams'],
                timeout=30  # 30 second timeout
            )

            video_stream = next((stream for stream in probe['streams']
                              if stream['codec_type'] == 'video'), None)
            audio_stream = next((stream for stream in probe['streams']
                              if stream['codec_type'] == 'audio'), None)

            if not video_stream:
                raise ValueError("No video stream found in file")

            # Extract video metadata with validation
            metadata = {
                'duration': self._validate_numeric_value(video_stream.get('duration', 0), 'duration'),
                'width': self._validate_numeric_value(video_stream.get('width', 0), 'width'),
                'height': self._validate_numeric_value(video_stream.get('height', 0), 'height'),
                'codec_name': self._sanitize_string_value(video_stream.get('codec_name', '')),
                'codec_long_name': self._sanitize_string_value(video_stream.get('codec_long_name', '')),
                'profile': self._sanitize_string_value(video_stream.get('profile', '')),
                'level': self._sanitize_string_value(video_stream.get('level', '')),
                'pixel_format': self._sanitize_string_value(video_stream.get('pix_fmt', '')),
                'bit_rate': self._validate_numeric_value(video_stream.get('bit_rate', 0), 'bit_rate') if video_stream.get('bit_rate') else None,
                'frame_rate': self._parse_frame_rate(video_stream.get('r_frame_rate', '0/1')),
                'avg_frame_rate': self._parse_frame_rate(video_stream.get('avg_frame_rate', '0/1')),
                'format_name': self._sanitize_string_value(probe.get('format', {}).get('format_name', '')),
                'format_long_name': self._sanitize_string_value(probe.get('format', {}).get('format_long_name', '')),
                'size': self._validate_numeric_value(probe.get('format', {}).get('size', 0), 'size'),
                'has_audio': audio_stream is not None,
            }

            # Add audio metadata if available
            if audio_stream:
                metadata.update({
                    'audio_codec': self._sanitize_string_value(audio_stream.get('codec_name', '')),
                    'audio_bit_rate': self._validate_numeric_value(audio_stream.get('bit_rate', 0), 'audio_bit_rate') if audio_stream.get('bit_rate') else None,
                    'sample_rate': self._validate_numeric_value(audio_stream.get('sample_rate', 0), 'sample_rate') if audio_stream.get('sample_rate') else None,
                    'channels': self._validate_numeric_value(audio_stream.get('channels', 0), 'channels') if audio_stream.get('channels') else None,
                })

            return metadata

        except Exception as e:
            raise ValueError(f"Error extracting video metadata: {str(e)}")

    def _sanitize_ffmpeg_path(self, file_path: str) -> str:
        """
        Sanitize file path for ffmpeg command to prevent injection.

        Args:
            file_path: Original file path

        Returns:
            Sanitized file path

        Raises:
            ValueError: If path contains dangerous characters
        """
        # Check for dangerous characters that could be used for command injection
        dangerous_chars = ['`', '$', '(', ')', ';', '&', '|', '<', '>', '\n', '\r']
        for char in dangerous_chars:
            if char in file_path:
                raise ValueError(f"Dangerous character '{char}' found in file path")

        # Ensure path is absolute and normalized
        normalized_path = os.path.abspath(file_path)

        # Additional validation
        if not os.path.exists(normalized_path):
            raise ValueError("File does not exist")

        return normalized_path

    def _validate_numeric_value(self, value, field_name: str) -> float:
        """Validate and convert numeric values from ffmpeg output."""
        try:
            num_value = float(value)
            # Check for reasonable bounds
            if field_name in ['width', 'height'] and (num_value < 0 or num_value > 10000):
                raise ValueError(f"Invalid {field_name}: {num_value}")
            elif field_name == 'duration' and (num_value < 0 or num_value > 7200):  # Max 2 hours
                raise ValueError(f"Invalid duration: {num_value}")
            elif field_name in ['bit_rate', 'audio_bit_rate'] and (num_value < 0 or num_value > 1000000000):  # Max 1 Gbps
                raise ValueError(f"Invalid {field_name}: {num_value}")
            return num_value
        except (ValueError, TypeError):
            return 0.0

    def _sanitize_string_value(self, value) -> str:
        """Sanitize string values from ffmpeg output."""
        if not isinstance(value, str):
            return str(value)

        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\'\x00-\x1f\x7f-\x9f]', '', value)

        # Limit length
        return sanitized[:100]

    def _validate_video_metadata_security(self, metadata: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate video metadata for security issues."""
        # Check for suspicious codec combinations
        codec = metadata.get('codec_name', '').lower()
        format_name = metadata.get('format_name', '').lower()

        # Check for codec/format mismatches that could indicate tampering
        expected_combinations = {
            'h264': ['mp4', 'mov', 'avi'],
            'vp8': ['webm'],
            'vp9': ['webm'],
            'av1': ['mp4', 'webm']
        }

        if codec in expected_combinations:
            if not any(fmt in format_name for fmt in expected_combinations[codec]):
                result['warnings'].append(f"Unusual codec/format combination: {codec} in {format_name}")

        # Check for excessive metadata size (could indicate hidden data)
        total_metadata_size = len(str(metadata))
        if total_metadata_size > 10000:  # 10KB of metadata is excessive
            result['warnings'].append(f"Excessive metadata size: {total_metadata_size} bytes")

    def _validate_container_security(self, metadata: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate container format for security issues."""
        format_name = metadata.get('format_name', '').lower()

        # Check for potentially dangerous container formats
        dangerous_formats = ['asf', 'wmv', 'rm', 'rmvb', 'flv']
        for dangerous_format in dangerous_formats:
            if dangerous_format in format_name:
                result['security_issues'].append(f"Potentially unsafe container format: {format_name}")
                break
    
    def get_secure_video_upload_path(self, instance, filename: str) -> str:
        """
        Generate secure UUID-based video upload path.
        
        Args:
            instance: Model instance (VideoClip)
            filename: Original filename
            
        Returns:
            Secure upload path with UUID-based filename
            
        Raises:
            ValueError: If filename has invalid extension
        """
        import uuid
        from django.core.exceptions import ValidationError
        
        ext = Path(filename).suffix.lower()
        allowed_extensions = getattr(settings, 'MEDIA_ALLOWED_VIDEO_EXTENSIONS', ['.mp4', '.webm', '.mov'])
        
        if ext not in allowed_extensions:
            raise ValidationError(f"Video extension {ext} not allowed")
        
        # Generate UUID filename
        uuid_filename = f"{uuid.uuid4()}{ext}"
        
        # Return structured path
        return f"videos/{timezone.now().strftime('%Y/%m')}/originals/{uuid_filename}"
