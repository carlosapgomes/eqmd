from django.db import models
from django.utils import timezone
from apps.events.models import Event
from apps.drugtemplates.models import *


def get_current_date():
    """Return current date for prescription_date default."""
    return timezone.now().date()


class OutpatientPrescription(Event):
    """
    Outpatient Prescription model that extends the base Event model.
    Used for medical outpatient prescriptions.
    """

    STATUS_CHOICES = (
        ("draft", "Rascunho"),
        ("finalized", "Finalizada"),
    )

    instructions = models.TextField(
        verbose_name="Instruções",
        # help_text="Instruções gerais da receita",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft", verbose_name="Status"
    )
    prescription_date = models.DateField(
        default=get_current_date, verbose_name="Data da Receita"
    )

    def save(self, *args, **kwargs):
        """Override save to set the correct event type."""
        self.event_type = Event.OUTPT_PRESCRIPTION_EVENT
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return the absolute URL for this outpatient prescription."""
        from django.urls import reverse

        return reverse(
            "outpatientprescriptions:outpatientprescription_detail",
            kwargs={"pk": self.pk},
        )

    def get_edit_url(self):
        """Return the edit URL for this outpatient prescription."""
        from django.urls import reverse

        return reverse(
            "outpatientprescriptions:outpatientprescription_update",
            kwargs={"pk": self.pk},
        )

    def copy_from_prescription_template(self, prescription_template):
        """
        Copy data from a PrescriptionTemplate instance into this OutpatientPrescription.
        This creates independent PrescriptionItem instances with copied data.
        """
        # Import here to avoid circular import
        from apps.drugtemplates.models import PrescriptionTemplateItem

        # Clear existing items
        self.items.all().delete()

        # Copy items from template
        template_items = prescription_template.items.all().order_by("order")
        for template_item in template_items:
            prescription_item = PrescriptionItem(
                prescription=self,
                drug_name=template_item.drug_name,
                presentation=template_item.presentation,
                usage_instructions=template_item.usage_instructions,
                quantity=template_item.quantity,
                order=template_item.order,
            )
            prescription_item.save()

    def __str__(self):
        """String representation of the outpatient prescription."""
        return f"Receita - {self.patient.name} - {self.prescription_date.strftime('%d/%m/%Y')}"

    class Meta:
        verbose_name = "Receita Ambulatorial"
        verbose_name_plural = "Receitas Ambulatoriais"
        ordering = ["-prescription_date", "-event_datetime"]


class PrescriptionItem(models.Model):
    """
    Individual prescription item with copied drug data.
    Each item represents a medication prescribed in an OutpatientPrescription.
    """

    prescription = models.ForeignKey(
        OutpatientPrescription,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Receita",
    )
    drug_name = models.CharField(max_length=200, verbose_name="Nome do Medicamento")
    presentation = models.CharField(max_length=300, verbose_name="Apresentação")
    usage_instructions = models.TextField(verbose_name="Instruções de Uso")
    quantity = models.CharField(max_length=100, verbose_name="Quantidade")
    order = models.PositiveIntegerField(
        verbose_name="Ordem", help_text="Ordem de exibição do item na receita"
    )
    source_template = models.ForeignKey(
        "drugtemplates.DrugTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Template Origem",
        help_text="Template de medicamento usado como base para este item",
    )

    def copy_from_drug_template(self, drug_template):
        """
        Copy data from a DrugTemplate instance into this PrescriptionItem.
        This ensures data independence from templates.
        """
        self.drug_name = drug_template.name
        self.presentation = drug_template.presentation
        self.usage_instructions = drug_template.usage_instructions
        self.source_template = drug_template

    def save(self, *args, **kwargs):
        """Override save to increment template usage count when template is used."""
        # Check if this is a new item with a source template
        is_new = self.pk is None

        if is_new and self.source_template:
            # Increment the usage count of the source template
            from django.db.models import F

            self.source_template.__class__.objects.filter(
                pk=self.source_template.pk
            ).update(usage_count=F("usage_count") + 1)

        super().save(*args, **kwargs)

    def __str__(self):
        """String representation of the prescription item."""
        return f"{self.drug_name} - {self.presentation}"

    class Meta:
        verbose_name = "Item da Receita"
        verbose_name_plural = "Itens da Receita"
        ordering = ["order"]
