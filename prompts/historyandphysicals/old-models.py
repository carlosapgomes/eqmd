# historyandphysicals/models.py
from django.db import models

from apps.events.models import Event


class HistoryAndPhysical(Event):
    content = models.TextField(verbose_name="Conteúdo do Histórico e Exame Físico")

    def save(self, *args, **kwargs):
        self.event_type = (
            Event.HISTORY_AND_PHYSICAL_EVENT
        )  # Assuming you add this event type in events.models
        self.description = Event.EVENT_TYPE_CHOICES[self.event_type][1]
        return super().save(*args, **kwargs)

    def __str__(self):
        return str(self.description)

    class Meta:
        verbose_name = "Histórico e Exame Físico"
        verbose_name_plural = "Históricos e Exames Físicos"
