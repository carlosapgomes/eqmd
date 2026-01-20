# Developer Guide: Adding New Document Types

This guide explains how to extend the PDF generator to support new document types.

## Overview

To add a new document type to the PDF generator, you need to:

1. Create a new view class extending `BasePDFView`
2. Add a URL route for the new endpoint
3. Optionally add a specific method in `HospitalLetterheadGenerator` if custom formatting is needed
4. Add tests for the new functionality

## Step-by-Step Guide

### Step 1: Define Requirements

Before implementing, answer these questions:

- What data is needed for this document type?
- Does it require special formatting beyond the base template?
- What metadata should be included?
- What should the document title be?
- Are there any special sections (e.g., signature block modifications)?

### Step 2: Create a New View Class

Create a new class in `apps/pdfgenerator/views.py`:

```python
class NewDocumentPDFView(BasePDFView):
    """Generate new document type PDFs"""
    
    def generate_pdf_content(self, content, document_title, patient_data, doctor_info, metadata):
        """
        Generate new document PDF content.
        
        Args:
            content: Main markdown content
            document_title: Title for the document
            patient_data: Patient information dict
            doctor_info: Doctor information dict
            metadata: Additional document-specific data
            
        Returns:
            BytesIO buffer with PDF content
        """
        content_elements = []
        
        # Add document-specific sections using metadata
        if metadata.get('custom_field'):
            content_elements.extend(self.markdown_parser.parse(
                f"**Custom Field:** {metadata['custom_field']}"
            ))
        
        # Add main content
        content_elements.extend(self.markdown_parser.parse(content))
        
        # Generate PDF
        return self.pdf_generator.generate_pdf(
            content_elements=content_elements,
            document_title=document_title or "DEFAULT TITLE",
            patient_data=patient_data,
            doctor_info=doctor_info
        )
```

### Step 3: Add URL Route

Add the route in `apps/pdfgenerator/urls.py`:

```python
from django.urls import path
from . import views

app_name = 'pdfgenerator'

urlpatterns = [
    path('prescription/', views.PrescriptionPDFView.as_view(), name='prescription_pdf'),
    path('discharge-report/', views.DischargeReportPDFView.as_view(), name='discharge_report_pdf'),
    path('exam-request/', views.ExamRequestPDFView.as_view(), name='exam_request_pdf'),
    path('new-document/', views.NewDocumentPDFView.as_view(), name='new_document_pdf'),  # Add this
]
```

### Step 4: (Optional) Add Custom PDF Generation Method

If the document type requires special formatting beyond what the base `generate_pdf()` provides, add a custom method in `HospitalLetterheadGenerator`:

```python
# In apps/pdfgenerator/services/pdf_generator.py

class HospitalLetterheadGenerator:
    # ... existing methods ...
    
    def create_custom_document_pdf(self, document_data, patient_data, doctor_info):
        """
        Create a custom document PDF with specific formatting.
        
        Args:
            document_data: Dict with document-specific information
            patient_data: Dict with patient information
            doctor_info: Dict with doctor information
            
        Returns:
            BytesIO buffer with PDF content
        """
        content = []
        
        # Custom header section
        if document_data.get('reference_number'):
            content.append(Spacer(1, 6))
            content.append(
                Paragraph(
                    f"<b>Nº Referência:</b> {document_data['reference_number']}",
                    self.styles["PatientInfo"]
                )
            )
            content.append(Spacer(1, 6))
        
        # Custom content section
        if document_data.get('custom_list'):
            content.append(Spacer(1, 6))
            content.append(
                Paragraph(
                    "<b>CUSTOM ITEMS:</b>",
                    self.styles["MedicalContentBold"]
                )
            )
            content.append(Spacer(1, 6))
            
            for item in document_data['custom_list']:
                item_content = f"<b>{item.get('name')}</b>"
                if item.get('description'):
                    item_content += f"<br/>{item['description']}"
                
                # Keep item together on same page
                content.append(
                    KeepTogether([
                        Paragraph(item_content, self.styles["MedicalContent"]),
                        Spacer(1, 8)
                    ])
                )
        
        # General notes
        if document_data.get('notes'):
            content.append(KeepTogether([
                Spacer(1, 12),
                Paragraph(
                    "<b>NOTAS:</b>",
                    self.styles["MedicalContentBold"]
                ),
                Spacer(1, 6),
                Paragraph(
                    document_data['notes'],
                    self.styles["MedicalContent"]
                ),
            ]))
        
        return self.generate_pdf(
            content_elements=content,
            document_title=document_data.get('title', 'CUSTOM DOCUMENT'),
            patient_data=patient_data,
            doctor_info=doctor_info
        )
```

Then update your view to use this method:

```python
class NewDocumentPDFView(BasePDFView):
    """Generate new document type PDFs"""
    
    def post(self, request, *args, **kwargs):
        """Handle new document PDF generation"""
        try:
            data = json.loads(request.body)
            patient_id = data.get('patient_id')
            
            # Get patient and validate access
            patient = get_object_or_404(Patient, id=patient_id)
            if not can_access_patient(request.user, patient):
                raise PermissionDenied("Access denied")
            
            # Prepare data
            patient_data = {
                'name': patient.name,
                'fiscal_number': patient.fiscal_number or '—',
                'birth_date': patient.birthday.strftime('%d/%m/%Y') if patient.birthday else '—',
                'health_card_number': patient.healthcard_number or '—',
            }
            
            doctor_info = {
                'name': request.user.get_full_name() or request.user.username,
                'profession': getattr(request.user, 'profession', 'Médico'),
            }
            
            # Prepare document data
            document_data = {
                'title': data.get('title', 'Custom Document'),
                'reference_number': data.get('reference_number'),
                'custom_list': data.get('items', []),
                'notes': data.get('notes'),
            }
            
            # Generate PDF using custom method
            pdf_buffer = self.pdf_generator.create_custom_document_pdf(
                document_data=document_data,
                patient_data=patient_data,
                doctor_info=doctor_info
            )
            
            # Create response
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            filename = self.create_filename(document_data['title'], patient.name, datetime.now())
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            logger.error(f"Custom document PDF error: {str(e)}", exc_info=True)
            return JsonResponse({'error': f'Error: {str(e)}'}, status=500)
```

### Step 5: Add Tests

Add tests in `apps/pdfgenerator/tests/test_pdf_generation.py`:

```python
class CustomDocumentPDFTestCase(TestCase):
    """Test case for custom document PDF generation"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testdoctor',
            email='test@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=date(1990, 1, 1),
            fiscal_number='123.456.789-00',
            healthcard_number='123456789012345',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.pdf_generator = HospitalLetterheadGenerator()
        self.markdown_parser = MarkdownToPDFParser(self.pdf_generator.styles)
    
    def test_custom_document_pdf_generation(self):
        """Test custom document PDF generation"""
        # Prepare test data
        patient_data = {
            'name': self.patient.name,
            'fiscal_number': self.patient.fiscal_number,
            'birth_date': '01/01/1990',
            'health_card_number': self.patient.healthcard_number
        }
        
        doctor_info = {
            'name': self.user.username,
            'profession': 'Médico'
        }
        
        document_data = {
            'title': 'Custom Document',
            'reference_number': 'REF-2025-001',
            'custom_list': [
                {'name': 'Item 1', 'description': 'Description 1'},
                {'name': 'Item 2', 'description': 'Description 2'},
            ],
            'notes': 'Additional notes here.'
        }
        
        # Generate PDF
        pdf_buffer = self.pdf_generator.create_custom_document_pdf(
            document_data=document_data,
            patient_data=patient_data,
            doctor_info=doctor_info
        )
        
        # Verify PDF was generated
        self.assertIsInstance(pdf_buffer, io.BytesIO)
        pdf_content = pdf_buffer.read()
        self.assertGreater(len(pdf_content), 0)
        
        # Basic PDF validation
        pdf_buffer.seek(0)
        first_bytes = pdf_buffer.read(4)
        self.assertEqual(first_bytes, b'%PDF')
    
    def test_custom_document_view(self):
        """Test custom document PDF view"""
        self.client.login(username='testdoctor', password='testpass123')
        
        url = reverse('pdfgenerator:new_document_pdf')
        data = {
            'patient_id': str(self.patient.id),
            'content': '## Test Content\n\nThis is a test.',
            'title': 'Test Document',
            'reference_number': 'REF-123',
            'items': [
                {'name': 'Item 1', 'description': 'Description 1'}
            ]
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
```

## Integration Example: Adding PDF Generation to Existing Views

### Scenario: Add PDF button to an existing view

```python
# In your app's views.py
from django.views.generic import DetailView
from django.http import HttpResponse
from apps.pdfgenerator.services.pdf_generator import HospitalLetterheadGenerator

class MyModelDetailView(LoginRequiredMixin, DetailView):
    model = MyModel
    template_name = 'myapp/mymodel_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add PDF URL to context
        context['pdf_url'] = reverse('myapp:mymodel_pdf', kwargs={'pk': self.object.id})
        return context


class MyModelPDFView(LoginRequiredMixin, DetailView):
    """Generate PDF for MyModel"""
    model = MyModel
    
    def get(self, request, *args, **kwargs):
        # Get object and check permissions
        obj = self.get_object()
        
        # Initialize PDF generator
        pdf_generator = HospitalLetterheadGenerator()
        
        # Prepare patient data if applicable
        patient_data = {
            'name': obj.patient.name if hasattr(obj, 'patient') else 'N/A',
            'fiscal_number': getattr(obj.patient, 'fiscal_number', None) or '—',
            'birth_date': obj.patient.birthday.strftime('%d/%m/%Y') if hasattr(obj, 'patient') and obj.patient.birthday else '—',
            'health_card_number': getattr(obj.patient, 'healthcard_number', None) or '—',
        }
        
        # Prepare doctor info
        doctor_info = {
            'name': request.user.get_full_name() or request.user.username,
            'profession': getattr(request.user, 'profession', 'Médico'),
        }
        
        # Prepare content
        markdown_content = f"""
        ## {obj.title or 'Document'}
        
        **Data:** {obj.created_at.strftime('%d/%m/%Y')}
        
        ### Descrição
        {obj.description or ''}
        
        ### Detalhes
        {obj.details or ''}
        """
        
        # Parse markdown
        from apps.pdfgenerator.services.markdown_parser import MarkdownToPDFParser
        markdown_parser = MarkdownToPDFParser(pdf_generator.styles)
        content_elements = markdown_parser.parse(markdown_content)
        
        # Generate PDF
        pdf_buffer = pdf_generator.generate_pdf(
            content_elements=content_elements,
            document_title=obj.title or 'DOCUMENTO',
            patient_data=patient_data,
            doctor_info=doctor_info
        )
        
        # Return response
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        filename = f"{obj.title or 'Documento'}_{datetime.now().strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
```

### Add URL route:

```python
# In your app's urls.py
from django.urls import path
from . import views

app_name = 'myapp'

urlpatterns = [
    # ... existing URLs ...
    path('<uuid:pk>/pdf/', views.MyModelPDFView.as_view(), name='mymodel_pdf'),
]
```

### Add button to template:

```html
<!-- In templates/myapp/mymodel_detail.html -->
<a href="{{ pdf_url }}" class="btn btn-primary" target="_blank">
    <i class="fas fa-file-pdf"></i> Gerar PDF
</a>
```

## Best Practices

### 1. Use `KeepTogether` for Multi-line Content

When displaying items that should stay on the same page:

```python
from reportlab.platypus import KeepTogether

content.append(
    KeepTogether([
        Paragraph(item_content, self.styles["MedicalContent"]),
        Spacer(1, 8)
    ])
)
```

### 2. Handle Optional Data Gracefully

Always provide fallback values for optional fields:

```python
patient_data = {
    'name': patient.name,
    'fiscal_number': patient.fiscal_number or '—',
    'birth_date': patient.birthday.strftime('%d/%m/%Y') if patient.birthday else '—',
    'health_card_number': patient.healthcard_number or '—',
}
```

### 3. Sanitize Filenames

Always sanitize filenames for safe downloads:

```python
def create_filename(self, document_title, patient_name, date):
    safe_title = "".join(c for c in document_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    date_str = date.strftime('%Y%m%d')
    return f"{safe_title}_{safe_name}_{date_str}.pdf"
```

### 4. Log PDF Generation

Add logging for debugging and auditing:

```python
import logging

logger = logging.getLogger(__name__)

# After successful generation
logger.info(
    f"PDF generated: {document_title} for patient {patient.name} "
    f"by {request.user.username}"
)

# On error
logger.error(
    f"PDF generation error: {str(e)}",
    exc_info=True
)
```

### 5. Validate Input

Always validate input before processing:

```python
def post(self, request, *args, **kwargs):
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        if not data.get('patient_id'):
            return JsonResponse({'error': 'patient_id is required'}, status=400)
        
        # Validate content length
        content = data.get('content', '')
        if len(content) > settings.PDF_CONFIG['max_content_length']:
            return JsonResponse({'error': 'Content too long'}, status=400)
        
        # ... process request
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
```

### 6. Use Existing Styles

Leverage the predefined styles instead of creating new ones:

```python
# Available styles:
# - DocumentTitle (14pt, bold, centered)
# - MedicalContent (11pt, justified)
# - MedicalContentBold (11pt, bold, justified)
# - PatientInfo (10pt, left-aligned)
# - Signature (10pt, centered)
# - Footer (9pt, centered, gray)
```

## Common Patterns

### Pattern 1: Document with Key-Value Metadata

```python
def generate_pdf_content(self, content, document_title, patient_data, doctor_info, metadata):
    content_elements = []
    
    # Add metadata as key-value pairs
    for key, label in [
        ('date', 'Data'),
        ('reference', 'Referência'),
        ('type', 'Tipo'),
    ]:
        if metadata.get(key):
            content_elements.extend(self.markdown_parser.parse(
                f"**{label}:** {metadata[key]}"
            ))
    
    # Add main content
    content_elements.extend(self.markdown_parser.parse(content))
    
    return self.pdf_generator.generate_pdf(
        content_elements=content_elements,
        document_title=document_title,
        patient_data=patient_data,
        doctor_info=doctor_info
    )
```

### Pattern 2: Document with Numbered Items

```python
def create_items_pdf(self, items_data, patient_data, doctor_info):
    content = []
    
    content.append(Spacer(1, 6))
    content.append(
        Paragraph(
            "<b>ITENS:</b>",
            self.styles["MedicalContentBold"]
        )
    )
    content.append(Spacer(1, 6))
    
    for i, item in enumerate(items_data, 1):
        item_content = [
            f"<b>{i}. {item.get('name')}</b>"
        ]
        
        if item.get('description'):
            item_content.append(item['description'])
        
        if item.get('quantity'):
            item_content.append(f"<b>Quantidade:</b> {item['quantity']}")
        
        content.append(
            KeepTogether([
                Paragraph("<br/>".join(item_content), self.styles["MedicalContent"]),
                Spacer(1, 8)
            ])
        )
    
    return self.generate_pdf(
        content_elements=content,
        document_title="LISTA DE ITENS",
        patient_data=patient_data,
        doctor_info=doctor_info
    )
```

### Pattern 3: Document with Tables

```python
from reportlab.platypus import Table, TableStyle

def create_table_pdf(self, table_data, patient_data, doctor_info):
    content = []
    
    # Create table data
    table_data_list = [
        ['Header 1', 'Header 2', 'Header 3'],
        *table_data
    ]
    
    # Create table
    table = Table(table_data_list, colWidths=[5*cm, 5*cm, 5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    content.append(Spacer(1, 12))
    content.append(table)
    
    return self.generate_pdf(
        content_elements=content,
        document_title="TABLE DOCUMENT",
        patient_data=patient_data,
        doctor_info=doctor_info
    )
```

## Testing Checklist

When adding a new document type, ensure you test:

- [ ] PDF generation with minimal data
- [ ] PDF generation with complete data
- [ ] PDF generation with empty/None optional fields
- [ ] Multi-page documents
- [ ] Long content handling
- [ ] Special characters (accents, symbols)
- [ ] Permission checks (access denied for unauthorized users)
- [ ] Invalid input handling
- [ ] Error logging
- [ ] Filename sanitization
- [ ] Content-Type header
- [ ] PDF validity (starts with %PDF)

## Resources

- **Main README**: `apps/pdfgenerator/README.md`
- **Implementation Plan**: `prompts/pdfgenerator/pdf_implementation_plan.md`
- **Existing Views**: `apps/pdfgenerator/views.py`
- **Existing Tests**: `apps/pdfgenerator/tests/test_pdf_generation.py`
- **ReportLab Docs**: https://reportlab.com/documentation/
