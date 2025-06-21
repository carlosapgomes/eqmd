from django.db import models
from apps.events.models import Event


class SimpleNote(Event):
    """
    Simple Note model that extends the base Event model.
    Used for day-to-day patient management observations and notes.
    """
    content = models.TextField(verbose_name="Conteúdo")

    def save(self, *args, **kwargs):
        """Override save to set the correct event type."""
        self.event_type = Event.SIMPLE_NOTE_EVENT
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return the absolute URL for this simple note."""
        from django.urls import reverse
        return reverse('apps.simplenotes:simplenote_detail', kwargs={'pk': self.pk})

    def get_edit_url(self):
        """Return the edit URL for this simple note."""
        from django.urls import reverse
        return reverse('apps.simplenotes:simplenote_update', kwargs={'pk': self.pk})

    def __str__(self):
        """String representation of the simple note."""
        return f"Nota - {self.patient.name} - {self.event_datetime.strftime('%d/%m/%Y %H:%M')}"

    class Meta:
        verbose_name = "Nota Simples"
        verbose_name_plural = "Notas Simples"
        ordering = ["-event_datetime"]