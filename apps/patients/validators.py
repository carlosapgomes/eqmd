from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

def validate_record_number_format(record_number):
    """Validate record number format (customize based on hospital requirements)"""
    if not record_number or not record_number.strip():
        raise ValidationError("Número do prontuário não pode estar vazio")
    
    # Example validation - customize based on hospital requirements
    if len(record_number.strip()) < 3:
        raise ValidationError("Número do prontuário deve ter pelo menos 3 caracteres")
    
    # Add more specific validation rules as needed
    # e.g., regex patterns, check digits, etc.

def validate_admission_datetime(admission_datetime):
    """Validate admission datetime"""
    if not admission_datetime:
        raise ValidationError("Data/hora de admissão é obrigatória")
    
    # Can't be in the future (allow some buffer for clock differences)
    if admission_datetime > timezone.now() + timedelta(minutes=5):
        raise ValidationError("Data de admissão não pode ser no futuro")
    
    # Can't be too far in the past (customize based on requirements)
    if admission_datetime < timezone.now() - timedelta(days=365):
        raise ValidationError("Data de admissão não pode ser superior a 1 ano atrás")

def validate_discharge_datetime(discharge_datetime, admission_datetime):
    """Validate discharge datetime against admission"""
    if not discharge_datetime:
        return  # Discharge is optional
    
    if not admission_datetime:
        raise ValidationError("Data de admissão deve estar definida para registrar alta")
    
    if discharge_datetime <= admission_datetime:
        raise ValidationError("Data de alta deve ser posterior à data de admissão")
    
    # Can't be in the future
    if discharge_datetime > timezone.now() + timedelta(minutes=5):
        raise ValidationError("Data de alta não pode ser no futuro")
    
    # Check for reasonable stay duration (customize based on requirements)
    stay_duration = discharge_datetime - admission_datetime
    if stay_duration.days > 365:
        raise ValidationError("Duração da internação parece muito longa (>365 dias)")

def validate_patient_admission_state(patient):
    """Validate patient's overall admission state for consistency"""
    active_admissions = patient.admissions.filter(is_active=True)
    
    if active_admissions.count() > 1:
        raise ValidationError("Paciente não pode ter múltiplas internações ativas")
    
    if patient.status == patient.Status.INPATIENT and not active_admissions.exists():
        raise ValidationError("Paciente marcado como internado mas sem internação ativa")
    
    if patient.status != patient.Status.INPATIENT and active_admissions.exists():
        raise ValidationError("Paciente tem internação ativa mas status indica que não está internado")