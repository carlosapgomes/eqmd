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

The system supports two configuration formats:

### 1. Section-Based Configuration (Recommended)

**NEW: Organize form fields into collapsible sections for better UX**

```json
{
  "sections": {
    "patient_info": {
      "label": "Informações do Paciente",
      "description": "Dados básicos e informações de contato do paciente",
      "order": 1,
      "collapsed": false,
      "icon": "bi-person"
    },
    "medical_history": {
      "label": "Histórico Médico",
      "description": "Antecedentes médicos relevantes",
      "order": 2,
      "collapsed": true,
      "icon": "bi-journal-medical"
    },
    "procedure_details": {
      "label": "Detalhes do Procedimento",
      "description": "Informações específicas sobre o procedimento",
      "order": 3,
      "collapsed": true,
      "icon": "bi-clipboard-pulse"
    }
  },
  "fields": {
    "patient_name": {
      "type": "text",
      "label": "Nome do Paciente",
      "section": "patient_info",
      "field_order": 1,
      "x": 4.5, "y": 8.5, "width": 12.0, "height": 0.7,
      "font_size": 12,
      "required": true,
      "max_length": 200
    },
    "patient_birth_date": {
      "type": "date",
      "label": "Data de Nascimento",
      "section": "patient_info",
      "field_order": 2,
      "x": 4.5, "y": 10.0, "width": 6.0, "height": 0.7,
      "required": true
    },
    "allergies": {
      "type": "multiple_choice",
      "label": "Alergias Conhecidas",
      "section": "medical_history",
      "field_order": 1,
      "x": 4.5, "y": 12.0, "width": 8.0, "height": 1.5,
      "choices": ["Penicilina", "Látex", "Nozes", "Frutos do Mar"],
      "required": false
    },
    "blood_type": {
      "type": "choice",
      "label": "Tipo Sanguíneo",
      "section": "medical_history",
      "field_order": 2,
      "x": 4.5, "y": 14.0, "width": 3.0, "height": 0.7,
      "choices": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
      "required": true
    },
    "procedure_name": {
      "type": "text",
      "label": "Nome do Procedimento",
      "section": "procedure_details",
      "field_order": 1,
      "x": 4.5, "y": 16.0, "width": 10.0, "height": 0.7,
      "required": true
    },
    "general_notes": {
      "type": "textarea",
      "label": "Observações Gerais",
      // No section assigned - will appear in "Other Fields" section
      "x": 4.5, "y": 18.0, "width": 12.0, "height": 3.0,
      "required": false
    }
  }
}
```

### 2. Legacy Configuration (Backward Compatible)

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
uv run python manage.py migrate_form_sections  # Migrate existing forms to sections

# Dependencies
uv add reportlab PyPDF2 pdf2image

# System Dependencies (for PDF preview)
# Ubuntu/Debian: sudo apt install poppler-utils
# macOS: brew install poppler  
# Windows: Download from https://blog.alivate.com.au/poppler-windows/

# Testing
uv run python manage.py test apps.pdf_forms.tests
```

## Section-Based Form Organization

**NEW: Enhanced UX with collapsible accordion sections**

### Features

- **Collapsible Sections**: Group related fields into expandable/collapsible sections
- **Visual Organization**: Icons, descriptions, and field counts for better navigation
- **State Persistence**: User's expand/collapse preferences saved across sessions
- **Smart Validation**: Invalid sections automatically expand during form validation
- **Backward Compatibility**: Existing forms continue to work without modification
- **Admin Interface**: Visual section management in the form configurator

### Section Configuration

#### Section Properties

```json
{
  "section_key": {
    "label": "Section Display Name",           // Required
    "description": "Optional section description",
    "order": 1,                              // Required - determines display order
    "collapsed": false,                      // Start expanded (false) or collapsed (true)
    "icon": "bi-person"                      // Bootstrap icon class (optional)
  }
}
```

#### Field Assignment

Fields are assigned to sections using the `section` and `field_order` properties:

```json
{
  "field_name": {
    "type": "text",
    "label": "Field Label",
    "section": "section_key",               // Links to section
    "field_order": 1,                      // Order within section
    "x": 4.5, "y": 8.5, "width": 6.0, "height": 0.7,
    // ... other field properties
  }
}
```

### Available Icons

Common Bootstrap icons for medical forms:

- `bi-person` - Patient information
- `bi-journal-medical` - Medical history
- `bi-clipboard-pulse` - Procedures/diagnostics
- `bi-prescription2` - Medications
- `bi-hospital` - Hospital information
- `bi-calendar-event` - Appointments/dates
- `bi-shield-check` - Insurance/coverage
- `bi-telephone` - Contact information
- `bi-geo-alt` - Address/location
- `bi-clipboard-data` - Test results

### Migration from Legacy Format

#### Automatic Migration

Use the management command to migrate existing forms:

```bash
# Preview migration (dry run)
uv run python manage.py migrate_form_sections --dry-run

# Migrate all forms with default sections
uv run python manage.py migrate_form_sections --create-default-sections

# Migrate specific template
uv run python manage.py migrate_form_sections --template-id 123

# Force migration even for forms with sections
uv run python manage.py migrate_form_sections --force
```

#### Manual Migration

Convert legacy configuration to sectioned format:

```python
from apps.pdf_forms.services.section_utils import SectionUtils

# Legacy format
legacy_config = {
    "patient_name": {"type": "text", "label": "Nome", ...},
    "birth_date": {"type": "date", "label": "Data Nascimento", ...}
}

# Convert to sectioned format
sectioned_config = SectionUtils.migrate_unsectioned_form(legacy_config)
```

### Best Practices

#### Section Organization

- **Group Related Fields**: Place logically related fields together
- **Prioritize by Importance**: Use section order to highlight critical information
- **Limit Section Size**: Keep sections manageable (5-10 fields maximum)
- **Use Descriptive Labels**: Make section purpose clear to users

#### Common Section Patterns

**Medical Forms**:
```json
{
  "sections": {
    "patient_identification": {
      "label": "Identificação do Paciente",
      "order": 1,
      "collapsed": false,
      "icon": "bi-person"
    },
    "medical_history": {
      "label": "História Médica",
      "order": 2,
      "collapsed": true,
      "icon": "bi-journal-medical"
    },
    "current_condition": {
      "label": "Condição Atual",
      "order": 3,
      "collapsed": false,
      "icon": "bi-clipboard-pulse"
    },
    "treatment_plan": {
      "label": "Plano de Tratamento",
      "order": 4,
      "collapsed": true,
      "icon": "bi-prescription2"
    }
  }
}
```

#### Section States

- **Critical sections**: `collapsed: false` (always visible)
- **Optional sections**: `collapsed: true` (initially hidden)
- **Reference sections**: `collapsed: true` (rarely modified)

### Troubleshooting

#### Common Issues

**Section Not Displaying**:
- Check section key matches field assignments
- Verify section has valid `label` and `order` properties
- Ensure section order values are unique

**Fields Missing from Sections**:
- Verify field `section` property matches existing section key
- Check for typos in section references
- Fields without valid section references appear in "Other Fields"

**Section Order Issues**:
- Ensure all sections have unique `order` values
- Use sequential numbering (1, 2, 3, ...) for best results
- Missing order values default to 999

**Template Errors After Migration**:
- Validate JSON structure after migration
- Check for special characters in section keys
- Use `--dry-run` to preview changes before applying

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