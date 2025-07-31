# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Essential Commands

### Development

```bash
# Development server
uv run python manage.py runserver

# Database
uv run python manage.py migrate
uv run python manage.py makemigrations
uv run python manage.py createsuperuser

# Testing

## Test Running Options

### Option 1: pytest (Recommended for most cases)
```bash
# All tests with coverage (requires DJANGO_SETTINGS_MODULE)
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest

# All tests without coverage
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest --no-cov

# Specific app tests with coverage
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/pdf_forms/tests/

# Single test file
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/pdf_forms/tests/test_models.py

# Single test method
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/pdf_forms/tests/test_models.py::PDFFormTemplateTests::test_str_method
```

### Option 2: Django test runner (Use for specific apps)
```bash
# For apps that work better with Django's test runner
uv run python manage.py test apps.patients.tests
uv run python manage.py test apps.core.tests.test_permissions

# For specific test files
uv run python manage.py test apps.pdf_forms.tests.test_models
```

### Option 3: pytest with coverage reports
```bash
# Generate HTML coverage report (opens in browser)
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest --cov=apps --cov-report=html

# Coverage for specific app with terminal output
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/pdf_forms/tests/ --cov=apps.pdf_forms --cov-report=term-missing
```

## Which to Use?
- **Use pytest** for most testing (faster, better features, coverage)
- **Use Django test runner** for specific apps that have import issues
- **Set DJANGO_SETTINGS_MODULE** when using pytest to avoid configuration errors

# Frontend
npm install && npm run build

# Python environment
uv install
uv add package-name

# Sample data
uv run python manage.py create_sample_tags
uv run python manage.py create_sample_wards
uv run python manage.py create_sample_content
uv run python manage.py create_sample_pdf_forms
```

## Project Architecture

**EquipeMed** - Django 5 medical team collaboration platform for single-hospital patient tracking and care management.

### Apps Overview

- **core**: Dashboard, permissions, landing page, hospital configuration
- **accounts**: Custom user model with medical professions (Doctor, Resident, Nurse, Physiotherapist, Student)
- **patients**: Patient management with tagging system and status tracking
- **events**: Base event model for medical records (UUID, audit trail, 24h edit window)
- **dailynotes**: Daily evolution notes extending Event model
- **sample_content**: Template content management for various event types
- **mediafiles**: Secure media file management for medical images and videos
- **pdf_forms**: Hospital-specific PDF form overlay functionality with dynamic form generation

### Key Features

- **Authentication**: django-allauth with email-based login
- **Frontend**: Bootstrap 5.3, Webpack, Portuguese localization
- **Security**: UUID identifiers, CSRF protection, role-based permissions
- **Testing**: pytest + Django test runner, factory-boy, comprehensive coverage
- **Hospital Configuration**: Environment-based single hospital setup
- **Permission System**: Simple role-based access control for medical staff

## App Details

### Patients App

**Full CRUD patient management with tagging system and status tracking**

- Patient models: Patient, AllowedTag, Tag
- Search by name, ID, fiscal/health card numbers
- Status tracking: inpatient, outpatient, emergency, discharged, transferred, deceased
- Gender field: Masculino, Feminino, Outro, Não Informado (default for legacy data)
- Color-coded tagging system with web admin interface
- Dashboard widgets: patient stats, recent patients
- Template tags: `patient_status_badge`, `patient_tags`
- URL structure: `/patients/`, `/patients/<uuid>/`, `/patients/tags/`

#### Patient Status Management

- **Status Types**: inpatient, outpatient, emergency, discharged, transferred, deceased
- **Role-Based Access**: Different access levels based on user profession and patient status
- **Death Declaration**: Only doctors/residents can declare death (change to deceased status)
- **Admin Override**: Only admin/superuser can change deceased patients (for data corrections)
- **Simple Validation**: Basic status validation without complex assignment logic
- **Universal Access**: All medical staff can access all patients regardless of status

### Events App

**Base event system for medical records**

- Event types: History/Physical, Daily Notes, Photos, Exam Results, etc.
- UUID primary keys, audit trail, 24-hour edit/delete window
- django-model-utils inheritance for extensibility
- URLs: `/events/patient/<uuid>/`, `/events/user/`

#### Timeline Template Architecture

**Modular event card system with type-specific functionality**

- **Template Partials**: Located in `apps/events/templates/events/partials/`
  - `event_card_base.html` - Base template with common structure
  - `event_card_dailynote.html` - DailyNote-specific card with duplicate button
  - `event_card_default.html` - Standard card for other event types
- **Dynamic Rendering**: Timeline uses `event.event_type` to select appropriate template
- **Event Type Detection**: `event.event_type == 1` identifies DailyNote events
- **Extensibility**: Easy to add custom cards for new event types

### Daily Notes App

**Medical evolution notes extending Event model**

- DailyNote model inherits from Event
- Portuguese localization ("Evolução"/"Evoluções")
- Automatic event_type assignment
- Admin interface with fieldsets and optimizations

#### Advanced Features (Slice 5)

- **Patient Integration**: Patient-specific daily note views with date filtering
- **Search & Filtering**: Advanced search by content, patient, creator, and date ranges
- **Dashboard Integration**: Recent daily notes widget and statistics counters
- **Export/Print**: Print-friendly individual notes and patient evolution reports
- **URLs**: `/dailynotes/`, `/dailynotes/patient/<uuid>/`, `/dailynotes/<uuid>/print/`
- **Template Tags**: `recent_dailynotes_widget`, `dailynotes_count_today`, `dailynotes_count_week`

#### Duplicate Functionality

**Create new dailynotes based on existing ones**

- **Multiple Access Points**: Available from detail page, list views, and patient timeline
- **Pre-population**: Original content copied, datetime set to current time
- **Permission-Based**: Only visible to users with `events.add_event` permission
- **Timeline Integration**: Specialized event card template with duplicate button
- **URL Pattern**: `/dailynotes/<uuid>/duplicate/`
- **Success Redirect**: Returns to patient timeline after creation

#### Performance Optimizations (Slice 6)

- **Database Optimization**: Added indexes for common query patterns on Event model
- **Query Optimization**: Enhanced views with `select_related()` and `prefetch_related()`
- **Pagination**: Improved pagination with `paginate_orphans` for better UX
- **Permission Caching**: Bulk patient access checks with `get_user_accessible_patients()`
- **Filter Caching**: Cached filter dropdown options for list views (5-minute cache)
- **Query Patterns**: Optimized patient/creator lookups with `only()` clauses

### Sample Content App

**Template content management for various event types**

- SampleContent model with UUID primary key, title, content, and event_type fields
- Integrates with Event.EVENT_TYPE_CHOICES for consistent event type mapping
- Superuser-only create/edit/delete permissions, all authenticated users can read
- Admin interface with proper field organization and permission controls
- Web interface with event type filtering and pagination
- API endpoint for retrieving sample content by event type
- URL structure: `/sample-content/`, `/sample-content/api/event-type/<id>/`

#### Key Features

- **Permission Model**: Read access for all users, write access restricted to superusers
- **Event Type Integration**: Uses same event types as Event model for consistency
- **Template Management**: Pre-defined content templates for common medical documentation
- **API Access**: JSON endpoint for programmatic access to sample content
- **Search & Filter**: Filter by event type, paginated results
- **Audit Trail**: Standard created_by/updated_by fields for tracking changes

#### Usage Examples

```python
# Get sample content for daily notes
sample_contents = SampleContent.objects.filter(event_type=Event.DAILY_NOTE_EVENT)

# API access
GET /sample-content/api/event-type/1/  # Returns JSON with daily note templates
```

#### Management Commands

```bash
uv run python manage.py create_sample_content  # Create initial sample content templates
```

### MediaFiles App

**Secure media file management for medical images and videos**

- Models: MediaFile (for photos), Photo, PhotoSeries, VideoClip (FilePond-based) extending Event model
- Security: UUID-based file naming, SHA-256 hash deduplication, comprehensive validation
- File types: Single images, image series, short video clips (up to 2 minutes)
- Processing: Automatic thumbnail generation, metadata extraction, secure file serving
- Integration: Seamless Event system integration with timeline display
- URL structure: `/mediafiles/file/<uuid>/`, `/mediafiles/thumbnail/<uuid>/`, `/mediafiles/fp/` (FilePond)

#### Key Features

- **Secure File Storage**: UUID-based filenames prevent enumeration attacks
- **File Deduplication**: SHA-256 hash-based duplicate detection and storage optimization (photos only)
- **Permission-Based Access**: Role-based access control
- **Multiple Media Types**: Photos (PHOTO_EVENT = 3), Photo Series (PHOTO_SERIES_EVENT = 9), Videos (VIDEO_CLIP_EVENT = 10)
- **Thumbnail Generation**: Automatic thumbnails for images and video previews
- **Audit Trail**: Complete access logging and file operation tracking
- **FilePond Integration**: Modern video upload with server-side H.264 conversion

#### Security Implementation

- **File Validation**: MIME type, extension, size, and content validation
- **Path Protection**: Comprehensive path traversal and injection protection
- **Secure Serving**: All files served through Django views with permission checks
- **Rate Limiting**: Configurable limits for file access and uploads
- **Access Control**: Integration with existing patient permission system

#### File Storage Structure

```
media/
├── photos/YYYY/MM/originals/uuid-filename.ext
├── photo_series/YYYY/MM/originals/uuid-filename.ext
└── videos/YYYY/MM/originals/uuid-filename.ext
```

#### Multiple File Upload Implementation

**PhotoSeries supports multiple file uploads using Django 5.2 best practices**

##### Custom Multiple File Field

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

##### PhotoSeries Form Implementation

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

##### Key Features

- **Django 5.2 Compatibility**: Uses `allow_multiple_selected = True` pattern
- **Batch Validation**: Individual file validation for size, type, and security
- **Template Integration**: Works with existing drag-and-drop upload interface
- **Security**: Comprehensive validation and secure file handling
- **User Experience**: Preview thumbnails and upload progress tracking

##### Usage in Views

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

##### Implementation Notes

**Important:** Django's built-in `FileField` and `FileInput` widgets do NOT support multiple file uploads by default. The implementation above is required for multiple file functionality.

**Common Issues:**

- `ValueError: FileInput doesn't support uploading multiple files` - Use `MultipleFileInput` with `allow_multiple_selected = True`
- Single file upload only - Ensure the form field uses `MultipleFileField` instead of `forms.FileField`
- Form validation errors - The `clean_images()` method expects a list of files from `cleaned_data['images']`

**Template Requirements:**

- The upload interface in `photoseries_form.html` includes drag-and-drop functionality
- JavaScript in `photoseries.js` handles the upload preview and progress tracking
- The `multi_upload.html` partial provides advanced upload UI components

#### VideoClip Current Architecture (Post-FilePond Migration)

**Modern video upload system using django-drf-filepond with server-side H.264 conversion**

##### ✅ Current Status: Fully Operational

- **Video uploads**: Working correctly with FilePond interface
- **File storage**: UUID-based files in structured directories (`media/videos/YYYY/MM/originals/`)
- **Video streaming**: Custom streaming views serving files with proper headers
- **Server-side conversion**: H.264/MP4 conversion with mobile optimization
- **Performance**: 99% JavaScript bundle size reduction (6.6KB → 376 bytes)

##### VideoClip Model Architecture

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

##### File Storage Structure

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

##### Video Processing Pipeline

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

##### VideoClipCreateForm Implementation

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

##### Configuration Requirements (Fixed)

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

##### Video Streaming Implementation

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

##### Migration Impact

- **Database Changes**: VideoClip model migrated from MediaFile relationship to direct file metadata storage
- **Bundle Optimization**: Removed videoclipCompression and videoclipPlayer bundles
- **Template Simplification**: FilePond-based template with CDN resources for upload interface
- **URL Structure**: Added `/mediafiles/fp/` endpoints for FilePond file processing

#### Template Tags

```django
{% load mediafiles_tags %}
{% mediafiles_thumbnail media_file size="medium" %}
{% mediafiles_duration video.duration %}
{% mediafiles_file_size media_file.file_size %}
```

#### Frontend JavaScript Architecture (Optimized)

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

### PDF Forms App

**Hospital-specific PDF form overlay functionality with dynamic form generation**

- Models: PDFFormTemplate, PDFFormSubmission extending Event model
- Dynamic form generation from JSON field configuration with coordinate-based positioning
- Integration with Event system for timeline display and audit trail
- Data-only storage approach with on-demand PDF generation for optimal storage efficiency
- Permission-based access control with patient access validation
- URL structure: `/pdf-forms/select/<patient_id>/`, `/pdf-forms/fill/<template_id>/<patient_id>/`

#### Key Features

- **Manual Field Configuration**: Coordinate-based positioning using centimeter measurements for precise PDF overlay
- **Dynamic Forms**: Generate Django forms from PDF template field mappings with support for text, choice, boolean, date, and textarea fields
- **On-Demand PDF Generation**: PDFs generated dynamically during downloads using ReportLab and PyPDF2 for optimal storage efficiency
- **Data-Only Storage**: Only form submission data stored in database, achieving 95%+ storage reduction compared to file-based approach
- **Event Integration**: PDF submissions appear in patient timeline with generate-and-download capabilities
- **Hospital Configuration**: Enable/disable per hospital installation with environment variable control
- **Security**: Comprehensive permission checks, data validation, and secure PDF generation
- **Universal PDF Support**: Works with any PDF format including scanned documents and legacy hospital forms

#### Field Configuration Structure

The system uses JSON-based field configuration with precise coordinate positioning:

```json
{
  "patient_name": {
    "type": "text",
    "label": "Nome do Paciente",
    "x": 4.5,           // cm from left edge
    "y": 8.5,           // cm from top edge  
    "width": 12.0,      // cm width
    "height": 0.7,      // cm height
    "font_size": 12,
    "required": true,
    "max_length": 200
  },
  "blood_type": {
    "type": "choice",
    "label": "Tipo Sanguíneo", 
    "x": 4.5,
    "y": 10.0,
    "width": 3.0,
    "height": 0.7,
    "choices": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
    "required": true
  }
}
```

#### Usage Examples

```bash
# Enable PDF forms for hospital
export HOSPITAL_PDF_FORMS_ENABLED=true

# Management commands
uv run python manage.py create_sample_pdf_forms

# Dependencies
uv add reportlab PyPDF2 pdf2image

# System Dependencies (for PDF preview)
# Ubuntu/Debian: sudo apt install poppler-utils
# macOS: brew install poppler  
# Windows: Download from https://blog.alivate.com.au/poppler-windows/

# Testing
uv run python manage.py test apps.pdf_forms.tests
```

#### Implementation Benefits

- **Storage Efficiency**: 95%+ reduction in storage usage through data-only approach
- **Reliability**: Works with any PDF format - scanned, image-based, or digitally created
- **Precision**: Exact positioning using centimeter coordinates for predictable results  
- **Hospital-Friendly**: Perfect for legacy hospital forms that are often scanned documents
- **User Control**: Complete control over field positioning, formatting, and appearance
- **No Dependency Issues**: Doesn't rely on PDF form field detection or specific PDF structures
- **Professional Output**: ReportLab integration provides professional-grade PDF generation
- **Template Flexibility**: Can update PDF templates without affecting existing form data
- **Simplified Deployment**: No file migration between environments, only database backup needed

#### Visual Field Configuration Interface

**NEW: Drag-and-drop visual PDF field configurator for admin users**

- **Visual PDF Preview**: PDF-to-image conversion with interactive overlay editing
- **Drag-and-Drop Fields**: Click to add fields, drag to position, real-time coordinate calculation
- **Property Panels**: User-friendly forms for field configuration (type, label, validation)
- **Automatic JSON Generation**: Converts visual layout to coordinate-based JSON configuration
- **Field Management**: Add, edit, delete, duplicate fields with visual feedback
- **Grid System**: Optional grid snapping and alignment helpers for precise positioning

**Access**: Admin → PDF Form Templates → Select template → "Configure Fields" button

**Requirements**: 
```bash
uv add pdf2image  # For PDF-to-image conversion

# System requirement for PDF preview:
# Ubuntu/Debian: sudo apt install poppler-utils
# macOS: brew install poppler
# Windows: Download from https://blog.alivate.com.au/poppler-windows/
```

**Features**:
- **Intuitive Interface**: No manual coordinate entry required
- **Real-time Preview**: See field positioning immediately (requires Poppler)
- **Fallback JSON Editor**: Manual JSON editor when PDF preview is unavailable
- **Field Types**: Support for text, textarea, number, date, choice, boolean, email fields  
- **Validation**: Real-time field validation and conflict detection
- **Import/Export**: Load and export field configurations as JSON
- **Responsive Design**: Works on desktop and tablet devices
- **Professional UI**: Integrated with Django admin design system

#### System Dependencies

**Poppler (Required for PDF Preview)**

The visual field configurator requires Poppler to convert PDF pages to images for the drag-and-drop interface.

**Installation by Platform:**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install poppler-utils

# CentOS/RHEL/Fedora
sudo yum install poppler-utils
# or (newer versions)
sudo dnf install poppler-utils

# macOS
brew install poppler

# Windows
# Download from: https://blog.alivate.com.au/poppler-windows/
# Extract to C:\Program Files\poppler
# Add C:\Program Files\poppler\bin to PATH
```

**Verification:**
```bash
# Test poppler installation
pdftoppm -h
# Should display help information if properly installed
```

**Fallback Behavior:**
- **With Poppler**: Full visual drag-and-drop interface with PDF preview
- **Without Poppler**: Automatic fallback to manual JSON editor with validation
- **No Loss of Functionality**: All field configuration features available through JSON editor

#### Configuration

```python
# config/settings.py - PDF Forms Configuration
PDF_FORMS_CONFIG = {
    'enabled': os.getenv('HOSPITAL_PDF_FORMS_ENABLED', 'false').lower() == 'true',
    'templates_path': os.getenv('HOSPITAL_PDF_FORMS_PATH', ''),
    'max_template_size': int(os.getenv('PDF_FORMS_MAX_TEMPLATE_SIZE', 10 * 1024 * 1024)),  # 10MB template limit
    'allowed_extensions': ['.pdf'],
    'require_form_validation': os.getenv('PDF_FORMS_REQUIRE_VALIDATION', 'true').lower() == 'true',
    'generation_timeout': int(os.getenv('PDF_FORMS_GENERATION_TIMEOUT', 30)),  # 30 seconds
    'cache_templates': os.getenv('PDF_FORMS_CACHE_TEMPLATES', 'true').lower() == 'true',
}
```

#### Performance Characteristics

- **Storage**: Only JSON form data stored (~1-5KB per submission vs ~100KB-2MB for PDF files)
- **Generation Time**: 1-3 seconds per PDF download (acceptable for on-demand approach)
- **Memory Usage**: ReportLab processing requires ~10-50MB during generation
- **Concurrency**: Multiple PDF generations can run simultaneously
- **Caching**: Template files cached in memory for improved performance

## Permission System

**Clean role-based access control with medical/administrative separation**

### Role Architecture

**ADMINISTRATIVE ROLES (Non-Medical Staff):**
- **Superuser**: Full system access (IT administrators)
- **User Managers**: User account management only (HR/Administrative staff)

**MEDICAL ROLES (Clinical Staff Only):**
- **Doctors/Residents**: Full clinical access, patient management, medical documentation
- **Nurses**: Limited clinical access, basic patient updates, nursing notes
- **Physiotherapists**: Clinical access, therapy documentation
- **Students**: Read-only clinical access

### Core Framework

Located in `apps/core/permissions/`:

- **constants.py**: Profession types (Doctor, Resident, Nurse, Physiotherapist, Student)
- **utils.py**: Core permission functions (`can_access_patient`, `can_edit_event`, etc.)
- **decorators.py**: View decorators (`@patient_access_required`, `@doctor_required`)

### Key Principle

**Medical staff manage patients, administrative staff manage users.**
No overlap between clinical and administrative permissions.

### Medical Role Permissions

**Doctors/Residents:**
- Full clinical access to all patients regardless of status
- Can discharge patients and declare death
- Can edit patient personal data
- Can create and edit all types of medical events
- Can manage prescriptions
- Can assign/remove patient tags (instances)
- ❌ NO user account management
- ❌ NO Django admin access
- ❌ NO system configuration

**Physiotherapists:**
- Full clinical access to all patients (for therapy needs)
- Can create medical events and therapy documentation
- Can upload therapy-related media
- Can fill hospital forms
- Can assign/remove patient tags
- ❌ NO prescriptions (not in scope)
- ❌ NO user account management
- ❌ NO Django admin access

**Nurses:**
- View/edit patient information (limited)
- Can create basic medical events and nursing notes
- Can view medical media
- Can fill hospital forms
- ❌ NO patient deletion
- ❌ NO discharge patients or declare death
- ❌ NO prescriptions
- ❌ NO user account management

**Students:**
- Read-only access to patient information
- Can view medical events and notes
- Can create learning notes (dailynotes, simplenotes)
- Can view medical media
- Can fill forms for practice
- ❌ NO patient management (add/edit/delete)
- ❌ NO discharge patients or declare death
- ❌ NO prescriptions
- ❌ NO user account management

### Administrative Role Permissions

**User Managers (Administrative Staff):**
- Can create/edit user accounts
- Can assign users to medical roles
- Can view user profiles
- Can view available groups
- ❌ NO access to patient data
- ❌ NO access to medical events
- ❌ NO access to clinical information
- ❌ NO permission to modify group permissions

**Superuser (IT Administrators):**
- Full system access for technical administration
- Can change status of deceased patients (for data corrections)
- Full override of all permission restrictions

### Key Functions

```python
can_access_patient(user, patient)           # Always True (all roles can access all patients)
can_edit_event(user, event)                 # Time-limited editing (24h)
can_change_patient_status(user, patient, status)  # Doctors/residents only for discharge/death; admin override for deceased
can_change_patient_personal_data(user, patient)   # Doctors/residents only
get_user_accessible_patients(user)          # Returns all patients for all roles
```

### Management Commands

```bash
uv run python manage.py setup_groups              # Create profession-based groups
uv run python manage.py permission_audit --action=report  # System audit
uv run python manage.py user_permissions --action=assign # Assign user to group
```

### Template Tags

```django
{% load permission_tags %}
{% if user|has_permission:"patients.add_patient" %}...{% endif %}
{% if user|in_group:"Medical Doctors" %}...{% endif %}
{% check_multiple_permissions user "perm1" "perm2" as has_all %}
```

## Hospital Configuration

**Environment-based single hospital configuration**

### Hospital Settings

Located in `config/settings.py` as `HOSPITAL_CONFIG`:

```python
HOSPITAL_CONFIG = {
    'name': os.getenv('HOSPITAL_NAME', 'Hospital Name'),
    'address': os.getenv('HOSPITAL_ADDRESS', ''),
    'phone': os.getenv('HOSPITAL_PHONE', ''),
    'email': os.getenv('HOSPITAL_EMAIL', ''),
    'website': os.getenv('HOSPITAL_WEBSITE', ''),
    'logo_path': os.getenv('HOSPITAL_LOGO_PATH', ''),
    'logo_url': os.getenv('HOSPITAL_LOGO_URL', ''),
}
```

### Template Tags

Available in `apps/core/templatetags/hospital_tags.py`:

```django
{% load hospital_tags %}
{% hospital_name %}        # Get configured hospital name
{% hospital_address %}     # Get configured hospital address
{% hospital_phone %}       # Get configured hospital phone
{% hospital_email %}       # Get configured hospital email
{% hospital_logo %}        # Get configured hospital logo URL
{% hospital_header %}      # Render hospital header with configuration
{% hospital_branding %}    # Get complete hospital branding info
```

### Environment Variables

```bash
# Hospital Configuration
HOSPITAL_NAME="Your Hospital Name"
HOSPITAL_ADDRESS="123 Medical Center Drive, City, State 12345"
HOSPITAL_PHONE="+1-555-123-4567"
HOSPITAL_EMAIL="info@yourhospital.com"
HOSPITAL_WEBSITE="https://www.yourhospital.com"
HOSPITAL_LOGO_PATH="static/images/hospital-logo.png"
HOSPITAL_LOGO_URL="https://cdn.yourhospital.com/logo.png"
```

## Django Template Development Best Practices

### Template Block Architecture

**Critical Rule**: When extending Django templates, ALWAYS ensure content is placed within proper template blocks.

#### Event Card Template Structure

Event card templates extend `event_card_base.html` which provides these blocks:

- `{% block event_actions %}` - Action buttons (view, edit, delete, etc.)
- `{% block event_content %}` - Main event content display
- `{% block event_metadata %}` - Footer metadata (creator, timestamps, etc.)
- `{% block extra_html %}` - Additional HTML (modals, hidden elements)
- `{% block extra_css %}` - Event-specific CSS styles
- `{% block extra_js %}` - Event-specific JavaScript

#### Template Development Checklist

**Before creating/modifying templates:**

1. **Identify Base Template**: Check which template is being extended
2. **Review Available Blocks**: Read the base template to see all available blocks
3. **Block Content Placement**: Ensure ALL content is within appropriate blocks
4. **Content Outside Blocks**: Verify nothing exists outside block definitions
5. **Testing**: Test that CSS, JavaScript, and HTML render correctly

#### Common Mistakes to Avoid

```django
<!-- ❌ WRONG: Content outside blocks will be ignored -->
{% extends "base.html" %}
<style>/* This CSS will NOT be rendered */</style>
{% block content %}...{% endblock %}
<script>/* This JS will NOT be executed */</script>

<!-- ✅ CORRECT: All content within blocks -->
{% extends "base.html" %}
{% block content %}...{% endblock %}
{% block extra_css %}<style>/* This CSS renders */</style>{% endblock %}
{% block extra_js %}<script>/* This JS executes */</script>{% endblock %}
```

#### Debugging Template Issues

If functionality doesn't work (CSS not applied, JavaScript not executing):

1. Check if content is outside template blocks
2. Verify block names match base template
3. Ensure base template defines required blocks
4. Test with browser dev tools for missing resources

# Task Master Integration

## Quick Reference

Task Master AI provides project task management and integration with Claude Code. Complete documentation is available in `CLAUDE-taskmaster.md`.

### Essential Commands

```bash
# Daily workflow
task-master next                           # Get next available task
task-master show <id>                     # View task details
task-master set-status --id=<id> --status=done    # Mark complete

# Task management
task-master list                          # Show all tasks
task-master add-task --prompt="description" --research
task-master update-subtask --id=<id> --prompt="notes"
```

### MCP Integration

Task Master provides MCP tools when connected via `.mcp.json`. Key tools include:
- `next_task` - Find next available task
- `get_task` - View task details  
- `set_task_status` - Mark tasks complete
- `update_subtask` - Log implementation notes

**See `CLAUDE-taskmaster.md` for complete documentation, configuration, and workflows.**

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.