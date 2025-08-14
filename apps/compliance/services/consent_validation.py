from django.core.exceptions import ValidationError
from apps.compliance.models import ConsentRecord, LGPDComplianceSettings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class HospitalConsentValidator:
    """Service to validate hospital consent documents for LGPD compliance"""
    
    def __init__(self):
        self.lgpd_settings = LGPDComplianceSettings.objects.first()
    
    def evaluate_hospital_consent(self, hospital_consent_document, patient, consent_activities):
        """
        Evaluate if hospital consent covers required activities
        
        Args:
            hospital_consent_document: Scanned hospital consent form
            patient: Patient object
            consent_activities: List of activities patient will engage in
            
        Returns:
            dict: {
                'sufficient': bool,
                'covered_activities': list,
                'gaps': list,
                'recommendations': list
            }
        """
        
        # Define what hospital consent typically covers
        hospital_covered_activities = [
            'medical_treatment',  # Always covered by hospital
            'data_processing',    # Basic data storage for medical care
            'emergency_contact',  # Usually included in hospital forms
        ]
        
        # Activities that typically need explicit consent
        explicit_consent_required = [
            'research',           # Research participation
            'marketing',          # Marketing communications 
            'photo_video',        # Medical photography
            'data_sharing',       # Sharing beyond care team
        ]
        
        covered_activities = []
        gaps = []
        recommendations = []
        
        # Evaluate coverage
        for activity in consent_activities:
            if activity in hospital_covered_activities:
                covered_activities.append(activity)
            elif activity in explicit_consent_required:
                gaps.append(activity)
            else:
                # Unknown activity - requires evaluation
                gaps.append(activity)
        
        # Generate recommendations
        if gaps:
            if 'research' in gaps:
                recommendations.append(
                    "Collect specific research consent form before including patient in studies"
                )
            if 'photo_video' in gaps:
                recommendations.append(
                    "Obtain explicit consent before capturing medical images"
                )
            if 'marketing' in gaps:
                recommendations.append(
                    "Collect marketing consent separately - cannot rely on hospital forms"
                )
        
        # Determine if hospital consent is sufficient
        sufficient = len(gaps) == 0
        
        return {
            'sufficient': sufficient,
            'covered_activities': covered_activities,
            'gaps': gaps,
            'recommendations': recommendations,
            'hospital_coverage_percentage': len(covered_activities) / len(consent_activities) * 100 if consent_activities else 0
        }
    
    def create_hospital_consent_record(self, patient, hospital_document, reference_number, clerk_name):
        """
        Create consent record based on hospital documentation
        
        Args:
            patient: Patient object
            hospital_document: Uploaded hospital consent file
            reference_number: Hospital form reference number
            clerk_name: Name of clerk who copied the data
            
        Returns:
            ConsentRecord: Created consent record
        """
        
        consent_record = ConsentRecord.objects.create(
            patient=patient,
            consent_type='hospital_consent',
            purpose_description='Consentimento coletado pelo hospital para tratamento médico e gestão de dados',
            data_categories='Dados de identificação, dados médicos, informações de contato',
            processing_activities='Coleta, armazenamento, uso para cuidados médicos, comunicação médica',
            status='granted',
            granted_at=datetime.now(),
            granted_by=patient.name,
            granted_by_relationship='self',
            consent_method='paper_form',
            consent_source='hospital_form',
            hospital_consent_reference=reference_number,
            hospital_consent_document=hospital_document,
            legal_basis='art11_ii_a',
            lawful_basis_explanation='Consentimento coletado pelo hospital para prestação de cuidados médicos'
        )
        
        logger.info(f"Created hospital consent record for patient {patient.name} (ref: {reference_number})")
        return consent_record
    
    def validate_consent_completeness(self, patient):
        """
        Validate that patient has all required consents for system use
        
        Returns:
            dict: Validation results with missing consents
        """
        
        required_consents = ['medical_treatment', 'data_processing']
        existing_consents = ConsentRecord.objects.filter(
            patient=patient,
            status='granted'
        ).values_list('consent_type', flat=True)
        
        missing_consents = []
        for required in required_consents:
            if required not in existing_consents:
                missing_consents.append(required)
        
        return {
            'complete': len(missing_consents) == 0,
            'missing_consents': missing_consents,
            'existing_consents': list(existing_consents)
        }