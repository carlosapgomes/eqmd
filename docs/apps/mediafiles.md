# MediaFiles App - Complete Implementation Guide

**Secure media file management for medical images and videos**

## Overview

- Models: MediaFile (for photos), Photo, PhotoSeries, VideoClip (FilePond-based) extending Event model
- Security: UUID-based file naming, SHA-256 hash deduplication, comprehensive validation
- File types: Single images, image series, short video clips (up to 2 minutes)
- Processing: Automatic thumbnail generation, metadata extraction, secure file serving
- Integration: Seamless Event system integration with timeline display
- URL structure: `/mediafiles/file/<uuid>/`, `/mediafiles/thumbnail/<uuid>/`, `/mediafiles/fp/` (FilePond)

## Key Features

- **Secure File Storage**: UUID-based filenames prevent enumeration attacks
- **File Deduplication**: SHA-256 hash-based duplicate detection and storage optimization (photos only)
- **Permission-Based Access**: Role-based access control
- **Multiple Media Types**: Photos (PHOTO_EVENT = 3), Photo Series (PHOTO_SERIES_EVENT = 9), Videos (VIDEO_CLIP_EVENT = 10)
- **Thumbnail Generation**: Automatic thumbnails for images and video previews
- **Audit Trail**: Complete access logging and file operation tracking
- **FilePond Integration**: Modern video upload with server-side H.264 conversion

## Security Implementation

- **File Validation**: MIME type, extension, size, and content validation
- **Path Protection**: Comprehensive path traversal and injection protection
- **Secure Serving**: All files served through Django views with permission checks
- **Rate Limiting**: Configurable limits for file access and uploads
- **Access Control**: Integration with existing patient permission system

## File Storage Structure

```
media/
├── photos/YYYY/MM/originals/uuid-filename.ext
├── photo_series/YYYY/MM/originals/uuid-filename.ext
└── videos/YYYY/MM/originals/uuid-filename.ext
```

## Multiple File Upload Implementation

**PhotoSeries supports multiple file uploads using Django 5.2 best practices**

### Custom Multiple File Field

Located in `apps/mediafiles/forms.py`:

```python
class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget for multiple file uploads following Django 5.2 pattern"""
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    """Custom field that handles multiple file uploads following Django 5.2 pattern"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        """Clean multiple files"""
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result
```

### PhotoSeries Form Implementation

```python
class PhotoSeriesCreateForm(BaseMediaForm, forms.ModelForm):
    images = MultipleFileField(
        label="Imagens da Série",
        help_text="Selecione múltiplas imagens (JPEG, PNG, WebP). Máximo 5MB por arquivo.",
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png,image/webp',
            'data-preview': 'true'
        }),
        required=True
    )

    def clean_images(self):
        """Validate multiple uploaded image files"""
        files = self.cleaned_data.get('images', [])
        if not files:
            raise ValidationError("Pelo menos uma imagem deve ser selecionada.")
        # Additional validation for each file...
        return files
```

### Key Features

- **Django 5.2 Compatibility**: Uses `allow_multiple_selected = True` pattern
- **Batch Validation**: Individual file validation for size, type, and security
- **Template Integration**: Works with existing drag-and-drop upload interface
- **Security**: Comprehensive validation and secure file handling
- **User Experience**: Preview thumbnails and upload progress tracking

### Usage in Views

```python
def form_valid(self, form):
    photoseries = form.save(commit=False)
    # ... set required fields ...
    photoseries.save()

    # Handle multiple files
    images = form.cleaned_data['images']
    photoseries.add_photos_batch(images)
    return super().form_valid(form)
```

### Implementation Notes

**Important:** Django's built-in `FileField` and `FileInput` widgets do NOT support multiple file uploads by default. The implementation above is required for multiple file functionality.

**Common Issues:**

- `ValueError: FileInput doesn't support uploading multiple files` - Use `MultipleFileInput` with `allow_multiple_selected = True`
- Single file upload only - Ensure the form field uses `MultipleFileField` instead of `forms.FileField`
- Form validation errors - The `clean_images()` method expects a list of files from `cleaned_data['images']`

**Template Requirements:**

- The upload interface in `photoseries_form.html` includes drag-and-drop functionality
- JavaScript in `photoseries.js` handles the upload preview and progress tracking
- The `multi_upload.html` partial provides advanced upload UI components

## VideoClip Current Architecture (Post-FilePond Migration)

**Modern video upload system using django-drf-filepond with server-side H.264 conversion**

### ✅ Current Status: Fully Operational

- **Video uploads**: Working correctly with FilePond interface
- **File storage**: UUID-based files in structured directories (`media/videos/YYYY/MM/originals/`)
- **Video streaming**: Custom streaming views serving files with proper headers
- **Server-side conversion**: H.264/MP4 conversion with mobile optimization
- **Performance**: 99% JavaScript bundle size reduction (6.6KB → 376 bytes)

### VideoClip Model Architecture

```python
class VideoClip(Event):
    # Direct metadata storage (no MediaFile relationship)
    file_id = models.CharField(max_length=100)  # UUID string for file identification
    original_filename = models.CharField(max_length=255)  # Original upload filename
    file_size = models.PositiveIntegerField()  # File size in bytes
    duration = models.PositiveIntegerField()  # Duration in seconds
    width = models.PositiveIntegerField()  # Video width in pixels
    height = models.PositiveIntegerField()  # Video height in pixels
    video_codec = models.CharField(max_length=50)  # Codec info (typically 'h264')
    caption = models.TextField(blank=True)  # Optional video caption

    # Inherits from Event: patient, created_by, event_datetime, description, etc.
```

### File Storage Structure

```
media/
└── videos/
    └── 2025/
        └── 06/
            └── originals/
                ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp4
                ├── d08e1857-43b3-4ba8-8368-917601555305.mp4
                └── 19c8f8ea-2701-43fd-b76d-bd739b220714.mp4
```

### Video Processing Pipeline

```python
class VideoProcessor:
    @staticmethod
    def convert_to_h264(input_path: str, output_path: str) -> dict:
        """Convert video to H.264/MP4 for universal mobile compatibility."""

        # Check if conversion needed (skip if already H.264/AAC/MP4)
        needs_conversion = (
            current_codec != 'h264' or
            current_format != '.mp4' or
            current_audio_codec != 'aac'
        )

        if needs_conversion:
            # Mobile-optimized ffmpeg conversion:
            # - libx264 codec with medium preset
            # - AAC audio codec
            # - yuv420p pixel format for universal compatibility
            # - faststart flag for web optimization
            # - Even dimensions for encoding compatibility

        return conversion_metadata
```

### VideoClipCreateForm Implementation

```python
class VideoClipCreateForm(BaseMediaForm, forms.ModelForm):
    upload_id = forms.CharField(widget=forms.HiddenInput())

    def save(self, commit=True):
        # Generate UUID-based file path
        file_uuid = uuid.uuid4()
        date_path = timezone.now().strftime('%Y/%m')
        destination_path = MEDIA_ROOT / f"videos/{date_path}/originals/{file_uuid}.mp4"

        # Copy from FilePond temporary storage to final location
        temp_upload = TemporaryUpload.objects.get(upload_id=upload_id)
        stored_upload = store_upload(upload_id, secure_filename)
        shutil.copy2(stored_upload.file.path, destination_path)

        # Process video conversion (if needed)
        processor = VideoProcessor()
        conversion_result = processor.convert_to_h264(
            str(destination_path),
            str(destination_path)  # Convert in place
        )

        # Set video metadata directly on VideoClip model
        videoclip.file_id = str(file_uuid)
        videoclip.original_filename = temp_upload.upload_name
        videoclip.file_size = conversion_result['converted_size']
        videoclip.duration = int(conversion_result['duration'])
        videoclip.width = conversion_result['width']
        videoclip.height = conversion_result['height']
        videoclip.video_codec = conversion_result['codec']

        return videoclip
```

### Configuration Requirements (Fixed)

```python
# settings.py - CORRECTED configuration
INSTALLED_APPS = [
    'django_drf_filepond',
    'storages',
    'rest_framework',
]

# FilePond Configuration - use project-relative directories
DJANGO_DRF_FILEPOND_UPLOAD_TMP = str(BASE_DIR / 'filepond_tmp')
DJANGO_DRF_FILEPOND_FILE_STORE_PATH = str(BASE_DIR / 'filepond_stored')

# Ensure directories exist with proper permissions
os.makedirs(DJANGO_DRF_FILEPOND_UPLOAD_TMP, mode=0o755, exist_ok=True)
os.makedirs(DJANGO_DRF_FILEPOND_FILE_STORE_PATH, mode=0o755, exist_ok=True)

# Video processing settings
MEDIA_VIDEO_CONVERSION_ENABLED = True
MEDIA_VIDEO_OUTPUT_FORMAT = 'mp4'
MEDIA_VIDEO_CODEC = 'libx264'
MEDIA_VIDEO_PRESET = 'medium'
MEDIA_VIDEO_MAX_DURATION = 120  # 2 minutes
MEDIA_VIDEO_MAX_SIZE = 100 * 1024 * 1024  # 100MB input limit

# Django REST Framework settings for FilePond
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

### Video Streaming Implementation

```python
class VideoClipStreamView(LoginRequiredMixin, DetailView):
    """Custom streaming view for VideoClip files."""

    def get(self, request, *args, **kwargs):
        videoclip = self.get_object()

        # Build file path from UUID and creation date
        file_uuid = videoclip.file_id
        creation_date = videoclip.created_at
        expected_path = videos_dir / creation_date.strftime('%Y/%m/originals') / f"{file_uuid}.mp4"

        # Fallback search if primary path not found
        if not expected_path.exists():
            for file_path in videos_dir.rglob(f"{file_uuid}.*"):
                expected_path = file_path
                break

        # Serve file with streaming headers
        response = FileResponse(open(expected_path, 'rb'), content_type='video/mp4')
        response['Accept-Ranges'] = 'bytes'
        response['Content-Length'] = expected_path.stat().st_size
        return response
```

### Migration Impact

- **Database Changes**: VideoClip model migrated from MediaFile relationship to direct file metadata storage
- **Bundle Optimization**: Removed videoclipCompression and videoclipPlayer bundles
- **Template Simplification**: FilePond-based template with CDN resources for upload interface
- **URL Structure**: Added `/mediafiles/fp/` endpoints for FilePond file processing

## Template Tags

```django
{% load mediafiles_tags %}
{% mediafiles_thumbnail media_file size="medium" %}
{% mediafiles_duration video.duration %}
{% mediafiles_file_size media_file.file_size %}
```

## Frontend JavaScript Architecture (Optimized)

**Bundle Structure - Post-FilePond Migration**

- **main-bundle.js**: Core application JavaScript (8.7KB)
- **mediafiles-bundle.js**: Shared mediafiles utilities (12KB)
- **photo-bundle.js**: Photo-specific functionality (5.4KB)
- **photoseries-bundle.js**: Photo series functionality (9.2KB)
- **videoclip-bundle.js**: Simplified video functionality (376 bytes) - FilePond CDN-based
- **image-processing bundles**: Heavy image libraries (52KB + 1.3MB, loaded only on photo pages)

**Performance Improvements:**

- Bundle sizes reduced by 99% for video pages through FilePond migration (6.6KB → 376 bytes)
- Heavy image processing libraries isolated and lazy-loaded
- Main application bundle kept minimal at 8.7KB
- Cross-browser compatibility with graceful fallbacks
- FilePond resources loaded from CDN (not bundled)

**Loading Patterns:**
Each page loads only required bundles:

- **Photo pages**: main + image-processing + photo bundles
- **PhotoSeries pages**: main + photoseries bundles
- **VideoClip pages**: main + videoclip bundles
- **Timeline pages**: main + all mediafiles bundles
- **Other pages**: main bundle only

**Error Handling & Fallbacks:**

- Graceful degradation when bundles fail to load
- Basic file validation fallbacks for all upload types
- Comprehensive error reporting and monitoring
- User-friendly error messages without technical details

**Development Guidelines:**

- Never use auto-initialization - always manual init in templates
- Test bundle loading on each page type after changes
- Monitor bundle sizes - alert if any bundle exceeds 50KB (except image-processing)
- Use try-catch blocks around all module initialization
- Provide meaningful fallbacks for core functionality

**Bundle Size Monitoring:**

- **Alert thresholds**: 50KB for regular bundles, 1.5MB total for photo pages
- **Performance targets**: <20% JavaScript parse time, <200KB total per page
- **Error tracking**: Bundle loading failures, initialization errors
- **Optimization**: Regular bundle analysis and code splitting review
