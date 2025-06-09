from django.db import models
from apps.events.models import Event


class DailyNote(Event):
    """
    Daily Note model that extends the base Event model.
    Used for medical daily evolution notes.
    """
    content = models.TextField(verbose_name="Conteúdo")

    def save(self, *args, **kwargs):
        """Override save to set the correct event type."""
        self.event_type = Event.DAILY_NOTE_EVENT
        super().save(*args, **kwargs)

    def __str__(self):
        """String representation of the daily note."""
        return f"Evolução - {self.patient.name} - {self.event_datetime.strftime('%d/%m/%Y %H:%M')}"

    class Meta:
        verbose_name = "Evolução"
        verbose_name_plural = "Evoluções"
        ordering = ["-event_datetime"]
