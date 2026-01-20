# PDF Generator App

Centralized PDF generation service for medical documents using ReportLab with hospital letterhead templates.

## Overview

The `pdfgenerator` app provides a standardized way to generate professional medical documents (prescriptions, discharge reports, exam requests) with consistent hospital branding, patient information headers, and medical signature sections. It replaces browser-based printing with proper PDF generation.

## Features

- **Hospital Letterhead**: Automatic header/footer with hospital logo, name, and patient information
- **Document Types**: Support for prescriptions, discharge reports, and exam requests
- **Markdown Support**: Convert markdown-formatted text to professional PDF content
- **Automatic Pagination**: Multi-page documents with proper page numbers and continuation headers
- **Medical Signature Sections**: Standardized signature areas with doctor information
- **Permission Integration**: Uses existing patient access controls
- **No Storage**: PDFs generated on-demand without persistent storage

## Architecture

```
apps/pdfgenerator/
├── services/
│   ├── pdf_generator.py       # Core ReportLab PDF generation
│   └── markdown_parser.py     # Markdown to PDF conversion
├── views.py                   # PDF generation endpoints
├── urls.py                    # URL routing
└── tests/
    └── test_pdf_generation.py # Unit tests
```

## Installation

The app is already installed and configured. Dependencies:

```bash
pip install reportlab markdown beautifulsoup4
```

## Configuration

Add to `settings.py`:

```python
# Hospital Configuration
HOSPITAL_CONFIG = {
    'name': 'Medical Center',
    'address': '123 Medical Street',
    'logo_path': 'static/images/logo.png',  # Optional
    'logo_url': '',  # Not implemented (security)
}

# PDF Configuration
PDF_CONFIG = {
    'page_size': 'A4',
    'orientation': 'portrait',
    'margins': {
        'top': 2.5,     # cm
        'bottom': 3.0,  # cm
        'left': 2.0,    # cm
        'right': 2.0    # cm
    },
    'max_content_length': 50000  # characters
}

INSTALLED_APPS = [
    ...
    'apps.pdfgenerator',
]
```

## URL Endpoints

All endpoints require authentication (`@login_required`) and validate patient access permissions.

### Prescription PDF

**Endpoint:** `/pdf/prescription/`

**Method:** `POST`

**Request Body:**
```json
{
    "prescription_id": "uuid-of-prescription"
}
```

**Response:** PDF file with `Content-Type: application/pdf`

**Example Usage:**
```python
# In views.py - see OutpatientPrescriptionPDFView
from apps.pdfgenerator.services.pdf_generator import HospitalLetterheadGenerator

pdf_generator = HospitalLetterheadGenerator()
pdf_buffer = pdf_generator.create_prescription_pdf(
    prescription_data=prescription_data,
    items=items,
    patient_data=patient_data,
    doctor_info=doctor_info
)

response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
response['Content-Disposition'] = f'attachment; filename="Receita_Medica_{patient_name}_{date}.pdf"'
```

### Discharge Report PDF

**Endpoint:** `/pdf/discharge-report/`

**Method:** `POST`

**Request Body:**
```json
{
    "patient_id": "uuid-of-patient",
    "content": "## Relatório de Alta\n\nPaciente apresentou evolução favorável...",
    "document_title": "RELATÓRIO DE ALTA HOSPITALAR",
    "metadata": {
        "admission_date": "2025-01-01",
        "discharge_date": "2025-01-05"
    }
}
```

### Exam Request PDF

**Endpoint:** `/pdf/exam-request/`

**Method:** `POST`

**Request Body:**
```json
{
    "patient_id": "uuid-of-patient",
    "content": "## Exames Solicitados\n\nHemograma completo...",
    "document_title": "SOLICITAÇÃO DE EXAMES",
    "metadata": {
        "requested_exams": "Hemograma\nGlicemia\nUrina tipo I",
        "clinical_indication": "Investigação de anemia..."
    }
}
```

## Core Services

### HospitalLetterheadGenerator

Main PDF generation class with hospital letterhead template.

**Methods:**

```python
class HospitalLetterheadGenerator:
    def __init__(self):
        """Initialize with hospital config and styles"""
        
    def generate_pdf(self, content_elements, document_title, patient_data, doctor_info):
        """
        Generate PDF with hospital letterhead.
        
        Args:
            content_elements: List of ReportLab flowables
            document_title: Document title (e.g., "RECEITA MÉDICA")
            patient_data: Dict with patient info
            doctor_info: Dict with doctor info
            
        Returns:
            BytesIO buffer with PDF content
        """
        
    def create_prescription_pdf(self, prescription_data, items, patient_data, doctor_info):
        """
        Generate prescription PDF with specific formatting.
        
        Args:
            prescription_data: Dict with prescription info (date, instructions, status)
            items: List of medication items (drug_name, presentation, usage_instructions, quantity)
            patient_data: Dict with patient info
            doctor_info: Dict with doctor info
            
        Returns:
            BytesIO buffer with PDF content
        """
```

**Patient Data Format:**
```python
patient_data = {
    'name': 'Patient Name',
    'fiscal_number': '123.456.789-00',
    'birth_date': '01/01/1990',
    'health_card_number': '123456789012345'
}
```

**Doctor Info Format:**
```python
doctor_info = {
    'name': 'Dr. Name',
    'profession': 'Médico',
    'registration_number': 'CRM/BA 12345'
}
```

### MarkdownToPDFParser

Converts markdown text to ReportLab flowables.

**Supported Markdown:**
- Headers: `#`, `##`, `###`
- Bold: `**text**`
- Italic: `*text*`
- Lists: `- item` or `1. item`
- Blockquotes: `> quote`
- Horizontal rules: `---`

**Methods:**

```python
class MarkdownToPDFParser:
    def __init__(self, styles):
        """Initialize parser with ReportLab styles"""
        
    def parse(self, markdown_text):
        """
        Parse markdown text to ReportLab flowables.
        
        Args:
            markdown_text: Markdown content string
            
        Returns:
            List of ReportLab flowables (Paragraph, Spacer objects)
        """
        
    def parse_medical_content(self, markdown_text, title=None):
        """Parse medical content with specific formatting"""
        
    def parse_prescription_instructions(self, instructions):
        """Parse prescription instructions with medical formatting"""
```

## PDF Document Structure

### Layout

```
+----------------------------------------+
|            [Hospital Logo]             |  Top margin: 2.5cm
|         Hospital Name                  |
|        Patient: John Doe               |  <- Patient name in header
+----------------------------------------+
|                                        |
|           RECEITA MÉDICA               |  Document title
|                                        |
|  1. Paracetamol                        |
|     500mg comprimido                   |  Content area
|     Uso: Tomar 1 comprimido...         |
|     Quantidade: 30 comprimidos         |
|                                        |
|  2. Ibuprofeno                         |
|     ...                                |
|                                        |
+----------------------------------------+
|                                        |
|  Data: 20/01/2026    Local: Salvador   |  Signature section
|  _____________________________         |
|  Dr. John Smith                        |
|  Médico - CRM: 12345                  |
|  Assinatura e Carimbo                  |
+----------------------------------------+
| Hospital Name - Address                |  Footer
|                      Página 1/1        |  Page numbers
+----------------------------------------+
```

### Header (Every Page)

- Hospital logo (left, if configured)
- Hospital name
- **Patient name prominently displayed**
- Separator line

### Footer (Every Page)

- Hospital name and address
- Separator line
- Page numbers (X/Y format)

### Signature Section

- Auto-filled current date
- Location (Salvador - BA)
- Signature line
- Doctor's name, profession, CRM number
- "Assinatura e Carimbo" label

### Multi-page Documents

- Patient name appears on every page header
- Small signature area on non-final pages
- Full signature section on last page
- Proper page numbering

## Usage Examples

### Example 1: Generate Prescription PDF

```python
from apps.pdfgenerator.services.pdf_generator import HospitalLetterheadGenerator

# Initialize generator
pdf_generator = HospitalLetterheadGenerator()

# Prepare data
patient_data = {
    'name': 'Maria Silva',
    'fiscal_number': '123.456.789-00',
    'birth_date': '15/03/1985',
    'health_card_number': '987654321098765'
}

doctor_info = {
    'name': 'Dr. João Santos',
    'profession': 'Médico Cardiologista',
    'registration_number': 'CRM/BA 12345'
}

prescription_data = {
    'prescription_date': '20/01/2026',
    'instructions': 'Seguir rigorosamente a posologia indicada.',
    'status': 'Ativa'
}

items = [
    {
        'drug_name': 'Losartana',
        'presentation': '50mg comprimido',
        'usage_instructions': 'Tomar 1 comprimido pela manhã',
        'quantity': '30 comprimidos'
    },
    {
        'drug_name': 'Hidroclorotiazida',
        'presentation': '25mg comprimido',
        'usage_instructions': 'Tomar 1 comprimido pela manhã',
        'quantity': '30 comprimidos'
    }
]

# Generate PDF
pdf_buffer = pdf_generator.create_prescription_pdf(
    prescription_data=prescription_data,
    items=items,
    patient_data=patient_data,
    doctor_info=doctor_info
)

# Return as HTTP response
from django.http import HttpResponse
response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
response['Content-Disposition'] = 'attachment; filename="Receita_Medica_Maria_Silva_20260120.pdf"'
return response
```

### Example 2: Generate PDF from Markdown

```python
from apps.pdfgenerator.services.pdf_generator import HospitalLetterheadGenerator
from apps.pdfgenerator.services.markdown_parser import MarkdownToPDFParser

# Initialize
pdf_generator = HospitalLetterheadGenerator()
markdown_parser = MarkdownToPDFParser(pdf_generator.styles)

# Prepare markdown content
markdown_content = """
## Relatório de Evolução

**Data:** 20/01/2026

**Paciente:** Maria Silva

### Histórico
Paciente apresenta evolução favorável desde o início do tratamento. Os sintomas de dor torácica diminuíram significativamente após o início da medicação.

### Exames Realizados
- Eletrocardiograma: Normal
- Ecocardiograma: Função sistólica preservada
- Hemograma: Sem alterações

### Conduta
- Manter medicação atual
- Retorno em 30 dias
- Monitorar pressão arterial semanalmente

**Observações:** Paciente orientada sobre sinais de alerta.
"""

# Parse markdown to PDF flowables
content_elements = markdown_parser.parse(markdown_content)

# Generate PDF
pdf_buffer = pdf_generator.generate_pdf(
    content_elements=content_elements,
    document_title="RELATÓRIO DE EVOLUÇÃO",
    patient_data=patient_data,
    doctor_info=doctor_info
)
```

### Example 3: Integrate with Existing Views

See `apps/outpatientprescriptions/views.py` - `OutpatientPrescriptionPDFView`:

```python
from django.views.generic import DetailView
from apps.pdfgenerator.services.pdf_generator import HospitalLetterheadGenerator

class OutpatientPrescriptionPDFView(LoginRequiredMixin, DetailView):
    model = OutpatientPrescription
    
    def get(self, request, *args, **kwargs):
        # Get prescription
        prescription = self.get_object()
        
        # Initialize PDF generator
        pdf_generator = HospitalLetterheadGenerator()
        
        # Prepare data
        patient_data = {
            'name': prescription.patient.name,
            'fiscal_number': prescription.patient.fiscal_number or '—',
            'birth_date': prescription.patient.birthday.strftime('%d/%m/%Y') if prescription.patient.birthday else '—',
            'health_card_number': prescription.patient.healthcard_number or '—',
        }
        
        doctor_info = {
            'name': prescription.created_by.get_full_name() or prescription.created_by.username,
            'profession': getattr(prescription.created_by, 'profession', 'Médico'),
            'registration_number': getattr(prescription.created_by, 'professional_registration_number', ''),
        }
        
        items = [{
            'drug_name': item.drug_name,
            'presentation': item.presentation,
            'usage_instructions': item.usage_instructions,
            'quantity': item.quantity,
        } for item in prescription.items.order_by('order')]
        
        prescription_data = {
            'prescription_date': prescription.prescription_date.strftime('%d/%m/%Y'),
            'instructions': prescription.instructions,
            'status': prescription.get_status_display(),
        }
        
        # Generate PDF
        pdf_buffer = pdf_generator.create_prescription_pdf(
            prescription_data=prescription_data,
            items=items,
            patient_data=patient_data,
            doctor_info=doctor_info
        )
        
        # Return response
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        filename = f"Receita_Medica_{prescription.patient.name}_{prescription.prescription_date.strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
```

## Styles and Formatting

The PDF generator uses custom ReportLab styles defined in `_create_styles()`:

| Style Name | Font | Size | Alignment | Usage |
|------------|------|------|-----------|-------|
| DocumentTitle | Times-Bold | 14 | Center | Document title |
| MedicalContent | Times-Roman | 11 | Justify | Main content |
| MedicalContentBold | Times-Bold | 11 | Justify | Bold content |
| PatientInfo | Times-Roman | 10 | Left | Patient info |
| Signature | Times-Roman | 10 | Center | Signature section |
| Footer | Times-Roman | 9 | Center | Footer text |

## Permissions

All PDF generation endpoints enforce:
- User authentication (`@login_required`)
- Patient access validation via `can_access_patient()`
- Existing permission system from `apps/core/permissions/`

## Testing

Run tests:

```bash
python manage.py test apps.pdfgenerator
```

Test coverage includes:
- PDF generator initialization
- Markdown parsing (bold, italic, lists, headers)
- Patient info table creation
- Signature section creation
- Basic PDF generation
- Prescription-specific PDF generation
- Empty content handling
- HTML escaping for security

See `apps/pdfgenerator/tests/test_pdf_generation.py` for examples.

## Security

- **XSS Prevention**: HTML characters are escaped in markdown parsing
- **Access Control**: All endpoints validate patient access
- **No File Storage**: PDFs generated on-demand, no persistent storage
- **Logo Security**: Local file paths only, no URL downloads
- **Input Validation**: Markdown content validated before processing

## Performance

- Target: 2-5 PDFs per minute (low volume)
- Synchronous PDF generation (no async needed)
- No caching required
- Basic error logging and monitoring

## Troubleshooting

### Logo Not Displaying

Check logo path in `HOSPITAL_CONFIG`:
```python
# Static file path (recommended)
'logo_path': 'static/images/hospital_logo.png'

# Or absolute path
'logo_path': '/var/www/static/images/hospital_logo.png'
```

### PDF Generation Errors

Enable debug logging:
```python
import logging
logger = logging.getLogger('apps.pdfgenerator')
logger.setLevel(logging.DEBUG)
```

Check common issues:
- Invalid markdown syntax
- Missing patient/doctor data
- Incorrect hospital config
- Permission denied

### Blank PDF Content

Ensure markdown content is properly formatted:
```python
# Bad: empty or None
content = ""

# Good: proper markdown
content = "## Title\n\nSome content..."
```

## Future Enhancements

Potential improvements:
- Template customization per document type
- Digital signature integration
- Batch PDF generation
- Email PDF delivery
- Advanced markdown formatting (tables, code blocks)
- PDF storage and archiving
- Custom fonts
- Multi-language support

## References

- **ReportLab Documentation**: https://reportlab.com/documentation/
- **Markdown Specification**: https://commonmark.org/
- **Django Views**: https://docs.djangoproject.com/en/stable/topics/class-based-views/
- **Implementation Plan**: `prompts/pdfgenerator/pdf_implementation_plan.md`

## Support

For issues or questions:
1. Check this documentation
2. Review test files for usage examples
3. Enable debug logging
4. Check Django logs for error messages
