import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords

from .services.renderer import validate_template_placeholders


class ReportTemplate(models.Model):
    """
    Model for storing report templates with markdown and placeholders.

    Templates support server-side rendering of placeholders and strict
    validation of allowed placeholders.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Name")
    markdown_body = models.TextField(verbose_name="Markdown Body")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_public = models.BooleanField(default=False, verbose_name="Public")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="report_templates_created",
        verbose_name="Created By",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="report_templates_updated",
        verbose_name="Updated By",
        null=True,
        blank=True,
    )

    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
    )

    def clean(self):
        """Validate template placeholders."""
        super().clean()
        errors = validate_template_placeholders(self.markdown_body)
        if errors:
            raise ValidationError({"markdown_body": errors})

    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Return template name as string representation."""
        return self.name

    class Meta:
        verbose_name = "Report Template"
        verbose_name_plural = "Report Templates"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active"], name="report_template_active_idx"),
            models.Index(fields=["is_public"], name="report_template_public_idx"),
        ]
