# dailynotes/models.py
from django.db import models

from apps.events.models import Event


class DailyNote(Event):
    content = models.TextField(verbose_name="Conteúdo")

    def save(self, *args, **kwargs):
        self.event_type = Event.DAILY_NOTE_EVENT
        self.description = Event.EVENT_TYPE_CHOICES[self.event_type][1]
        return super().save(*args, **kwargs)

    def __str__(self):
        return str(self.description)
    
    class Meta:
        verbose_name = "Evolução"
        verbose_name_plural = "Evoluções"
