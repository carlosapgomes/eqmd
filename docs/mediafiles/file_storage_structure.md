# MediaFiles File Storage Structure

## Overview

This document defines the file storage organization strategy for the MediaFiles app, emphasizing security, scalability, and maintainability.

## Storage Directory Structure

### Root Media Directory

```
media/
├── photos/              # Single photo uploads
├── photo_series/        # Photo series uploads  
├── videos/              # Video clip uploads
└── temp/               # Temporary upload processing
```

### Photo Storage Structure

```
media/photos/
├── 2024/
│   ├── 01/             # January 2024
│   │   ├── originals/
│   │   │   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
│   │   │   ├── f9e8d7c6-b5a4-3210-9876-543210fedcba.png
│   │   │   └── 12345678-90ab-cdef-1234-567890abcdef.webp
│   │   ├── large/      # 1200px max dimension
│   │   │   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
│   │   │   ├── f9e8d7c6-b5a4-3210-9876-543210fedcba.jpg
│   │   │   └── 12345678-90ab-cdef-1234-567890abcdef.jpg
│   │   ├── medium/     # 800px max dimension
│   │   │   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
│   │   │   ├── f9e8d7c6-b5a4-3210-9876-543210fedcba.jpg
│   │   │   └── 12345678-90ab-cdef-1234-567890abcdef.jpg
│   │   └── thumbnails/ # 200px max dimension
│   │       ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
│   │       ├── f9e8d7c6-b5a4-3210-9876-543210fedcba.jpg
│   │       └── 12345678-90ab-cdef-1234-567890abcdef.jpg
│   ├── 02/             # February 2024
│   └── ...
├── 2025/
│   ├── 01/
│   └── ...
```

### Photo Series Storage Structure

```
media/photo_series/
├── 2024/
│   ├── 01/
│   │   ├── originals/
│   │   │   ├── series1-uuid1.jpg    # First image in series
│   │   │   ├── series1-uuid2.jpg    # Second image in series
│   │   │   ├── series1-uuid3.jpg    # Third image in series
│   │   │   ├── series2-uuid1.jpg    # Different series
│   │   │   └── series2-uuid2.jpg
│   │   └── thumbnails/
│   │       ├── series1-uuid1.jpg
│   │       ├── series1-uuid2.jpg
│   │       ├── series1-uuid3.jpg
│   │       ├── series2-uuid1.jpg
│   │       └── series2-uuid2.jpg
│   └── ...
```

### Video Storage Structure (Post-Phase 1 Migration)

```
media/videos/
├── 2024/
│   ├── 01/
│   │   ├── originals/              # FilePond-managed files
│   │   │   ├── video-uuid1.mp4     # All converted to H.264/MP4
│   │   │   ├── video-uuid2.mp4     # Server-side conversion
│   │   │   └── video-uuid3.mp4     # Universal mobile compatibility
│   │   └── thumbnails/             # TODO: FilePond thumbnail generation
│   │       ├── video-uuid1.jpg     # Future implementation
│   │       ├── video-uuid2.jpg
│   │       └── video-uuid3.jpg
│   └── ...
└── tmp/                           # FilePond temporary storage
    ├── filepond_uploads/          # Temporary uploads
    └── filepond_stored/           # Permanently stored files
```

**Phase 1 Changes:**
- All videos automatically converted to H.264/MP4 format
- FilePond manages temporary storage and conversion process
- Thumbnail generation pending future implementation
- Server-side VideoProcessor handles all format conversion

## File Naming Strategy

### UUID-Based Secure Naming

```python
# Example filename generation
import uuid
from pathlib import Path

def generate_secure_filename(original_filename):
    """Generate secure UUID-based filename"""
    ext = Path(original_filename).suffix.lower()
    secure_name = f"{uuid.uuid4()}{ext}"
    return secure_name

# Examples:
# "patient_photo.jpg" → "a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg"
# "wound_series_1.png" → "f9e8d7c6-b5a4-3210-9876-543210fedcba.png"
# "procedure_video.mp4" → "12345678-90ab-cdef-1234-567890abcdef.mp4"
```

### Path Generation Logic

```python
def get_secure_upload_path(instance, filename):
    """Generate secure upload path with UUID filename"""
    from django.utils import timezone
    
    # Get file extension
    ext = Path(filename).suffix.lower()
    
    # Generate UUID-based filename
    secure_filename = f"{uuid.uuid4()}{ext}"
    
    # Get current date for organization
    current_date = timezone.now()
    year_month = current_date.strftime('%Y/%m')
    
    # Determine media type from instance
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
    
    return f"{media_type}/{year_month}/originals/{secure_filename}"
```

## Security Features

### Filename Security

1. **UUID-based filenames** prevent enumeration attacks
2. **No patient information** in file paths
3. **Extension validation** enforced
4. **Path traversal protection** built-in
5. **Original filename preservation** in database only

### Directory Security

1. **Year/month organization** limits directory size
2. **Separate media type directories** for access control
3. **No executable files** allowed
4. **Proper file permissions** set on creation

### Access Control

1. **No direct web access** to media files
2. **Django view-based serving** with permission checks
3. **Secure URL generation** with time-limited tokens
4. **Rate limiting** on file access

## Image Size Variants

### Automatic Generation

For each uploaded image, the system automatically generates:

1. **Original**: Stored as-is (up to 5MB)
2. **Large**: 1200px max dimension, 85% quality
3. **Medium**: 800px max dimension, 80% quality  
4. **Thumbnail**: 200px max dimension, 75% quality

### Size Selection Logic

```python
def get_image_variant_path(original_path, size):
    """Get path for specific image size variant"""
    path_obj = Path(original_path)
    
    # Replace 'originals' with size directory
    size_path = str(path_obj).replace('/originals/', f'/{size}/')
    
    # Ensure .jpg extension for variants (optimization)
    if size != 'originals':
        size_path = Path(size_path).with_suffix('.jpg')
    
    return str(size_path)
```

## Video Processing

### Thumbnail Extraction

```python
def extract_video_thumbnail(video_path, time_offset=1.0):
    """Extract thumbnail from video at specified time"""
    import ffmpeg
    
    path_obj = Path(video_path)
    thumbnail_dir = path_obj.parent.parent / 'thumbnails'
    thumbnail_path = thumbnail_dir / f"{path_obj.stem}.jpg"
    
    # Extract frame using ffmpeg
    (
        ffmpeg
        .input(video_path, ss=time_offset)
        .output(str(thumbnail_path), vframes=1, format='image2')
        .overwrite_output()
        .run()
    )
    
    return str(thumbnail_path)
```

## File Deduplication

### Hash-Based Deduplication (Photos Only)

```python
import hashlib

def calculate_file_hash(file_obj):
    """Calculate SHA-256 hash for file deduplication"""
    hash_sha256 = hashlib.sha256()
    
    # Reset file pointer
    file_obj.seek(0)
    
    # Read file in chunks
    for chunk in iter(lambda: file_obj.read(4096), b""):
        hash_sha256.update(chunk)
    
    # Reset file pointer
    file_obj.seek(0)
    
    return hash_sha256.hexdigest()
```

### Deduplication Strategy

**For Photos and PhotoSeries (MediaFile-based):**
1. Calculate hash on upload
2. Check if hash exists in database
3. If exists, link to existing file instead of storing duplicate
4. Maintain reference count for cleanup
5. Delete file only when no references remain

**For Videos (FilePond-based):**
- File deduplication handled by FilePond system
- VideoClip model stores metadata directly (no MediaFile relationship)
- Each video conversion creates unique H.264/MP4 output
- Deduplication occurs at FilePond storage level

## Backup and Maintenance

### Backup Strategy

1. **Database backup** includes all metadata
2. **File system backup** preserves directory structure
3. **Hash verification** ensures backup integrity
4. **Incremental backups** based on creation date

### Cleanup Operations

1. **Orphaned file detection** using database queries
2. **Unused variant cleanup** for deleted originals
3. **Temporary file cleanup** for failed uploads
4. **Old file archival** based on retention policies

## Performance Optimization

### Directory Organization

- **Year/month structure** keeps directories manageable
- **Separate size directories** enable efficient serving
- **Predictable paths** allow for CDN optimization

### Caching Strategy

- **Thumbnail caching** with appropriate headers
- **Size variant caching** for frequently accessed images
- **Metadata caching** to reduce database queries

### CDN Preparation

- **Static URL structure** compatible with CDN
- **Cache-friendly headers** for optimal performance
- **Geographic distribution** ready structure

## Migration and Scaling

### Horizontal Scaling

- **Shared storage** compatible (NFS, S3, etc.)
- **Load balancer** friendly structure
- **Microservice** ready organization

### Cloud Storage Migration

- **S3-compatible** path structure
- **Metadata preservation** during migration
- **Gradual migration** support with fallbacks
