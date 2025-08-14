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
        
        # Process patients that don't have retention schedules yet
        # Note: Using exclude with a subquery to work around Django GenericForeignKey limitations
        content_type = ContentType.objects.get_for_model(Patient)
        existing_schedule_object_ids = DataRetentionSchedule.objects.filter(
            content_type=content_type
        ).values_list('object_id', flat=True)
        
        patients = Patient.objects.exclude(id__in=existing_schedule_object_ids)
        
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