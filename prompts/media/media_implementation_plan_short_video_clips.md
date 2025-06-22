# Short Video Clips Implementation Plan - Phase 2C

## Overview

This plan implements the VideoClip model for short video uploads (up to 2 minutes) in the EquipeMed media system. VideoClip will extend the base Event model and use the new VIDEO_CLIP_EVENT type (10). Each video will have a single associated MediaFile with automatic thumbnail generation from the first frame and duration validation.

## Vertical Slice 1: Model and Admin

### Step 1.1: Update MediaFile Model for Video Support

**File**: `apps/mediafiles/models.py`

**Action**: Enhance MediaFile model to support video metadata

**New fields to add**:
- `duration` - DurationField for video length (null=True, blank=True)
- `video_codec` - CharField for video codec information (null=True, blank=True)
- `video_bitrate` - PositiveIntegerField for bitrate (null=True, blank=True)
- `fps` - FloatField for frames per second (null=True, blank=True)

**New methods to implement**:
- `is_video()` - Check if file is a video
- `get_duration_display()` - Format duration as MM:SS
- `extract_video_metadata()` - Extract video metadata using ffmpeg
- `generate_video_thumbnail()` - Generate secure thumbnail from first frame
- `validate_video_duration()` - Ensure video is ≤ 2 minutes
- `validate_video_security()` - Comprehensive video file security validation
- `get_secure_video_path()` - Generate secure UUID-based video path

### Step 1.2: Create VideoClip Model

**File**: `apps/mediafiles/models.py`

**Action**: Implement VideoClip model extending Event

**Model specifications**:
- Inherits from Event model
- OneToOneField to MediaFile
- Auto-set event_type to VIDEO_CLIP_EVENT in save()
- Custom manager for video-specific queries

**Key methods to implement**:
- `save()` - Set event_type, validate duration, call super()
- `get_absolute_url()` - Return detail view URL
- `get_edit_url()` - Return edit view URL
- `get_thumbnail()` - Delegate to media_file.get_thumbnail_url()
- `get_duration()` - Return formatted duration
- `get_video_url()` - Return video file URL
- `clean()` - Validate media_file is a video and duration ≤ 2 minutes

### Step 1.3: Create Video Processing Utilities

**File**: `apps/mediafiles/utils.py`

**Action**: Implement video processing utilities using ffmpeg

**VideoProcessor class methods**:
- `extract_metadata(video_file)` - Extract duration, codec, bitrate, fps
- `generate_secure_thumbnail(video_file, timestamp=0)` - Generate thumbnail with UUID naming
- `validate_video_file(video_file)` - Validate format, duration, and security
- `get_video_info(video_file)` - Get comprehensive video information
- `compress_video(video_file, target_size)` - Optional compression
- `validate_video_security(video_file)` - Security validation for video content
- `get_secure_video_upload_path(instance, filename)` - Generate secure upload path

**Security features**:
- Video content validation (prevent malicious video files)
- Codec validation against whitelist
- Container format validation
- Video stream analysis for security threats

**Error handling**:
- FFmpeg not installed detection
- Corrupted video file handling
- Unsupported format detection
- Duration extraction failures
- Security validation failures

### Step 1.4: Create Database Migration

**Action**: Generate and review migration for VideoClip model

```bash
uv run python manage.py makemigrations mediafiles
```

**Migration review checklist**:
- VideoClip model creation with Event inheritance
- MediaFile model updates for video fields
- Proper field types and constraints
- Indexes on duration and video-specific fields

### Step 1.5: Configure Admin Interface

**File**: `apps/mediafiles/admin.py`

**Action**: Create comprehensive admin interface for VideoClip management

**VideoClipAdmin specifications**:
- List display: thumbnail_preview, description, duration, patient, event_datetime, created_by
- List filters: event_datetime, created_by, patient__current_hospital, duration
- Search fields: description, patient__name, media_file__original_filename
- Readonly fields: created_at, updated_at, duration, video_codec, video_bitrate, fps
- Fieldsets: Event Info, Video File, Video Metadata, Audit Trail
- Video thumbnail preview in detail view
- Duration display in MM:SS format
- Custom queryset with select_related optimization

**Admin methods**:
- `thumbnail_preview()` - Display video thumbnail
- `duration_display()` - Format duration nicely
- `file_size_display()` - Format file size
- `video_info_display()` - Show codec and bitrate info

### Step 1.6: Create Model Tests

**File**: `apps/mediafiles/tests/test_models.py`

**Action**: Implement comprehensive model testing for VideoClip

**Test cases for VideoClip**:
- Event type auto-assignment
- Duration validation (≤ 2 minutes)
- Video file relationship
- Thumbnail generation
- Metadata extraction
- URL generation methods
- Manager methods

**Test cases for video MediaFile**:
- Video metadata extraction
- Thumbnail generation from video
- Duration validation
- Video format validation
- File size validation

**Test utilities**:
- Factory classes for VideoClip
- Sample video file creation (various durations)
- Mock ffmpeg responses for testing
- Video file cleanup utilities

## Security Implementation for Video Clips

### Security Requirements for Videos

**Video File Security**:
- UUID-based video filenames prevent enumeration
- Video codec validation against whitelist
- Container format validation (MP4, WebM, MOV only)
- Duration validation (≤ 2 minutes enforcement)
- File size validation (≤ 50MB)
- Video content analysis for malicious payloads

**Video Processing Security**:
- Secure thumbnail generation with UUID naming
- FFmpeg command injection prevention
- Temporary file cleanup during processing
- Error handling for corrupted video files

**Video Serving Security**:
- Permission-based video streaming
- HTTP range request validation
- Secure video URL generation
- Access logging for video views

### Security Implementation for Videos

**Secure Video Upload Path**:
```python
def get_secure_video_upload_path(instance, filename):
    ext = Path(filename).suffix.lower()
    if ext not in settings.MEDIA_ALLOWED_VIDEO_EXTENSIONS:
        raise ValidationError(f"Video extension {ext} not allowed")

    uuid_filename = f"{uuid.uuid4()}{ext}"
    return f"videos/{timezone.now().strftime('%Y/%m')}/originals/{uuid_filename}"
```

**Video Security Validation**:
```python
def validate_video_security(video_file):
    # File size validation
    if video_file.size > settings.MEDIA_VIDEO_MAX_SIZE:
        raise ValidationError("Video file too large")

    # MIME type validation
    if video_file.content_type not in settings.MEDIA_ALLOWED_VIDEO_TYPES:
        raise ValidationError("Invalid video type")

    # Duration validation using ffmpeg
    duration = extract_video_duration(video_file)
    if duration > settings.MEDIA_VIDEO_MAX_DURATION:
        raise ValidationError("Video duration exceeds 2 minutes")

    # Codec validation
    codec_info = extract_video_codec(video_file)
    if not is_safe_video_codec(codec_info):
        raise ValidationError("Unsupported or unsafe video codec")
```

## Vertical Slice 2: Forms and Views

### Step 2.1: Create VideoClip Forms

**File**: `apps/mediafiles/forms.py`

**Action**: Implement forms for video upload and editing

**VideoClipCreateForm specifications**:
- Fields: description, event_datetime, video (FileField)
- Custom video field with validation
- File size validation (max 50MB)
- Video format validation (MP4, WebM, MOV)
- Duration validation (≤ 2 minutes)
- Progress indicator for upload
- Bootstrap styling with video preview

**VideoClipUpdateForm specifications**:
- Fields: description, event_datetime (no video change)
- Inherits validation from VideoClipCreateForm
- Displays current video thumbnail and metadata

**Form validation methods**:
- `clean_video()` - Validate file type, size, duration, format, and security
- `clean_event_datetime()` - Ensure datetime is not in future
- `validate_video_security()` - Comprehensive security validation
- `save()` - Handle secure MediaFile creation, metadata extraction, and VideoClip instance

### Step 2.2: Create VideoClip Views

**File**: `apps/mediafiles/views.py`

**Action**: Implement CRUD views for video clip management

**VideoClipCreateView specifications**:
- Extends CreateView
- Permission required: 'events.add_event'
- Hospital context validation
- Patient parameter from URL
- Async video processing (thumbnail generation)
- Progress tracking for upload and processing
- Success redirect to patient timeline

**VideoClipDetailView specifications**:
- Extends DetailView
- Permission check with patient access validation
- Video player with controls
- Video metadata display (duration, size, format)
- Thumbnail display as fallback
- Edit/delete action buttons (if permitted)
- Download video button

**VideoClipUpdateView specifications**:
- Extends UpdateView
- Permission check: can_edit_event (24-hour rule)
- Form with current video preview
- Success redirect to detail view

**VideoClipDeleteView specifications**:
- Extends DeleteView
- Permission check: can_delete_event (24-hour rule)
- Confirmation page with video preview
- File cleanup on deletion (video + thumbnail)
- Success redirect to patient timeline

### Step 2.3: Create Video Streaming Views

**File**: `apps/mediafiles/views.py`

**Action**: Implement secure video streaming views

**VideoStreamView specifications**:
- Permission-protected video streaming
- Patient access validation
- Secure video path resolution (no direct file access)
- HTTP range request support for video seeking
- Proper MIME type headers
- Browser caching headers
- Bandwidth optimization
- Access logging for audit trails
- Rate limiting for video streaming

**VideoDownloadView specifications**:
- Secure video file download
- Permission validation
- Proper filename handling
- Download progress support

### Step 2.4: Create URL Patterns

**File**: `apps/mediafiles/urls.py`

**Action**: Define URL patterns for video clip views

**URL patterns**:
- `videos/create/<uuid:patient_id>/` - VideoClipCreateView
- `videos/<uuid:pk>/` - VideoClipDetailView
- `videos/<uuid:pk>/edit/` - VideoClipUpdateView
- `videos/<uuid:pk>/delete/` - VideoClipDeleteView
- `videos/<uuid:pk>/stream/` - Video streaming view
- `videos/<uuid:pk>/download/` - Video download view

**URL naming convention**:
- `videoclip_create`, `videoclip_detail`, `videoclip_update`, `videoclip_delete`
- `videoclip_stream`, `videoclip_download`

### Step 2.5: Create View Tests

**File**: `apps/mediafiles/tests/test_views.py`

**Action**: Implement comprehensive view testing for VideoClip

**Test cases**:
- Video upload with valid/invalid files
- Duration validation enforcement
- Permission-based access control
- Video streaming functionality
- File download handling
- Patient context validation
- 24-hour edit window enforcement
- Async processing handling

## Vertical Slice 3: Templates and Testing

### Step 3.1: Create VideoClip Templates

**File**: `apps/mediafiles/templates/mediafiles/videoclip_form.html`

**Action**: Create video upload/edit form template

**Template features**:
- Video file upload with preview
- Upload progress indicator
- Processing status indicator (thumbnail generation)
- Duration validation feedback
- File size validation feedback
- Video format validation
- Cancel/submit buttons
- Client-side duration check (if possible)

**File**: `apps/mediafiles/templates/mediafiles/videoclip_detail.html`

**Action**: Create video detail view template

**Template features**:
- HTML5 video player with controls
- Video metadata display (duration, size, format, codec)
- Thumbnail fallback if video fails to load
- Event information (patient, datetime, description)
- Action buttons (edit, delete, download) with permission checks
- Navigation back to patient timeline
- Responsive video player

### Step 3.2: Create Event Card Template

**File**: `apps/events/templates/events/partials/event_card_videoclip.html`

**Action**: Create specialized event card for video clips

**Template features**:
- Video thumbnail display
- Duration badge (e.g., "1:30")
- Play icon overlay
- Event metadata (datetime, description)
- Click to open video detail view
- Edit/delete buttons (if permitted)
- Responsive design for mobile

### Step 3.3: Create Video Player Components

**File**: `apps/mediafiles/templates/mediafiles/partials/video_player.html`

**Action**: Create reusable video player component

**Template features**:
- HTML5 video element with controls
- Custom video controls (optional)
- Poster image (thumbnail)
- Multiple source formats support
- Fallback message for unsupported browsers
- Loading indicator
- Error handling display

**File**: `apps/mediafiles/templates/mediafiles/partials/video_modal.html`

**Action**: Create modal for video viewing

**Template features**:
- Modal video player
- Video metadata overlay
- Download button
- Close button
- Keyboard controls (space to play/pause, escape to close)
- Responsive modal sizing

### Step 3.4: Add CSS Styling

**File**: `apps/mediafiles/static/mediafiles/css/videoclip.css`

**Action**: Create video-specific styling

**CSS features**:
- Video player styling
- Thumbnail styling with play overlay
- Upload form styling
- Progress indicator styling
- Modal video player styling
- Responsive video containers
- Loading animations
- Error state styling

### Step 3.5: Add JavaScript Functionality

**File**: `apps/mediafiles/static/mediafiles/js/videoclip.js`

**Action**: Create video-specific JavaScript

**JavaScript features**:
- Video upload progress tracking
- Client-side duration validation
- Video preview during upload
- Custom video player controls
- Modal video player functionality
- Video metadata display
- Error handling and user feedback
- Video compression (optional, client-side)

### Step 3.6: Create Template Tags

**File**: `apps/mediafiles/templatetags/mediafiles_tags.py`

**Action**: Add video-specific template tags

**Template tags**:
- `{% video_player videoclip %}` - Display video player
- `{% video_thumbnail videoclip %}` - Display video thumbnail
- `{% video_duration videoclip %}` - Format and display duration
- `{% video_modal_trigger videoclip %}` - Create modal trigger button

### Step 3.7: Security Testing

**File**: `apps/mediafiles/tests/test_security.py`

**Action**: Create comprehensive security tests for VideoClip

**Security test scenarios**:
- Video file enumeration prevention
- Video codec validation
- Container format validation
- Duration limit enforcement
- Malicious video file detection
- FFmpeg command injection prevention
- Video streaming security validation
- Thumbnail generation security

### Step 3.8: Integration Testing

**File**: `apps/mediafiles/tests/test_integration.py`

**Action**: Create end-to-end integration tests for VideoClip

**Test scenarios**:
- Complete video upload workflow
- Video appears in patient timeline
- Video player functionality
- Duration validation enforcement
- Permission-based access
- File cleanup on deletion
- Video streaming performance
- Cross-browser compatibility
- Security integration across all video components

### Step 3.9: Performance Testing

**File**: `apps/mediafiles/tests/test_performance.py`

**Action**: Create performance tests for video handling

**Performance tests**:
- Large video upload handling (up to 50MB)
- Video streaming performance
- Thumbnail generation speed
- Multiple video loading
- Database query optimization
- Memory usage during video processing

### Step 3.10: Browser Compatibility Testing

**Action**: Test video functionality across browsers

**Browser test scenarios**:
- Chrome/Chromium video playback
- Firefox video playback
- Safari video playback (if available)
- Mobile browser video playback
- Video format support testing
- HTML5 video controls functionality

### Step 3.11: User Acceptance Testing

**Action**: Create UAT scenarios for video functionality

**UAT scenarios**:
- Medical professional uploads procedure video
- Video appears in patient timeline with duration badge
- Video can be played with standard controls
- Video metadata is accurate and displayed
- Video can be edited within 24 hours
- Video integrates with existing event system
- Video download works properly
- Video quality is acceptable for medical use

## Success Criteria

Short Video Clips implementation is complete when:
- [ ] VideoClip model properly extends Event with VIDEO_CLIP_EVENT type
- [ ] MediaFile model handles video metadata and thumbnails
- [ ] Admin interface provides full video management
- [ ] Upload form includes duration and format validation
- [ ] Video detail view displays player with controls
- [ ] Event cards show video thumbnails with duration badges
- [ ] Video streaming works efficiently with range requests
- [ ] Thumbnail generation from first frame works reliably
- [ ] Permission system enforces 24-hour edit window
- [ ] All tests pass with >90% coverage
- [ ] Performance meets requirements (<10s upload for 2min video)
- [ ] Cross-browser video playback works
- [ ] Integration with patient timeline works seamlessly
- [ ] File cleanup works properly on deletion

## Final Integration Steps

After completing all three media types:
1. Test integration between Photo, PhotoSeries, and VideoClip
2. Ensure consistent UI/UX across all media types
3. Verify event timeline displays all media types properly
4. Test permission system across all media types
5. Validate performance with mixed media content
6. Complete end-to-end testing scenarios
7. Update documentation with all media features
8. Prepare for production deployment

## Success Criteria for Complete Media Feature

The media feature is fully implemented when:
- [ ] All three media types (Photo, PhotoSeries, VideoClip) work independently
- [ ] Event timeline displays all media types with appropriate cards
- [ ] Upload forms work for all media types
- [ ] Permission system works consistently across all types
- [ ] File storage and cleanup work properly
- [ ] Performance requirements are met for all media types
- [ ] All tests pass with comprehensive coverage
- [ ] Documentation is complete and accurate
- [ ] User acceptance testing scenarios pass
- [ ] Production deployment is ready
