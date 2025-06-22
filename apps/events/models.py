import uuid
from django.db import models
from django.conf import settings
from model_utils.managers import InheritanceManager


class Event(models.Model):
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

    objects = InheritanceManager()

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
            7: "bg-medical-light",  # Prescription
            8: "bg-medical-teal",  # Report
            9: "bg-info",  # Photo Series
            10: "bg-primary",  # Video Clip
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
        }
        return short_display_map.get(self.event_type, self.get_event_type_display())

    def get_absolute_url(self):
        """Return the absolute URL for this event.
        Should be overridden by derived classes.
        """
        from django.urls import reverse
        from django.core.exceptions import ImproperlyConfigured

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
        ordering = ["-created_at"]
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        permissions = [
            ("edit_own_event_24h", "Can edit own events within 24 hours"),
            ("delete_own_event_24h", "Can delete own events within 24 hours"),
        ]
        indexes = [
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
