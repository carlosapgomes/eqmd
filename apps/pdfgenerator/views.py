import json
import logging
from datetime import datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.conf import settings

from apps.patients.models import Patient
from apps.outpatientprescriptions.models import OutpatientPrescription
from apps.core.permissions.utils import can_access_patient
from .services.pdf_generator import HospitalLetterheadGenerator
from .services.markdown_parser import MarkdownToPDFParser

logger = logging.getLogger(__name__)


class BasePDFView(LoginRequiredMixin, View):
    """Base view for PDF generation with common functionality"""
    
    def __init__(self):
        super().__init__()
        self.pdf_generator = HospitalLetterheadGenerator()
        self.markdown_parser = MarkdownToPDFParser(self.pdf_generator.styles)
    
    def post(self, request, *args, **kwargs):
        """Handle PDF generation requests"""
        try:
            # Parse request data
            data = json.loads(request.body)
            patient_id = data.get('patient_id')
            content = data.get('content', '')
            document_title = data.get('document_title', 'Document')
            metadata = data.get('metadata', {})
            
            # Validate input
            if not patient_id:
                return JsonResponse({'error': 'patient_id is required'}, status=400)
            
            # Get patient and validate access
            patient = get_object_or_404(Patient, id=patient_id)
            if not can_access_patient(request.user, patient):
                raise PermissionDenied("You don't have permission to access this patient")
            
            # Prepare patient data
            patient_data = {
                'name': patient.name,
                'fiscal_number': patient.fiscal_number or '—',
                'birth_date': patient.birthday.strftime('%d/%m/%Y') if patient.birthday else '—',
                'health_card_number': patient.healthcard_number or '—',
            }
            
            # Prepare doctor info
            doctor_info = {
                'name': request.user.get_full_name() or request.user.username,
                'profession': getattr(request.user, 'profession', 'Médico'),
            }
            
            # Generate PDF content
            pdf_buffer = self.generate_pdf_content(
                content=content,
                document_title=document_title,
                patient_data=patient_data,
                doctor_info=doctor_info,
                metadata=metadata
            )
            
            # Create response
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            
            # Generate filename
            filename = self.create_filename(document_title, patient.name, datetime.now())
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Log PDF generation
            logger.info(f"PDF generated: {document_title} for patient {patient.name} by {request.user.username}")
            
            return response
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except PermissionDenied as e:
            return JsonResponse({'error': str(e)}, status=403)
        except Exception as e:
            logger.error(f"PDF generation error: {str(e)}", exc_info=True)
            return JsonResponse({'error': f'Error generating PDF: {str(e)}'}, status=500)
    
    def generate_pdf_content(self, content, document_title, patient_data, doctor_info, metadata):
        """Generate PDF content - to be overridden by subclasses"""
        # Parse markdown content
        content_elements = self.markdown_parser.parse(content)
        
        # Generate PDF
        return self.pdf_generator.generate_pdf(
            content_elements=content_elements,
            document_title=document_title,
            patient_data=patient_data,
            doctor_info=doctor_info
        )
    
    def create_filename(self, document_title, patient_name, date):
        """Create safe filename for PDF"""
        # Sanitize strings for filename
        safe_title = "".join(c for c in document_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        date_str = date.strftime('%Y%m%d')
        
        return f"{safe_title}_{safe_name}_{date_str}.pdf"


class PrescriptionPDFView(BasePDFView):
    """Generate prescription PDFs from existing OutpatientPrescription records"""
    
    def post(self, request, *args, **kwargs):
        """Handle prescription PDF generation"""
        try:
            # Parse request data
            data = json.loads(request.body)
            prescription_id = data.get('prescription_id')
            
            if not prescription_id:
                return JsonResponse({'error': 'prescription_id is required'}, status=400)
            
            # Get prescription and validate access
            prescription = get_object_or_404(OutpatientPrescription, id=prescription_id)
            if not can_access_patient(request.user, prescription.patient):
                raise PermissionDenied("You don't have permission to access this prescription")
            
            # Prepare data for PDF generation
            patient_data = {
                'name': prescription.patient.name,
                'fiscal_number': prescription.patient.fiscal_number or '—',
                'birth_date': prescription.patient.birthday.strftime('%d/%m/%Y') if prescription.patient.birthday else '—',
                'health_card_number': prescription.patient.healthcard_number or '—',
            }
            
            doctor_info = {
                'name': prescription.created_by.get_full_name() or prescription.created_by.username,
                'profession': getattr(prescription.created_by, 'profession', 'Médico'),
            }
            
            # Get prescription items
            items = []
            for item in prescription.prescriptionitem_set.all():
                items.append({
                    'drug_name': item.drug_name,
                    'presentation': item.presentation,
                    'usage_instructions': item.usage_instructions,
                    'quantity': item.quantity,
                })
            
            # Prepare prescription data
            prescription_data = {
                'prescription_date': prescription.prescription_date.strftime('%d/%m/%Y'),
                'instructions': prescription.instructions,
                'status': prescription.get_status_display(),
            }
            
            # Generate prescription PDF
            pdf_buffer = self.pdf_generator.create_prescription_pdf(
                prescription_data=prescription_data,
                items=items,
                patient_data=patient_data,
                doctor_info=doctor_info
            )
            
            # Create response
            response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
            
            # Generate filename
            filename = self.create_filename(
                "Receita_Medica", 
                prescription.patient.name, 
                prescription.prescription_date
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Log PDF generation
            logger.info(f"Prescription PDF generated for {prescription.patient.name} by {request.user.username}")
            
            return response
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except PermissionDenied as e:
            return JsonResponse({'error': str(e)}, status=403)
        except Exception as e:
            logger.error(f"Prescription PDF generation error: {str(e)}", exc_info=True)
            return JsonResponse({'error': f'Error generating prescription PDF: {str(e)}'}, status=500)


class DischargeReportPDFView(BasePDFView):
    """Generate discharge report PDFs"""
    
    def generate_pdf_content(self, content, document_title, patient_data, doctor_info, metadata):
        """Generate discharge report PDF content"""
        content_elements = []
        
        # Add discharge-specific sections
        if metadata.get('admission_date'):
            content_elements.extend(self.markdown_parser.parse(
                f"**Data de Internação:** {metadata['admission_date']}"
            ))
        
        if metadata.get('discharge_date'):
            content_elements.extend(self.markdown_parser.parse(
                f"**Data de Alta:** {metadata['discharge_date']}"
            ))
        
        # Add main content
        content_elements.extend(self.markdown_parser.parse(content))
        
        return self.pdf_generator.generate_pdf(
            content_elements=content_elements,
            document_title=document_title or "RELATÓRIO DE ALTA HOSPITALAR",
            patient_data=patient_data,
            doctor_info=doctor_info
        )


class ExamRequestPDFView(BasePDFView):
    """Generate exam request PDFs"""
    
    def generate_pdf_content(self, content, document_title, patient_data, doctor_info, metadata):
        """Generate exam request PDF content"""
        content_elements = []
        
        # Add exam request-specific sections
        if metadata.get('requested_exams'):
            content_elements.extend(self.markdown_parser.parse(
                f"**Exames Solicitados:**\n\n{metadata['requested_exams']}"
            ))
        
        if metadata.get('clinical_indication'):
            content_elements.extend(self.markdown_parser.parse(
                f"**Indicação Clínica:**\n\n{metadata['clinical_indication']}"
            ))
        
        # Add main content
        if content.strip():
            content_elements.extend(self.markdown_parser.parse(content))
        
        return self.pdf_generator.generate_pdf(
            content_elements=content_elements,
            document_title=document_title or "SOLICITAÇÃO DE EXAMES",
            patient_data=patient_data,
            doctor_info=doctor_info
        )