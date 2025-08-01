# MediaFiles App Documentation

## Overview and Purpose

The MediaFiles app provides comprehensive media file management capabilities for the EquipeMed medical collaboration platform. It enables healthcare professionals to securely upload, store, and manage medical images and videos associated with patient records.

### Key Features

- **Secure File Storage**: UUID-based file naming with comprehensive security validation
- **Multiple Media Types**: Support for single photos, photo series, and short video clips
- **Event Integration**: Seamless integration with the Event system for medical record tracking
- **Permission-Based Access**: Role-based access control for medical staff
- **File Deduplication**: SHA-256 hash-based duplicate detection and storage optimization
- **Thumbnail Generation**: Automatic thumbnail creation for images and video previews
- **Audit Trail**: Complete access logging and file operation tracking

### Architecture Decision

The MediaFiles app implements a **single app with multiple specialized models** approach:

- **Photo** model for single images (uses existing PHOTO_EVENT = 3)
- **PhotoSeries** model for image series (uses existing PHOTO_SERIES_EVENT = 9)  
- **VideoClip** model for short video clips (new VIDEO_CLIP_EVENT = 10)
- **MediaFile** model for actual file storage and metadata
- **PhotoSeriesFile** through model for ordering images in series

## Model Relationships

### Core Model Structure

```
Event (base model)
├── Photo (1:1 with MediaFile)
│   └── MediaFile
├── PhotoSeries (1:M with MediaFile through PhotoSeriesFile)
│   └── PhotoSeriesFile
│       └── MediaFile
└── VideoClip (FilePond-based, stores metadata directly)
    └── file_id, original_filename, file_size, duration, etc.
```

**Note**: VideoClip stores file metadata directly using FilePond integration, without MediaFile relationship.

### MediaFile Model (Core File Storage)

The central model for storing file metadata and managing secure file storage:

```python
class MediaFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    file = models.FileField(upload_to=get_secure_upload_path)
    original_filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, unique=True)  # SHA-256
    file_size = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=100)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True)  # seconds
    thumbnail_path = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Event Model Extensions

#### Photo Model
```python
class Photo(Event):
    media_file = models.OneToOneField(MediaFile, on_delete=models.CASCADE)
    caption = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Foto"
        verbose_name_plural = "Fotos"
```

#### PhotoSeries Model
```python
class PhotoSeries(Event):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Série de Fotos"
        verbose_name_plural = "Séries de Fotos"
```

#### VideoClip Model
```python
class VideoClip(Event):
    # FilePond-based implementation - no MediaFile relationship
    file_id = models.CharField(max_length=100, null=True, blank=True)
    original_filename = models.CharField(max_length=255, null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True)  # seconds
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    video_codec = models.CharField(max_length=50, null=True, blank=True)
    caption = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Vídeo Curto"
        verbose_name_plural = "Vídeos Curtos"
```

#### PhotoSeriesFile Model (Through Model)
```python
class PhotoSeriesFile(models.Model):
    photo_series = models.ForeignKey(PhotoSeries, on_delete=models.CASCADE)
    media_file = models.ForeignKey(MediaFile, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    caption = models.TextField(blank=True)
    
    class Meta:
        ordering = ['order']
        unique_together = [['photo_series', 'order']]
```

## FilePond Integration

### Overview

The VideoClip model uses a modern FilePond implementation with server-side H.264 conversion. This approach provides:

- **Simplified Architecture**: Direct file metadata storage without MediaFile relationship
- **Server-Side Processing**: All video conversion handled by `VideoProcessor` with ffmpeg
- **Mobile Optimization**: Automatic H.264/MP4 conversion for universal device compatibility
- **Reduced Complexity**: Clean client-side interface with server-side processing

### Key Components

#### VideoProcessor
```python
# Located in apps/mediafiles/video_processor.py
class VideoProcessor:
    @staticmethod
    def convert_to_h264(input_path: str, output_path: str) -> dict:
        """Convert video to H.264/MP4 with mobile-optimized settings."""
        # ffmpeg settings:
        # - libx264 codec with medium preset
        # - AAC audio codec  
        # - yuv420p pixel format for compatibility
        # - faststart flag for web optimization
        # - Even dimensions for encoding compatibility
```

#### SecureVideoStorage
```python
# Located in apps/mediafiles/storage.py
class SecureVideoStorage(FileSystemStorage):
    """Custom storage backend for FilePond maintaining UUID naming."""
    
    def _save(self, name, content):
        # Generates UUID-based filename
        # Creates date-based directory: videos/YYYY/MM/originals/
        # Ensures secure file storage structure
```

#### Configuration
```python
# settings.py additions
INSTALLED_APPS = [
    'django_drf_filepond',
    'storages', 
    'rest_framework',
]

# FilePond settings
DJANGO_DRF_FILEPOND_UPLOAD_TMP = '/tmp/filepond_uploads'
DJANGO_DRF_FILEPOND_FILE_STORE_PATH = '/tmp/filepond_stored'
DJANGO_DRF_FILEPOND_STORAGES_BACKEND = 'apps.mediafiles.storage.SecureVideoStorage'

# Video processing
MEDIA_VIDEO_CONVERSION_ENABLED = True
MEDIA_VIDEO_MAX_DURATION = 120  # 2 minutes
MEDIA_VIDEO_MAX_SIZE = 100 * 1024 * 1024  # 100MB input limit
```

### Implementation Features

1. **Database Schema**: VideoClip model stores file metadata directly without MediaFile relationship
2. **File Processing**: Server-side H.264 conversion for optimal compatibility
3. **Bundle Size**: Minimal JavaScript footprint with FilePond integration
4. **Template**: Clean FilePond CDN-based interface for video uploads
5. **URL Structure**: Includes `/mediafiles/fp/` endpoints for FilePond processing

## File Handling Strategy

### Secure File Storage Structure

```
media/
├── photos/
│   ├── 2024/01/
│   │   ├── originals/
│   │   │   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
│   │   │   └── f9e8d7c6-b5a4-3210-9876-543210fedcba.png
│   │   ├── large/
│   │   ├── medium/
│   │   └── thumbnails/
├── photo_series/
│   └── 2024/01/
│       ├── originals/
│       └── thumbnails/
└── videos/
    ├── 2024/01/
    │   ├── originals/
    │   │   └── video-uuid.mp4
    │   └── thumbnails/
    │       └── video-uuid.jpg
```

### Security Features

1. **UUID-based Filenames**: Prevent enumeration attacks and ensure uniqueness
2. **Original Filename Storage**: User's original filename stored in database only
3. **Path Traversal Protection**: Comprehensive validation against directory traversal
4. **File Extension Validation**: Strict whitelist of allowed file types
5. **MIME Type Validation**: Content-based file type verification
6. **File Size Limits**: Configurable limits for different media types
7. **Hash-based Deduplication**: SHA-256 hash calculation for duplicate detection
8. **Secure File Serving**: All files served through Django views with permission checks

### File Processing Pipeline

1. **Upload Validation**: File type, size, and content validation
2. **Security Scanning**: Malicious content detection and sanitization
3. **Hash Calculation**: SHA-256 hash for deduplication
4. **Secure Storage**: UUID-based filename generation and secure path creation
5. **Thumbnail Generation**: Automatic thumbnail creation for images and videos
6. **Metadata Extraction**: Image/video metadata extraction and storage
7. **Database Recording**: File metadata and relationship storage

## API Reference

### Core Utility Functions

#### File Security and Naming

```python
def get_secure_upload_path(instance, filename: str) -> str:
    """Generate secure upload path with UUID filename."""

def normalize_filename(filename: str) -> str:
    """Normalize and sanitize original filename for safe database storage."""

def calculate_file_hash(file_obj: UploadedFile) -> str:
    """Calculate SHA-256 hash for file deduplication."""

def validate_file_extension(filename: str, file_type: str) -> bool:
    """Validate file extension against allowed types."""

def clean_filename(filename: str) -> str:
    """Remove dangerous characters and path components."""
```

#### Image Processing

```python
def generate_image_thumbnail(image_path: str, thumbnail_path: str, size: tuple = (150, 150)) -> bool:
    """Generate thumbnail for image file."""

def get_image_dimensions(image_path: str) -> tuple:
    """Extract image dimensions."""

def resize_image(image_path: str, output_path: str, max_size: tuple) -> bool:
    """Resize image to maximum dimensions while maintaining aspect ratio."""
```

#### Video Processing

```python
def extract_video_thumbnail(video_path: str, thumbnail_path: str, timestamp: float = 1.0) -> bool:
    """Extract thumbnail from video at specified timestamp."""

def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds."""

def get_video_metadata(video_path: str) -> dict:
    """Extract comprehensive video metadata."""
```

### View Classes

#### SecureFileServeView
```python
class SecureFileServeView(View):
    """Secure file serving with permission checks and access logging."""
    
    def get(self, request: HttpRequest, file_id: str) -> HttpResponse:
        """Serve media file with security checks."""
```

#### SecureThumbnailServeView
```python
class SecureThumbnailServeView(View):
    """Secure thumbnail serving with caching and permission checks."""
    
    def get(self, request: HttpRequest, file_id: str) -> HttpResponse:
        """Serve thumbnail with security checks."""
```

### Template Tags

```python
# Load template tags
{% load mediafiles_tags %}

# Display media thumbnails
{% mediafiles_thumbnail media_file size="medium" %}

# Format video duration
{% mediafiles_duration video_clip.media_file.duration %}

# Format file sizes
{% mediafiles_file_size media_file.file_size %}

# Get appropriate icons
{% mediafiles_type_icon media_file.mime_type %}
```

## Usage Examples

### Single Photo Upload

```python
from apps.mediafiles.models import Photo, MediaFile
from apps.events.models import Event

# Create photo event
photo = Photo.objects.create(
    patient=patient,
    created_by=user,
    event_type=Event.PHOTO_EVENT,
    description="Patient X-ray results"
)

# Handle file upload through form
form = PhotoUploadForm(request.POST, request.FILES)
if form.is_valid():
    media_file = form.save(photo=photo)
```

### Photo Series Management

```python
from apps.mediafiles.models import PhotoSeries, PhotoSeriesFile

# Create photo series
series = PhotoSeries.objects.create(
    patient=patient,
    created_by=user,
    event_type=Event.PHOTO_SERIES_EVENT,
    title="Wound healing progression",
    description="Weekly photos showing healing progress"
)

# Add photos to series
for i, uploaded_file in enumerate(uploaded_files):
    media_file = MediaFile.objects.create_from_upload(uploaded_file)
    PhotoSeriesFile.objects.create(
        photo_series=series,
        media_file=media_file,
        order=i + 1,
        caption=f"Week {i + 1}"
    )
```

### Video Clip Upload

```python
from apps.mediafiles.models import VideoClip

# Create video clip event
video = VideoClip.objects.create(
    patient=patient,
    created_by=user,
    event_type=Event.VIDEO_CLIP_EVENT,
    title="Physical therapy session",
    description="Patient mobility assessment"
)

# Handle video upload
form = VideoUploadForm(request.POST, request.FILES)
if form.is_valid():
    media_file = form.save(video=video)
```

### Secure File Access

```python
# Template usage
<img src="{% url 'mediafiles:serve_file' media_file.id %}" 
     alt="{{ media_file.original_filename }}" 
     class="img-thumbnail">

# Thumbnail display
<img src="{% url 'mediafiles:serve_thumbnail' media_file.id %}" 
     alt="Thumbnail" 
     class="thumbnail">
```

### File Deduplication

```python
from apps.mediafiles.utils import calculate_file_hash

# Check for existing file
file_hash = calculate_file_hash(uploaded_file)
existing_file = MediaFile.objects.filter(file_hash=file_hash).first()

if existing_file:
    # Use existing file instead of uploading duplicate
    photo.media_file = existing_file
else:
    # Create new media file
    media_file = MediaFile.objects.create_from_upload(uploaded_file)
    photo.media_file = media_file
```

## Configuration Settings

### Media File Settings

```python
# File size limits
MEDIA_IMAGE_MAX_SIZE = 5 * 1024 * 1024  # 5MB
MEDIA_VIDEO_MAX_SIZE = 50 * 1024 * 1024  # 50MB
MEDIA_VIDEO_MAX_DURATION = 120  # 2 minutes in seconds

# Allowed file types
MEDIA_ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
MEDIA_ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/webm', 'video/quicktime']

# Security settings
MEDIA_ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
MEDIA_ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.webm', '.mov']
MEDIA_MAX_FILENAME_LENGTH = 100
MEDIA_USE_UUID_FILENAMES = True
MEDIA_ENABLE_FILE_DEDUPLICATION = True
```

### URL Configuration

```python
# apps/mediafiles/urls.py
app_name = 'mediafiles'
urlpatterns = [
    path('file/<uuid:file_id>/', views.serve_media_file, name='serve_file'),
    path('thumbnail/<uuid:file_id>/', views.serve_thumbnail, name='serve_thumbnail'),
    path('photo/upload/', views.PhotoUploadView.as_view(), name='photo_upload'),
    path('series/upload/', views.PhotoSeriesUploadView.as_view(), name='series_upload'),
    path('video/upload/', views.VideoUploadView.as_view(), name='video_upload'),
]
```

## Integration with Events System

The MediaFiles app seamlessly integrates with the existing Event system:

1. **Event Type Extension**: Adds VIDEO_CLIP_EVENT = 10 to existing event types
2. **Timeline Integration**: Media events appear in patient timelines with appropriate icons
3. **Permission Inheritance**: Uses existing patient access permissions
4. **Audit Trail**: Leverages Event model's audit trail capabilities
5. **Access Control**: Respects role-based access control

## Performance Considerations

### Database Optimization

- **Indexes**: File hash, creation date, and foreign key relationships
- **Query Optimization**: Use `select_related()` and `prefetch_related()` for media queries
- **Pagination**: Implement pagination for large media collections

### File System Optimization

- **Thumbnail Caching**: Generated thumbnails cached with appropriate headers
- **CDN Integration**: Ready for CDN deployment for static file serving
- **Compression**: Automatic image optimization and compression

### Security Performance

- **Rate Limiting**: Configurable rate limits for file access and uploads
- **Permission Caching**: Cached permission checks for frequently accessed files
- **Access Logging**: Efficient logging system for audit trails

## Testing Infrastructure

The MediaFiles app includes comprehensive testing coverage:

- **Model Tests**: Validation, relationships, and business logic
- **View Tests**: Permission checks, file serving, and upload handling
- **Form Tests**: File validation, upload processing, and error handling
- **Utility Tests**: File processing, security functions, and thumbnail generation
- **Security Tests**: File naming, validation, and access control
- **Integration Tests**: Event system integration and permission inheritance

## Future Enhancements

### Planned Features

1. **Advanced Image Processing**: Image rotation, cropping, and enhancement tools
2. **Video Streaming**: Progressive video loading and streaming capabilities
3. **Bulk Operations**: Batch upload and management tools
4. **Advanced Search**: Content-based image search and tagging
5. **Export Features**: PDF reports with embedded media
6. **Mobile Optimization**: Progressive web app features for mobile uploads

### Scalability Considerations

1. **Cloud Storage Integration**: AWS S3, Google Cloud Storage support
2. **Microservice Architecture**: Separate media processing service
3. **Advanced Caching**: Redis-based caching for metadata and thumbnails
4. **Load Balancing**: Multi-server file serving capabilities

## Troubleshooting

### Common Issues

1. **File Upload Failures**: Check file size limits and MIME type validation
2. **Permission Denied**: Verify user has patient access permissions
3. **Thumbnail Generation**: Ensure Pillow and ffmpeg dependencies are installed
4. **Storage Issues**: Check media directory permissions and disk space

### Debug Commands

```bash
# Check media file integrity
python manage.py check_media_files

# Regenerate thumbnails
python manage.py regenerate_thumbnails

# Audit file permissions
python manage.py audit_media_permissions

# Clean orphaned files
python manage.py cleanup_orphaned_media
```

## Support and Maintenance

For technical support and maintenance issues:

1. Check the comprehensive test suite for examples
2. Review security implementation documentation
3. Consult the database schema documentation
4. Follow the migration plan for updates
5. Use the provided debugging tools and commands

The MediaFiles app is designed for reliability, security, and scalability in medical environments, ensuring patient data protection while providing efficient media management capabilities.
