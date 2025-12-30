# Single Image Implementation Plan - Phase 2A

## Overview

This plan implements the Photo model for single image uploads in the EquipeMed media system. Photos will extend the base Event model and use the existing PHOTO_EVENT type (3). Each photo will have a single associated MediaFile with automatic thumbnail generation and multiple size variants.

## Vertical Slice 1: Model and Admin

### Step 1.1: Create MediaFile Model

**File**: `apps/mediafiles/models.py`

**Action**: Implement the base MediaFile model for file storage and metadata

**Model specifications**:

- UUID primary key
- FileField with secure UUID-based upload paths (`photos/YYYY/MM/originals/uuid.ext`)
- Metadata fields: original_filename, secure_filename, file_size, mime_type, width, height
- File hash field for deduplication (SHA-256)
- Thumbnail ImageField with UUID naming (`photos/YYYY/MM/thumbnails/uuid.jpg`)
- Created/updated timestamps
- File validation methods
- Thumbnail generation methods
- Secure file naming utilities

**Key methods to implement**:

- `save()` - Override to generate secure filename, thumbnails, and extract metadata
- `clean()` - Validate file type, size, and security constraints
- `get_thumbnail_url()` - Return thumbnail URL with fallback
- `get_display_size()` - Return human-readable file size
- `get_secure_url()` - Return secure file URL for authorized access
- `calculate_file_hash()` - Generate SHA-256 hash for deduplication
- `normalize_original_filename()` - Sanitize original filename
- `__str__()` - Return original filename

### Step 1.2: Create Photo Model

**File**: `apps/mediafiles/models.py`

**Action**: Implement Photo model extending Event

**Model specifications**:

- Inherits from Event model
- OneToOneField to MediaFile
- Auto-set event_type to PHOTO_EVENT in save()
- Custom manager for photo-specific queries

**Key methods to implement**:

- `save()` - Set event_type and call super()
- `get_absolute_url()` - Return detail view URL
- `get_edit_url()` - Return edit view URL
- `get_thumbnail()` - Delegate to media_file.get_thumbnail_url()
- `clean()` - Validate media_file is an image

### Step 1.3: Create Database Migration

**Action**: Generate and review migration for new models

```bash
uv run python manage.py makemigrations mediafiles
```

**Migration review checklist**:

- MediaFile model creation with proper field types
- Photo model creation with Event inheritance
- Foreign key relationships properly defined
- Indexes on commonly queried fields

### Step 1.4: Configure Admin Interface

**File**: `apps/mediafiles/admin.py`

**Action**: Create comprehensive admin interface for Photo management

**PhotoAdmin specifications**:

- List display: thumbnail preview, description, patient, event_datetime, created_by
- List filters: event_datetime, created_by, patient__current_hospital
- Search fields: description, patient__name, original_filename
- Readonly fields: created_at, updated_at, file_size, mime_type, width, height
- Fieldsets: Event Info, Media File, Metadata, Audit Trail
- Thumbnail preview in detail view
- Custom queryset with select_related optimization

**MediaFileAdmin specifications**:

- List display: thumbnail, original_filename, file_size, mime_type, created_at
- List filters: mime_type, created_at
- Search fields: original_filename
- Readonly fields: file_size, mime_type, width, height, thumbnail
- Thumbnail preview method

### Step 1.5: Security Implementation

**File**: `apps/mediafiles/models.py`

**Action**: Implement security features in MediaFile model

**Security features to implement**:

- UUID-based secure filename generation
- File extension validation
- MIME type validation
- File size validation
- Path traversal prevention
- File hash calculation for deduplication
- Original filename sanitization

**Security methods**:

```python
def get_secure_upload_path(instance, filename):
    """Generate secure upload path with UUID filename"""

def validate_image_file(file):
    """Comprehensive image file validation"""

def sanitize_filename(filename):
    """Remove dangerous characters from filename"""
```

### Step 1.6: Create Model Tests

**File**: `apps/mediafiles/tests/test_models.py`

**Action**: Implement comprehensive model testing

**Test cases for MediaFile**:

- File upload and metadata extraction
- Thumbnail generation
- File validation (type, size, security)
- URL generation methods
- String representation
- Secure filename generation
- File hash calculation
- Deduplication functionality

**Test cases for Photo**:

- Event type auto-assignment
- Media file relationship
- Validation rules
- URL generation
- Manager methods
- Security constraints

**Security test cases**:

- Path traversal attack prevention
- File extension validation
- MIME type spoofing detection
- Malicious file upload prevention
- Filename sanitization

**Test utilities**:

- Factory classes using factory_boy
- Sample image file creation
- Malicious file samples for security testing
- Test file cleanup

## Security Implementation for Single Images

### Security Requirements

**File Security**:

- UUID-based filenames prevent enumeration attacks
- Original filenames stored in database only
- File extension validation against whitelist
- MIME type validation with magic number checking
- File size limits enforced
- Path traversal prevention

**Access Security**:

- Permission-based file access
- Patient context validation
- Secure file serving through Django views
- No direct file system access
- Audit logging for file access

**Data Security**:

- File hash calculation for integrity
- Deduplication prevents storage waste
- Secure file deletion with cleanup
- No patient information in file paths

### Security Implementation Details

**Secure Upload Path Generation**:

```python
def get_secure_photo_upload_path(instance, filename):
    ext = Path(filename).suffix.lower()
    if ext not in settings.MEDIA_ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"File extension {ext} not allowed")

    uuid_filename = f"{uuid.uuid4()}{ext}"
    return f"photos/{timezone.now().strftime('%Y/%m')}/originals/{uuid_filename}"
```

**File Validation**:

```python
def validate_photo_file(file):
    # Size validation
    if file.size > settings.MEDIA_IMAGE_MAX_SIZE:
        raise ValidationError("File too large")

    # MIME type validation
    if file.content_type not in settings.MEDIA_ALLOWED_IMAGE_TYPES:
        raise ValidationError("Invalid file type")

    # Magic number validation
    file.seek(0)
    header = file.read(1024)
    if not is_valid_image_header(header):
        raise ValidationError("Invalid image file")
```

## Vertical Slice 2: Forms and Views

### Step 2.1: Create Photo Forms

**File**: `apps/mediafiles/forms.py`

**Action**: Implement forms for photo upload and editing

**PhotoCreateForm specifications**:

- Fields: description, event_datetime, image (FileField)
- Custom image field with validation
- File size and type validation
- Preview functionality with JavaScript
- Bootstrap styling with proper classes

**PhotoUpdateForm specifications**:

- Fields: description, event_datetime (no image change)
- Inherits validation from PhotoCreateForm
- Displays current image thumbnail

**Form validation methods**:

- `clean_image()` - Validate file type, size, format, and security constraints
- `clean_event_datetime()` - Ensure datetime is not in future
- `validate_file_security()` - Check for malicious content and path traversal
- `save()` - Handle secure MediaFile creation and Photo instance

### Step 2.2: Create Photo Views

**File**: `apps/mediafiles/views.py`

**Action**: Implement CRUD views for photo management

**PhotoCreateView specifications**:

- Extends CreateView
- Permission required: 'events.add_event'
- Hospital context validation
- Patient parameter from URL
- Success redirect to patient timeline
- Form processing with file handling

**PhotoDetailView specifications**:

- Extends DetailView
- Permission check with patient access validation
- Full-size image display
- Metadata display
- Edit/delete action buttons (if permitted)

**PhotoUpdateView specifications**:

- Extends UpdateView
- Permission check: can_edit_event (24-hour rule)
- Form with current image preview
- Success redirect to detail view

**PhotoDeleteView specifications**:

- Extends DeleteView
- Permission check: can_delete_event (24-hour rule)
- Confirmation page with image preview
- File cleanup on deletion
- Success redirect to patient timeline

### Step 2.3: Create URL Patterns

**File**: `apps/mediafiles/urls.py`

**Action**: Define URL patterns for photo views

**URL patterns**:

- `photos/create/<uuid:patient_id>/` - PhotoCreateView
- `photos/<uuid:pk>/` - PhotoDetailView
- `photos/<uuid:pk>/edit/` - PhotoUpdateView
- `photos/<uuid:pk>/delete/` - PhotoDeleteView
- `photos/<uuid:pk>/download/` - File download view

**URL naming convention**:

- `photo_create`, `photo_detail`, `photo_update`, `photo_delete`, `photo_download`

### Step 2.4: Implement File Serving Views

**File**: `apps/mediafiles/views.py`

**Action**: Create secure file serving views

**PhotoDownloadView specifications**:

- Permission-protected file serving
- Patient access validation
- Secure file path resolution (no direct file system access)
- Proper HTTP headers for file download
- Support for different image sizes (thumbnail, medium, large)
- Browser caching headers
- Access logging for audit trails
- Rate limiting for download requests

### Step 2.5: Create View Tests

**File**: `apps/mediafiles/tests/test_views.py`

**Action**: Implement comprehensive view testing

**Test cases**:

- Photo creation with valid/invalid data
- Permission-based access control
- File upload handling
- Patient context validation
- 24-hour edit window enforcement
- File serving and download functionality

## Vertical Slice 3: Templates and Testing

### Step 3.1: Create Base Templates

**File**: `apps/mediafiles/templates/mediafiles/base.html`

**Action**: Create base template for mediafiles views

**Template specifications**:

- Extends main site base template
- Media-specific CSS and JavaScript includes
- Breadcrumb navigation
- Common media styling

### Step 3.2: Create Photo Templates

**File**: `apps/mediafiles/templates/mediafiles/photo_form.html`

**Action**: Create photo upload/edit form template

**Template features**:

- Bootstrap form styling
- File upload with preview
- Progress indicator for upload
- Client-side image resizing (JavaScript)
- Validation error display
- Cancel/submit buttons

**File**: `apps/mediafiles/templates/mediafiles/photo_detail.html`

**Action**: Create photo detail view template

**Template features**:

- Full-size image display with zoom functionality
- Image metadata display
- Event information (patient, datetime, description)
- Action buttons (edit, delete) with permission checks
- Navigation back to patient timeline
- Download link

**File**: `apps/mediafiles/templates/mediafiles/photo_confirm_delete.html`

**Action**: Create photo deletion confirmation template

**Template features**:

- Image preview
- Confirmation message
- Cancel/delete buttons
- Warning about permanent deletion

### Step 3.3: Create Event Card Template

**File**: `apps/events/templates/events/partials/event_card_photo.html`

**Action**: Create specialized event card for photos

**Template features**:

- Thumbnail display (300x200px)
- Camera icon overlay
- Event metadata (datetime, description)
- Click to open in modal or detail view
- Edit/delete buttons (if permitted)
- Responsive design for mobile

### Step 3.4: Create Photo Modal Template

**File**: `apps/mediafiles/templates/mediafiles/partials/photo_modal.html`

**Action**: Create modal for photo viewing

**Template features**:

- Full-size image display
- Image zoom functionality
- Navigation controls (if part of series)
- Metadata overlay
- Download button
- Close button

### Step 3.5: Add CSS Styling

**File**: `apps/mediafiles/static/mediafiles/css/photo.css`

**Action**: Create photo-specific styling

**CSS features**:

- Image thumbnail styling
- Modal overlay styling
- Upload form styling
- Responsive image display
- Loading indicators
- Hover effects

### Step 3.6: Add JavaScript Functionality

**File**: `apps/mediafiles/static/mediafiles/js/photo.js`

**Action**: Create photo-specific JavaScript

**JavaScript features**:

- Client-side image resizing before upload
- Upload progress indication
- Image preview functionality
- Modal image viewer
- Zoom and pan functionality
- File validation feedback

### Step 3.7: Create Template Tags

**File**: `apps/mediafiles/templatetags/mediafiles_tags.py`

**Action**: Create photo-specific template tags

**Template tags**:

- `{% photo_thumbnail photo size %}` - Display photo thumbnail
- `{% photo_modal_trigger photo %}` - Create modal trigger button
- `{% photo_metadata photo %}` - Display photo metadata
- `{% photo_file_size photo %}` - Format file size display

### Step 3.8: Security Testing

**File**: `apps/mediafiles/tests/test_security.py`

**Action**: Create comprehensive security tests

**Security test scenarios**:

- File enumeration attack prevention
- Path traversal attack prevention
- Malicious file upload prevention
- MIME type spoofing detection
- File extension validation
- Filename sanitization
- Permission-based access control
- Secure file serving validation

### Step 3.9: Integration Testing

**File**: `apps/mediafiles/tests/test_integration.py`

**Action**: Create end-to-end integration tests

**Test scenarios**:

- Complete photo upload workflow
- Photo viewing in patient timeline
- Modal functionality
- Permission-based access
- File cleanup on deletion
- Error handling and user feedback
- Security integration across all components

### Step 3.10: Performance Testing

**File**: `apps/mediafiles/tests/test_performance.py`

**Action**: Create performance tests for photo handling

**Performance tests**:

- Large image upload handling
- Thumbnail generation speed
- Multiple photo loading
- Database query optimization
- File serving performance

### Step 3.11: User Acceptance Testing

**Action**: Create UAT scenarios for photo functionality

**UAT scenarios**:

- Medical professional uploads wound photo
- Photo appears in patient timeline
- Photo can be viewed in detail
- Photo metadata is accurate
- Photo can be edited within 24 hours
- Photo integrates with existing event system

## Success Criteria

Single Image implementation is complete when:

- [ ] Photo model properly extends Event with PHOTO_EVENT type
- [ ] MediaFile model handles file storage and metadata
- [ ] Admin interface provides full photo management
- [ ] Upload form includes client-side resizing and validation
- [ ] Photo detail view displays full-size image with metadata
- [ ] Event cards show photo thumbnails appropriately
- [ ] Modal viewer provides zoom and navigation functionality
- [ ] Permission system enforces 24-hour edit window
- [ ] All tests pass with >90% coverage
- [ ] Performance meets requirements (<2s upload, <1s display)
- [ ] Integration with patient timeline works seamlessly
- [ ] File cleanup works properly on deletion

## Next Steps

After completing Single Image implementation:

1. Proceed to Image Series implementation
2. Ensure Photo model integration with PhotoSeries
3. Test cross-functionality between single and series photos
