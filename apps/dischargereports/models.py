from django.db import models
from apps.events.models import Event


class DischargeReport(Event):
    """Discharge report extending the base Event model"""

    # Date fields
    admission_date = models.DateField(
        verbose_name="Data de Admissão",
        help_text="Data da admissão hospitalar"
    )
    discharge_date = models.DateField(
        verbose_name="Data de Alta",
        help_text="Data da alta hospitalar"
    )

    # Text content fields
    admission_history = models.TextField(
        verbose_name="História da Admissão",
        help_text="História clínica da admissão"
    )
    problems_and_diagnosis = models.TextField(
        verbose_name="Problemas e Diagnósticos",
        help_text="Problemas principais e diagnósticos"
    )
    exams_list = models.TextField(
        verbose_name="Lista de Exames",
        help_text="Exames realizados durante a internação"
    )
    procedures_list = models.TextField(
        verbose_name="Lista de Procedimentos",
        help_text="Procedimentos realizados"
    )
    inpatient_medical_history = models.TextField(
        verbose_name="História Médica da Internação",
        help_text="Evolução médica durante a internação"
    )
    discharge_status = models.TextField(
        verbose_name="Status da Alta",
        help_text="Condições do paciente na alta"
    )
    discharge_recommendations = models.TextField(
        verbose_name="Recomendações de Alta",
        help_text="Orientações e recomendações para pós-alta"
    )

    # Classification field
    medical_specialty = models.CharField(
        max_length=100,
        verbose_name="Especialidade Médica",
        help_text="Especialidade responsável pela alta"
    )

    class Meta:
        verbose_name = "Relatório de Alta"
        verbose_name_plural = "Relatórios de Alta"
        ordering = ["-event_datetime"]
        indexes = [
            models.Index(fields=['admission_date']),
            models.Index(fields=['discharge_date']),
            models.Index(fields=['medical_specialty']),
        ]

    def save(self, *args, **kwargs):
        """Override save to set the correct event type and clean text fields."""
        from .utils import clean_discharge_report_text_fields
        
        self.event_type = Event.DISCHARGE_REPORT_EVENT
        
        # Set default draft status for new discharge reports
        if not self.pk and not hasattr(self, 'is_draft'):
            self.is_draft = True
        
        # Clean text fields before saving
        clean_discharge_report_text_fields(self)
        
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return the absolute URL for this discharge report."""
        from django.urls import reverse
        return reverse('apps.dischargereports:dischargereport_detail', kwargs={'pk': self.pk})

    def get_edit_url(self):
        """Return the edit URL for this discharge report."""
        from django.urls import reverse
        return reverse('apps.dischargereports:dischargereport_update', kwargs={'pk': self.pk})

    def can_be_edited_by_user(self, user):
        """Check if report can be edited by specific user"""
        if self.is_draft:
            # Drafts can be edited by creator or users with edit permissions
            return self.created_by == user or user.has_perm('events.change_event')
        else:
            # Finalized reports follow 24h rule
            return self.can_be_edited and (self.created_by == user or user.has_perm('events.change_event'))

    def can_be_deleted_by_user(self, user):
        """Check if report can be deleted by specific user"""
        # Only drafts can be deleted
        return self.is_draft and (self.created_by == user or user.has_perm('events.delete_event'))

    @property
    def status_display(self):
        """Get display text for report status"""
        if self.is_draft:
            return "Rascunho"
        else:
            return "Finalizado"

    @property
    def status_badge_class(self):
        """Get CSS class for status badge"""
        return "badge bg-warning text-dark" if self.is_draft else "badge bg-success"

    def __str__(self):
        """String representation of the discharge report."""
        draft_text = " (Rascunho)" if self.is_draft else ""
        return f"Relatório de Alta - {self.patient.name} - {self.discharge_date.strftime('%d/%m/%Y')}{draft_text}"