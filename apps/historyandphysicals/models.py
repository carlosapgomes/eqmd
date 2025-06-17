from django.db import models
from apps.events.models import Event


class HistoryAndPhysical(Event):
    """
    History and Physical model that extends the base Event model.
    Used for medical history and physical examination documentation.
    """
    content = models.TextField(verbose_name="Conteúdo")

    def save(self, *args, **kwargs):
        """Override save to set the correct event type."""
        self.event_type = Event.HISTORY_AND_PHYSICAL_EVENT
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return the absolute URL for this history and physical."""
        from django.urls import reverse
        return reverse('apps.historyandphysicals:historyandphysical_detail', kwargs={'pk': self.pk})

    def get_edit_url(self):
        """Return the edit URL for this history and physical."""
        from django.urls import reverse
        return reverse('apps.historyandphysicals:historyandphysical_update', kwargs={'pk': self.pk})

    def __str__(self):
        """String representation of the history and physical."""
        return f"Anamnese e Exame Físico - {self.patient.name} - {self.event_datetime.strftime('%d/%m/%Y %H:%M')}"

    class Meta:
        verbose_name = "Anamnese e Exame Físico"
        verbose_name_plural = "Anamneses e Exames Físicos"
        ordering = ["-event_datetime"]