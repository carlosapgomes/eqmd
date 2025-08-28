import uuid
from django.db import models
from django.conf import settings
from model_utils.managers import InheritanceManager
from simple_history.models import HistoricalRecords

from apps.core.models.soft_delete import SoftDeleteModel, SoftDeleteInheritanceQuerySet


class SoftDeleteInheritanceManager(InheritanceManager):
    """Manager that combines InheritanceManager with soft delete functionality."""
    
    def get_queryset(self):
        return SoftDeleteInheritanceQuerySet(self.model, using=self._db).active()
    
    def all_with_deleted(self):
        """Get all objects including soft-deleted ones."""
        return SoftDeleteInheritanceQuerySet(self.model, using=self._db)
    
    def deleted_only(self):
        """Get only soft-deleted objects."""
        return SoftDeleteInheritanceQuerySet(self.model, using=self._db).deleted()


class Event(SoftDeleteModel):
    HISTORY_AND_PHYSICAL_EVENT = 0
    DAILY_NOTE_EVENT = 1
    SIMPLE_NOTE_EVENT = 2
    PHOTO_EVENT = 3
    EXAM_RESULT_EVENT = 4
    EXAMS_REQUEST_EVENT = 5
    DISCHARGE_REPORT_EVENT = 6
    OUTPT_PRESCRIPTION_EVENT = 7
    REPORT_EVENT = 8
    PHOTO_SERIES_EVENT = 9
    VIDEO_CLIP_EVENT = 10
    PDF_FORM_EVENT = 11
    RECORD_NUMBER_CHANGE_EVENT = 12  # NEW
    ADMISSION_EVENT = 13             # NEW
    DISCHARGE_EVENT = 14             # NEW
    STATUS_CHANGE_EVENT = 15         # NEW
    EMERGENCY_ADMISSION_EVENT = 16   # NEW
    TRANSFER_EVENT = 17              # NEW
    DEATH_DECLARATION_EVENT = 18     # NEW
    OUTPATIENT_STATUS_EVENT = 19     # NEW
    TAG_ADDED_EVENT = 20              # NEW
    TAG_REMOVED_EVENT = 21            # NEW
    TAG_BULK_REMOVE_EVENT = 22        # NEW

    EVENT_TYPE_CHOICES = (
        (HISTORY_AND_PHYSICAL_EVENT, "Anamnese e Exame Físico"),
        (DAILY_NOTE_EVENT, "Evolução"),
        (SIMPLE_NOTE_EVENT, "Nota/Observação"),
        (PHOTO_EVENT, "Imagem"),
        (EXAM_RESULT_EVENT, "Resultado de Exame"),
        (EXAMS_REQUEST_EVENT, "Requisição de Exame"),
        (DISCHARGE_REPORT_EVENT, "Relatório de Alta"),
        (OUTPT_PRESCRIPTION_EVENT, "Receita"),
        (REPORT_EVENT, "Relatório"),
        (PHOTO_SERIES_EVENT, "Série de Fotos"),
        (VIDEO_CLIP_EVENT, "Vídeo Curto"),
        (PDF_FORM_EVENT, "Formulário PDF"),
        (RECORD_NUMBER_CHANGE_EVENT, "Alteração de Prontuário"),  # NEW
        (ADMISSION_EVENT, "Admissão Hospitalar"),                 # NEW
        (DISCHARGE_EVENT, "Alta Hospitalar"),                     # NEW
        (STATUS_CHANGE_EVENT, "Alteração de Status"),             # NEW
        (EMERGENCY_ADMISSION_EVENT, "Admissão de Emergência"),    # NEW
        (TRANSFER_EVENT, "Transferência"),                        # NEW
        (DEATH_DECLARATION_EVENT, "Declaração de Óbito"),         # NEW
        (OUTPATIENT_STATUS_EVENT, "Status Ambulatorial"),         # NEW
        (TAG_ADDED_EVENT, "Tag Adicionada"),                      # NEW
        (TAG_REMOVED_EVENT, "Tag Removida"),                      # NEW
        (TAG_BULK_REMOVE_EVENT, "Tags Removidas em Lote"),        # NEW
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.PositiveSmallIntegerField(
        choices=EVENT_TYPE_CHOICES, verbose_name="Tipo de Evento"
    )
    event_datetime = models.DateTimeField(verbose_name="Data e Hora do Evento")
    description = models.CharField(max_length=255, verbose_name="Descrição")
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, verbose_name="Paciente"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="event_set",
        verbose_name="Criado por",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="event_updated",
        verbose_name="Atualizado por",
    )

    objects = SoftDeleteInheritanceManager()
    
    # History tracking
    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
    )

    def __str__(self):
        return str(self.description)

    def get_excerpt(self, max_length=150):
        """Generate a short excerpt from event content."""
        content = getattr(self, "content", None) or getattr(self, "description", "")
        if content:
            # Remove HTML tags
            import re

            clean_content = re.sub("<[^<]+?>", "", str(content))
            return (
                clean_content[:max_length] + "..."
                if len(clean_content) > max_length
                else clean_content
            )
        return "No content available"

    def get_event_type_badge_class(self):
        """Return CSS class for event type badge."""
        badge_classes = {
            0: "bg-medical-primary",  # History & Physical
            1: "bg-medical-success",  # Daily Notes
            2: "bg-medical-info",  # Simple Note
            3: "bg-medical-warning",  # Photos
            4: "bg-medical-danger",  # Exam Results
            5: "bg-medical-secondary",  # Exam Request
            6: "bg-medical-dark",  # Discharge Report
            7: "bg-medical-teal",  # Prescription - Changed from bg-medical-light to bg-medical-teal
            8: "bg-medical-teal",  # Report
            9: "bg-info",  # Photo Series
            10: "bg-primary",  # Video Clip
            11: "bg-secondary",  # PDF Form
            12: "bg-warning",  # Record Number Change
            13: "bg-success",  # Admission
            14: "bg-info",  # Discharge
            15: "bg-secondary",  # Status Change
            16: "bg-danger",  # Emergency Admission
            17: "bg-primary",  # Transfer
            18: "bg-dark",  # Death Declaration
            19: "bg-light",  # Outpatient Status
            20: "bg-success",  # Tag Added
            21: "bg-warning",  # Tag Removed
            22: "bg-danger",  # Tag Bulk Remove
        }
        return badge_classes.get(self.event_type, "bg-secondary")

    def get_event_type_icon(self):
        """Return Bootstrap icon class for event type."""
        icon_classes = {
            0: "bi-clipboard2-heart",  # History & Physical
            1: "bi-journal-text",  # Daily Notes
            2: "bi-sticky",  # Simple Note
            3: "bi-camera",  # Photos
            4: "bi-clipboard2-data",  # Exam Results
            5: "bi-clipboard2-check",  # Exam Request
            6: "bi-door-open",  # Discharge Report
            7: "bi-prescription2",  # Prescription
            8: "bi-file-text",  # Report
            9: "bi-images",  # Photo Series
            10: "bi-play-circle",  # Video Clip
            11: "bi-file-pdf",  # PDF Form
            12: "bi-hash",  # Record Number Change
            13: "bi-hospital",  # Admission
            14: "bi-door-open",  # Discharge
            15: "bi-arrow-repeat",  # Status Change
            16: "bi-exclamation-triangle",  # Emergency Admission
            17: "bi-arrow-left-right",  # Transfer
            18: "bi-heart-pulse",  # Death Declaration
            19: "bi-person-check",  # Outpatient Status
            20: "bi-tag-fill",  # Tag Added
            21: "bi-tag",  # Tag Removed
            22: "bi-tags",  # Tag Bulk Remove
        }
        return icon_classes.get(self.event_type, "bi-file-text")

    def get_event_type_short_display(self):
        """Return shortened event type display for mobile-friendly badges."""
        short_display_map = {
            0: "Anamese",  # Anamnese e Exame Físico
            1: "Evolução",  # Evolução (already short)
            2: "Nota/Obs.",  # Nota/Observação
            3: "Imagem",  # Imagem (already short)
            4: "Resultado",  # Resultado de Exame
            5: "Requisição",  # Requisição de Exame
            6: "Alta",  # Relatório de Alta
            7: "Receita",  # Receita (already short)
            8: "Relatório",  # Relatório (already short)
            9: "Fotos",  # Série de Fotos
            10: "Vídeo",  # Vídeo Curto
            11: "PDF",  # Formulário PDF
            12: "Prontuário",  # Alteração de Prontuário
            13: "Admissão",  # Admissão Hospitalar
            14: "Alta",  # Alta Hospitalar
            15: "Status",  # Alteração de Status
            16: "Emergência",  # Admissão de Emergência
            17: "Transferência",  # Transferência
            18: "Óbito",  # Declaração de Óbito
            19: "Ambulatorial",  # Status Ambulatorial
            20: "Tag +",  # Tag Adicionada
            21: "Tag -",  # Tag Removida
            22: "Tags --",  # Tags Removidas em Lote
        }
        return short_display_map.get(self.event_type, self.get_event_type_display())

    def get_absolute_url(self):
        """Return the absolute URL for this event.
        Should be overridden by derived classes. For timeline-only events,
        returns the patient timeline URL as a fallback.
        """
        from django.urls import reverse
        from django.core.exceptions import ImproperlyConfigured
        
        # Timeline-only events that don't have detail pages
        timeline_only_events = [
            self.TRANSFER_EVENT,
            self.STATUS_CHANGE_EVENT, 
            self.RECORD_NUMBER_CHANGE_EVENT,
            self.ADMISSION_EVENT,
            self.DISCHARGE_EVENT,
            self.DEATH_DECLARATION_EVENT,
            self.OUTPATIENT_STATUS_EVENT,
            self.TAG_ADDED_EVENT,
            self.TAG_REMOVED_EVENT,
            self.TAG_BULK_REMOVE_EVENT,
        ]
        
        if self.event_type in timeline_only_events:
            # Redirect to patient timeline for informational events
            return reverse('apps.patients:patient_events_timeline', kwargs={'patient_id': self.patient.pk})

        raise ImproperlyConfigured(
            f"The {self.__class__.__name__} model must define a get_absolute_url() method."
        )

    def get_edit_url(self):
        """Return the edit URL for this event.
        Should be overridden by derived classes.
        """
        from django.urls import reverse
        from django.core.exceptions import ImproperlyConfigured

        raise ImproperlyConfigured(
            f"The {self.__class__.__name__} model must define a get_edit_url() method."
        )

    @property
    def can_be_edited(self):
        """Check if event is within edit window (24 hours)."""
        if not self.created_at:
            return False
        from datetime import timedelta
        from django.utils import timezone

        edit_deadline = self.created_at + timedelta(hours=24)
        return timezone.now() <= edit_deadline

    class Meta:
        db_table = 'events_event'
        ordering = ["-created_at"]
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        permissions = [
            ("edit_own_event_24h", "Can edit own events within 24 hours"),
            ("delete_own_event_24h", "Can delete own events within 24 hours"),
        ]
        indexes = [
            models.Index(fields=['is_deleted', 'patient', 'event_datetime']),
            models.Index(fields=['is_deleted', 'created_by']),
            models.Index(
                fields=["patient", "-event_datetime"], name="event_patient_dt_idx"
            ),
            models.Index(
                fields=["created_by", "-event_datetime"], name="event_creator_dt_idx"
            ),
            models.Index(fields=["event_datetime"], name="event_datetime_idx"),
            models.Index(
                fields=["event_type", "-event_datetime"], name="event_type_dt_idx"
            ),
            models.Index(
                fields=["patient", "event_type", "-event_datetime"],
                name="event_pt_type_dt_idx",
            ),
        ]


class RecordNumberChangeEvent(Event):
    """Event for tracking record number changes in patient timeline"""
    
    record_change = models.OneToOneField(
        'patients.PatientRecordNumber',
        on_delete=models.CASCADE,
        related_name='timeline_event',
        verbose_name="Alteração de Prontuário"
    )
    
    # Denormalized fields for performance and display
    old_record_number = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name="Número Anterior",
        help_text="Número de prontuário anterior"
    )
    new_record_number = models.CharField(
        max_length=50,
        verbose_name="Novo Número",
        help_text="Novo número de prontuário"
    )
    change_reason = models.TextField(
        blank=True,
        verbose_name="Motivo da Alteração",
        help_text="Razão para a mudança do número"
    )
    
    class Meta:
        verbose_name = "Evento de Alteração de Prontuário"
        verbose_name_plural = "Eventos de Alteração de Prontuário"
    
    def save(self, *args, **kwargs):
        """Override save to set event_type and sync with record_change"""
        self.event_type = self.RECORD_NUMBER_CHANGE_EVENT
        
        # Sync data from related PatientRecordNumber if available
        if self.record_change_id:
            record = self.record_change
            self.new_record_number = record.record_number
            self.old_record_number = record.previous_record_number
            self.change_reason = record.change_reason
            self.patient = record.patient
            self.event_datetime = record.effective_date
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.old_record_number:
            return f"Alteração de prontuário: {self.old_record_number} → {self.new_record_number}"
        return f"Novo prontuário: {self.new_record_number}"
    
    def get_absolute_url(self):
        """Return URL to view record number change details"""
        from django.urls import reverse
        return reverse('patients:api_patient_record_numbers', kwargs={'patient_id': self.patient.pk})
    
    def get_edit_url(self):
        """Return URL to edit record number change"""
        from django.urls import reverse
        return reverse('patients:record_number_update', kwargs={'pk': self.record_change.pk})


class AdmissionEvent(Event):
    """Event for tracking patient admissions in timeline"""
    
    admission = models.OneToOneField(
        'patients.PatientAdmission',
        on_delete=models.CASCADE,
        related_name='timeline_event',
        verbose_name="Internação"
    )
    
    # Denormalized fields for performance and display
    admission_type = models.CharField(
        max_length=20,
        verbose_name="Tipo de Admissão",
        help_text="Tipo da admissão hospitalar"
    )
    initial_bed = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="Leito Inicial",
        help_text="Leito/quarto inicial"
    )
    admission_diagnosis = models.TextField(
        blank=True,
        verbose_name="Diagnóstico de Admissão",
        help_text="Diagnóstico principal na admissão"
    )
    
    class Meta:
        verbose_name = "Evento de Admissão"
        verbose_name_plural = "Eventos de Admissão"
    
    def save(self, *args, **kwargs):
        """Override save to set event_type and sync with admission"""
        self.event_type = self.ADMISSION_EVENT
        
        # Sync data from related PatientAdmission if available
        if self.admission_id:
            admission = self.admission
            self.admission_type = admission.get_admission_type_display()
            self.initial_bed = admission.initial_bed
            self.admission_diagnosis = admission.admission_diagnosis
            self.patient = admission.patient
            self.event_datetime = admission.admission_datetime
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Admissão - {self.admission_type}"
    
    def get_absolute_url(self):
        """Return URL to view admission details"""
        from django.urls import reverse
        return reverse('patients:api_admission_detail', kwargs={'admission_id': self.admission.pk})
    
    def get_edit_url(self):
        """Return URL to edit admission"""
        from django.urls import reverse
        return reverse('patients:admission_update', kwargs={'pk': self.admission.pk})


class DischargeEvent(Event):
    """Event for tracking patient discharges in timeline"""
    
    admission = models.OneToOneField(
        'patients.PatientAdmission',
        on_delete=models.CASCADE,
        related_name='discharge_timeline_event',
        verbose_name="Internação"
    )
    
    # Denormalized fields for performance and display
    discharge_type = models.CharField(
        max_length=20,
        verbose_name="Tipo de Alta",
        help_text="Tipo da alta hospitalar"
    )
    final_bed = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="Leito Final",
        help_text="Último leito/quarto"
    )
    discharge_diagnosis = models.TextField(
        blank=True,
        verbose_name="Diagnóstico de Alta",
        help_text="Diagnóstico principal na alta"
    )
    stay_duration_days = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="Duração da Internação (dias)",
        help_text="Duração total em dias"
    )
    
    class Meta:
        verbose_name = "Evento de Alta"
        verbose_name_plural = "Eventos de Alta"
    
    def save(self, *args, **kwargs):
        """Override save to set event_type and sync with admission"""
        self.event_type = self.DISCHARGE_EVENT
        
        # Sync data from related PatientAdmission if available
        if self.admission_id:
            admission = self.admission
            self.discharge_type = admission.get_discharge_type_display()
            self.final_bed = admission.final_bed
            self.discharge_diagnosis = admission.discharge_diagnosis
            self.stay_duration_days = admission.stay_duration_days
            self.patient = admission.patient
            self.event_datetime = admission.discharge_datetime
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        duration_text = f" ({self.stay_duration_days}d)" if self.stay_duration_days else ""
        return f"Alta - {self.discharge_type}{duration_text}"
    
    def get_absolute_url(self):
        """Return URL to view discharge details"""
        from django.urls import reverse
        return reverse('patients:api_admission_detail', kwargs={'admission_id': self.admission.pk})
    
    def get_edit_url(self):
        """Return URL to edit discharge"""
        from django.urls import reverse
        return reverse('patients:discharge_patient', kwargs={'pk': self.admission.pk})


class StatusChangeEvent(Event):
    """Event for tracking patient status changes in timeline"""
    
    previous_status = models.PositiveSmallIntegerField(
        choices=None,  # Will be set in __init__
        verbose_name="Status Anterior"
    )
    new_status = models.PositiveSmallIntegerField(
        choices=None,  # Will be set in __init__
        verbose_name="Novo Status"
    )
    reason = models.TextField(
        blank=True,
        verbose_name="Motivo da Alteração"
    )
    
    # Optional fields for specific status changes
    ward = models.ForeignKey(
        'patients.Ward',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Ala"
    )
    bed = models.CharField(
        max_length=20, blank=True,
        verbose_name="Leito"
    )
    discharge_reason = models.TextField(
        blank=True,
        verbose_name="Motivo da Alta"
    )
    death_time = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Hora do Óbito"
    )
    
    class Meta:
        verbose_name = "Evento de Alteração de Status"
        verbose_name_plural = "Eventos de Alteração de Status"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Import here to avoid circular import
        from apps.patients.models import Patient
        # Set choices dynamically to avoid circular import
        self._meta.get_field('previous_status').choices = Patient.Status.choices
        self._meta.get_field('new_status').choices = Patient.Status.choices
    
    def save(self, *args, **kwargs):
        """Override save to set event_type"""
        self.event_type = self.STATUS_CHANGE_EVENT
        super().save(*args, **kwargs)
    
    def __str__(self):
        from apps.patients.models import Patient
        status_dict = dict(Patient.Status.choices)
        prev_label = status_dict.get(self.previous_status, "Desconhecido")
        new_label = status_dict.get(self.new_status, "Desconhecido")
        return f"Status: {prev_label} → {new_label}"
    
    def get_absolute_url(self):
        """Return URL to view status change details"""
        from django.urls import reverse
        return reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
    
    def get_edit_url(self):
        """Return URL to edit status change"""
        from django.urls import reverse
        return reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})


class TagAddedEvent(Event):
    """Event for tracking tag additions to patients in timeline"""
    
    tag_name = models.CharField(
        max_length=100,
        verbose_name="Nome da Tag",
        help_text="Nome da tag adicionada"
    )
    tag_color = models.CharField(
        max_length=7,
        verbose_name="Cor da Tag",
        help_text="Cor da tag em formato hexadecimal"
    )
    tag_notes = models.TextField(
        blank=True,
        verbose_name="Observações da Tag",
        help_text="Observações sobre a atribuição da tag"
    )
    
    class Meta:
        verbose_name = "Evento de Tag Adicionada"
        verbose_name_plural = "Eventos de Tags Adicionadas"
    
    def save(self, *args, **kwargs):
        """Override save to set event_type"""
        self.event_type = self.TAG_ADDED_EVENT
        # Set description based on tag name
        if not self.description:
            self.description = f"Tag '{self.tag_name}' adicionada"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Tag adicionada: {self.tag_name}"
    
    def get_absolute_url(self):
        """Return URL to view patient tags"""
        from django.urls import reverse
        return reverse('patients:patient_tags_api', kwargs={'patient_id': self.patient.pk})
    
    def get_edit_url(self):
        """Return URL to patient detail (tags can't be edited, only removed)"""
        from django.urls import reverse
        return reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})


class TagRemovedEvent(Event):
    """Event for tracking tag removals from patients in timeline"""
    
    tag_name = models.CharField(
        max_length=100,
        verbose_name="Nome da Tag",
        help_text="Nome da tag removida"
    )
    tag_color = models.CharField(
        max_length=7,
        verbose_name="Cor da Tag",
        help_text="Cor da tag em formato hexadecimal"
    )
    tag_notes = models.TextField(
        blank=True,
        verbose_name="Observações da Tag",
        help_text="Observações que a tag tinha antes da remoção"
    )
    
    class Meta:
        verbose_name = "Evento de Tag Removida"
        verbose_name_plural = "Eventos de Tags Removidas"
    
    def save(self, *args, **kwargs):
        """Override save to set event_type"""
        self.event_type = self.TAG_REMOVED_EVENT
        # Set description based on tag name
        if not self.description:
            self.description = f"Tag '{self.tag_name}' removida"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Tag removida: {self.tag_name}"
    
    def get_absolute_url(self):
        """Return URL to view patient tags"""
        from django.urls import reverse
        return reverse('patients:patient_tags_api', kwargs={'patient_id': self.patient.pk})
    
    def get_edit_url(self):
        """Return URL to patient detail (removed tags can't be restored from timeline)"""
        from django.urls import reverse
        return reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})


class TagBulkRemoveEvent(Event):
    """Event for tracking bulk removal of tags from patients in timeline"""
    
    tag_count = models.PositiveIntegerField(
        verbose_name="Quantidade de Tags",
        help_text="Número de tags removidas na operação em lote"
    )
    tag_names = models.TextField(
        verbose_name="Nomes das Tags",
        help_text="Lista de nomes das tags removidas, separados por vírgula"
    )
    
    class Meta:
        verbose_name = "Evento de Remoção em Lote de Tags"
        verbose_name_plural = "Eventos de Remoção em Lote de Tags"
    
    def save(self, *args, **kwargs):
        """Override save to set event_type"""
        self.event_type = self.TAG_BULK_REMOVE_EVENT
        # Set description based on tag count
        if not self.description:
            self.description = f"{self.tag_count} tag(s) removida(s) em lote"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Remoção em lote: {self.tag_count} tag(s)"
    
    def get_absolute_url(self):
        """Return URL to view patient tags"""
        from django.urls import reverse
        return reverse('patients:patient_tags_api', kwargs={'patient_id': self.patient.pk})
    
    def get_edit_url(self):
        """Return URL to patient detail (bulk removed tags can't be restored from timeline)"""
        from django.urls import reverse
        return reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
