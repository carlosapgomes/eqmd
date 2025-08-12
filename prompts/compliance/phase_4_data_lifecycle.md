# Phase 4: Data Lifecycle Management Implementation

**Timeline**: Week 7-8  
**Priority**: MEDIUM  
**Dependencies**: Phases 1-2 completed  

## Objective

Implement comprehensive data lifecycle management including retention policies, automated deletion procedures, data anonymization, and cleanup systems as required by LGPD Articles 15-16 (data minimization and purpose limitation).

## Legal Requirements Addressed

- **LGPD Article 15**: Data retention duration
- **LGPD Article 16**: Data deletion when purpose is fulfilled
- **LGPD Article 6, III**: Principle of necessity (data minimization)
- **LGPD Article 6, IV**: Principle of adequacy
- **LGPD Article 37**: Record keeping for processing activities

## Deliverables

1. **Data Retention Policy System**
2. **Automated Deletion Procedures**  
3. **Data Anonymization Framework**
4. **Retention Monitoring Dashboard**
5. **Cleanup Audit System**

---

## Implementation Steps

### Step 1: Data Retention Management Models

#### 1.1 Retention Policy Models

**File**: `apps/core/models.py` (additions)

```python
from django.db import models
from django.utils import timezone
from datetime import timedelta, date
import uuid

class DataRetentionPolicy(models.Model):
    """Defines retention policies for different data categories - LGPD Article 15"""
    
    DATA_CATEGORIES = [
        ('patient_identification', 'Identificação do Paciente'),
        ('patient_medical_records', 'Registros Médicos'),
        ('patient_contact_info', 'Informações de Contato'),
        ('staff_professional_data', 'Dados Profissionais da Equipe'),
        ('audit_logs', 'Logs de Auditoria'),
        ('consent_records', 'Registros de Consentimento'),
        ('media_files', 'Arquivos de Mídia'),
        ('communication_logs', 'Logs de Comunicação'),
        ('emergency_contacts', 'Contatos de Emergência'),
    ]
    
    RETENTION_BASIS = [
        ('legal_obligation', 'Obrigação Legal'),
        ('medical_requirement', 'Exigência Médica'),
        ('consent_duration', 'Duração do Consentimento'),
        ('business_necessity', 'Necessidade Operacional'),
        ('statute_limitation', 'Prazo Prescricional'),
    ]
    
    # Policy identification
    policy_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    data_category = models.CharField(max_length=50, choices=DATA_CATEGORIES)
    
    # Retention rules
    retention_period_days = models.IntegerField(help_text="Período de retenção em dias")
    retention_basis = models.CharField(max_length=30, choices=RETENTION_BASIS)
    legal_reference = models.CharField(max_length=200, help_text="Referência legal (ex: CFM 1.821/2007)")
    
    # Grace periods and warnings
    warning_period_days = models.IntegerField(
        default=180,
        help_text="Dias antes da exclusão para enviar aviso"
    )
    grace_period_days = models.IntegerField(
        default=30,
        help_text="Período de graça após vencimento"
    )
    
    # Deletion behavior
    auto_delete_enabled = models.BooleanField(default=False)
    anonymize_instead_delete = models.BooleanField(default=False)
    require_manual_approval = models.BooleanField(default=True)
    
    # Exceptions and holds
    legal_hold_exempt = models.BooleanField(default=False)
    emergency_access_required = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.EqmdCustomUser', on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Política de Retenção"
        verbose_name_plural = "Políticas de Retenção"
        ordering = ['data_category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.retention_period_days} dias)"

class DataRetentionSchedule(models.Model):
    """Tracks retention schedules for specific data records"""
    
    # Record identification
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.UUIDField()  # UUID of the data record
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Retention details
    retention_policy = models.ForeignKey(DataRetentionPolicy, on_delete=models.CASCADE)
    data_creation_date = models.DateTimeField()
    last_activity_date = models.DateTimeField(auto_now=True)
    
    # Calculated dates
    retention_end_date = models.DateField()
    warning_date = models.DateField()
    deletion_date = models.DateField()
    
    # Status tracking
    STATUS_CHOICES = [
        ('active', 'Ativo'),
        ('warning_sent', 'Aviso Enviado'),
        ('grace_period', 'Período de Graça'),
        ('scheduled_deletion', 'Agendado para Exclusão'),
        ('legal_hold', 'Retenção Legal'),
        ('deleted', 'Excluído'),
        ('anonymized', 'Anonimizado'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Warning and deletion tracking
    warning_sent_at = models.DateTimeField(null=True, blank=True)
    deletion_approved_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_deletions'
    )
    deletion_approved_at = models.DateTimeField(null=True, blank=True)
    
    # Legal holds
    legal_hold_reason = models.TextField(blank=True)
    legal_hold_applied_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applied_legal_holds'
    )
    legal_hold_applied_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Cronograma de Retenção"
        verbose_name_plural = "Cronogramas de Retenção"
        ordering = ['retention_end_date']
        indexes = [
            models.Index(fields=['retention_end_date', 'status']),
            models.Index(fields=['warning_date', 'status']),
            models.Index(fields=['content_type', 'object_id']),
        ]
        unique_together = ['content_type', 'object_id']
    
    def save(self, *args, **kwargs):
        if not self.retention_end_date:
            self.calculate_dates()
        super().save(*args, **kwargs)
    
    def calculate_dates(self):
        """Calculate retention and deletion dates"""
        base_date = self.last_activity_date.date() if self.last_activity_date else self.data_creation_date.date()
        
        self.retention_end_date = base_date + timedelta(days=self.retention_policy.retention_period_days)
        self.warning_date = self.retention_end_date - timedelta(days=self.retention_policy.warning_period_days)
        self.deletion_date = self.retention_end_date + timedelta(days=self.retention_policy.grace_period_days)
    
    def is_eligible_for_warning(self):
        """Check if warning should be sent"""
        return (
            date.today() >= self.warning_date and 
            self.status == 'active' and 
            not self.warning_sent_at
        )
    
    def is_eligible_for_deletion(self):
        """Check if data is eligible for deletion"""
        return (
            date.today() >= self.deletion_date and 
            self.status in ['warning_sent', 'grace_period'] and
            not self.legal_hold_applied_at
        )
    
    def apply_legal_hold(self, user, reason):
        """Apply legal hold to prevent deletion"""
        self.status = 'legal_hold'
        self.legal_hold_reason = reason
        self.legal_hold_applied_by = user
        self.legal_hold_applied_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.content_object} - {self.retention_policy.name}"

class DataDeletionLog(models.Model):
    """Audit log for data deletions - compliance evidence"""
    
    # Deletion identification
    deletion_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Original record information
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    original_object_id = models.UUIDField()
    original_object_representation = models.TextField()  # String representation before deletion
    
    # Deletion details
    deletion_type = models.CharField(
        max_length=20,
        choices=[
            ('automatic', 'Automática'),
            ('manual', 'Manual'),
            ('patient_request', 'Solicitação do Paciente'),
            ('legal_requirement', 'Exigência Legal'),
            ('anonymization', 'Anonimização'),
        ]
    )
    
    deletion_reason = models.TextField()
    retention_policy_applied = models.CharField(max_length=200)
    
    # Authorization
    authorized_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='authorized_deletions'
    )
    authorization_date = models.DateTimeField()
    
    # Execution
    executed_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executed_deletions'
    )
    executed_at = models.DateTimeField()
    
    # Technical details
    deletion_method = models.CharField(
        max_length=30,
        choices=[
            ('soft_delete', 'Exclusão Suave'),
            ('hard_delete', 'Exclusão Completa'),
            ('anonymization', 'Anonimização'),
            ('archival', 'Arquivamento'),
        ]
    )
    
    # Verification
    verification_hash = models.CharField(max_length=64, blank=True)  # SHA-256 of deleted data
    deletion_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    
    # Related data impact
    related_records_affected = models.IntegerField(default=0)
    cascading_deletions = models.TextField(blank=True)  # JSON list of related deletions
    
    # Legal compliance
    legal_basis_for_deletion = models.CharField(max_length=200)
    compliance_notes = models.TextField(blank=True)
    
    # Recovery information (for soft deletes)
    recovery_possible = models.BooleanField(default=False)
    recovery_deadline = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Log de Exclusão de Dados"
        verbose_name_plural = "Logs de Exclusão de Dados"
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['executed_at', 'deletion_type']),
            models.Index(fields=['content_type', 'deletion_type']),
        ]
    
    def __str__(self):
        return f"{self.deletion_id} - {self.original_object_representation[:50]}"

class DataAnonymizationLog(models.Model):
    """Log for data anonymization processes"""
    
    anonymization_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Source data
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    original_object_id = models.UUIDField()
    anonymized_object_id = models.UUIDField(null=True, blank=True)  # If creating new anonymized record
    
    # Anonymization details
    anonymization_method = models.CharField(
        max_length=30,
        choices=[
            ('field_removal', 'Remoção de Campos'),
            ('field_masking', 'Mascaramento'),
            ('data_generalization', 'Generalização'),
            ('pseudonymization', 'Pseudonimização'),
            ('statistical_disclosure', 'Controle Estatístico'),
        ]
    )
    
    fields_anonymized = models.TextField()  # JSON list of fields
    anonymization_rules = models.TextField()  # JSON with anonymization rules
    
    # Quality control
    anonymization_quality_score = models.FloatField(null=True, blank=True)  # 0-1 score
    re_identification_risk = models.CharField(
        max_length=10,
        choices=[('low', 'Baixo'), ('medium', 'Médio'), ('high', 'Alto')],
        default='low'
    )
    
    # Execution details
    executed_by = models.ForeignKey('accounts.EqmdCustomUser', on_delete=models.SET_NULL, null=True)
    executed_at = models.DateTimeField(auto_now_add=True)
    
    # Purpose and retention
    anonymization_purpose = models.CharField(
        max_length=30,
        choices=[
            ('research', 'Pesquisa'),
            ('statistics', 'Estatísticas'),
            ('quality_improvement', 'Melhoria da Qualidade'),
            ('retention_compliance', 'Conformidade de Retenção'),
        ]
    )
    
    anonymized_data_retention = models.IntegerField(help_text="Dias para manter dados anonimizados")
    
    class Meta:
        verbose_name = "Log de Anonimização"
        verbose_name_plural = "Logs de Anonimização"
        ordering = ['-executed_at']
```

#### 1.2 Extend Existing Models for Retention Tracking

**File**: `apps/patients/models.py` (additions to existing Patient model)

```python
# Add to existing Patient model
class Patient(models.Model):
    # ... existing fields ...
    
    # Retention tracking fields
    last_interaction_date = models.DateTimeField(auto_now=True)
    retention_category = models.CharField(
        max_length=30,
        choices=[
            ('active_treatment', 'Tratamento Ativo'),
            ('follow_up', 'Acompanhamento'),
            ('discharged', 'Alta Médica'),
            ('transferred', 'Transferido'),
            ('deceased', 'Óbito'),
        ],
        default='active_treatment'
    )
    
    # Deletion protection
    deletion_protected = models.BooleanField(default=False)
    protection_reason = models.CharField(max_length=200, blank=True)
    protection_applied_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='protected_patients'
    )
    protection_applied_at = models.DateTimeField(null=True, blank=True)
    
    # Data quality flags
    data_completeness_score = models.FloatField(default=1.0)  # 0-1 score
    last_data_audit = models.DateTimeField(null=True, blank=True)
    
    def update_last_interaction(self):
        """Update last interaction timestamp"""
        self.last_interaction_date = timezone.now()
        self.save(update_fields=['last_interaction_date'])
    
    def calculate_retention_end_date(self):
        """Calculate when patient data should be deleted"""
        from apps.core.models import DataRetentionPolicy
        
        try:
            policy = DataRetentionPolicy.objects.get(
                data_category='patient_medical_records',
                is_active=True
            )
            return self.last_interaction_date.date() + timedelta(days=policy.retention_period_days)
        except DataRetentionPolicy.DoesNotExist:
            # Default to 20 years if no policy
            return self.last_interaction_date.date() + timedelta(days=7300)
    
    def is_eligible_for_deletion(self):
        """Check if patient is eligible for deletion"""
        if self.deletion_protected:
            return False
        
        retention_end = self.calculate_retention_end_date()
        return date.today() >= retention_end
    
    def apply_deletion_protection(self, user, reason):
        """Apply deletion protection"""
        self.deletion_protected = True
        self.protection_reason = reason
        self.protection_applied_by = user
        self.protection_applied_at = timezone.now()
        self.save()
```

### Step 2: Retention Management Services

#### 2.1 Data Retention Service

**File**: `apps/core/services/retention_management.py`

```python
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from datetime import date, timedelta
from typing import List, Dict, Any
import logging
import hashlib
import json

from ..models import (
    DataRetentionPolicy, DataRetentionSchedule, DataDeletionLog, 
    DataAnonymizationLog
)
from apps.patients.models import Patient

logger = logging.getLogger(__name__)

class DataRetentionService:
    """Service for managing data retention and deletion"""
    
    def __init__(self):
        self.deletion_stats = {
            'candidates_found': 0,
            'warnings_sent': 0,
            'deletions_executed': 0,
            'errors': 0
        }
    
    def process_retention_schedules(self, dry_run=False):
        """Main method to process all retention schedules"""
        logger.info(f"Starting retention processing (dry_run={dry_run})")
        
        # Step 1: Create/update retention schedules
        self.update_retention_schedules()
        
        # Step 2: Send warnings for approaching deletions
        self.send_deletion_warnings(dry_run=dry_run)
        
        # Step 3: Process eligible deletions
        self.process_deletions(dry_run=dry_run)
        
        # Step 4: Anonymize data where appropriate
        self.process_anonymizations(dry_run=dry_run)
        
        return self.deletion_stats
    
    def update_retention_schedules(self):
        """Create/update retention schedules for all data"""
        
        # Process patients
        patients = Patient.objects.filter(
            dataretentionschedule__isnull=True
        )
        
        patient_policy = DataRetentionPolicy.objects.filter(
            data_category='patient_medical_records',
            is_active=True
        ).first()
        
        if patient_policy:
            for patient in patients:
                self.create_retention_schedule(patient, patient_policy)
        
        # Process other data types as needed
        # TODO: Add retention schedules for events, media files, etc.
        
    def create_retention_schedule(self, obj, policy: DataRetentionPolicy):
        """Create retention schedule for a data object"""
        
        content_type = ContentType.objects.get_for_model(obj)
        
        # Determine data creation date
        creation_date = getattr(obj, 'created_at', None) or timezone.now()
        last_activity = getattr(obj, 'last_interaction_date', None) or creation_date
        
        schedule, created = DataRetentionSchedule.objects.get_or_create(
            content_type=content_type,
            object_id=obj.id,
            defaults={
                'retention_policy': policy,
                'data_creation_date': creation_date,
                'last_activity_date': last_activity,
            }
        )
        
        if created:
            logger.info(f"Created retention schedule for {obj}")
        
        return schedule
    
    def send_deletion_warnings(self, dry_run=False):
        """Send warnings for upcoming deletions"""
        
        warning_schedules = DataRetentionSchedule.objects.filter(
            warning_date__lte=date.today(),
            status='active'
        )
        
        for schedule in warning_schedules:
            try:
                if self.send_deletion_warning(schedule, dry_run=dry_run):
                    self.deletion_stats['warnings_sent'] += 1
            except Exception as e:
                logger.error(f"Error sending warning for {schedule}: {e}")
                self.deletion_stats['errors'] += 1
    
    def send_deletion_warning(self, schedule: DataRetentionSchedule, dry_run=False):
        """Send deletion warning for specific schedule"""
        
        obj = schedule.content_object
        if not obj:
            logger.warning(f"Object not found for schedule {schedule.id}")
            return False
        
        # For patients, try to get contact email
        if isinstance(obj, Patient):
            if hasattr(obj, 'email') and obj.email:
                if not dry_run:
                    self.send_patient_deletion_warning_email(obj, schedule)
                    schedule.status = 'warning_sent'
                    schedule.warning_sent_at = timezone.now()
                    schedule.save()
                
                logger.info(f"{'[DRY RUN] ' if dry_run else ''}Sent deletion warning to {obj}")
                return True
        
        # For other objects, log the warning
        if not dry_run:
            schedule.status = 'warning_sent'
            schedule.warning_sent_at = timezone.now()
            schedule.save()
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Logged deletion warning for {obj}")
        return True
    
    def send_patient_deletion_warning_email(self, patient: Patient, schedule: DataRetentionSchedule):
        """Send email warning to patient about upcoming deletion"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f"Aviso de Retenção de Dados - {patient.name}"
        message = f"""
        Prezado(a) {patient.name},
        
        Conforme nossa Política de Retenção de Dados e a LGPD, informamos que seus dados
        médicos estão programados para exclusão em {schedule.deletion_date.strftime('%d/%m/%Y')}.
        
        Detalhes:
        - Último atendimento: {schedule.last_activity_date.strftime('%d/%m/%Y')}
        - Política aplicada: {schedule.retention_policy.name}
        - Período de retenção: {schedule.retention_policy.retention_period_days} dias
        
        Se você deseja manter seus dados por mais tempo ou tem alguma necessidade médica
        específica, entre em contato conosco através dos canais:
        
        - Email: [EMAIL_HOSPITAL]
        - Telefone: [TELEFONE_HOSPITAL]
        
        Seus direitos conforme LGPD:
        - Pode solicitar cópia dos seus dados antes da exclusão
        - Pode solicitar transferência para outro prestador
        - Pode questionar a necessidade da exclusão
        
        Atenciosamente,
        Equipe de Proteção de Dados
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [patient.email] if hasattr(patient, 'email') and patient.email else [],
                fail_silently=False
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send deletion warning email to {patient}: {e}")
            return False
    
    def process_deletions(self, dry_run=False):
        """Process eligible deletions"""
        
        deletion_schedules = DataRetentionSchedule.objects.filter(
            deletion_date__lte=date.today(),
            status__in=['warning_sent', 'grace_period']
        ).exclude(
            legal_hold_applied_at__isnull=False
        )
        
        for schedule in deletion_schedules:
            try:
                if self.execute_deletion(schedule, dry_run=dry_run):
                    self.deletion_stats['deletions_executed'] += 1
            except Exception as e:
                logger.error(f"Error deleting {schedule}: {e}")
                self.deletion_stats['errors'] += 1
    
    def execute_deletion(self, schedule: DataRetentionSchedule, dry_run=False):
        """Execute deletion for specific schedule"""
        
        obj = schedule.content_object
        if not obj:
            logger.warning(f"Object not found for schedule {schedule.id}")
            return False
        
        # Check if manual approval is required
        if schedule.retention_policy.require_manual_approval and not schedule.deletion_approved_by:
            logger.info(f"Deletion requires manual approval for {obj}")
            return False
        
        # Create deletion log before deleting
        deletion_log = self.create_deletion_log(
            obj, 
            schedule,
            deletion_type='automatic',
            deletion_reason=f'Fim do período de retenção: {schedule.retention_policy.name}'
        )
        
        if not dry_run:
            # Execute the deletion
            if schedule.retention_policy.anonymize_instead_delete:
                success = self.anonymize_object(obj, schedule)
                deletion_log.deletion_method = 'anonymization'
            else:
                success = self.delete_object(obj, schedule)
                deletion_log.deletion_method = 'soft_delete'
            
            if success:
                deletion_log.deletion_verified = True
                deletion_log.verification_date = timezone.now()
                deletion_log.save()
                
                schedule.status = 'deleted' if not schedule.retention_policy.anonymize_instead_delete else 'anonymized'
                schedule.save()
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Deleted {obj}")
        return True
    
    def delete_object(self, obj, schedule: DataRetentionSchedule):
        """Perform actual deletion of object"""
        
        # For patients, use soft delete to preserve audit trail
        if isinstance(obj, Patient):
            # Mark as deleted but don't actually delete
            obj.status = 'deleted'
            obj.save()
            
            # Delete related sensitive data
            if hasattr(obj, 'events'):
                obj.events.all().delete()
            if hasattr(obj, 'dailynotes'):
                obj.dailynotes.all().delete()
            if hasattr(obj, 'mediafiles'):
                obj.mediafiles.all().delete()
            
            return True
        
        # For other objects, perform hard delete
        try:
            obj.delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting {obj}: {e}")
            return False
    
    def anonymize_object(self, obj, schedule: DataRetentionSchedule):
        """Anonymize object instead of deleting"""
        
        if isinstance(obj, Patient):
            return self.anonymize_patient(obj, schedule)
        
        # Add anonymization for other object types as needed
        return False
    
    def anonymize_patient(self, patient: Patient, schedule: DataRetentionSchedule):
        """Anonymize patient data"""
        
        # Create anonymization log
        anonymization_log = DataAnonymizationLog.objects.create(
            content_type=ContentType.objects.get_for_model(patient),
            original_object_id=patient.id,
            anonymization_method='field_masking',
            fields_anonymized=json.dumps([
                'name', 'id_number', 'phone', 'email', 'address'
            ]),
            anonymization_rules=json.dumps({
                'name': 'PACIENTE_ANONIMO',
                'id_number': 'XXXXX',
                'phone': 'XXXXX',
                'email': None,
                'address': 'ENDERECO_ANONIMO'
            }),
            executed_by=None,  # System execution
            anonymization_purpose='retention_compliance',
            anonymized_data_retention=1095  # 3 years for anonymized data
        )
        
        # Perform anonymization
        original_name = patient.name
        patient.name = f"PACIENTE_ANONIMO_{patient.id.hex[:8]}"
        
        if hasattr(patient, 'id_number'):
            patient.id_number = "XXXXXXXXXXX"
        if hasattr(patient, 'phone'):
            patient.phone = "XXXXX-XXXX"
        if hasattr(patient, 'email'):
            patient.email = None
        if hasattr(patient, 'address'):
            patient.address = "ENDERECO_ANONIMIZADO"
        
        patient.save()
        
        # Anonymize related medical data while preserving medical value
        self.anonymize_patient_medical_data(patient)
        
        logger.info(f"Anonymized patient: {original_name} -> {patient.name}")
        return True
    
    def anonymize_patient_medical_data(self, patient: Patient):
        """Anonymize patient's medical data while preserving medical insights"""
        
        # Keep medical data but remove personal identifiers
        if hasattr(patient, 'events'):
            for event in patient.events.all():
                if hasattr(event, 'content'):
                    # Simple anonymization - replace names with generic terms
                    content = event.content
                    content = content.replace(patient.name, 'PACIENTE')
                    event.content = content
                    event.save()
        
        # Similar anonymization for daily notes, keeping medical value
        if hasattr(patient, 'dailynotes'):
            for note in patient.dailynotes.all():
                if hasattr(note, 'content'):
                    content = note.content
                    content = content.replace(patient.name, 'PACIENTE')
                    note.content = content
                    note.save()
    
    def create_deletion_log(self, obj, schedule: DataRetentionSchedule, deletion_type: str, deletion_reason: str):
        """Create deletion audit log"""
        
        # Create hash of object data for verification
        obj_data = str(obj.__dict__)
        verification_hash = hashlib.sha256(obj_data.encode()).hexdigest()
        
        return DataDeletionLog.objects.create(
            content_type=ContentType.objects.get_for_model(obj),
            original_object_id=obj.id,
            original_object_representation=str(obj),
            deletion_type=deletion_type,
            deletion_reason=deletion_reason,
            retention_policy_applied=schedule.retention_policy.name,
            authorized_by=schedule.deletion_approved_by,
            authorization_date=schedule.deletion_approved_at or timezone.now(),
            executed_at=timezone.now(),
            verification_hash=verification_hash,
            legal_basis_for_deletion=f"LGPD Art. 15 - {schedule.retention_policy.legal_reference}",
            recovery_possible=True,
            recovery_deadline=timezone.now() + timedelta(days=30)
        )
    
    def process_anonymizations(self, dry_run=False):
        """Process scheduled anonymizations"""
        
        # Find data that should be anonymized instead of deleted
        anonymization_schedules = DataRetentionSchedule.objects.filter(
            deletion_date__lte=date.today(),
            status='warning_sent',
            retention_policy__anonymize_instead_delete=True
        )
        
        for schedule in anonymization_schedules:
            try:
                if self.execute_anonymization(schedule, dry_run=dry_run):
                    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Anonymized {schedule.content_object}")
            except Exception as e:
                logger.error(f"Error anonymizing {schedule}: {e}")
    
    def execute_anonymization(self, schedule: DataRetentionSchedule, dry_run=False):
        """Execute anonymization for specific schedule"""
        
        obj = schedule.content_object
        if not obj:
            return False
        
        if not dry_run:
            success = self.anonymize_object(obj, schedule)
            if success:
                schedule.status = 'anonymized'
                schedule.save()
            return success
        
        return True
    
    def get_retention_statistics(self):
        """Get retention management statistics"""
        
        today = date.today()
        
        stats = {
            'total_schedules': DataRetentionSchedule.objects.count(),
            'active_schedules': DataRetentionSchedule.objects.filter(status='active').count(),
            'warning_pending': DataRetentionSchedule.objects.filter(
                warning_date__lte=today,
                status='active'
            ).count(),
            'deletion_pending': DataRetentionSchedule.objects.filter(
                deletion_date__lte=today,
                status='warning_sent'
            ).count(),
            'legal_holds': DataRetentionSchedule.objects.filter(status='legal_hold').count(),
            'total_deletions': DataDeletionLog.objects.count(),
            'deletions_last_30_days': DataDeletionLog.objects.filter(
                executed_at__gte=timezone.now() - timedelta(days=30)
            ).count(),
        }
        
        return stats
```

### Step 3: Management Commands for Retention

#### 3.1 Retention Processing Command

**File**: `apps/core/management/commands/process_data_retention.py`

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.services.retention_management import DataRetentionService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process data retention schedules and deletions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without executing'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force execution without confirmation'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Process only specific data category'
        )
        parser.add_argument(
            '--warning-only',
            action='store_true',
            help='Only send warnings, do not delete'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Data Retention Processing - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"Mode: {'DRY RUN' if dry_run else 'EXECUTION'}")
        self.stdout.write(f"{'='*60}")
        
        if not dry_run and not force:
            confirm = input("\nThis will process deletions. Continue? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write("Operation cancelled.")
                return
        
        # Initialize retention service
        retention_service = DataRetentionService()
        
        # Get initial statistics
        initial_stats = retention_service.get_retention_statistics()
        self.stdout.write(f"\nInitial Statistics:")
        for key, value in initial_stats.items():
            self.stdout.write(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Process retention
        try:
            if options['warning_only']:
                retention_service.send_deletion_warnings(dry_run=dry_run)
                stats = {'warnings_sent': retention_service.deletion_stats['warnings_sent']}
            else:
                stats = retention_service.process_retention_schedules(dry_run=dry_run)
            
            # Display results
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write("Processing Results:")
            self.stdout.write(f"{'='*60}")
            
            for key, value in stats.items():
                self.stdout.write(f"  {key.replace('_', ' ').title()}: {value}")
            
            if stats['errors'] > 0:
                self.stdout.write(
                    self.style.WARNING(f"\n⚠️  {stats['errors']} errors occurred. Check logs for details.")
                )
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS("\n✓ Dry run completed. No changes were made.")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"\n✓ Processing completed successfully.")
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n❌ Error during processing: {e}")
            )
            logger.error(f"Retention processing error: {e}", exc_info=True)
```

#### 3.2 Setup Retention Policies Command

**File**: `apps/core/management/commands/setup_retention_policies.py`

```python
from django.core.management.base import BaseCommand
from apps.core.models import DataRetentionPolicy

class Command(BaseCommand):
    help = 'Sets up default data retention policies'
    
    def handle(self, *args, **options):
        self.stdout.write("Setting up default retention policies...")
        
        policies = [
            {
                'policy_id': 'PATIENT_MEDICAL_RECORDS',
                'name': 'Registros Médicos de Pacientes',
                'data_category': 'patient_medical_records',
                'retention_period_days': 7300,  # 20 years
                'retention_basis': 'legal_obligation',
                'legal_reference': 'Resolução CFM 1.821/2007',
                'warning_period_days': 180,
                'grace_period_days': 90,
                'auto_delete_enabled': False,
                'anonymize_instead_delete': True,
                'require_manual_approval': True,
                'legal_hold_exempt': False,
                'emergency_access_required': True,
            },
            {
                'policy_id': 'PATIENT_IDENTIFICATION',
                'name': 'Dados de Identificação de Pacientes',
                'data_category': 'patient_identification',
                'retention_period_days': 7300,  # 20 years
                'retention_basis': 'legal_obligation',
                'legal_reference': 'Resolução CFM 1.821/2007',
                'warning_period_days': 180,
                'grace_period_days': 90,
                'auto_delete_enabled': False,
                'anonymize_instead_delete': True,
                'require_manual_approval': True,
                'legal_hold_exempt': False,
                'emergency_access_required': True,
            },
            {
                'policy_id': 'STAFF_PROFESSIONAL_DATA',
                'name': 'Dados Profissionais da Equipe',
                'data_category': 'staff_professional_data',
                'retention_period_days': 1825,  # 5 years
                'retention_basis': 'legal_obligation',
                'legal_reference': 'Legislação Trabalhista',
                'warning_period_days': 90,
                'grace_period_days': 30,
                'auto_delete_enabled': False,
                'anonymize_instead_delete': False,
                'require_manual_approval': True,
                'legal_hold_exempt': False,
                'emergency_access_required': False,
            },
            {
                'policy_id': 'AUDIT_LOGS',
                'name': 'Logs de Auditoria',
                'data_category': 'audit_logs',
                'retention_period_days': 1095,  # 3 years
                'retention_basis': 'business_necessity',
                'legal_reference': 'LGPD Art. 37 - Registro de Operações',
                'warning_period_days': 30,
                'grace_period_days': 7,
                'auto_delete_enabled': True,
                'anonymize_instead_delete': False,
                'require_manual_approval': False,
                'legal_hold_exempt': True,
                'emergency_access_required': False,
            },
            {
                'policy_id': 'CONSENT_RECORDS',
                'name': 'Registros de Consentimento',
                'data_category': 'consent_records',
                'retention_period_days': 7665,  # 21 years (1 year beyond medical records)
                'retention_basis': 'legal_obligation',
                'legal_reference': 'LGPD Art. 8 - Comprovação de Consentimento',
                'warning_period_days': 365,
                'grace_period_days': 180,
                'auto_delete_enabled': False,
                'anonymize_instead_delete': False,
                'require_manual_approval': True,
                'legal_hold_exempt': False,
                'emergency_access_required': True,
            },
            {
                'policy_id': 'MEDIA_FILES',
                'name': 'Arquivos de Mídia Médica',
                'data_category': 'media_files',
                'retention_period_days': 7300,  # 20 years
                'retention_basis': 'medical_requirement',
                'legal_reference': 'Resolução CFM 1.821/2007',
                'warning_period_days': 180,
                'grace_period_days': 90,
                'auto_delete_enabled': False,
                'anonymize_instead_delete': True,
                'require_manual_approval': True,
                'legal_hold_exempt': False,
                'emergency_access_required': True,
            }
        ]
        
        created_count = 0
        for policy_data in policies:
            policy, created = DataRetentionPolicy.objects.get_or_create(
                policy_id=policy_data['policy_id'],
                defaults=policy_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"✓ Created: {policy}")
            else:
                self.stdout.write(f"- Exists: {policy}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} retention policies')
        )
        
        # Show summary
        total_policies = DataRetentionPolicy.objects.filter(is_active=True).count()
        self.stdout.write(f"\nActive retention policies: {total_policies}")
        
        # Show policy overview
        self.stdout.write(f"\nPolicy Overview:")
        for policy in DataRetentionPolicy.objects.filter(is_active=True).order_by('data_category'):
            years = policy.retention_period_days / 365.25
            self.stdout.write(f"  {policy.data_category}: {years:.1f} years")
```

### Step 4: Admin Interface

#### 4.1 Retention Admin

**File**: `apps/core/admin.py` (additions)

```python
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    DataRetentionPolicy, DataRetentionSchedule, DataDeletionLog, 
    DataAnonymizationLog
)

@admin.register(DataRetentionPolicy)
class DataRetentionPolicyAdmin(admin.ModelAdmin):
    list_display = [
        'policy_id', 'name', 'data_category', 'retention_period_days', 
        'retention_years', 'auto_delete_enabled', 'is_active'
    ]
    list_filter = [
        'data_category', 'retention_basis', 'auto_delete_enabled', 
        'anonymize_instead_delete', 'is_active'
    ]
    search_fields = ['policy_id', 'name', 'legal_reference']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Identificação', {
            'fields': ['policy_id', 'name', 'data_category', 'is_active']
        }),
        ('Período de Retenção', {
            'fields': ['retention_period_days', 'retention_basis', 'legal_reference']
        }),
        ('Avisos e Prazos', {
            'fields': ['warning_period_days', 'grace_period_days']
        }),
        ('Comportamento de Exclusão', {
            'fields': [
                'auto_delete_enabled', 'anonymize_instead_delete', 
                'require_manual_approval'
            ]
        }),
        ('Proteções', {
            'fields': ['legal_hold_exempt', 'emergency_access_required']
        }),
        ('Metadados', {
            'fields': ['created_at', 'updated_at', 'created_by'],
            'classes': ['collapse']
        })
    ]
    
    def retention_years(self, obj):
        return f"{obj.retention_period_days / 365.25:.1f} anos"
    retention_years.short_description = 'Anos de Retenção'
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(DataRetentionSchedule)
class DataRetentionScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'content_object_link', 'retention_policy', 'status', 
        'retention_end_date', 'days_remaining', 'warning_sent'
    ]
    list_filter = [
        'status', 'retention_policy__data_category', 'content_type',
        'retention_end_date', 'warning_sent_at'
    ]
    search_fields = ['object_id']
    readonly_fields = [
        'content_type', 'object_id', 'data_creation_date', 
        'retention_end_date', 'warning_date', 'deletion_date',
        'created_at', 'updated_at'
    ]
    
    fieldsets = [
        ('Objeto de Dados', {
            'fields': ['content_type', 'object_id']
        }),
        ('Política de Retenção', {
            'fields': ['retention_policy']
        }),
        ('Datas Calculadas', {
            'fields': [
                'data_creation_date', 'last_activity_date',
                'retention_end_date', 'warning_date', 'deletion_date'
            ]
        }),
        ('Status e Processamento', {
            'fields': [
                'status', 'warning_sent_at', 'deletion_approved_by', 
                'deletion_approved_at'
            ]
        }),
        ('Retenção Legal', {
            'fields': [
                'legal_hold_reason', 'legal_hold_applied_by', 
                'legal_hold_applied_at'
            ]
        })
    ]
    
    def content_object_link(self, obj):
        if obj.content_object:
            return format_html(
                '<a href="{}">{}</a>',
                reverse(f'admin:{obj.content_type.app_label}_{obj.content_type.model}_change',
                       args=[obj.object_id]),
                str(obj.content_object)
            )
        return "Object not found"
    content_object_link.short_description = 'Objeto'
    
    def days_remaining(self, obj):
        from datetime import date
        if obj.retention_end_date:
            remaining = (obj.retention_end_date - date.today()).days
            if remaining < 0:
                return format_html('<span style="color: red;">Vencido ({} dias)</span>', abs(remaining))
            elif remaining < 30:
                return format_html('<span style="color: orange;">{} dias</span>', remaining)
            else:
                return f"{remaining} dias"
        return "-"
    days_remaining.short_description = 'Dias Restantes'
    
    def warning_sent(self, obj):
        return obj.warning_sent_at is not None
    warning_sent.boolean = True
    warning_sent.short_description = 'Aviso Enviado'
    
    actions = ['apply_legal_hold', 'approve_deletion']
    
    def apply_legal_hold(self, request, queryset):
        # Would open a form for legal hold reason
        pass
    apply_legal_hold.short_description = 'Aplicar retenção legal'
    
    def approve_deletion(self, request, queryset):
        updated = queryset.update(
            deletion_approved_by=request.user,
            deletion_approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} exclusões aprovadas.')
    approve_deletion.short_description = 'Aprovar exclusão'

@admin.register(DataDeletionLog)
class DataDeletionLogAdmin(admin.ModelAdmin):
    list_display = [
        'deletion_id', 'original_object_representation', 'deletion_type',
        'executed_at', 'authorized_by', 'deletion_verified'
    ]
    list_filter = [
        'deletion_type', 'deletion_method', 'deletion_verified', 
        'executed_at', 'content_type'
    ]
    search_fields = [
        'deletion_id', 'original_object_representation', 'deletion_reason'
    ]
    readonly_fields = [
        'deletion_id', 'content_type', 'original_object_id',
        'verification_hash', 'executed_at'
    ]
    
    fieldsets = [
        ('Identificação da Exclusão', {
            'fields': [
                'deletion_id', 'content_type', 'original_object_id',
                'original_object_representation'
            ]
        }),
        ('Detalhes da Exclusão', {
            'fields': [
                'deletion_type', 'deletion_reason', 'retention_policy_applied'
            ]
        }),
        ('Autorização', {
            'fields': ['authorized_by', 'authorization_date']
        }),
        ('Execução', {
            'fields': [
                'executed_by', 'executed_at', 'deletion_method'
            ]
        }),
        ('Verificação', {
            'fields': [
                'verification_hash', 'deletion_verified', 'verification_date'
            ]
        }),
        ('Impacto', {
            'fields': [
                'related_records_affected', 'cascading_deletions'
            ]
        }),
        ('Conformidade Legal', {
            'fields': ['legal_basis_for_deletion', 'compliance_notes']
        }),
        ('Recuperação', {
            'fields': [
                'recovery_possible', 'recovery_deadline'
            ]
        })
    ]
    
    def has_add_permission(self, request):
        return False  # Logs should only be created programmatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Logs should be immutable

@admin.register(DataAnonymizationLog)
class DataAnonymizationLogAdmin(admin.ModelAdmin):
    list_display = [
        'anonymization_id', 'content_type', 'anonymization_method',
        'anonymization_purpose', 're_identification_risk', 'executed_at'
    ]
    list_filter = [
        'anonymization_method', 'anonymization_purpose', 're_identification_risk',
        'executed_at'
    ]
    readonly_fields = ['anonymization_id', 'executed_at']
    
    fieldsets = [
        ('Identificação', {
            'fields': [
                'anonymization_id', 'content_type', 'original_object_id',
                'anonymized_object_id'
            ]
        }),
        ('Método de Anonimização', {
            'fields': [
                'anonymization_method', 'fields_anonymized', 'anonymization_rules'
            ]
        }),
        ('Controle de Qualidade', {
            'fields': [
                'anonymization_quality_score', 're_identification_risk'
            ]
        }),
        ('Execução', {
            'fields': ['executed_by', 'executed_at']
        }),
        ('Finalidade e Retenção', {
            'fields': [
                'anonymization_purpose', 'anonymized_data_retention'
            ]
        })
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
```

### Step 5: Monitoring Dashboard

#### 5.1 Retention Dashboard View

**File**: `apps/core/views.py` (additions)

```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from datetime import date, timedelta
from .models import DataRetentionSchedule, DataDeletionLog
from .services.retention_management import DataRetentionService

@staff_member_required
def retention_dashboard(request):
    """Dashboard for monitoring data retention"""
    
    retention_service = DataRetentionService()
    stats = retention_service.get_retention_statistics()
    
    # Upcoming actions
    today = date.today()
    upcoming_warnings = DataRetentionSchedule.objects.filter(
        warning_date__lte=today + timedelta(days=7),
        status='active'
    ).order_by('warning_date')[:10]
    
    upcoming_deletions = DataRetentionSchedule.objects.filter(
        deletion_date__lte=today + timedelta(days=30),
        status='warning_sent'
    ).order_by('deletion_date')[:10]
    
    # Recent activities
    recent_deletions = DataDeletionLog.objects.order_by('-executed_at')[:10]
    
    context = {
        'stats': stats,
        'upcoming_warnings': upcoming_warnings,
        'upcoming_deletions': upcoming_deletions,
        'recent_deletions': recent_deletions,
    }
    
    return render(request, 'admin/core/retention_dashboard.html', context)

@staff_member_required
def retention_statistics_api(request):
    """API endpoint for retention statistics"""
    
    retention_service = DataRetentionService()
    stats = retention_service.get_retention_statistics()
    
    # Add trend data
    last_30_days = date.today() - timedelta(days=30)
    recent_deletions = DataDeletionLog.objects.filter(
        executed_at__gte=last_30_days
    ).count()
    
    stats['recent_deletions'] = recent_deletions
    
    return JsonResponse(stats)
```

### Step 6: Testing and Validation

#### 6.1 Retention Testing Command

**File**: `apps/core/management/commands/test_retention_system.py`

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.core.models import DataRetentionPolicy, DataRetentionSchedule
from apps.core.services.retention_management import DataRetentionService
from apps.patients.models import Patient

class Command(BaseCommand):
    help = 'Test data retention system with sample data'
    
    def add_arguments(self, parser):
        parser.add_argument('--create-test-data', action='store_true', help='Create test data')
        parser.add_argument('--run-retention', action='store_true', help='Run retention processing')
    
    def handle(self, *args, **options):
        if options['create_test_data']:
            self.create_test_data()
        
        if options['run_retention']:
            self.test_retention_processing()
        
        self.show_retention_overview()
    
    def create_test_data(self):
        """Create test patients with different retention scenarios"""
        
        self.stdout.write("Creating test data...")
        
        # Patient with old data (should trigger warning)
        old_patient = Patient.objects.create(
            name="Paciente Teste - Antigo",
            birthday=timezone.now().date() - timedelta(days=365*40),
            status='discharged'
        )
        old_patient.last_interaction_date = timezone.now() - timedelta(days=7200)  # ~19.7 years ago
        old_patient.save()
        
        # Patient with recent data
        recent_patient = Patient.objects.create(
            name="Paciente Teste - Recente",
            birthday=timezone.now().date() - timedelta(days=365*30),
            status='active'
        )
        
        # Patient with protection
        protected_patient = Patient.objects.create(
            name="Paciente Teste - Protegido",
            birthday=timezone.now().date() - timedelta(days=365*50),
            status='discharged',
            deletion_protected=True,
            protection_reason="Participação em estudo longitudinal"
        )
        protected_patient.last_interaction_date = timezone.now() - timedelta(days=7300)  # Exactly 20 years
        protected_patient.save()
        
        self.stdout.write("✓ Test patients created")
    
    def test_retention_processing(self):
        """Test retention processing"""
        
        self.stdout.write("Testing retention processing...")
        
        retention_service = DataRetentionService()
        
        # Process with dry run first
        stats_dry = retention_service.process_retention_schedules(dry_run=True)
        self.stdout.write("Dry run results:")
        for key, value in stats_dry.items():
            self.stdout.write(f"  {key}: {value}")
        
        # Confirm before actual processing
        if stats_dry['deletions_executed'] > 0:
            confirm = input(f"\nWould process {stats_dry['deletions_executed']} deletions. Continue? (yes/no): ")
            if confirm.lower() == 'yes':
                stats_real = retention_service.process_retention_schedules(dry_run=False)
                self.stdout.write("Actual processing results:")
                for key, value in stats_real.items():
                    self.stdout.write(f"  {key}: {value}")
    
    def show_retention_overview(self):
        """Show retention system overview"""
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("Data Retention System Overview")
        self.stdout.write(f"{'='*60}")
        
        # Policies
        policies = DataRetentionPolicy.objects.filter(is_active=True)
        self.stdout.write(f"\nActive Retention Policies: {policies.count()}")
        for policy in policies:
            years = policy.retention_period_days / 365.25
            self.stdout.write(f"  • {policy.name}: {years:.1f} years")
        
        # Schedules by status
        schedules = DataRetentionSchedule.objects.all()
        self.stdout.write(f"\nRetention Schedules by Status:")
        for status, label in DataRetentionSchedule.STATUS_CHOICES:
            count = schedules.filter(status=status).count()
            if count > 0:
                self.stdout.write(f"  • {label}: {count}")
        
        # Upcoming actions
        today = timezone.now().date()
        warnings_due = schedules.filter(
            warning_date__lte=today,
            status='active'
        ).count()
        deletions_due = schedules.filter(
            deletion_date__lte=today,
            status='warning_sent'
        ).count()
        
        self.stdout.write(f"\nUpcoming Actions:")
        self.stdout.write(f"  • Warnings due: {warnings_due}")
        self.stdout.write(f"  • Deletions due: {deletions_due}")
        
        # Recent activity
        recent_deletions = DataDeletionLog.objects.filter(
            executed_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        self.stdout.write(f"\nRecent Activity (last 30 days):")
        self.stdout.write(f"  • Deletions executed: {recent_deletions}")
```

## Migration and Setup

### Step 7: Database Migration and Initial Setup

```bash
# Create and run migrations
python manage.py makemigrations core --name "add_data_lifecycle_models"
python manage.py migrate

# Set up retention policies
python manage.py setup_retention_policies

# Test the system
python manage.py test_retention_system --create-test-data

# Schedule regular retention processing (add to crontab)
# 0 2 * * * cd /path/to/project && python manage.py process_data_retention
```

## Deliverable Summary

### Files Created
1. **Models**: `DataRetentionPolicy`, `DataRetentionSchedule`, `DataDeletionLog`, `DataAnonymizationLog`
2. **Services**: `DataRetentionService` for automated retention management
3. **Commands**: Retention processing, policy setup, testing commands
4. **Admin**: Complete admin interfaces with retention dashboard
5. **Views**: Retention monitoring dashboard for staff

### Key Features Implemented
- **Automated retention scheduling** based on configurable policies
- **Warning system** before data deletion
- **Legal hold functionality** to prevent deletion when required
- **Data anonymization** as alternative to deletion
- **Comprehensive audit trails** for all deletions
- **Manual approval workflows** for sensitive deletions
- **Grace periods** and recovery options

### Database Changes
- New tables: `core_dataretentionpolicy`, `core_dataretentionschedule`, `core_datadeletionlog`, `core_dataanonymizationlog`
- Enhanced Patient model with retention tracking
- Indexes for performance on date-based queries

## Next Phase

After completing Phase 4, proceed to **Phase 5: Breach Response System** to implement incident detection, notification procedures, and ANPD reporting capabilities.

---

**Phase 4 Completion Criteria**:
- [ ] Retention policies configured for all data categories
- [ ] Automated retention processing functional
- [ ] Warning system operational
- [ ] Deletion and anonymization procedures tested
- [ ] Admin dashboard accessible to staff
- [ ] Audit logging comprehensive
- [ ] Legal hold system functional
- [ ] Management commands working correctly