# PDF Generator Quick Reference

Quick reference for common PDF generation tasks.

## Basic Setup

```python
from apps.pdfgenerator.services.pdf_generator import HospitalLetterheadGenerator
from apps.pdfgenerator.services.markdown_parser import MarkdownToPDFParser

# Initialize
pdf_generator = HospitalLetterheadGenerator()
markdown_parser = MarkdownToPDFParser(pdf_generator.styles)
```

## Common Data Formats

### Patient Data

```python
patient_data = {
    'name': 'Patient Name',
    'fiscal_number': '123.456.789-00',
    'birth_date': '01/01/1990',
    'health_card_number': '123456789012345'
}
```

### Doctor Info

```python
doctor_info = {
    'name': 'Dr. Name',
    'profession': 'Médico',
    'registration_number': 'CRM/BA 12345'
}
```

## Generate Simple PDF from Markdown

```python
# Markdown content
content = """
## Document Title

This is **bold** and this is *italic*.

### Lists
- Item 1
- Item 2

### Ordered Lists
1. First
2. Second
"""

# Parse markdown
content_elements = markdown_parser.parse(content)

# Generate PDF
pdf_buffer = pdf_generator.generate_pdf(
    content_elements=content_elements,
    document_title="DOCUMENT TITLE",
    patient_data=patient_data,
    doctor_info=doctor_info
)

# Return as response
from django.http import HttpResponse
response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
return response
```

## Generate Prescription PDF

```python
prescription_data = {
    'prescription_date': '20/01/2026',
    'instructions': 'Seguir rigorosamente a posologia.',
    'status': 'Ativa'
}

items = [
    {
        'drug_name': 'Paracetamol',
        'presentation': '500mg comprimido',
        'usage_instructions': 'Tomar 1 comprimido a cada 8 horas',
        'quantity': '30 comprimidos'
    }
]

pdf_buffer = pdf_generator.create_prescription_pdf(
    prescription_data=prescription_data,
    items=items,
    patient_data=patient_data,
    doctor_info=doctor_info
)
```

## Generate PDF in a View

```python
from django.views.generic import DetailView
from django.http import HttpResponse
from apps.pdfgenerator.services.pdf_generator import HospitalLetterheadGenerator

class MyPDFView(LoginRequiredMixin, DetailView):
    model = MyModel
    
    def get(self, request, *args, **kwargs):
        # Get object
        obj = self.get_object()
        
        # Initialize
        pdf_generator = HospitalLetterheadGenerator()
        
        # Prepare data
        patient_data = {'name': obj.patient.name, ...}
        doctor_info = {'name': request.user.username, ...}
        
        # Generate PDF
        pdf_buffer = pdf_generator.generate_pdf(...)
        
        # Return
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="document.pdf"'
        return response
```

## Markdown Examples

### Basic Formatting

```markdown
## Title

Normal text, **bold text**, *italic text*.

Underline: <u>text</u>
Code: `code`
```

### Lists

```markdown
### Bullet List
- Item 1
- Item 2
- Item 3

### Ordered List
1. First item
2. Second item
3. Third item
```

### Blockquotes

```markdown
> This is a blockquote
> Multiple lines
```

### Horizontal Rule

```markdown
---
```

### Medical Document Example

```markdown
## Receita Médica

**Data:** 20/01/2026

### Medicamentos

**1. Paracetamol 500mg**
*Apresentação:* Comprimido
*Posologia:* Tomar 1 comprimido a cada 8 horas
*Quantidade:* 30 comprimidos

### Instruções Gerais
- Tomar conforme orientação médica
- Não interromper o tratamento
- Em caso de reações adversas, procure o médico
```

## Available Styles

| Style | Font | Size | Use Case |
|-------|------|------|----------|
| `DocumentTitle` | Times-Bold | 14pt | Document title |
| `MedicalContent` | Times-Roman | 11pt | Main content |
| `MedicalContentBold` | Times-Bold | 11pt | Emphasized content |
| `PatientInfo` | Times-Roman | 10pt | Patient information |
| `Signature` | Times-Roman | 10pt | Signature section |
| `Footer` | Times-Roman | 9pt (gray) | Footer text |

## Custom Formatting

### Add Custom Paragraph

```python
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle

# Create custom style
custom_style = ParagraphStyle(
    name='Custom',
    parent=pdf_generator.styles['MedicalContent'],
    fontName='Times-Italic',
    textColor=colors.red
)

# Add to content
content_elements.append(Paragraph("Custom text", custom_style))
content_elements.append(Spacer(1, 6))
```

### Add Table

```python
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

# Table data
table_data = [
    ['Header 1', 'Header 2', 'Header 3'],
    ['Data 1', 'Data 2', 'Data 3'],
    ['Data 4', 'Data 5', 'Data 6']
]

# Create table
table = Table(table_data, colWidths=[5*cm, 5*cm, 5*cm])
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('GRID', (0, 0), (-1, -1), 1, colors.black),
]))

content_elements.append(table)
```

### Keep Content Together

```python
from reportlab.platypus import KeepTogether

content_elements.append(
    KeepTogether([
        Paragraph("Item 1", pdf_generator.styles['MedicalContent']),
        Spacer(1, 6),
        Paragraph("Item 2", pdf_generator.styles['MedicalContent']),
    ])
)
```

## Response Handling

### Download as Attachment

```python
response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
response['Content-Disposition'] = 'attachment; filename="document.pdf"'
return response
```

### Display in Browser

```python
response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
response['Content-Disposition'] = 'inline; filename="document.pdf"'
return response
```

### Safe Filename

```python
def safe_filename(text):
    return "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).rstrip()

filename = f"Document_{safe_filename(patient.name)}_{date_str}.pdf"
```

## URL Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/pdf/prescription/` | POST | Generate prescription PDF |
| `/pdf/discharge-report/` | POST | Generate discharge report PDF |
| `/pdf/exam-request/` | POST | Generate exam request PDF |

## Error Handling

```python
try:
    pdf_buffer = pdf_generator.generate_pdf(...)
    # Handle success
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"PDF generation error: {str(e)}", exc_info=True)
    # Handle error
    return HttpResponse(f"Error: {str(e)}", status=500)
```

## Configuration

### Hospital Config

```python
# settings.py
HOSPITAL_CONFIG = {
    'name': 'Hospital Name',
    'address': 'Street Address',
    'logo_path': 'static/images/logo.png'
}
```

### PDF Config

```python
# settings.py
PDF_CONFIG = {
    'page_size': 'A4',
    'orientation': 'portrait',
    'margins': {
        'top': 2.5,
        'bottom': 3.0,
        'left': 2.0,
        'right': 2.0
    }
}
```

## Testing

```python
# Generate PDF
pdf_buffer = pdf_generator.generate_pdf(...)

# Validate
import io
assert isinstance(pdf_buffer, io.BytesIO)
pdf_content = pdf_buffer.read()
assert len(pdf_content) > 0
assert pdf_content[:4] == b'%PDF'
```

## Common Issues

### Logo Not Showing

Check logo path is correct:
```python
'logo_path': 'static/images/logo.png'  # or absolute path
```

### Blank PDF

Ensure content is not empty:
```python
if not content.strip():
    content = "## Empty Document\n\nNo content provided."
```

### Permission Denied

Check patient access:
```python
from apps.core.permissions.utils import can_access_patient

if not can_access_patient(request.user, patient):
    raise PermissionDenied("Access denied")
```

## Performance Tips

- PDFs are generated on-demand (no storage)
- Target: 2-5 PDFs per minute (low volume)
- Use `KeepTogether` to prevent content splitting
- Cache repeated content if needed

## See Also

- **Full Documentation**: `README.md`
- **Developer Guide**: `DEVELOPER_GUIDE.md`
- **Implementation Plan**: `prompts/pdfgenerator/pdf_implementation_plan.md`
