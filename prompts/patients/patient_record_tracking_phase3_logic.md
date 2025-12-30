# Phase 3: Business Logic and Automation

## Overview

Implement the business logic, validation rules, and automatic updates to maintain data consistency between the normalized and denormalized data, and ensure proper status management.

## Step-by-Step Implementation

### Step 3.1: Enhanced Patient Model Methods

**File**: `apps/patients/models.py` - Add comprehensive methods to Patient model

```python
class Patient(models.Model):
    # ... existing fields and new denormalized fields ...
    
    def update_current_record_number(self, record_number, user, reason="", effective_date=None):
        """Update patient's current record number and create history entry"""
        if effective_date is None:
            effective_date = timezone.now()
        
        # Get current record for history
        current_record = self.record_numbers.filter(is_current=True).first()
        previous_number = current_record.record_number if current_record else ""
        
        # Deactivate current record
        if current_record:
            current_record.is_current = False
            current_record.updated_by = user
            current_record.save()
        
        # Create new current record
        new_record = PatientRecordNumber.objects.create(
            patient=self,
            record_number=record_number,
            previous_record_number=previous_number,
            change_reason=reason,
            effective_date=effective_date,
            is_current=True,
            created_by=user,
            updated_by=user
        )
        
        # Update denormalized field
        self.current_record_number = record_number
        self.updated_by = user
        self.save(update_fields=['current_record_number', 'updated_by', 'updated_at'])
        
        return new_record
    
    def admit_patient(self, admission_datetime, admission_type, user, **kwargs):
        """Admit patient and create admission record"""
        # Check if patient is already admitted
        if self.is_currently_admitted():
            raise ValidationError("Paciente já está internado")
        
        # Create admission record
        admission = PatientAdmission.objects.create(
            patient=self,
            admission_datetime=admission_datetime,
            admission_type=admission_type,
            initial_bed=kwargs.get('initial_bed', ''),
            admission_diagnosis=kwargs.get('admission_diagnosis', ''),
            created_by=user,
            updated_by=user
        )
        
        # Update patient status and denormalized fields
        self.status = self.Status.INPATIENT
        self.current_admission_id = admission.id
        self.last_admission_date = admission_datetime.date() if isinstance(admission_datetime, timezone.datetime) else admission_datetime
        self.bed = admission.initial_bed
        self.total_admissions_count = self.admissions.count()
        self.updated_by = user
        self.save(update_fields=[
            'status', 'current_admission_id', 'last_admission_date', 
            'bed', 'total_admissions_count', 'updated_by', 'updated_at'
        ])
        
        return admission
    
    def discharge_patient(self, discharge_datetime, discharge_type, user, **kwargs):
        """Discharge patient and update admission record"""
        current_admission = self.get_current_admission()
        if not current_admission:
            raise ValidationError("Paciente não está internado")
        
        # Update admission record
        current_admission.discharge_datetime = discharge_datetime
        current_admission.discharge_type = discharge_type
        current_admission.final_bed = kwargs.get('final_bed', current_admission.initial_bed)
        current_admission.discharge_diagnosis = kwargs.get('discharge_diagnosis', '')
        current_admission.updated_by = user
        current_admission.save()  # This will trigger duration calculation and is_active=False
        
        # Update patient status and denormalized fields
        self.status = self.Status.DISCHARGED
        self.current_admission_id = None
        self.last_discharge_date = discharge_datetime.date() if isinstance(discharge_datetime, timezone.datetime) else discharge_datetime
        self.bed = ""
        
        # Recalculate total inpatient days
        self.total_inpatient_days = sum(
            admission.stay_duration_days or 0 
            for admission in self.admissions.filter(stay_duration_days__isnull=False)
        )
        
        self.updated_by = user
        self.save(update_fields=[
            'status', 'current_admission_id', 'last_discharge_date', 
            'bed', 'total_inpatient_days', 'updated_by', 'updated_at'
        ])
        
        return current_admission
    
    def get_admission_history(self):
        """Get ordered admission history"""
        return self.admissions.order_by('-admission_datetime')
    
    def get_record_number_history(self):
        """Get ordered record number history"""
        return self.record_numbers.order_by('-effective_date')
    
    def calculate_total_hospital_days(self):
        """Calculate total days spent in hospital across all admissions"""
        completed_admissions = self.admissions.filter(
            discharge_datetime__isnull=False,
            stay_duration_days__isnull=False
        )
        return sum(admission.stay_duration_days for admission in completed_admissions)
    
    def get_current_stay_duration(self):
        """Get current stay duration if patient is admitted"""
        current_admission = self.get_current_admission()
        return current_admission.calculate_current_duration() if current_admission else None
    
    def refresh_denormalized_fields(self):
        """Refresh all denormalized fields from source data"""
        # Update current record number
        current_record = self.record_numbers.filter(is_current=True).first()
        self.current_record_number = current_record.record_number if current_record else ""
        
        # Update admission statistics
        admissions = self.admissions.all()
        self.total_admissions_count = admissions.count()
        self.total_inpatient_days = self.calculate_total_hospital_days()
        
        # Update current admission
        current_admission = admissions.filter(is_active=True).first()
        self.current_admission_id = current_admission.id if current_admission else None
        
        # Update status based on current state
        if current_admission:
            self.status = self.Status.INPATIENT
            self.bed = current_admission.initial_bed or current_admission.final_bed
        elif self.status == self.Status.INPATIENT:
            # Patient was marked as inpatient but has no active admission
            self.status = self.Status.OUTPATIENT
            self.bed = ""
        
        self.save(update_fields=[
            'current_record_number', 'total_admissions_count', 'total_inpatient_days',
            'current_admission_id', 'status', 'bed', 'updated_at'
        ])
```

### Step 3.2: Enhanced PatientAdmission Model Methods

**File**: `apps/patients/models.py` - Add methods to PatientAdmission

```python
class PatientAdmission(models.Model):
    # ... existing fields ...
    
    def calculate_current_duration(self):
        """Calculate current stay duration for active admissions"""
        if self.is_active and self.admission_datetime:
            duration = timezone.now() - self.admission_datetime
            return {
                'total_seconds': int(duration.total_seconds()),
                'hours': int(duration.total_seconds() / 3600),
                'days': duration.days,
                'weeks': duration.days // 7
            }
        return None
    
    def can_discharge(self):
        """Check if admission can be discharged"""
        return self.is_active and not self.discharge_datetime
    
    def get_bed_changes(self):
        """Get history of bed changes during this admission"""
        # This could be extended to track bed changes via a separate model
        beds = []
        if self.initial_bed:
            beds.append(('admission', self.initial_bed, self.admission_datetime))
        if self.final_bed and self.final_bed != self.initial_bed and self.discharge_datetime:
            beds.append(('discharge', self.final_bed, self.discharge_datetime))
        return beds
    
    def update_discharge_info(self, discharge_datetime, discharge_type, user, **kwargs):
        """Update discharge information with validation"""
        if not self.is_active:
            raise ValidationError("Esta internação já foi finalizada")
        
        if discharge_datetime <= self.admission_datetime:
            raise ValidationError("Data de alta deve ser posterior à data de admissão")
        
        self.discharge_datetime = discharge_datetime
        self.discharge_type = discharge_type
        self.final_bed = kwargs.get('final_bed', self.initial_bed)
        self.discharge_diagnosis = kwargs.get('discharge_diagnosis', '')
        self.updated_by = user
        
        # save() will trigger duration calculation and status update
        self.save()
        
        # Update patient denormalized fields
        self.patient.refresh_denormalized_fields()
        
        return self
    
    def cancel_discharge(self, user):
        """Cancel discharge and reactivate admission"""
        if self.is_active:
            raise ValidationError("Internação já está ativa")
        
        self.discharge_datetime = None
        self.discharge_type = ""
        self.stay_duration_hours = None
        self.stay_duration_days = None
        self.is_active = True
        self.updated_by = user
        self.save()
        
        # Update patient status
        self.patient.status = self.patient.Status.INPATIENT
        self.patient.current_admission_id = self.id
        self.patient.bed = self.final_bed or self.initial_bed
        self.patient.updated_by = user
        self.patient.save(update_fields=['status', 'current_admission_id', 'bed', 'updated_by', 'updated_at'])
        
        return self
```

### Step 3.3: Data Consistency Signal Handlers

**File**: `apps/patients/signals.py` - Enhanced signal handlers

```python
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Patient, PatientRecordNumber, PatientAdmission
from apps.events.models import RecordNumberChangeEvent, AdmissionEvent, DischargeEvent


@receiver(pre_save, sender=PatientRecordNumber)
def validate_record_number_change(sender, instance, **kwargs):
    """Validate record number changes before saving"""
    if instance.is_current:
        # Ensure only one current record per patient
        existing_current = PatientRecordNumber.objects.filter(
            patient=instance.patient,
            is_current=True
        ).exclude(pk=instance.pk)
        
        if existing_current.exists():
            # Auto-deactivate existing current record
            existing_current.update(is_current=False)


@receiver(post_save, sender=PatientRecordNumber)
def update_patient_record_number(sender, instance, created, **kwargs):
    """Update patient's denormalized record number field"""
    if instance.is_current:
        # Update denormalized field
        Patient.objects.filter(pk=instance.patient.pk).update(
            current_record_number=instance.record_number
        )


@receiver(pre_save, sender=PatientAdmission)
def validate_admission_change(sender, instance, **kwargs):
    """Validate admission changes before saving"""
    if instance.is_active:
        # Ensure only one active admission per patient
        existing_active = PatientAdmission.objects.filter(
            patient=instance.patient,
            is_active=True
        ).exclude(pk=instance.pk)
        
        if existing_active.exists():
            raise ValidationError("Paciente já possui uma internação ativa")


@receiver(post_save, sender=PatientAdmission)
def update_patient_admission_status(sender, instance, created, **kwargs):
    """Update patient status and denormalized fields after admission changes"""
    # Update patient denormalized fields
    patient = instance.patient
    
    if instance.is_active:
        # Patient is being admitted
        updates = {
            'status': Patient.Status.INPATIENT,
            'current_admission_id': instance.id,
            'last_admission_date': instance.admission_datetime.date(),
            'bed': instance.initial_bed or instance.final_bed,
        }
    else:
        # Patient is being discharged
        updates = {
            'status': Patient.Status.DISCHARGED,
            'current_admission_id': None,
            'last_discharge_date': instance.discharge_datetime.date() if instance.discharge_datetime else None,
            'bed': "",
        }
    
    # Update admission count and total days
    updates.update({
        'total_admissions_count': patient.admissions.count(),
        'total_inpatient_days': patient.calculate_total_hospital_days(),
    })
    
    Patient.objects.filter(pk=patient.pk).update(**updates)


@receiver(post_delete, sender=PatientAdmission)
def cleanup_patient_after_admission_delete(sender, instance, **kwargs):
    """Clean up patient data after admission deletion"""
    patient = instance.patient
    
    # Check if this was the current admission
    if patient.current_admission_id == instance.id:
        # Find another active admission or clear current admission
        active_admission = patient.admissions.filter(is_active=True).first()
        if active_admission:
            patient.current_admission_id = active_admission.id
            patient.status = Patient.Status.INPATIENT
            patient.bed = active_admission.initial_bed or active_admission.final_bed
        else:
            patient.current_admission_id = None
            patient.status = Patient.Status.OUTPATIENT
            patient.bed = ""
        
        patient.save(update_fields=['current_admission_id', 'status', 'bed', 'updated_at'])
    
    # Refresh admission statistics
    patient.refresh_denormalized_fields()


@receiver(post_delete, sender=PatientRecordNumber)
def cleanup_patient_after_record_delete(sender, instance, **kwargs):
    """Clean up patient data after record number deletion"""
    if instance.is_current:
        patient = instance.patient
        # Find the most recent record number to make current
        latest_record = patient.record_numbers.order_by('-effective_date').first()
        if latest_record:
            latest_record.is_current = True
            latest_record.save()
            patient.current_record_number = latest_record.record_number
        else:
            patient.current_record_number = ""
        
        patient.save(update_fields=['current_record_number', 'updated_at'])
```

### Step 3.4: Management Commands for Data Consistency

Since this is a greenfield project, we can skip the complex data migration command and instead just add a simple data refresh utility for development:

**File**: `apps/patients/management/commands/refresh_patient_data.py`

```python
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.patients.models import Patient

class Command(BaseCommand):
    help = 'Refresh denormalized fields for all patients (development utility)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--patient-id',
            type=str,
            help='Refresh specific patient by UUID',
        )
    
    def handle(self, *args, **options):
        if options['patient_id']:
            try:
                patients = [Patient.objects.get(pk=options['patient_id'])]
            except Patient.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Patient {options["patient_id"]} not found')
                )
                return
        else:
            patients = Patient.objects.all()
        
        updated_count = 0
        
        for patient in patients:
            patient.refresh_denormalized_fields()
            updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Refreshed denormalized fields for {updated_count} patients')
        )
```

### Step 3.5: Validation and Business Rules

**File**: `apps/patients/validators.py` - Create validation utilities

```python
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
    
    if patient.status == Patient.Status.INPATIENT and not active_admissions.exists():
        raise ValidationError("Paciente marcado como internado mas sem internação ativa")
    
    if patient.status != Patient.Status.INPATIENT and active_admissions.exists():
        raise ValidationError("Paciente tem internação ativa mas status indica que não está internado")
```

### Step 3.6: Add Validation to Models

**File**: `apps/patients/models.py` - Update models with validation

```python
from .validators import (
    validate_record_number_format, 
    validate_admission_datetime, 
    validate_discharge_datetime
)

class PatientRecordNumber(models.Model):
    # ... existing fields ...
    
    def clean(self):
        """Enhanced validation"""
        super().clean()
        
        # Validate record number format
        validate_record_number_format(self.record_number)
        
        # Validate effective date
        if self.effective_date and self.effective_date > timezone.now():
            raise ValidationError({
                'effective_date': 'Data de vigência não pode ser no futuro'
            })
        
        # Validate current record uniqueness
        if self.is_current:
            existing_current = PatientRecordNumber.objects.filter(
                patient=self.patient,
                is_current=True
            ).exclude(pk=self.pk)
            
            if existing_current.exists():
                raise ValidationError({
                    'is_current': 'Já existe um número de prontuário atual para este paciente'
                })

class PatientAdmission(models.Model):
    # ... existing fields ...
    
    def clean(self):
        """Enhanced validation"""
        super().clean()
        
        # Validate admission datetime
        validate_admission_datetime(self.admission_datetime)
        
        # Validate discharge datetime
        if self.discharge_datetime:
            validate_discharge_datetime(self.discharge_datetime, self.admission_datetime)
        
        # Validate discharge type when discharged
        if self.discharge_datetime and not self.discharge_type:
            raise ValidationError({
                'discharge_type': 'Tipo de alta é obrigatório quando há data de alta'
            })
        
        # Validate active status consistency
        if self.discharge_datetime and self.is_active:
            raise ValidationError({
                'is_active': 'Internação não pode estar ativa se há data de alta'
            })
        
        # Validate bed information
        if not self.initial_bed and not self.final_bed:
            raise ValidationError("Pelo menos um leito (inicial ou final) deve ser informado")
```

## Testing

### Step 3.7: Comprehensive Business Logic Tests

**File**: `apps/patients/tests/test_business_logic.py`

```python
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from ..models import Patient, PatientRecordNumber, PatientAdmission

User = get_user_model()

class PatientBusinessLogicTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_update_record_number_creates_history(self):
        """Test that updating record number creates proper history"""
        # Set initial record number
        self.patient.update_current_record_number('REC001', self.user, 'Initial setup')
        
        # Update to new record number
        self.patient.update_current_record_number('REC002', self.user, 'Hospital transfer')
        
        # Check history
        records = self.patient.record_numbers.order_by('-effective_date')
        self.assertEqual(records.count(), 2)
        
        current_record = records.first()
        old_record = records.last()
        
        self.assertEqual(current_record.record_number, 'REC002')
        self.assertTrue(current_record.is_current)
        self.assertEqual(current_record.previous_record_number, 'REC001')
        
        self.assertEqual(old_record.record_number, 'REC001')
        self.assertFalse(old_record.is_current)
    
    def test_admit_discharge_cycle(self):
        """Test complete admission and discharge cycle"""
        admission_time = timezone.now() - timedelta(hours=48)
        discharge_time = timezone.now()
        
        # Admit patient
        admission = self.patient.admit_patient(
            admission_datetime=admission_time,
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user,
            initial_bed='A101',
            admission_diagnosis='Chest pain'
        )
        
        # Check patient status after admission
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.INPATIENT)
        self.assertEqual(self.patient.current_admission_id, admission.id)
        self.assertEqual(self.patient.bed, 'A101')
        self.assertTrue(self.patient.is_currently_admitted())
        
        # Discharge patient
        self.patient.discharge_patient(
            discharge_datetime=discharge_time,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            user=self.user,
            final_bed='A101',
            discharge_diagnosis='Stable, discharged home'
        )
        
        # Check patient status after discharge
        self.patient.refresh_from_db()
        admission.refresh_from_db()
        
        self.assertEqual(self.patient.status, Patient.Status.DISCHARGED)
        self.assertIsNone(self.patient.current_admission_id)
        self.assertEqual(self.patient.bed, "")
        self.assertFalse(self.patient.is_currently_admitted())
        
        # Check admission record
        self.assertFalse(admission.is_active)
        self.assertEqual(admission.stay_duration_days, 2)
        self.assertGreater(admission.stay_duration_hours, 47)
    
    def test_cannot_admit_already_admitted_patient(self):
        """Test that cannot admit patient who is already admitted"""
        # Admit patient
        self.patient.admit_patient(
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user
        )
        
        # Try to admit again
        with self.assertRaises(ValidationError):
            self.patient.admit_patient(
                admission_datetime=timezone.now(),
                admission_type=PatientAdmission.AdmissionType.SCHEDULED,
                user=self.user
            )
    
    def test_denormalized_field_consistency(self):
        """Test that denormalized fields stay consistent"""
        # Create multiple admissions and record changes
        self.patient.update_current_record_number('REC001', self.user)
        
        # First admission
        admission1 = self.patient.admit_patient(
            admission_datetime=timezone.now() - timedelta(days=10),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user
        )
        self.patient.discharge_patient(
            discharge_datetime=timezone.now() - timedelta(days=5),
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            user=self.user
        )
        
        # Second admission
        admission2 = self.patient.admit_patient(
            admission_datetime=timezone.now() - timedelta(days=3),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            user=self.user
        )
        
        # Check denormalized fields
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.total_admissions_count, 2)
        self.assertEqual(self.patient.total_inpatient_days, 5)  # First admission was 5 days
        self.assertEqual(self.patient.current_admission_id, admission2.id)
        self.assertEqual(self.patient.current_record_number, 'REC001')
```

## Success Criteria

- ✅ Enhanced Patient model methods for record and admission management
- ✅ PatientAdmission model methods for discharge management and duration calculation
- ✅ Signal handlers for automatic denormalization and data consistency
- ✅ Management command for refreshing denormalized data
- ✅ Comprehensive validation rules and business logic
- ✅ Models properly validate data before saving
- ✅ Automatic status updates when admissions/discharges occur
- ✅ Data consistency maintained between normalized and denormalized fields
- ✅ Business logic tests covering all scenarios
- ✅ Proper error handling and user feedback

## Next Phase

Continue to **Phase 4: User Interface and Forms** to create the user-facing forms and templates for managing record numbers and admissions/discharges.
