import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.events.models import Event
from .services.renderer import validate_template_placeholders
from .utils import get_consent_upload_path, normalize_filename


class ConsentTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nome")
    markdown_body = models.TextField(verbose_name="Markdown do Termo")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="consent_templates_created",
        verbose_name="Criado por",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="consent_templates_updated",
        verbose_name="Atualizado por",
        null=True,
        blank=True,
    )

    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
    )

    def clean(self):
        super().clean()
        validate_template_placeholders(self.markdown_body)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Template de Consentimento"
        verbose_name_plural = "Templates de Consentimento"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active"], name="consent_template_active_idx"),
        ]


class ConsentForm(Event):
    template = models.ForeignKey(
        ConsentTemplate,
        on_delete=models.PROTECT,
        related_name="consent_forms",
        verbose_name="Template",
    )
    document_date = models.DateField(verbose_name="Data do Documento")
    procedure_description = models.TextField(verbose_name="Descrição do Procedimento")
    rendered_markdown = models.TextField(verbose_name="Markdown Renderizado")
    rendered_at = models.DateTimeField(verbose_name="Renderizado em")

    def save(self, *args, **kwargs):
        if not self.event_type:
            self.event_type = Event.CONSENT_FORM_EVENT
        if not self.event_datetime:
            self.event_datetime = timezone.now()

        if self.pk:
            original = ConsentForm.objects.filter(pk=self.pk).values_list(
                "rendered_markdown", flat=True
            ).first()
            if original is not None and original != self.rendered_markdown:
                raise ValidationError("Rendered markdown is immutable")

        if not self.description:
            template_name = self.template.name if self.template_id else "Consentimento"
            self.description = f"Termo de Consentimento - {template_name}"

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("consentforms:consentform_detail", kwargs={"pk": self.pk})

    def get_edit_url(self):
        from django.urls import reverse
        return reverse("consentforms:consentform_update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        from django.urls import reverse
        return reverse("consentforms:consentform_delete", kwargs={"pk": self.pk})

    @property
    def content(self):
        return self.rendered_markdown

    def __str__(self):
        return f"Consentimento - {self.patient.name} - {self.document_date.strftime('%d/%m/%Y')}"

    class Meta:
        verbose_name = "Termo de Consentimento"
        verbose_name_plural = "Termos de Consentimento"
        ordering = ["-event_datetime"]


class ConsentAttachment(models.Model):
    FILE_TYPE_IMAGE = "image"
    FILE_TYPE_PDF = "pdf"

    FILE_TYPE_CHOICES = (
        (FILE_TYPE_IMAGE, "Imagem"),
        (FILE_TYPE_PDF, "PDF"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consent_form = models.ForeignKey(
        ConsentForm,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Termo de Consentimento",
    )
    file = models.FileField(upload_to=get_consent_upload_path, verbose_name="Arquivo")
    original_filename = models.CharField(max_length=255, verbose_name="Nome Original")
    file_size = models.PositiveIntegerField(verbose_name="Tamanho do Arquivo")
    mime_type = models.CharField(max_length=100, verbose_name="Tipo MIME")
    file_type = models.CharField(
        max_length=10,
        choices=FILE_TYPE_CHOICES,
        verbose_name="Tipo de Arquivo",
    )
    order = models.PositiveSmallIntegerField(default=1, verbose_name="Ordem")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    def save(self, *args, **kwargs):
        if self.file and not self.original_filename:
            self.original_filename = normalize_filename(self.file.name)
        if self.file and not self.file_size:
            self.file_size = self.file.size
        if self.file and not self.mime_type:
            self.mime_type = getattr(self.file, "content_type", "")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.original_filename} ({self.get_file_type_display()})"

    class Meta:
        verbose_name = "Anexo de Consentimento"
        verbose_name_plural = "Anexos de Consentimento"
        ordering = ["order", "created_at"]
