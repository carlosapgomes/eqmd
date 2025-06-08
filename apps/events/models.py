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

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        permissions = [
            ("edit_own_event_24h", "Can edit own events within 24 hours"),
            ("delete_own_event_24h", "Can delete own events within 24 hours"),
        ]
