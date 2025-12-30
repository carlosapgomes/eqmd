# Media Files App Initial Implementation Plan - Phase 1

## Overview

This phase establishes the foundation for the media upload feature in EquipeMed. Based on our analysis, we'll implement a single `mediafiles` app with three specialized models extending the base Event model: Photo (single images), PhotoSeries (image series), and VideoClip (short video clips up to 2 minutes).

## Architecture Decision

**Chosen Approach**: Single app with multiple specialized models

- **Photo** model for single images (uses existing PHOTO_EVENT = 3)
- **PhotoSeries** model for image series (uses existing PHOTO_SERIES_EVENT = 9)  
- **VideoClip** model for short video clips (new VIDEO_CLIP_EVENT = 10)
- **MediaFile** model for actual file storage and metadata
- **PhotoSeriesFile** through model for ordering images in series

Follow each step bellow to implement the initial structure for the media files app.
Stop after completing each step and ask for permission to proceed.

## Step 1: Create Media App Structure

### 1.1 Create App Directory and Files

**Action**: Create the mediafiles app with standard Django structure in the apps directory

```bash
uv run python manage.py startapp mediafiles apps/mediafiles
```

**Expected Structure**:

```
apps/mediafiles/
├── __init__.py
├── admin.py
├── apps.py
├── forms.py
├── migrations/
│   └── __init__.py
├── models.py
├── templates/
│   └── mediafiles/
├── templatetags/
│   ├── __init__.py
│   └── mediafiles_tags.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_forms.py
│   └── test_utils.py
├── urls.py
├── utils.py
└── views.py
```

### 1.2 Create Additional Directories

**Action**: Create template and static directories

**Directories to create**:

- `apps/mediafiles/templates/mediafiles/`
- `apps/mediafiles/templates/mediafiles/partials/`
- `apps/mediafiles/static/mediafiles/`
- `apps/mediafiles/static/mediafiles/css/`
- `apps/mediafiles/static/mediafiles/js/`

## Step 2: Update Django Settings

### 2.1 Add MediaFiles App to INSTALLED_APPS

**File**: `config/settings.py`

**Action**: Add 'apps.mediafiles' to INSTALLED_APPS list after existing apps

**Location**: Insert after 'apps.simplenotes' in the INSTALLED_APPS list

### 2.2 Configure Media File Handling

**File**: `config/settings.py`

**Action**: Verify and enhance media settings

**Settings to verify/add**:

- MEDIA_URL = "media/"
- MEDIA_ROOT = BASE_DIR / "media"
- FILE_UPLOAD_MAX_MEMORY_SIZE (set to 5MB for images)
- DATA_UPLOAD_MAX_MEMORY_SIZE (set to 10MB for videos)

### 2.3 Add Media-Specific Settings

**File**: `config/settings.py`

**Action**: Add media-specific configuration

**New settings to add**:

- MEDIA_IMAGE_MAX_SIZE = 5 *1024* 1024  # 5MB
- MEDIA_VIDEO_MAX_SIZE = 50 *1024* 1024  # 50MB
- MEDIA_VIDEO_MAX_DURATION = 120  # 2 minutes in seconds
- MEDIA_ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
- MEDIA_ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/webm', 'video/quicktime']

### 2.4 Add Security Settings

**File**: `config/settings.py`

**Action**: Add security-specific configuration for media files

**New security settings to add**:

- MEDIA_ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
- MEDIA_ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.webm', '.mov']
- MEDIA_MAX_FILENAME_LENGTH = 100
- MEDIA_USE_UUID_FILENAMES = True  # Use UUID-based secure filenames
- MEDIA_ENABLE_FILE_DEDUPLICATION = True  # Enable SHA-256 hash deduplication

## Step 3: Update Events Model

### 3.1 Add New Event Type

**File**: `apps/events/models.py`

**Action**: Add VIDEO_CLIP_EVENT to the Event model

**Changes needed**:

1. Add `VIDEO_CLIP_EVENT = 10` constant
2. Add to EVENT_TYPE_CHOICES: `(VIDEO_CLIP_EVENT, "Vídeo Curto")`
3. Update `get_event_type_badge_class()` method to include video type
4. Update `get_event_type_icon()` method to include 'bi-play-circle' for videos

### 3.2 Create Migration

**Action**: Generate and apply migration for the new event type

```bash
python manage.py makemigrations events
python manage.py migrate
```

## Step 4: Install Required Dependencies

### 4.1 Add Image Processing Dependencies

**Action**: Add Pillow for image processing

```bash
uv add Pillow
```

### 4.2 Add Video Processing Dependencies

**Action**: Add ffmpeg-python for video processing

```bash
uv add ffmpeg-python
```

**Note**: Requires ffmpeg system installation (already installed on dev machines):

- Ubuntu/Debian: `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: Download from <https://ffmpeg.org/>

### 4.3 Update Requirements Documentation

**File**: `pyproject.toml`

**Action**: Verify dependencies are properly added to the project dependencies

## Step 5: Create Base Media App Files

### 5.1 Configure Apps.py

**File**: `apps/mediafiles/apps.py`

**Action**: Set up proper app configuration

**Content structure**:

- Set name = 'apps.mediafiles'
- Set verbose_name = 'Media Files'
- Add ready() method for signal registration if needed

### 5.2 Create Base URLs

**File**: `apps/mediafiles/urls.py`

**Action**: Create URL namespace structure

**URL patterns to define**:

- App namespace: 'mediafiles'
- Placeholder patterns for future implementation
- Include patterns for each media type

### 5.3 Update Main URLs

**File**: `config/urls.py`

**Action**: Include media app URLs

**Changes**:

- Add `path('mediafiles/', include('apps.mediafiles.urls', namespace='mediafiles'))`
- Ensure media file serving is configured for development

## Step 6: Create Utility Modules

### 6.1 Create Media Processing Utilities

**File**: `apps/mediafiles/utils.py`

**Action**: Create utility functions for media processing

**Functions to implement**:

- Image resizing and thumbnail generation
- Video thumbnail extraction
- File validation functions
- Metadata extraction utilities
- Secure file naming and path generation
- File hash calculation for deduplication
- Filename normalization and sanitization

### 6.2 Create Template Tags

**File**: `apps/mediafiles/templatetags/mediafiles_tags.py`

**Action**: Create template tags for media display

**Template tags to implement**:

- `mediafiles_thumbnail` - Display media thumbnails
- `mediafiles_duration` - Format video duration
- `mediafiles_file_size` - Format file sizes
- `mediafiles_type_icon` - Get appropriate icons

## Step 7: Database Preparation

### 7.1 Plan Database Schema

**Action**: Document the planned database schema

**Tables to create**:

- `mediafiles_mediafile` - Core file storage and metadata
- `mediafiles_photo` - Single photo events (inherits from Event)
- `mediafiles_photoseries` - Photo series events (inherits from Event)
- `mediafiles_videoclip` - Video clip events (inherits from Event)
- `mediafiles_photoseriesfile` - Through table for photo series ordering

### 7.2 Plan File Storage Structure

**Action**: Define file organization strategy with secure naming

**Storage structure**:

```
media/
├── photos/
│   ├── 2024/01/
│   │   ├── originals/
│   │   │   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
│   │   │   └── f9e8d7c6-b5a4-3210-9876-543210fedcba.png
│   │   ├── large/
│   │   │   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg
│   │   │   └── f9e8d7c6-b5a4-3210-9876-543210fedcba.png
│   │   ├── medium/
│   │   └── thumbnails/
├── photo_series/
│   └── 2024/01/
│       ├── originals/
│       │   ├── series1-uuid1.jpg
│       │   └── series1-uuid2.jpg
│       └── thumbnails/
└── videos/
    ├── 2024/01/
    │   ├── originals/
    │   │   └── video-uuid.mp4
    │   └── thumbnails/
    │       └── video-uuid.jpg
```

**Security Features**:

- UUID-based filenames prevent enumeration attacks
- Original filenames stored in database only
- No patient information in file paths
- File extension validation enforced
- File hash calculation for deduplication

## Step 8: Security Implementation

### 8.1 Create Secure File Naming Utilities

**File**: `apps/mediafiles/utils.py`

**Action**: Implement secure file naming and validation functions

**Security utilities to implement**:

```python
def get_secure_upload_path(instance, filename):
    """Generate secure upload path with UUID filename"""

def normalize_filename(filename):
    """Normalize and sanitize original filename"""

def calculate_file_hash(file_obj):
    """Calculate SHA-256 hash for deduplication"""

def validate_file_extension(filename, file_type):
    """Validate file extension against allowed types"""

def clean_filename(filename):
    """Remove dangerous characters and path components"""
```

### 8.2 Implement File Security Validation

**File**: `apps/mediafiles/validators.py`

**Action**: Create comprehensive file validation

**Validators to implement**:

- File size validation
- MIME type validation
- File extension validation
- File content validation (magic number checking)
- Malicious file detection
- Image/video format validation

### 8.3 Create Security Middleware

**File**: `apps/mediafiles/middleware.py`

**Action**: Implement security middleware for file serving

**Middleware features**:

- Permission-based file access control
- Rate limiting for file downloads
- Secure headers for file responses
- Access logging for audit trails
- IP-based access restrictions (if needed)

### 8.4 Configure Secure File Serving

**Action**: Set up secure file serving configuration

**Security measures**:

- Prevent direct file system access
- Use Django views for all file serving
- Implement proper HTTP headers
- Add content disposition headers
- Configure browser caching policies

## Step 9: Testing Infrastructure

### 9.1 Create Test Structure

**Action**: Set up comprehensive testing framework

**Test files to create**:

- `test_models.py` - Model validation and behavior
- `test_views.py` - View functionality and permissions
- `test_forms.py` - Form validation and file handling
- `test_utils.py` - Utility function testing
- `test_security.py` - Security validation and file naming tests
- `test_validators.py` - File validation and sanitization tests

### 9.2 Create Test Media Files

**Action**: Create sample media files for testing

**Test files needed**:

- Sample JPEG images (various sizes)
- Sample PNG images
- Sample MP4 video (under 2 minutes)
- Invalid file types for negative testing
- Malicious file samples for security testing
- Files with dangerous names for sanitization testing
- Duplicate files for deduplication testing

## Step 10: Documentation

### 10.1 Create App Documentation

**File**: `docs/mediafiles/index.md`

**Action**: Document the mediafiles app architecture and usage

**Documentation sections**:

- Overview and purpose
- Model relationships
- File handling strategy
- API reference
- Usage examples

### 10.2 Update Main Documentation

**File**: `CLAUDE.md`

**Action**: Add media app section to the main documentation

**Content to add**:

- MediaFiles app overview
- Key features and capabilities
- URL structure
- Integration with events system

## Step 11: Validation and Verification

### 11.1 Verify App Installation

**Action**: Confirm the app is properly installed

**Verification steps**:

1. Run `uv run python manage.py check` - should pass without errors
2. Run `uv run python manage.py migrate` - should complete successfully
3. Access Django admin - mediafiles app should appear
4. Import mediafiles models - should work without errors

### 11.2 Verify Security Implementation

**Action**: Test security measures are properly implemented

**Security verification checklist**:

- [ ] UUID-based file naming working
- [ ] File extension validation enforced
- [ ] File size limits respected
- [ ] MIME type validation working
- [ ] Path traversal protection active
- [ ] File deduplication functioning
- [ ] Secure file serving implemented
- [ ] Permission-based access control working

### 11.3 Prepare for Phase 2

**Action**: Ensure foundation is ready for vertical slice implementation

**Checklist**:

- [ ] App structure created
- [ ] Settings updated
- [ ] Dependencies installed
- [ ] Event model updated
- [ ] URLs configured
- [ ] Utility modules created
- [ ] Testing infrastructure ready
- [ ] Documentation started

## Next Steps

After completing Phase 1, ask for permission to proceed to Phase 2 with the three vertical slice implementations:

1. Single Image implementation (Photo model)
2. Image Series implementation (PhotoSeries model)
3. Short Video Clips implementation (VideoClip model)

Each vertical slice will follow the pattern:

- Slice 1: Model and Admin
- Slice 2: Forms and Views
- Slice 3: Templates and Testing

## Success Criteria

Phase 1 is complete when:

- MediaFiles app is properly installed and configured
- All dependencies are installed and working
- Event model includes new video event type
- Basic app structure is in place
- Testing infrastructure is ready
- Documentation foundation is established
- No Django check errors or migration issues
