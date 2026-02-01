import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.events.models import Event

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
        errors = validate_template_placeholders(
            self.markdown_body,
            require_required=self._state.adding,
        )
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


class Report(Event):
    """
    Report model extending Event for storing generated reports.

    Reports are created from templates with rendered placeholders and
    can be edited within a 24-hour window.
    """

    content = models.TextField(verbose_name="Content")
    document_date = models.DateField(verbose_name="Document Date")
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Title",
        help_text="Optional title for the report",
    )
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
        verbose_name="Template",
        help_text="Template used to create this report (null if manual creation)",
    )

    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
    )

    @property
    def can_be_edited(self):
        """
        Check if report is within edit window (24 hours).

        Override Event's can_be_edited to use event_datetime instead of created_at,
        since event_datetime is what we control for Reports.
        """
        if not self.event_datetime:
            return False
        from datetime import timedelta
        from django.utils import timezone

        edit_deadline = self.event_datetime + timedelta(hours=24)
        return timezone.now() <= edit_deadline

    def save(self, *args, **kwargs):
        """Override save to set event_type to REPORT_EVENT."""
        if not self.event_type:
            self.event_type = Event.REPORT_EVENT
        if not self.event_datetime:
            self.event_datetime = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return the absolute URL for this report."""
        from django.urls import reverse

        return reverse("reports:report_detail", kwargs={"pk": self.pk})

    def get_edit_url(self):
        """Return the URL for editing this report."""
        from django.urls import reverse

        return reverse("reports:report_update", kwargs={"pk": self.pk})

    def __str__(self):
        """Return description as string representation."""
        return str(self.description)

    class Meta:
        verbose_name = "Report"
        verbose_name_plural = "Reports"
        ordering = ["-event_datetime"]
