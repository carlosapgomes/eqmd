import uuid
from django.db import models
from django.conf import settings
from apps.events.models import Event


class SampleContent(models.Model):
    """
    Sample content model to hold template content for various event types.
    All users can read but only superusers can create/edit/delete.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, verbose_name="Título")
    content = models.TextField(verbose_name="Conteúdo")
    event_type = models.PositiveSmallIntegerField(
        choices=Event.EVENT_TYPE_CHOICES, 
        verbose_name="Tipo de Evento"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sample_content_created",
        verbose_name="Criado por",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sample_content_updated",
        verbose_name="Atualizado por",
    )

    def __str__(self):
        return self.title

    def get_event_type_display_formatted(self):
        """Return the formatted event type display name."""
        return self.get_event_type_display()

    class Meta:
        ordering = ['event_type', 'title']
        verbose_name = "Conteúdo de Exemplo"
        verbose_name_plural = "Conteúdos de Exemplo"
        indexes = [
            models.Index(fields=['event_type'], name='sample_content_event_type_idx'),
            models.Index(fields=['created_at'], name='sample_content_created_at_idx'),
        ]