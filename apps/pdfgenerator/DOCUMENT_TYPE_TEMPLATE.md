# Document Type Template

Use this template when adding a new document type to the PDF generator. Copy this file, rename it to match your document type (e.g., `medical_certificate.md`), and fill in the sections.

---

## Document Name

**Type:** (Prescription | Report | Form | Certificate | Other)
**Endpoint:** `/pdf/<document-type>/`
**View Class:** `<DocumentName>PDFView`
**Status:** (Draft | Implemented | Deprecated)

## Overview

Brief description of what this document type is and its purpose.

### Use Case

When should this document be generated? What is the workflow?

### Example

```python
# Example usage
pdf_generator = HospitalLetterheadGenerator()
pdf_buffer = pdf_generator.create_<document_type>_pdf(...)
```

## API Reference

### Endpoint

**URL:** `/pdf/<document-type>/`
**Method:** `POST`
**Authentication:** Required

### Request

#### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `patient_id` | UUID | Patient identifier | `"123e4567-e89b-12d3-a456-426614174000"` |

#### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `document_title` | string | Document title | `"Medical Certificate"` |
| `content` | string | Markdown content | `"## Certificate..."` |
| `metadata` | object | Document-specific metadata | `{...}` |

#### Metadata Schema

```json
{
  "custom_field_1": "string",
  "custom_field_2": "string",
  "custom_date": "YYYY-MM-DD",
  "custom_list": [
    {"name": "item1", "value": "value1"},
    {"name": "item2", "value": "value2"}
  ]
}
```

### Response

**Content-Type:** `application/pdf`
**Content-Disposition:** `attachment; filename="<Document>_<PatientName>_<Date>.pdf"`

### Example Request

```bash
curl -X POST /pdf/<document-type>/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "patient_id": "123e4567-e89b-12d3-a456-426614174000",
    "document_title": "Document Title",
    "content": "## Content\n\nDetails here...",
    "metadata": {
      "custom_field": "value"
    }
  }'
```

### Example Response

Binary PDF file.

## Implementation Details

### View Class

**File:** `apps/pdfgenerator/views.py`
**Class:** `<DocumentName>PDFView`
**Base Class:** `BasePDFView`

#### Methods

- `generate_pdf_content()` - Generates PDF content with document-specific formatting

### PDF Generator Method

**File:** `apps/pdfgenerator/services/pdf_generator.py`
**Method:** `create_<document_type>_pdf()`

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_data` | dict | Yes | Document-specific data |
| `patient_data` | dict | Yes | Patient information |
| `doctor_info` | dict | Yes | Doctor information |

#### Returns

`BytesIO` buffer with PDF content

## PDF Structure

### Layout

Describe the PDF layout:

```
+----------------------------------------+
|            [Hospital Logo]             |
|         Hospital Name                  |
|        Patient: John Doe               |
+----------------------------------------+
|                                        |
|           DOCUMENT TITLE               |
|                                        |
|  Section 1: Custom Header             |
|  - Field 1: Value                      |  Content area
|  - Field 2: Value                      |
|                                        |
|  Section 2: Items                      |
|  1. Item 1 - Description               |
|  2. Item 2 - Description               |
|                                        |
+----------------------------------------+
|                                        |
|  Date: 20/01/2026    Local: Salvador   |  Signature
|  _____________________________         |
|  Dr. John Smith                        |
|  Médico - CRM: 12345                  |
+----------------------------------------+
| Hospital Name - Address                |  Footer
|                      Página 1/1        |
+----------------------------------------+
```

### Custom Sections

Describe any custom sections beyond the standard header/footer/signature:

- **Section 1:** Description
- **Section 2:** Description
- **Signature:** Any modifications to standard signature?

## Data Structures

### Document Data

```python
document_data = {
    'title': 'Document Title',
    'date': '2025-01-20',
    'custom_field': 'value',
    'items': [
        {'name': 'Item 1', 'description': 'Description 1'},
        {'name': 'Item 2', 'description': 'Description 2'}
    ],
    'notes': 'Additional notes'
}
```

### Patient Data

Standard patient data structure (see QUICK_REFERENCE.md).

### Doctor Info

Standard doctor info structure (see QUICK_REFERENCE.md).

## Markdown Examples

### Basic Template

```markdown
## Document Title

**Date:** 20/01/2026
**Patient:** John Doe

### Section 1
Content here...

### Section 2
- Item 1
- Item 2

### Notes
Additional notes...
```

### Advanced Example

```markdown
## Medical Certificate

**Certifico que o paciente** John Doe **foi examinado em** 20/01/2026.

### Diagnóstico
Paciente apresenta sintomas compatíveis com gripe.

### Recomendações
- Repouso por 3 dias
- Hidratação adequada
- Medicar conforme prescrição

### Validade
Este certificado é válido por 5 dias a partir da data de emissão.

---

**Dr. João Santos**
**CRM/BA 12345**
```

## Usage Examples

### Example 1: Generate PDF from API

```python
import requests
import json

url = 'http://localhost:8000/pdf/<document-type>/'
data = {
    'patient_id': 'patient-uuid',
    'document_title': 'Document Title',
    'content': '## Content\n\nDetails...',
    'metadata': {
        'custom_field': 'value'
    }
}

response = requests.post(
    url,
    headers={'Authorization': 'Bearer <token>'},
    json=data
)

# Save PDF
with open('document.pdf', 'wb') as f:
    f.write(response.content)
```

### Example 2: Generate PDF from View

```python
from django.views.generic import DetailView
from apps.pdfgenerator.services.pdf_generator import HospitalLetterheadGenerator

class MyDocumentPDFView(LoginRequiredMixin, DetailView):
    model = MyModel
    
    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        
        # Initialize
        pdf_generator = HospitalLetterheadGenerator()
        
        # Prepare data
        document_data = {
            'title': obj.title,
            'date': obj.date.strftime('%d/%m/%Y'),
            'items': obj.items.all(),
            'notes': obj.notes
        }
        
        patient_data = {
            'name': obj.patient.name,
            'fiscal_number': obj.patient.fiscal_number or '—',
            'birth_date': obj.patient.birthday.strftime('%d/%m/%Y') if obj.patient.birthday else '—',
            'health_card_number': obj.patient.healthcard_number or '—',
        }
        
        doctor_info = {
            'name': request.user.get_full_name() or request.user.username,
            'profession': getattr(request.user, 'profession', 'Médico'),
        }
        
        # Generate PDF
        pdf_buffer = pdf_generator.create_<document_type>_pdf(
            document_data=document_data,
            patient_data=patient_data,
            doctor_info=doctor_info
        )
        
        # Return response
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        filename = f"{document_data['title']}_{obj.patient.name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
```

### Example 3: Add PDF Button to Template

```html
<!-- templates/myapp/mymodel_detail.html -->
<a href="{% url 'myapp:mymodel_pdf' object.id %}" 
   class="btn btn-primary"
   target="_blank">
    <i class="fas fa-file-pdf"></i> Gerar PDF
</a>
```

## Testing

### Test Cases

```python
class CustomDocumentPDFTestCase(TestCase):
    """Test case for custom document PDF generation"""
    
    def setUp(self):
        self.user = User.objects.create_user(...)
        self.patient = Patient.objects.create(...)
        self.pdf_generator = HospitalLetterheadGenerator()
    
    def test_custom_document_pdf_generation(self):
        """Test custom document PDF generation"""
        # Prepare test data
        document_data = {...}
        patient_data = {...}
        doctor_info = {...}
        
        # Generate PDF
        pdf_buffer = self.pdf_generator.create_custom_document_pdf(
            document_data=document_data,
            patient_data=patient_data,
            doctor_info=doctor_info
        )
        
        # Validate
        self.assertIsInstance(pdf_buffer, io.BytesIO)
        pdf_content = pdf_buffer.read()
        self.assertGreater(len(pdf_content), 0)
        self.assertEqual(pdf_content[:4], b'%PDF')
    
    def test_custom_document_view(self):
        """Test custom document PDF view"""
        self.client.login(username='test', password='pass')
        
        url = reverse('pdfgenerator:custom_document_pdf')
        response = self.client.post(
            url,
            data=json.dumps({'patient_id': str(self.patient.id)}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
```

### Testing Checklist

- [ ] PDF generation with minimal data
- [ ] PDF generation with complete data
- [ ] PDF generation with empty/None optional fields
- [ ] Multi-page documents
- [ ] Long content handling
- [ ] Special characters
- [ ] Permission checks
- [ ] Invalid input handling
- [ ] Error logging
- [ ] Filename sanitization

## Security Considerations

- **Permissions:** What permissions are required?
- **Patient Access:** How is patient access validated?
- **Input Validation:** What input validation is performed?
- **Data Privacy:** Are there any sensitive data concerns?

## Performance Notes

- Typical PDF generation time: X seconds
- Average PDF size: Y KB
- Caching strategy: (if any)
- Performance considerations

## Known Issues

List any known issues or limitations:

- Issue 1: Description
- Issue 2: Description

## Future Enhancements

Planned improvements:

- [ ] Enhancement 1
- [ ] Enhancement 2

## Changelog

### [Version] - Date

- Added: Initial implementation
- Changed: (if modifying existing)
- Fixed: (if fixing issues)

## Related Documentation

- **Main Documentation:** `README.md`
- **Developer Guide:** `DEVELOPER_GUIDE.md`
- **Quick Reference:** `QUICK_REFERENCE.md`
- **Implementation:** `apps/pdfgenerator/views.py`

## Contact

**Developer:** Your Name
**Email:** your.email@example.com
**Date Created:** 2025-01-20

---

## Notes

Add any additional notes or comments here.
