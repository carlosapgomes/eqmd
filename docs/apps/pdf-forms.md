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

## Data Sources and Linked Fields

**NEW: Advanced data relationship functionality for automatic field population**

Data Sources enable creation of reusable datasets that automatically populate related fields when a user selects a value. This creates "linked field" functionality where selecting one value automatically fills multiple related fields.

### Features

- **Reusable Datasets**: Define data once, use across multiple fields
- **Automatic Population**: Select one value, related fields auto-fill
- **Data Integrity**: Ensures consistency across related fields  
- **Read-only Protection**: Auto-filled fields can be locked to prevent manual changes
- **Multiple Data Sources**: Support multiple independent datasets per form
- **Section Support**: Works seamlessly with section-based forms

### Creating Data Sources

#### 1. Access Data Source Manager

In the visual field configurator:

1. Go to **Admin** → **PDF Form Templates** → **Configure Fields**
2. Scroll to the **"Data Sources"** section at the bottom
3. Click **"Add Data Source"** to create a new dataset

#### 2. Define Data Structure

Each data source contains a list of items with consistent key-value pairs:

**Example - Medical Procedures:**

```json
Data Source Name: "procedures"

Item 1: {
  "name": "Appendectomy", 
  "code": "AP001", 
  "duration": "2 hours", 
  "room": "OR-1",
  "anesthesia": "General"
}

Item 2: {
  "name": "Cholecystectomy", 
  "code": "CH002", 
  "duration": "3 hours", 
  "room": "OR-2",
  "anesthesia": "General"
}

Item 3: {
  "name": "Hernia Repair", 
  "code": "HR003", 
  "duration": "1 hour", 
  "room": "OR-3",
  "anesthesia": "Local"
}
```

#### 3. Data Source Guidelines

- **Consistent Structure**: All items must have the same keys
- **Unique Names**: Use descriptive, unique data source names
- **Key Naming**: Use clear, descriptive key names (avoid spaces)
- **Data Types**: Support strings, numbers, dates

### Linking Fields to Data Sources

#### 1. Primary Selection Field

Configure the field users will interact with:

```json
{
  "procedure_selection": {
    "type": "choice",
    "label": "Select Procedure",
    "data_source": "procedures",
    "data_source_key": "name",
    "x": 4.5, "y": 8.5, "width": 8.0, "height": 0.7,
    "required": true
  }
}
```

This creates a dropdown with: ["Appendectomy", "Cholecystectomy", "Hernia Repair"]

#### 2. Auto-Filled Fields

Configure fields that auto-populate based on the selection:

```json
{
  "procedure_code": {
    "type": "text",
    "label": "Procedure Code",
    "data_source": "procedures",
    "data_source_key": "code",
    "linked_readonly": true,
    "x": 13.0, "y": 8.5, "width": 4.0, "height": 0.7
  },
  "estimated_duration": {
    "type": "text", 
    "label": "Duration",
    "data_source": "procedures",
    "data_source_key": "duration",
    "linked_readonly": true,
    "x": 4.5, "y": 9.5, "width": 4.0, "height": 0.7
  },
  "operating_room": {
    "type": "text",
    "label": "Operating Room", 
    "data_source": "procedures",
    "data_source_key": "room",
    "linked_readonly": true,
    "x": 9.0, "y": 9.5, "width": 4.0, "height": 0.7
  }
}
```

#### 3. Field Configuration Properties

**Data Source Linking Properties:**

- `data_source`: Name of the data source to link to
- `data_source_key`: Which property from the data source to use
- `linked_readonly`: (Optional) Make field read-only when auto-filled

### Complete Configuration Example

```json
{
  "data_sources": {
    "procedures": [
      {
        "name": "Appendectomy",
        "code": "AP001", 
        "duration": "2 hours",
        "room": "OR-1",
        "specialist": "Dr. Silva"
      },
      {
        "name": "Cholecystectomy",
        "code": "CH002",
        "duration": "3 hours", 
        "room": "OR-2",
        "specialist": "Dr. Costa"
      }
    ],
    "medications": [
      {
        "name": "Amoxicillin",
        "dosage": "500mg",
        "frequency": "3x daily",
        "duration": "7 days"
      },
      {
        "name": "Ibuprofen", 
        "dosage": "400mg",
        "frequency": "2x daily",
        "duration": "5 days"
      }
    ]
  },
  "sections": {
    "procedure_info": {
      "label": "Procedure Information",
      "order": 1,
      "collapsed": false
    },
    "medication_info": {
      "label": "Medication Information", 
      "order": 2,
      "collapsed": true
    }
  },
  "fields": {
    "procedure_name": {
      "type": "choice",
      "label": "Select Procedure",
      "section": "procedure_info",
      "field_order": 1,
      "data_source": "procedures",
      "data_source_key": "name",
      "x": 4.5, "y": 8.5, "width": 8.0, "height": 0.7,
      "required": true
    },
    "procedure_code": {
      "type": "text", 
      "label": "Code",
      "section": "procedure_info",
      "field_order": 2,
      "data_source": "procedures",
      "data_source_key": "code",
      "linked_readonly": true,
      "x": 13.0, "y": 8.5, "width": 4.0, "height": 0.7
    },
    "medication_name": {
      "type": "choice",
      "label": "Select Medication",
      "section": "medication_info", 
      "field_order": 1,
      "data_source": "medications",
      "data_source_key": "name",
      "x": 4.5, "y": 12.0, "width": 8.0, "height": 0.7,
      "required": false
    },
    "medication_dosage": {
      "type": "text",
      "label": "Dosage",
      "section": "medication_info",
      "field_order": 2, 
      "data_source": "medications",
      "data_source_key": "dosage",
      "linked_readonly": true,
      "x": 13.0, "y": 12.0, "width": 4.0, "height": 0.7
    }
  }
}
```

### User Experience

1. **User selects "Appendectomy"** from procedure dropdown
2. **Auto-filled fields populate**:
   - Procedure Code → "AP001"
   - Duration → "2 hours" 
   - Operating Room → "OR-1"
   - Specialist → "Dr. Silva"
3. **Read-only fields** cannot be manually edited
4. **User can still edit** non-linked fields normally

### Benefits

- **Data Consistency**: Eliminates manual entry errors
- **User Efficiency**: One selection populates multiple fields
- **Maintainability**: Update data source once, affects all forms
- **Professional Forms**: Ensures standardized data entry
- **Reduced Training**: Users only need to know primary selections

### Best Practices

#### Data Source Design

- **Logical Grouping**: Group related data together (procedures, medications, etc.)
- **Complete Data**: Include all necessary related fields
- **Standardized Names**: Use consistent naming conventions
- **Validation**: Ensure all items have the same structure

#### Field Configuration

- **Primary Fields**: Use `choice` type for user selections
- **Auto-Fill Fields**: Use appropriate field types (text, number, date)
- **Read-Only Protection**: Enable `linked_readonly` for critical auto-filled data
- **Clear Labels**: Make field relationships obvious to users

### Common Use Cases

#### Medical Procedures
```json
"procedures": [
  {"name": "Surgery Name", "code": "Code", "duration": "Time", "room": "Location"}
]
```

#### Medications
```json
"medications": [
  {"name": "Drug Name", "dosage": "Amount", "frequency": "Schedule", "warnings": "Notes"}
]
```

#### Hospital Departments
```json
"departments": [
  {"name": "Dept Name", "head": "Manager", "phone": "Contact", "location": "Building"}
]
```

#### Insurance Plans
```json
"insurance": [
  {"plan": "Plan Name", "provider": "Company", "code": "ID", "copay": "Amount"}
]
```

### Management Commands

```bash
# No specific commands - managed through admin interface
# Data sources are stored as part of form configuration JSON
```

### Implementation Details

Data sources are implemented using:
- `apps.pdf_forms.services.data_source_utils.DataSourceUtils` - Core utilities
- JavaScript frontend for real-time field linking
- JSON storage within form template configuration
- Section-aware field grouping support

## Troubleshooting

### Common Issues

**Data Sources Not Appearing**:

- Verify data source has valid name and structure
- Check all items have identical keys  
- Ensure data source is saved before linking fields

**Auto-Fill Not Working**:

- Confirm field `data_source` matches existing data source name
- Verify `data_source_key` exists in all data items
- Check JavaScript console for errors

**Fields Not Updating**:

- Ensure primary selection field has valid `data_source` configuration
- Verify linked fields are in the same form section (if using sections)
- Test with browser developer tools enabled

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

**Data Source Errors**:

- Validate JSON structure in data sources
- Ensure consistent data types across all items
- Check for special characters in keys or values
