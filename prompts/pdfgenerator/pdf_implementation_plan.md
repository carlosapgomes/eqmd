# PDF Generation App Implementation Plan

## Overview
Create a centralized `apps/pdfgenerator/` app that standardizes PDF generation across the platform, replacing browser-based printing with proper ReportLab PDFs. The app will handle outpatient prescriptions, discharge reports, and exam requests.

## Requirements Analysis
- **Volume**: 2-5 PDFs per minute during work day (low volume)
- **Format**: A4 portrait letterhead PDF pages
- **Content**: Markdown formatted text input
- **Storage**: No PDF storage - generate on demand and serve immediately
- **Security**: Only logged in users can generate/download PDFs
- **Integration**: Replace existing HTML print templates

## Current State Analysis
Based on `apps/outpatientprescriptions/` implementation:
- Uses HTML templates with print-specific CSS
- Hospital branding via `HOSPITAL_CONFIG` and template tags
- Patient info, medication lists, instructions formatting
- Manual pagination with continuation headers
- Print button triggers browser print dialog

## 1. App Structure & Dependencies

### Django App Setup
- Create `apps/pdfgenerator/` with standard Django structure
- Add to `INSTALLED_APPS` in settings
- Install ReportLab: `uv add reportlab markdown`

### Core Files Structure
```
apps/pdfgenerator/
├── __init__.py
├── apps.py
├── models.py              # PDF template configurations (optional)
├── urls.py                # PDF generation endpoints
├── views.py               # PDF generation views
├── services/
│   ├── __init__.py
│   ├── pdf_generator.py   # Core ReportLab service
│   └── markdown_parser.py # Markdown to ReportLab conversion
├── templates/
│   └── pdfgenerator/
│       └── (if needed for error pages)
└── tests/
    ├── __init__.py
    └── test_pdf_generation.py
```

## 2. Core PDF Generation Service

### Base PDF Template (`services/pdf_generator.py`)
- A4 portrait letterhead template using ReportLab
- Hospital branding integration from `HOSPITAL_CONFIG`
- Header: hospital logo + name (mimic existing template)
- Footer: hospital details + pagination ("página X/Y")
- Content area with automatic pagination
- Signature section for medical documents

### Key ReportLab Components
- `SimpleDocTemplate` for A4 portrait layout
- Custom `PageTemplate` with header/footer
- `Paragraph` and `Spacer` for content formatting
- `Table` for structured data (patient info, medication lists)
- `Canvas` for signature lines and custom elements

### Markdown Parser (`services/markdown_parser.py`)
- Convert markdown text to ReportLab Paragraph objects
- Support basic formatting: **bold**, *italic*, lists, headers
- Handle line breaks and spacing appropriately
- Integration with ReportLab styling system

## 3. Document Type Handlers

### PDF Generation Views (`views.py`)
Three main endpoints that accept markdown content:

1. **`/pdf/prescription/`** - Generate prescription PDFs
   - Replace current HTML print template
   - Include patient info, medication list, instructions
   - Medical signature section

2. **`/pdf/discharge-report/`** - Generate discharge reports
   - Patient summary, treatment notes, follow-up instructions
   - Medical signature section

3. **`/pdf/exam-request/`** - Generate exam request forms
   - Patient info, requested exams, clinical justification
   - Medical signature section

### Request Format
```python
POST /pdf/prescription/
{
    "patient_id": "uuid",
    "content": "markdown content",
    "document_title": "Receita Médica",
    "metadata": {...}  # additional document-specific data
}
```

### Response Format
- Return PDF as `HttpResponse` with proper MIME type
- Content-Type: `application/pdf`
- Filename: `"{document_type}_{patient_name}_{date}.pdf"`
- No storage - generate and serve immediately
- Browser handles download/display

## 4. Integration Strategy

### Replace Existing Print Views
- Modify `outpatientprescriptions/views.py` to use PDF generation
- Update URL from `/print/` to call PDF service
- Maintain existing permission checks and access controls

### Template Integration
- Add PDF generation buttons to existing templates
- Remove print-specific CSS from outpatient prescriptions
- Update forms to submit to PDF generation endpoints

### Permission Integration
- Use existing `@login_required` and patient access controls
- Integrate with current permission system from `apps/core/permissions/`
- No additional access restrictions beyond existing ones

## 5. Technical Implementation Details

### Hospital Branding Integration
Leverage existing hospital configuration from settings:
```python
from django.conf import settings
hospital_config = settings.HOSPITAL_CONFIG
# Use hospital_config['name'], hospital_config['logo_url'], etc.
```

### Error Handling
- Validate markdown content before processing
- Graceful fallback for malformed input
- Logging for debugging PDF generation issues
- User-friendly error messages

### Performance Considerations
- Target: 2-5 PDFs per minute (very low volume)
- No caching needed for this volume
- Simple synchronous PDF generation
- Basic error logging and monitoring

## 6. Migration & Testing Strategy

### Phase 1: Core PDF Service
- Implement base PDF generation service
- Create prescription PDF endpoint
- Basic testing with sample data

### Phase 2: Integration
- Update outpatient prescription views
- Replace print template with PDF generation
- Comprehensive testing with real prescription data

### Phase 3: New Document Types
- Implement discharge report PDF generation
- Implement exam request PDF generation
- User acceptance testing

### Testing Approach
- Unit tests for PDF generation service
- Integration tests with existing prescription data
- Visual verification of PDF output quality
- Performance testing for concurrent PDF generation

## 7. Configuration & Settings

### PDF Settings Addition to `settings.py`
```python
# PDF Generation Settings
PDF_CONFIG = {
    'page_size': 'A4',
    'orientation': 'portrait',
    'margins': {
        'top': 2.5,    # cm
        'bottom': 3.0, # cm  
        'left': 2.0,   # cm
        'right': 2.0   # cm
    },
    'max_content_length': 50000,  # characters
    'fonts': {
        'default': 'Times-Roman',
        'bold': 'Times-Bold',
        'italic': 'Times-Italic'
    }
}
```

## 8. URL Structure

```python
# apps/pdfgenerator/urls.py
urlpatterns = [
    path('prescription/', views.PrescriptionPDFView.as_view(), name='prescription_pdf'),
    path('discharge-report/', views.DischargeReportPDFView.as_view(), name='discharge_report_pdf'),
    path('exam-request/', views.ExamRequestPDFView.as_view(), name='exam_request_pdf'),
]

# Main urls.py
path('pdf/', include('apps.pdfgenerator.urls')),
```

## 9. Security Considerations

- All endpoints require authentication (`@login_required`)
- Patient access validation using existing permission system
- Input validation for markdown content
- File name sanitization for PDF downloads
- No persistent storage of generated PDFs
- Rate limiting not needed for low volume

## 10. Future Enhancements

- Template customization for different document types
- Digital signature integration
- Batch PDF generation
- Email PDF delivery
- Advanced markdown formatting support

This plan provides a clean, centralized PDF generation solution that integrates seamlessly with the existing Django medical platform while maintaining all current functionality and security measures.