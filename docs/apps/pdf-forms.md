# PDF Forms App - Implementation Guide

**Hospital-specific PDF form overlay functionality with dynamic form generation**

## Overview

- Models: PDFFormTemplate, PDFFormSubmission extending Event model
- Dynamic form generation from JSON field configuration with coordinate-based positioning
- Integration with Event system for timeline display and audit trail
- Data-only storage approach with on-demand PDF generation for optimal storage efficiency
- Permission-based access control with patient access validation
- URL structure: `/pdf-forms/select/<patient_id>/`, `/pdf-forms/fill/<template_id>/<patient_id>/`

## Key Features

- **Manual Field Configuration**: Coordinate-based positioning using centimeter measurements for precise PDF overlay
- **Dynamic Forms**: Generate Django forms from PDF template field mappings with support for text, choice, boolean, date, and textarea fields
- **On-Demand PDF Generation**: PDFs generated dynamically during downloads using ReportLab and PyPDF2 for optimal storage efficiency
- **Data-Only Storage**: Only form submission data stored in database, achieving 95%+ storage reduction compared to file-based approach
- **Event Integration**: PDF submissions appear in patient timeline with generate-and-download capabilities
- **Hospital Configuration**: Enable/disable per hospital installation with environment variable control
- **Security**: Comprehensive permission checks, data validation, and secure PDF generation
- **Universal PDF Support**: Works with any PDF format including scanned documents and legacy hospital forms

## Field Configuration Structure

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

## Usage Examples

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

## Implementation Benefits

- **Storage Efficiency**: 95%+ reduction in storage usage through data-only approach
- **Reliability**: Works with any PDF format - scanned, image-based, or digitally created
- **Precision**: Exact positioning using centimeter coordinates for predictable results  
- **Hospital-Friendly**: Perfect for legacy hospital forms that are often scanned documents
- **User Control**: Complete control over field positioning, formatting, and appearance
- **No Dependency Issues**: Doesn't rely on PDF form field detection or specific PDF structures
- **Professional Output**: ReportLab integration provides professional-grade PDF generation
- **Template Flexibility**: Can update PDF templates without affecting existing form data
- **Simplified Deployment**: No file migration between environments, only database backup needed

## Visual Field Configuration Interface

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

## System Dependencies

### Poppler (Required for PDF Preview)

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

## Configuration

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

## Performance Characteristics

- **Storage**: Only JSON form data stored (~1-5KB per submission vs ~100KB-2MB for PDF files)
- **Generation Time**: 1-3 seconds per PDF download (acceptable for on-demand approach)
- **Memory Usage**: ReportLab processing requires ~10-50MB during generation
- **Concurrency**: Multiple PDF generations can run simultaneously
- **Caching**: Template files cached in memory for improved performance

## Field Types and Configuration

### Text Fields
```json
{
  "field_name": {
    "type": "text",
    "label": "Field Label",
    "x": 4.5, "y": 8.5, "width": 12.0, "height": 0.7,
    "font_size": 12,
    "required": true,
    "max_length": 200,
    "placeholder": "Enter text here"
  }
}
```

### Choice Fields
```json
{
  "field_name": {
    "type": "choice",
    "label": "Select Option",
    "x": 4.5, "y": 8.5, "width": 6.0, "height": 0.7,
    "choices": ["Option 1", "Option 2", "Option 3"],
    "required": true
  }
}
```

### Boolean Fields
```json
{
  "field_name": {
    "type": "boolean",
    "label": "Yes/No Question",
    "x": 4.5, "y": 8.5, "width": 3.0, "height": 0.7,
    "required": false
  }
}
```

### Date Fields
```json
{
  "field_name": {
    "type": "date",
    "label": "Date Field",
    "x": 4.5, "y": 8.5, "width": 4.0, "height": 0.7,
    "required": true,
    "date_format": "%d/%m/%Y"
  }
}
```

## Troubleshooting

### Common Issues

**PDF Preview Not Working**:
- Ensure Poppler is installed (`pdftoppm -h`)
- Check file permissions on PDF templates
- Verify PDF file is not corrupted

**Field Positioning Issues**:
- Use centimeter measurements for precision
- Test with different PDF readers/printers
- Verify coordinate system (0,0 is top-left)

**Performance Issues**:
- Enable template caching in production
- Monitor memory usage during PDF generation
- Consider background task queue for large forms