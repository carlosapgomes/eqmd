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
    current_hospital = models.ForeignKey(
        "hospitals.Hospital",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_patients",
        verbose_name="Hospital Atual",
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

    @property
    def requires_hospital_assignment(self):
        """Check if patient status requires hospital assignment"""
        return self.status in [self.Status.INPATIENT, self.Status.EMERGENCY, self.Status.TRANSFERRED]

    @property
    def should_clear_hospital_assignment(self):
        """Check if patient status should clear hospital assignment"""
        return self.status in [self.Status.OUTPATIENT, self.Status.DISCHARGED]

    def clean(self):
        """Validate patient data including hospital assignment rules"""
        super().clean()
        
        # Validate hospital assignment based on status
        if self.requires_hospital_assignment and not self.current_hospital:
            raise ValidationError({
                'current_hospital': f'Hospital é obrigatório para pacientes com status "{self.get_status_display()}"'
            })
        
        # Clear bed assignment if no hospital
        if not self.current_hospital:
            self.bed = ""

    def save(self, *args, **kwargs):
        """Override save to handle hospital assignment logic"""
        # Store previous status to detect changes
        previous_status = None
        if self.pk:
            try:
                previous_instance = Patient.objects.get(pk=self.pk)
                previous_status = previous_instance.status
            except Patient.DoesNotExist:
                pass

        # Handle status change logic
        if previous_status is not None and previous_status != self.status:
            self._handle_status_change(previous_status)

        # Auto-clear hospital assignment for outpatients/discharged
        if self.should_clear_hospital_assignment:
            self.current_hospital = None
            self.bed = ""

        # Update admission/discharge dates
        if previous_status is not None and previous_status != self.status:
            self._update_admission_discharge_dates(previous_status)

        # Run validation
        self.full_clean()
        
        super().save(*args, **kwargs)

    def _handle_status_change(self, previous_status):
        """Handle business logic when patient status changes"""
        current_date = timezone.now().date()
        
        # Handle admission (to inpatient/emergency)
        if (previous_status in [self.Status.OUTPATIENT, self.Status.DISCHARGED] and 
            self.status in [self.Status.INPATIENT, self.Status.EMERGENCY]):
            self.last_admission_date = current_date
            
        # Handle discharge
        elif (previous_status in [self.Status.INPATIENT, self.Status.EMERGENCY, self.Status.TRANSFERRED] and 
              self.status == self.Status.DISCHARGED):
            self.last_discharge_date = current_date

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

    def get_hospital_records(self):
        """Get all hospital records for this patient"""
        return self.hospital_records.select_related('hospital').order_by('-last_admission_date')

    def has_hospital_record_at(self, hospital):
        """Check if patient has a record at the given hospital"""
        return self.hospital_records.filter(hospital=hospital).exists()

    def is_currently_admitted(self):
        """Check if patient is currently admitted (has active hospital assignment)"""
        return self.current_hospital is not None and self.requires_hospital_assignment


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
        verbose_name = "Registro Hospitalar"
        verbose_name_plural = "Registros Hospitalares"
        indexes = [
            models.Index(fields=["patient", "hospital"]),
            models.Index(fields=["hospital", "record_number"]),
        ]

    def __str__(self):
        return f"{self.patient.name} - {self.hospital.name} ({self.record_number})"

