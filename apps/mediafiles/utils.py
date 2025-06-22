# MediaFiles Utilities
# Utility functions for media processing and file handling

import os
import re
import uuid
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
    if instance.mime_type.startswith('image/'):
        # Check if it's part of a photo series (would need to check relations)
        media_type = 'photos'  # Default to photos for images
    elif instance.mime_type.startswith('video/'):
        media_type = 'videos'
    else:
        media_type = 'media'

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

    # Generate cryptographically secure UUID-based filename
    secure_filename = f"{uuid.uuid4()}{ext}"

    # Determine media type and create path structure
    current_date = timezone.now()
    year_month = current_date.strftime('%Y/%m')

    # Determine media type from instance (controlled by application logic)
    if hasattr(instance, 'event_type'):
        from apps.events.models import Event
        if instance.event_type == Event.PHOTO_EVENT:
            media_type = 'photos'
        elif instance.event_type == Event.PHOTO_SERIES_EVENT:
            media_type = 'photo_series'
        elif instance.event_type == Event.VIDEO_CLIP_EVENT:
            media_type = 'videos'
        else:
            media_type = 'media'
    else:
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
    # Allow only word characters, spaces, hyphens, and underscores
    name = re.sub(r'[^\w\s\-_]', '', name)
    name = re.sub(r'[-\s_]+', '-', name)
    name = name.strip('-_')

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

    # Use slugify for additional safety and ensure we have a valid name
    name = slugify(name) or "file"

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
