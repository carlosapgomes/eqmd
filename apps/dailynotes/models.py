from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from apps.events.models import Event


class DailyNote(Event):
    """
    Daily Note model that extends the base Event model.
    Used for medical daily evolution notes.
    """
    content = models.TextField(verbose_name="Conteúdo")

    # Full text search field
    search_vector = SearchVectorField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """Override save to set the correct event type."""
        self.event_type = Event.DAILY_NOTE_EVENT
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return the absolute URL for this daily note."""
        from django.urls import reverse
        return reverse('apps.dailynotes:dailynote_detail', kwargs={'pk': self.pk})

    def get_edit_url(self):
        """Return the edit URL for this daily note."""
        from django.urls import reverse
        return reverse('apps.dailynotes:dailynote_update', kwargs={'pk': self.pk})

    def __str__(self):
        """String representation of the daily note."""
        return f"Evolução - {self.patient.name} - {self.event_datetime.strftime('%d/%m/%Y %H:%M')}"

    class Meta:
        verbose_name = "Evolução"
        verbose_name_plural = "Evoluções"
        ordering = ["-event_datetime"]
        indexes = [
            GinIndex(fields=['search_vector'], name='dailynote_search_gin_idx'),
        ]
