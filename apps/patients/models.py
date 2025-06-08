import uuid
from django.db import models
from django.conf import settings


class AllowedTag(models.Model):
    """Model representing allowed tags that can be assigned to patients"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Nome")
    description = models.TextField(blank=True, verbose_name="Descrição")
    color = models.CharField(
        max_length=7, 
        default="#007bff", 
        help_text="Color in hex format (e.g., #007bff)",
        verbose_name="Cor"
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    
    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+",
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
        verbose_name="Tag Permitida"
    )
    notes = models.TextField(blank=True, verbose_name="Notas")
    
    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+",
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
        OUTPATIENT = 1, "Outpatient"
        INPATIENT = 2, "Inpatient"
        EMERGENCY = 3, "Emergency"
        DISCHARGED = 4, "Discharged"
        TRANSFERRED = 5, "Transferred"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nome Completo")
    birthday = models.DateField(verbose_name="Data de Nascimento")
    healthcard_number = models.CharField(max_length=30, blank=True, verbose_name="Número do Cartão de Saúde")
    id_number = models.CharField(max_length=30, blank=True, verbose_name="Número de Identidade")
    fiscal_number = models.CharField(max_length=30, blank=True, verbose_name="Número Fiscal")
    phone = models.CharField(max_length=30, blank=True, verbose_name="Telefone")

    # Address fields
    address = models.CharField(max_length=255, blank=True, verbose_name="Endereço")
    city = models.CharField(max_length=100, blank=True, verbose_name="Cidade")
    state = models.CharField(max_length=100, blank=True, verbose_name="Estado/Província")
    zip_code = models.CharField(max_length=20, blank=True, verbose_name="Código Postal")

    # Hospital status
    status = models.IntegerField(choices=Status.choices, default=Status.OUTPATIENT, verbose_name="Status")
    current_hospital = models.ForeignKey(
        "hospitals.Hospital",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_patients",
        verbose_name="Hospital Atual",
    )
    bed = models.CharField(max_length=20, blank=True, verbose_name="Leito/Cama")
    last_admission_date = models.DateField(null=True, blank=True, verbose_name="Data da Última Admissão")
    last_discharge_date = models.DateField(null=True, blank=True, verbose_name="Data da Última Alta")
    
    # Tags relationship
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="patients",
        verbose_name="Tags"
    )


    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def __str__(self):
        return self.name

class PatientHospitalRecord(models.Model):
    """Model representing a patient's record at a specific hospital"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="hospital_records",
        verbose_name="Paciente",
    )
    hospital = models.ForeignKey(
        "hospitals.Hospital",
        on_delete=models.PROTECT,
        related_name="patient_records",
        verbose_name="Hospital",
    )
    record_number = models.CharField(max_length=30, verbose_name="Número de Registro")
    first_admission_date = models.DateField(
        null=True, blank=True, verbose_name="Data da Primeira Admissão"
    )
    last_admission_date = models.DateField(
        null=True, blank=True, verbose_name="Data da Última Admissão"
    )
    last_discharge_date = models.DateField(
        null=True, blank=True, verbose_name="Data da Última Alta"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        unique_together = ["patient", "hospital"]
        verbose_name = "Hospital Record"
        verbose_name_plural = "Hospital Records"
        indexes = [
            models.Index(fields=["patient", "hospital"]),
            models.Index(fields=["hospital", "record_number"]),
        ]

    def __str__(self):
        return f"{self.patient.name} - {self.hospital.name} ({self.record_number})"