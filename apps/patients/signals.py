from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Patient, PatientRecordNumber, PatientAdmission
from apps.events.models import RecordNumberChangeEvent, AdmissionEvent, DischargeEvent, StatusChangeEvent


@receiver(post_save, sender=PatientRecordNumber)
def create_record_change_event(sender, instance, created, **kwargs):
    """Create timeline event when record number is changed"""
    if created or instance.is_current:
        # Create or update the timeline event
        event, event_created = RecordNumberChangeEvent.objects.get_or_create(
            record_change=instance,
            defaults={
                'patient': instance.patient,
                'event_datetime': instance.effective_date,
                'description': f"Alteração de prontuário para {instance.record_number}",
                'created_by': instance.created_by,
                'updated_by': instance.updated_by,
            }
        )
        
        if not event_created:
            # Update existing event
            event.event_datetime = instance.effective_date
            event.description = f"Alteração de prontuário para {instance.record_number}"
            event.updated_by = instance.updated_by
            event.save()


@receiver(post_save, sender=PatientAdmission)
def create_admission_discharge_events(sender, instance, created, **kwargs):
    """Create timeline events for admission and discharge"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Signal: create_admission_discharge_events triggered for admission {instance.pk}")
    logger.info(f"Signal: created={created}, discharge_datetime={instance.discharge_datetime}")
    
    # Create or update admission event
    admission_event, admission_created = AdmissionEvent.objects.get_or_create(
        admission=instance,
        defaults={
            'patient': instance.patient,
            'event_datetime': instance.admission_datetime,
            'description': f"Admissão hospitalar - {instance.get_admission_type_display()}",
            'created_by': instance.created_by,
            'updated_by': instance.updated_by,
        }
    )
    logger.info(f"Signal: Admission event - created={admission_created}, ID={admission_event.pk}")
    
    if not admission_created:
        # Update existing admission event
        admission_event.event_datetime = instance.admission_datetime
        admission_event.description = f"Admissão hospitalar - {instance.get_admission_type_display()}"
        admission_event.updated_by = instance.updated_by
        admission_event.save()
        logger.info("Signal: Updated existing admission event")
    
    # Handle discharge event
    if instance.discharge_datetime:
        logger.info("Signal: Creating/updating discharge event")
        # Create or update discharge event
        discharge_event, discharge_created = DischargeEvent.objects.get_or_create(
            admission=instance,
            defaults={
                'patient': instance.patient,
                'event_datetime': instance.discharge_datetime,
                'description': f"Alta hospitalar - {instance.get_discharge_type_display()}",
                'created_by': instance.created_by,
                'updated_by': instance.updated_by,
            }
        )
        logger.info(f"Signal: Discharge event - created={discharge_created}, ID={discharge_event.pk}")
        
        if not discharge_created:
            # Update existing discharge event
            discharge_event.event_datetime = instance.discharge_datetime
            discharge_event.description = f"Alta hospitalar - {instance.get_discharge_type_display()}"
            discharge_event.updated_by = instance.updated_by
            discharge_event.save()
            logger.info("Signal: Updated existing discharge event")
    else:
        logger.info("Signal: No discharge datetime, removing any existing discharge events")
        # Remove discharge event if discharge was cancelled
        delete_result = DischargeEvent.objects.filter(admission=instance).delete()
        deleted_count = delete_result[0] if isinstance(delete_result, tuple) else delete_result
        logger.info(f"Signal: Deleted {deleted_count} discharge events")


@receiver(post_delete, sender=PatientRecordNumber)
def delete_record_change_event(sender, instance, **kwargs):
    """Delete timeline event when record number is deleted"""
    RecordNumberChangeEvent.objects.filter(record_change=instance).delete()


@receiver(post_delete, sender=PatientAdmission)
def delete_admission_events(sender, instance, **kwargs):
    """Delete timeline events when admission is deleted"""
    AdmissionEvent.objects.filter(admission=instance).delete()
    DischargeEvent.objects.filter(admission=instance).delete()


# Enhanced signal handlers for data consistency

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
            'status': Patient.Status.OUTPATIENT,
            'current_admission_id': None,
            'last_discharge_date': instance.discharge_datetime.date() if instance.discharge_datetime else None,
            'bed': "",
            'ward': None,
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


# Status change tracking signals

@receiver(pre_save, sender=Patient)
def track_status_changes(sender, instance, **kwargs):
    """Track patient status changes and store for post_save signal"""
    
    if instance.pk:  # Only for existing patients
        try:
            old_instance = Patient.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                # Store for post_save signal
                instance._status_changed = True
                instance._old_status = old_instance.status
                instance._new_status = instance.status
                # Store the user who made the change (from request context)
                instance._status_change_user = getattr(instance, 'updated_by', None)
        except Patient.DoesNotExist:
            pass


@receiver(post_save, sender=Patient)
def create_status_change_event(sender, instance, created, **kwargs):
    """Create timeline event for status changes"""
    
    if not created and getattr(instance, '_status_changed', False):
        # Get the user who made the change
        change_user = getattr(instance, '_status_change_user', None)
        if not change_user:
            # Fallback to updated_by if available
            change_user = instance.updated_by
        
        # Determine reason based on status change
        old_status = instance._old_status
        new_status = instance._new_status
        reason = _get_status_change_reason(old_status, new_status)
        
        # Create status change event
        status_event = StatusChangeEvent.objects.create(
            patient=instance,
            event_datetime=timezone.now(),
            description=f"Alteração de status: {instance.get_status_display()}",
            created_by=change_user,
            updated_by=change_user,
            previous_status=old_status,
            new_status=new_status,
            reason=reason,
            ward=instance.ward,
            bed=instance.bed,
        )
        
        # Clean up temporary attributes
        delattr(instance, '_status_changed')
        delattr(instance, '_old_status')
        delattr(instance, '_new_status')
        if hasattr(instance, '_status_change_user'):
            delattr(instance, '_status_change_user')


def _get_status_change_reason(old_status, new_status):
    """Generate default reason for status change"""
    status_dict = dict(Patient.Status.choices)
    old_label = status_dict.get(old_status, "Desconhecido")
    new_label = status_dict.get(new_status, "Desconhecido")
    
    # Generate appropriate reason based on transition
    if new_status == Patient.Status.INPATIENT:
        return "Paciente admitido para internação"
    elif new_status == Patient.Status.EMERGENCY:
        return "Paciente admitido em emergência"
    elif new_status == Patient.Status.DISCHARGED:
        return "Paciente recebeu alta hospitalar"
    elif new_status == Patient.Status.TRANSFERRED:
        return "Paciente transferido para outra unidade"
    elif new_status == Patient.Status.DECEASED:
        return "Declaração de óbito"
    elif new_status == Patient.Status.OUTPATIENT:
        return "Paciente em acompanhamento ambulatorial"
    else:
        return f"Status alterado de {old_label} para {new_label}"