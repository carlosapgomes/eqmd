import uuid
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone


class AllowedTag(models.Model):
    """Model representing allowed tags that can be assigned to patients"""

    name = models.CharField(max_length=100, unique=True, verbose_name="Nome")
    description = models.TextField(blank=True, verbose_name="Descrição")
    color = models.CharField(
        max_length=7,
        default="#007bff",
        help_text="Cor em formato hexadecimal (ex: #007bff)",
        verbose_name="Cor",
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Tag Permitida"
        verbose_name_plural = "Tags Permitidas"

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Model representing a tag instance assigned to a patient"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    allowed_tag = models.ForeignKey(
        AllowedTag,
        on_delete=models.CASCADE,
        related_name="tag_instances",
        verbose_name="Tag Permitida",
    )
    notes = models.TextField(blank=True, verbose_name="Notas")

    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self):
        return f"{self.allowed_tag.name}"

    @property
    def name(self):
        return self.allowed_tag.name

    @property
    def color(self):
        return self.allowed_tag.color


class Patient(models.Model):
    """Model representing a patient in the system"""

    class Status(models.IntegerChoices):
        OUTPATIENT = 1, "Ambulatorial"
        INPATIENT = 2, "Internado"
        EMERGENCY = 3, "Emergência"
        DISCHARGED = 4, "Alta"
        TRANSFERRED = 5, "Transferido"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nome Completo")
    birthday = models.DateField(verbose_name="Data de Nascimento")
    healthcard_number = models.CharField(
        max_length=30, blank=True, verbose_name="Número do Cartão de Saúde"
    )
    id_number = models.CharField(
        max_length=30, blank=True, verbose_name="Número de Identidade"
    )
    fiscal_number = models.CharField(
        max_length=30, blank=True, verbose_name="Número Fiscal"
    )
    phone = models.CharField(max_length=30, blank=True, verbose_name="Telefone")

    # Address fields
    address = models.CharField(max_length=255, blank=True, verbose_name="Endereço")
    city = models.CharField(max_length=100, blank=True, verbose_name="Cidade")
    state = models.CharField(
        max_length=100, blank=True, verbose_name="Estado/Província"
    )
    zip_code = models.CharField(max_length=20, blank=True, verbose_name="Código Postal")

    # Hospital status
    status = models.IntegerField(
        choices=Status.choices, default=Status.OUTPATIENT, verbose_name="Status"
    )
    bed = models.CharField(max_length=20, blank=True, verbose_name="Leito/Cama")
    last_admission_date = models.DateField(
        null=True, blank=True, verbose_name="Data da Última Admissão"
    )
    last_discharge_date = models.DateField(
        null=True, blank=True, verbose_name="Data da Última Alta"
    )

    # Tags relationship
    tags = models.ManyToManyField(
        Tag, blank=True, related_name="patients", verbose_name="Tags"
    )

    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("patients:patient_detail", kwargs={"pk": self.pk})


    def clean(self):
        """Validate patient data"""
        super().clean()

    def save(self, *args, **kwargs):
        """Override save to handle status change logic"""
        # Store previous status to detect changes
        previous_status = None
        if self.pk:
            try:
                previous_instance = Patient.objects.get(pk=self.pk)
                previous_status = previous_instance.status
            except Patient.DoesNotExist:
                pass

        # Update admission/discharge dates
        if previous_status is not None and previous_status != self.status:
            self._update_admission_discharge_dates(previous_status)

        # Run validation
        self.full_clean()
        
        super().save(*args, **kwargs)


    def _update_admission_discharge_dates(self, previous_status):
        """Update admission and discharge dates based on status changes"""
        current_date = timezone.now().date()
        
        # Set admission date when moving to inpatient/emergency
        if (self.status in [self.Status.INPATIENT, self.Status.EMERGENCY] and 
            previous_status not in [self.Status.INPATIENT, self.Status.EMERGENCY, self.Status.TRANSFERRED]):
            self.last_admission_date = current_date
            
        # Set discharge date when moving to discharged
        if self.status == self.Status.DISCHARGED and previous_status != self.Status.DISCHARGED:
            self.last_discharge_date = current_date


