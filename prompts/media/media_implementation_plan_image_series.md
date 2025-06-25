# Image Series Implementation Plan - Phase 2B

## Overview

This plan implements the PhotoSeries model for multiple image uploads in the EquipeMed media system. PhotoSeries will extend the base Event model and use the existing PHOTO_SERIES_EVENT type (9). Each series will contain multiple MediaFile instances with ordering capabilities and batch operations.

## Extra Requirements and Navigation Guidelines

### Navigation Requirements

- All photoseries operations (Create, Update, Delete, Detail) must return to the patient's timeline view
- PhotoSeries is accessible only from the "Criar Evento" dropdown in the patient's timeline view
- All photoseries pages must have consistent breadcrumb navigation: Patient Detail → Timeline → PhotoSeries page

### Styling Requirements

- Follow the overall styling and structure used for the photo feature from @app/mediafiles
- Maintain consistency with existing media file interfaces

### PhotoSeries Detail Page Requirements

- Display photoseries as a carousel with navigation between photos
- Each photo must have action buttons: zoom in, zoom out, original size, full page, download
- Similar to photo detail page but with carousel functionality

### Timeline Card Requirements

- Show number of photos in the series
- Display first photo as thumbnail
- Template location: @app/events/templates/events/partials/event_card_photoseries.html
- No zoom (bi-zoom-in) button - only download, details, and edit buttons

### Editing Requirements

- Users can only change: description, datetime, and caption
- Similar to photo editing functionality

## Vertical Slice 1: Model and Admin

### Step 1.1: Create PhotoSeriesFile Through Model

**File**: `apps/mediafiles/models.py`

**Action**: Implement through model for PhotoSeries-MediaFile relationship

**Model specifications**:

- UUID primary key
- ForeignKey to PhotoSeries
- ForeignKey to MediaFile
- PositiveIntegerField for ordering (order)
- CharField for individual image description (optional)
- Created/updated timestamps

**Key methods to implement**:

- `save()` - Auto-assign order if not provided
- `__str__()` - Return series and order information
- Meta class with ordering by 'order'
- Unique constraint on (photo_series, order)

### Step 1.2: Create PhotoSeries Model

**File**: `apps/mediafiles/models.py`

**Action**: Implement PhotoSeries model extending Event

**Model specifications**:

- Inherits from Event model
- ManyToManyField to MediaFile through PhotoSeriesFile
- Auto-set event_type to PHOTO_SERIES_EVENT in save()
- Custom manager for series-specific queries

**Key methods to implement**:

- `save()` - Set event_type and call super()
- `get_absolute_url()` - Return detail view URL
- `get_edit_url()` - Return edit view URL
- `get_timeline_return_url()` - Return patient timeline URL for navigation
- `get_primary_thumbnail()` - Return first image thumbnail (for timeline card)
- `get_photo_count()` - Return number of images in series (for timeline card)
- `get_ordered_photos()` - Return MediaFiles in order
- `add_photo(media_file, order=None, description='')` - Add photo to series
- `remove_photo(media_file)` - Remove photo from series
- `reorder_photos(photo_order_list)` - Reorder photos in series
- `clean()` - Validate series has at least one photo

### Step 1.3: Update MediaFile Model for Series

**File**: `apps/mediafiles/models.py`

**Action**: Add series-related methods to MediaFile with security enhancements

**New methods to add**:

- `get_series_info()` - Return series and order if part of series
- `is_in_series()` - Check if file is part of a series
- `get_series_position()` - Return position in series
- `get_secure_series_path()` - Generate secure path for series files
- `validate_series_file()` - Validate file for series inclusion

**Security enhancements for series**:

- Consistent UUID naming across series files
- Series-specific file validation
- Batch security validation for multiple uploads

### Step 1.4: Create Database Migration

**Action**: Generate and review migration for PhotoSeries models

```bash
uv run python manage.py makemigrations mediafiles
```

**Migration review checklist**:

- PhotoSeries model creation with Event inheritance
- PhotoSeriesFile through model creation
- ManyToMany relationship properly defined
- Unique constraints and indexes
- Ordering fields properly configured

### Step 1.5: Configure Admin Interface

**File**: `apps/mediafiles/admin.py`

**Action**: Create comprehensive admin interface for PhotoSeries management

**PhotoSeriesFileInline specifications**:

- TabularInline for PhotoSeriesFile
- Fields: media_file (thumbnail preview), order, description
- Extra = 0
- Sortable by order field
- Custom thumbnail display method

**PhotoSeriesAdmin specifications**:

- List display: primary_thumbnail, description, photo_count, patient, event_datetime
- List filters: event_datetime, created_by, patient\_\_current_hospital
- Search fields: description, patient\_\_name
- Inlines: PhotoSeriesFileInline
- Readonly fields: created_at, updated_at, photo_count
- Fieldsets: Event Info, Photos, Audit Trail
- Custom queryset with prefetch_related optimization

**Admin actions**:

- Bulk reorder photos action
- Export series as ZIP action
- Duplicate series action

### Step 1.6: Create Model Tests

**File**: `apps/mediafiles/tests/test_models.py`

**Action**: Implement comprehensive model testing for PhotoSeries

**Test cases for PhotoSeriesFile**:

- Through model creation and relationships
- Ordering functionality
- Unique constraints
- Description handling

**Test cases for PhotoSeries**:

- Event type auto-assignment
- Photo addition and removal
- Ordering and reordering
- Primary thumbnail selection
- Photo count calculation
- Validation rules (minimum photos)
- Manager methods

**Test utilities**:

- Factory classes for PhotoSeries and PhotoSeriesFile
- Helper methods for creating test series
- Bulk photo creation utilities

## Security Implementation for Image Series

### Security Requirements for Series

**Batch Upload Security**:

- Individual file validation for each image in series
- Consistent UUID naming across all series files
- Batch file size validation (total series size limits)
- Prevention of mixed file types in series
- Atomic upload operations (all or nothing)

**Series Access Security**:

- Permission validation for entire series
- Individual photo access control within series
- Secure batch download (ZIP) functionality
- Series modification audit logging

**File Organization Security**:

- Secure series file grouping
- Prevention of series file enumeration
- Consistent security policies across all series files

### Security Implementation for Series

**Secure Series Upload Path**:

```python
def get_secure_series_upload_path(instance, filename):
    ext = Path(filename).suffix.lower()
    if ext not in settings.MEDIA_ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"File extension {ext} not allowed")

    # Generate UUID with series prefix for organization
    uuid_filename = f"series_{uuid.uuid4()}{ext}"
    return f"photo_series/{timezone.now().strftime('%Y/%m')}/originals/{uuid_filename}"
```

**Batch File Validation**:

```python
def validate_series_files(files):
    total_size = 0
    for file in files:
        validate_photo_file(file)  # Individual validation
        total_size += file.size

    if total_size > settings.MEDIA_SERIES_MAX_TOTAL_SIZE:
        raise ValidationError("Series total size exceeds limit")
```

## Vertical Slice 2: Forms and Views

### Step 2.1: Create PhotoSeries Forms

**File**: `apps/mediafiles/forms.py`

**Action**: Implement forms for photo series upload and editing

**PhotoSeriesCreateForm specifications**:

- Fields: description, event_datetime, images (MultipleFileField)
- Custom images field with multiple file validation
- Individual file size and type validation
- Batch upload progress tracking
- Bootstrap styling with drag-and-drop interface

**PhotoSeriesUpdateForm specifications**:

- Fields: description, event_datetime, caption (limited editing per extra requirements)
- Separate form for adding/removing photos
- Photo reordering interface
- Individual photo description editing

**PhotoSeriesPhotoForm specifications**:

- Form for adding individual photos to existing series
- Fields: image, description, order
- AJAX-compatible for dynamic addition

**Form validation methods**:

- `clean_images()` - Validate multiple files with security checks
- `clean()` - Ensure at least one image and validate series constraints
- `validate_batch_security()` - Comprehensive security validation for all files
- `save()` - Handle secure multiple MediaFile creation and PhotoSeries setup

### Step 2.2: Create PhotoSeries Views

**File**: `apps/mediafiles/views.py`

**Action**: Implement CRUD views for photo series management

**PhotoSeriesCreateView specifications**:

- Extends CreateView
- Permission required: 'events.add_event'
- Handles multiple file upload
- Progress tracking for batch upload
- Patient parameter from URL
- Success redirect to patient timeline (required by navigation guidelines)
- Breadcrumb navigation: Patient Detail → Timeline → Create PhotoSeries

**PhotoSeriesDetailView specifications**:

- Extends DetailView
- Permission check with patient access validation
- Carousel display with navigation between photos (per extra requirements)
- Photo ordering display
- Individual photo metadata
- Action buttons for each photo: zoom in, zoom out, original size, full page, download
- Edit/delete action buttons (if permitted)
- Breadcrumb navigation: Patient Detail → Timeline → PhotoSeries Detail
- Return to timeline navigation

**PhotoSeriesUpdateView specifications**:

- Extends UpdateView
- Permission check: can_edit_event (24-hour rule)
- Form with current photos preview
- Limited editing: only description, datetime, and caption (per extra requirements)
- Add/remove photo functionality
- Reorder interface
- Success redirect to patient timeline (required by navigation guidelines)
- Breadcrumb navigation: Patient Detail → Timeline → Edit PhotoSeries

**PhotoSeriesDeleteView specifications**:

- Extends DeleteView
- Permission check: can_delete_event (24-hour rule)
- Confirmation page with photo previews
- Batch file cleanup on deletion
- Success redirect to patient timeline (required by navigation guidelines)
- Breadcrumb navigation: Patient Detail → Timeline → Delete PhotoSeries

### Step 2.3: Create AJAX Views

**File**: `apps/mediafiles/views.py`

**Action**: Implement AJAX views for dynamic photo management

**PhotoSeriesAddPhotoView specifications**:

- AJAX view for adding photos to existing series
- JSON response with new photo data
- Permission validation
- File processing and thumbnail generation

**PhotoSeriesRemovePhotoView specifications**:

- AJAX view for removing photos from series
- JSON response with success/error status
- File cleanup handling
- Order adjustment for remaining photos

**PhotoSeriesReorderView specifications**:

- AJAX view for reordering photos in series
- Accepts new order array
- Batch update of PhotoSeriesFile orders
- JSON response with updated order

### Step 2.4: Create URL Patterns

**File**: `apps/mediafiles/urls.py`

**Action**: Define URL patterns for photo series views

**URL patterns**:

- `photo-series/create/<uuid:patient_id>/` - PhotoSeriesCreateView
- `photo-series/<uuid:pk>/` - PhotoSeriesDetailView
- `photo-series/<uuid:pk>/edit/` - PhotoSeriesUpdateView
- `photo-series/<uuid:pk>/delete/` - PhotoSeriesDeleteView
- `photo-series/<uuid:pk>/add-photo/` - AJAX add photo
- `photo-series/<uuid:pk>/remove-photo/<uuid:photo_id>/` - AJAX remove photo
- `photo-series/<uuid:pk>/reorder/` - AJAX reorder photos
- `photo-series/<uuid:pk>/download/` - ZIP download

**URL naming convention**:

- `photoseries_create`, `photoseries_detail`, `photoseries_update`, `photoseries_delete`
- `photoseries_add_photo`, `photoseries_remove_photo`, `photoseries_reorder`

### Step 2.5: Create View Tests

**File**: `apps/mediafiles/tests/test_views.py`

**Action**: Implement comprehensive view testing for PhotoSeries

**Test cases**:

- Series creation with multiple photos
- Photo addition/removal via AJAX
- Photo reordering functionality
- Permission-based access control
- Batch file upload handling
- ZIP download functionality
- 24-hour edit window enforcement

## Vertical Slice 3: Templates and Testing

### Step 3.1: Create PhotoSeries Templates

**File**: `apps/mediafiles/templates/mediafiles/photoseries_form.html`

**Action**: Create photo series upload/edit form template

**Template features**:

- Multiple file upload with drag-and-drop
- Upload progress indicators for each file
- Photo preview grid during upload
- Batch upload controls (select all, remove all)
- Individual photo description fields
- Client-side image resizing for each photo
- Validation error display per photo

**File**: `apps/mediafiles/templates/mediafiles/photoseries_detail.html`

**Action**: Create photo series detail view template (per extra requirements)

**Template features**:

- Carousel display with navigation between photos (per extra requirements)
- Action buttons for each photo: zoom in, zoom out, original size, full page, download (per extra requirements)
- Photo ordering display with reorder controls
- Individual photo metadata display
- Series metadata (total count, upload date)
- Series action buttons (edit, delete, download ZIP)
- Breadcrumb navigation: Patient Detail → Timeline → PhotoSeries Detail
- Return to timeline navigation
- Follow styling from @app/mediafiles photo feature
- Responsive design for mobile

### Step 3.2: Create Event Card Template

**File**: `apps/events/templates/events/partials/event_card_photoseries.html`

**Action**: Create specialized event card for photo series (per extra requirements)

**Template features**:

- First photo as thumbnail display (per extra requirements)
- Photo count badge showing number of photos in series (per extra requirements)
- Images icon overlay
- Event metadata (datetime, description)
- Click to open series detail view
- Download, details, and edit buttons ONLY (no zoom/bi-zoom-in button per extra requirements)
- Responsive design for mobile
- Follow styling from @app/mediafiles photo feature

### Step 3.3: Create Photo Gallery Components

**File**: `apps/mediafiles/templates/mediafiles/partials/photo_gallery.html`

**Action**: Create reusable photo gallery component

**Template features**:

- Responsive thumbnail grid
- Lazy loading for performance
- Click to open in lightbox
- Photo ordering indicators
- Individual photo actions (if editable)
- Keyboard navigation support

**File**: `apps/mediafiles/templates/mediafiles/partials/photo_lightbox.html`

**Action**: Create lightbox modal for photo viewing

**Template features**:

- Full-size photo display
- Navigation arrows (previous/next)
- Photo counter (e.g., "3 of 8")
- Zoom functionality
- Photo metadata overlay
- Download individual photo button
- Keyboard shortcuts (arrow keys, escape)

### Step 3.4: Create Upload Interface

**File**: `apps/mediafiles/templates/mediafiles/partials/multi_upload.html`

**Action**: Create advanced multi-file upload interface

**Template features**:

- Drag-and-drop zone
- File selection button
- Upload queue with progress bars
- Photo preview thumbnails
- Individual file controls (remove, reorder)
- Batch operations (clear all, upload all)
- Error handling per file

### Step 3.5: Add CSS Styling

**File**: `apps/mediafiles/static/mediafiles/css/photoseries.css`

**Action**: Create photo series specific styling (following @app/mediafiles photo feature styling)

**CSS features**:

- Carousel layout (responsive) instead of gallery grid
- Action buttons styling for each photo (zoom in, zoom out, original size, full page, download)
- Upload interface styling consistent with photo feature
- Progress indicator animations
- Drag-and-drop visual feedback
- Photo ordering controls
- Timeline card styling (first photo thumbnail, photo count badge)
- Breadcrumb navigation styling
- Mobile-optimized layouts
- Consistent styling with existing photo feature

### Step 3.6: Add JavaScript Functionality

**File**: `apps/mediafiles/static/mediafiles/js/photoseries.js`

**Action**: Create photo series specific JavaScript

**JavaScript features**:

- Multi-file upload handling
- Drag-and-drop functionality
- Photo reordering (sortable interface)
- AJAX photo addition/removal
- Carousel navigation between photos (per extra requirements)
- Photo action buttons functionality: zoom in, zoom out, original size, full page, download
- Client-side image resizing
- Upload progress tracking
- Error handling and user feedback
- Breadcrumb navigation handling
- Return to timeline functionality

### Step 3.7: Create Template Tags

**File**: `apps/mediafiles/templatetags/mediafiles_tags.py`

**Action**: Add photo series specific template tags

**Template tags**:

- `{% photoseries_carousel series %}` - Display photo carousel (per extra requirements)
- `{% photoseries_thumbnail series %}` - Display first photo thumbnail (per extra requirements)
- `{% photoseries_count series %}` - Display photo count badge (per extra requirements)
- `{% photoseries_action_buttons photo %}` - Create action buttons for each photo
- `{% photoseries_breadcrumb series %}` - Generate breadcrumb navigation

### Step 3.8: Security Testing

**File**: `apps/mediafiles/tests/test_security.py`

**Action**: Create comprehensive security tests for PhotoSeries

**Security test scenarios**:

- Batch upload security validation
- Series file enumeration prevention
- Mixed file type upload prevention
- Series size limit enforcement
- Individual file security in series context
- ZIP download security validation
- Series modification permission checks

### Step 3.9: Integration Testing

**File**: `apps/mediafiles/tests/test_integration.py`

**Action**: Create end-to-end integration tests for PhotoSeries

**Test scenarios**:

- Complete photo series upload workflow
- Photo series viewing in patient timeline
- Gallery and lightbox functionality
- Photo reordering via drag-and-drop
- AJAX photo addition/removal
- ZIP download functionality
- Permission-based access control
- Security integration across all series components

### Step 3.10: Performance Testing

**File**: `apps/mediafiles/tests/test_performance.py`

**Action**: Create performance tests for photo series

**Performance tests**:

- Large batch upload handling (10+ photos)
- Gallery loading with many photos
- Thumbnail generation performance
- Database query optimization
- Memory usage during batch operations

### Step 3.11: User Acceptance Testing

**Action**: Create UAT scenarios for photo series functionality

**UAT scenarios**:

- Medical professional uploads wound progression series
- Series appears in patient timeline with count badge
- Individual photos can be viewed in gallery
- Photos can be reordered to show progression
- Series can be edited within 24 hours
- ZIP download provides all photos
- Integration with existing event system works

## Success Criteria

Image Series implementation is complete when:

- [ ] PhotoSeries model properly extends Event with PHOTO_SERIES_EVENT type
- [ ] PhotoSeriesFile through model handles ordering and relationships
- [ ] Admin interface provides full series management with inline editing
- [ ] Multi-file upload form includes drag-and-drop and progress tracking
- [ ] Carousel view displays photos with navigation (per extra requirements)
- [ ] Each photo has action buttons: zoom in, zoom out, original size, full page, download (per extra requirements)
- [ ] Event cards show first photo thumbnail with photo count badge (per extra requirements)
- [ ] Event cards have only download, details, and edit buttons (no zoom button per extra requirements)
- [ ] Photo reordering works via drag-and-drop interface
- [ ] AJAX photo addition/removal functions properly
- [ ] ZIP download provides all photos in series
- [ ] Permission system enforces 24-hour edit window
- [ ] Editing limited to description, datetime, and caption only (per extra requirements)
- [ ] All operations return to patient timeline (per navigation requirements)
- [ ] Breadcrumb navigation works: Patient Detail → Timeline → PhotoSeries (per navigation requirements)
- [ ] Styling follows @app/mediafiles photo feature (per styling requirements)
- [ ] All tests pass with >90% coverage
- [ ] Performance meets requirements (<5s for 10 photos upload)
- [ ] Integration with patient timeline works seamlessly
- [ ] File cleanup works properly on deletion

## Next Steps

After completing Image Series implementation:

1. Proceed to Short Video Clips implementation
2. Test integration between all media types
3. Ensure consistent UI/UX across all media types
