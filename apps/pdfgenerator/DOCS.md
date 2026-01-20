# PDF Generator Documentation Index

Welcome to the PDF Generator documentation. This index helps you find the right documentation for your needs.

## 📚 Documentation Files

### [README.md](./README.md) - **Start Here**
**Main documentation for the PDF Generator app**

Topics covered:
- Overview and features
- Installation and configuration
- URL endpoints and API
- Core services (HospitalLetterheadGenerator, MarkdownToPDFParser)
- PDF document structure and layout
- Usage examples (prescriptions, markdown content, view integration)
- Styles and formatting
- Permissions and security
- Testing
- Troubleshooting
- Future enhancements

**Read this when:** You're new to the PDF Generator or need a complete overview.

---

### [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - **For Developers**
**Guide for extending the PDF Generator with new document types**

Topics covered:
- Step-by-step guide to adding new document types
- Creating custom view classes
- Adding URL routes
- Custom PDF generation methods
- Testing new functionality
- Integration examples with existing views
- Best practices
- Common patterns (key-value metadata, numbered items, tables)
- Testing checklist

**Read this when:** You need to add a new document type or extend PDF functionality.

---

### [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - **Reference**
**Quick lookup for common tasks and code patterns**

Topics covered:
- Basic setup
- Common data formats (patient_data, doctor_info)
- Generate simple PDF from markdown
- Generate prescription PDF
- Generate PDF in a view
- Markdown examples (formatting, lists, medical documents)
- Available styles
- Custom formatting (paragraphs, tables, keep-together)
- Response handling
- URL endpoints
- Error handling
- Configuration
- Testing
- Common issues and solutions

**Read this when:** You need quick code examples or want to look up a specific task.

---

### [CHANGELOG.md](./CHANGELOG.md) - **Version History**
**History of changes and future plans**

Topics covered:
- Current unreleased changes
- Version 0.1.0 release notes
- Initial features and technical details
- Security considerations
- Known limitations
- Future planned features
- Migration notes from HTML print templates
- Contributors and support

**Read this when:** You want to know what changed, what's planned, or how to migrate from print templates.

---

## 🚀 Quick Start

### 1. Generate a Simple PDF

```python
from apps.pdfgenerator.services.pdf_generator import HospitalLetterheadGenerator
from apps.pdfgenerator.services.markdown_parser import MarkdownToPDFParser

# Initialize
pdf_generator = HospitalLetterheadGenerator()
markdown_parser = MarkdownToPDFParser(pdf_generator.styles)

# Parse markdown
content = "## Title\n\nContent here..."
content_elements = markdown_parser.parse(content)

# Generate PDF
pdf_buffer = pdf_generator.generate_pdf(
    content_elements=content_elements,
    document_title="DOCUMENT",
    patient_data={'name': 'Patient Name', ...},
    doctor_info={'name': 'Dr. Name', ...}
)

# Return as response
from django.http import HttpResponse
response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
return response
```

### 2. Generate a Prescription PDF

```python
pdf_generator = HospitalLetterheadGenerator()

pdf_buffer = pdf_generator.create_prescription_pdf(
    prescription_data={
        'prescription_date': '20/01/2026',
        'instructions': 'Instructions here',
        'status': 'Ativa'
    },
    items=[{
        'drug_name': 'Paracetamol',
        'presentation': '500mg comprimido',
        'usage_instructions': 'Take 1 tablet every 8 hours',
        'quantity': '30 tablets'
    }],
    patient_data={'name': 'Patient Name', ...},
    doctor_info={'name': 'Dr. Name', ...}
)
```

## 📖 Documentation by Use Case

### I want to...

#### Understand the PDF Generator
→ **Start with** [README.md - Overview](./README.md#overview)

#### Generate a prescription PDF
→ **See** [README.md - Usage Examples](./README.md#usage-examples)
→ Or [QUICK_REFERENCE.md - Generate Prescription PDF](./QUICK_REFERENCE.md#generate-prescription-pdf)

#### Generate a PDF from markdown
→ **See** [QUICK_REFERENCE.md - Generate Simple PDF](./QUICK_REFERENCE.md#generate-simple-pdf-from-markdown)

#### Add a new document type
→ **See** [DEVELOPER_GUIDE.md - Step-by-Step Guide](./DEVELOPER_GUIDE.md#step-by-step-guide)

#### Integrate PDF generation into existing views
→ **See** [DEVELOPER_GUIDE.md - Integration Example](./DEVELOPER_GUIDE.md#integration-example-adding-pdf-generation-to-existing-views)

#### Understand the PDF layout and structure
→ **See** [README.md - PDF Document Structure](./README.md#pdf-document-structure)

#### Customize styles or formatting
→ **See** [README.md - Styles and Formatting](./README.md#styles-and-formatting)
→ Or [QUICK_REFERENCE.md - Available Styles](./QUICK_REFERENCE.md#available-styles)

#### Troubleshoot PDF generation issues
→ **See** [README.md - Troubleshooting](./README.md#troubleshooting)
→ Or [QUICK_REFERENCE.md - Common Issues](./QUICK_REFERENCE.md#common-issues)

#### Add tests for PDF functionality
→ **See** [DEVELOPER_GUIDE.md - Testing Checklist](./DEVELOPER_GUIDE.md#testing-checklist)
→ Or [README.md - Testing](./README.md#testing)

#### Understand what changed in recent versions
→ **See** [CHANGELOG.md](./CHANGELOG.md)

#### Learn best practices
→ **See** [DEVELOPER_GUIDE.md - Best Practices](./DEVELOPER_GUIDE.md#best-practices)

## 🔧 API Reference

### Core Classes

#### HospitalLetterheadGenerator
- **Location:** `apps/pdfgenerator/services/pdf_generator.py`
- **Purpose:** Main PDF generation class
- **Documentation:** [README.md - HospitalLetterheadGenerator](./README.md#hospitaletterheadgenerator)
- **Methods:**
  - `generate_pdf()` - Generate generic PDF
  - `create_prescription_pdf()` - Generate prescription PDF

#### MarkdownToPDFParser
- **Location:** `apps/pdfgenerator/services/markdown_parser.py`
- **Purpose:** Convert markdown to ReportLab flowables
- **Documentation:** [README.md - MarkdownToPDFParser](./README.md#markdowntopdfparser)
- **Methods:**
  - `parse()` - Parse markdown to flowables
  - `parse_medical_content()` - Parse medical content
  - `parse_prescription_instructions()` - Parse instructions

### View Classes

#### BasePDFView
- **Location:** `apps/pdfgenerator/views.py`
- **Purpose:** Base class for PDF generation views
- **Documentation:** [README.md - URL Endpoints](./README.md#url-endpoints)

#### PrescriptionPDFView
- **Location:** `apps/pdfgenerator/views.py`
- **Purpose:** Generate prescription PDFs
- **Endpoint:** `POST /pdf/prescription/`

#### DischargeReportPDFView
- **Location:** `apps/pdfgenerator/views.py`
- **Purpose:** Generate discharge report PDFs
- **Endpoint:** `POST /pdf/discharge-report/`

#### ExamRequestPDFView
- **Location:** `apps/pdfgenerator/views.py`
- **Purpose:** Generate exam request PDFs
- **Endpoint:** `POST /pdf/exam-request/`

## 🎓 Learning Path

### Beginner
1. Read [README.md - Overview](./README.md#overview)
2. Read [README.md - Installation](./README.md#installation)
3. Try the [Quick Start examples](#-quick-start)
4. Explore [QUICK_REFERENCE.md - Markdown Examples](./QUICK_REFERENCE.md#markdown-examples)

### Intermediate
1. Read [README.md - Usage Examples](./README.md#usage-examples)
2. Read [README.md - PDF Document Structure](./README.md#pdf-document-structure)
3. Practice with [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
4. Review [README.md - Testing](./README.md#testing)

### Advanced
1. Read [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
2. Add a custom document type
3. Explore [DEVELOPER_GUIDE.md - Common Patterns](./DEVELOPER_GUIDE.md#common-patterns)
4. Follow [DEVELOPER_GUIDE.md - Testing Checklist](./DEVELOPER_GUIDE.md#testing-checklist)

## 📦 File Structure

```
apps/pdfgenerator/
├── README.md                 # Main documentation
├── DEVELOPER_GUIDE.md        # Developer guide
├── QUICK_REFERENCE.md        # Quick reference
├── CHANGELOG.md              # Version history
├── DOCS.md                   # This file (index)
├── services/
│   ├── pdf_generator.py      # Core PDF generation
│   └── markdown_parser.py    # Markdown parser
├── views.py                  # PDF generation views
├── urls.py                   # URL routing
└── tests/
    └── test_pdf_generation.py # Tests
```

## 🔗 Related Resources

### Project Documentation
- **Outpatient Prescriptions:** `apps/outpatientprescriptions/`
- **Core Permissions:** `apps/core/permissions/`
- **Settings:** Project `settings.py`

### External Documentation
- **ReportLab:** https://reportlab.com/documentation/
- **Python-Markdown:** https://python-markdown.github.io/
- **Django Views:** https://docs.djangoproject.com/en/stable/topics/class-based-views/

### Implementation History
- **Original Plan:** `prompts/pdfgenerator/pdf_implementation_plan.md`

## 💡 Tips

- **Search first:** Use Ctrl+F to find specific topics in the documentation files
- **Start simple:** Begin with [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) for code examples
- **Check tests:** Review `tests/test_pdf_generation.py` for working examples
- **Enable logging:** Set `DEBUG=True` and check logs for troubleshooting
- **Ask for help:** See [README.md - Support](./README.md#support) for troubleshooting steps

## 📝 Contributing

When making changes to the PDF Generator:

1. Update this index if adding new documentation
2. Update [CHANGELOG.md](./CHANGELOG.md) with your changes
3. Add tests for new functionality
4. Update relevant documentation sections
5. Follow [DEVELOPER_GUIDE.md - Best Practices](./DEVELOPER_GUIDE.md#best-practices)

---

**Last Updated:** January 20, 2025

**Version:** 0.1.0
