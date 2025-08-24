import uuid
from datetime import date
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.core.models.soft_delete import SoftDeleteModel
from .validators import (
    validate_record_number_format,
    validate_admission_datetime,
    validate_discharge_datetime,
)


class AllowedTag(SoftDeleteModel):
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

    # History tracking
    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
        cascade_delete_history=False,
    )

    class Meta:
        db_table = 'patients_allowedtag'
        ordering = ["name"]
        verbose_name = "Tag Permitida"
        verbose_name_plural = "Tags Permitidas"
        indexes = [
            models.Index(fields=['is_deleted', 'name']),
        ]

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
    patient = models.ForeignKey(
        'Patient',
        on_delete=models.CASCADE,
        related_name="patient_tags",
        verbose_name="Paciente",
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
        constraints = [
            models.UniqueConstraint(
                fields=['allowed_tag', 'patient'],
                name='unique_tag_per_patient_per_allowed_tag'
            )
        ]

    def __str__(self):
        return f"{self.allowed_tag.name}"

    @property
    def name(self):
        return self.allowed_tag.name

    @property
    def color(self):
        return self.allowed_tag.color



class Ward(models.Model):
    """Model representing hospital wards/departments"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100, 
        unique=True,
        verbose_name="Nome da Ala",
        help_text="Nome completo da ala (ex: Unidade de Terapia Intensiva)"
    )
    abbreviation = models.CharField(
        max_length=10, 
        unique=True,
        verbose_name="Sigla",
        help_text="Sigla da ala (ex: UTI, CC, PS)"
    )
    description = models.TextField(
        blank=True, 
        verbose_name="Descrição",
        help_text="Descrição detalhada da ala e suas especialidades"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Ativa",
        help_text="Indica se a ala está ativa e disponível para uso"
    )
    
    # Optional ward characteristics
    floor = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Andar",
        help_text="Andar onde a ala está localizada (ex: 2º Andar, Térreo)"
    )
    capacity_estimate = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Capacidade Estimada",
        help_text="Estimativa de capacidade de leitos (informativo apenas)"
    )
    
    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="created_wards",
        verbose_name="Criado por"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="updated_wards",
        verbose_name="Atualizado por"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Ala"
        verbose_name_plural = "Alas"

    def __str__(self):
        return f"{self.abbreviation} - {self.name}"
    
    def get_current_patients_count(self):
        """Get count of patients currently in this ward"""
        return self.patients.filter(
            status__in=[Patient.Status.INPATIENT, Patient.Status.EMERGENCY]
        ).count()
    
    def get_available_beds_list(self):
        """Get list of bed identifiers currently in use in this ward"""
        return list(
            self.patients.filter(
                status__in=[Patient.Status.INPATIENT, Patient.Status.EMERGENCY]
            ).exclude(bed="").values_list("bed", flat=True).distinct()
        )


class PatientRecordNumber(models.Model):
    """Model for tracking patient record number changes with full history"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "Patient",
        on_delete=models.CASCADE,
        related_name="record_numbers",
        verbose_name="Paciente",
    )

    # Record number tracking
    record_number = models.CharField(
        max_length=50,
        verbose_name="Número do Prontuário",
        help_text="Número do prontuário do paciente no hospital",
    )
    is_current = models.BooleanField(
        default=True,
        verbose_name="Atual",
        help_text="Indica se este é o número de prontuário atual",
    )

    # Change tracking
    previous_record_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Número Anterior",
        help_text="Número de prontuário anterior (se houver)",
    )
    change_reason = models.TextField(
        blank=True,
        verbose_name="Motivo da Alteração",
        help_text="Razão para a mudança do número do prontuário",
    )
    effective_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Data de Vigência",
        help_text="Data em que o número passou a ser válido",
    )

    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_record_numbers",
        verbose_name="Criado por",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_record_numbers",
        verbose_name="Atualizado por",
    )

    class Meta:
        ordering = ["-effective_date", "-created_at"]
        verbose_name = "Número de Prontuário"
        verbose_name_plural = "Números de Prontuário"
        constraints = [
            models.UniqueConstraint(
                fields=["patient"],
                condition=models.Q(is_current=True),
                name="unique_current_record_per_patient",
            )
        ]
        indexes = [
            models.Index(fields=["patient", "is_current"]),
            models.Index(fields=["record_number"]),
            models.Index(fields=["effective_date"]),
        ]

    def __str__(self):
        status = " (Atual)" if self.is_current else ""
        return f"{self.patient.name} - {self.record_number}{status}"

    def clean(self):
        """Enhanced validation"""
        super().clean()

        # Validate record number format
        validate_record_number_format(self.record_number)

        # Validate effective date
        if self.effective_date and self.effective_date > timezone.now():
            raise ValidationError(
                {"effective_date": "Data de vigência não pode ser no futuro"}
            )

        # Validate current record uniqueness
        if self.is_current:
            existing_current = PatientRecordNumber.objects.filter(
                patient=self.patient, is_current=True
            ).exclude(pk=self.pk)

            if existing_current.exists():
                raise ValidationError(
                    {
                        "is_current": "Já existe um número de prontuário atual para este paciente"
                    }
                )


class PatientAdmission(models.Model):
    """Model for tracking patient admission and discharge events"""

    class AdmissionType(models.TextChoices):
        EMERGENCY = "emergency", "Emergência"
        SCHEDULED = "scheduled", "Programada"
        TRANSFER = "transfer", "Transferência"
        READMISSION = "readmission", "Reinternação"

    class DischargeType(models.TextChoices):
        MEDICAL = "medical", "Alta Médica"
        ADMINISTRATIVE = "administrative", "Alta Administrativa"
        TRANSFER_OUT = "transfer_out", "Transferência"
        EVASION = "evasion", "Evasão"
        DEATH = "death", "Óbito"
        REQUEST = "request", "A Pedido"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "Patient",
        on_delete=models.CASCADE,
        related_name="admissions",
        verbose_name="Paciente",
    )

    # Admission data
    admission_datetime = models.DateTimeField(
        verbose_name="Data/Hora de Admissão",
        help_text="Data e hora da admissão hospitalar",
    )
    admission_type = models.CharField(
        max_length=20,
        choices=AdmissionType.choices,
        default=AdmissionType.SCHEDULED,
        verbose_name="Tipo de Admissão",
    )

    # Discharge data
    discharge_datetime = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data/Hora de Alta",
        help_text="Data e hora da alta hospitalar",
    )
    discharge_type = models.CharField(
        max_length=20,
        choices=DischargeType.choices,
        blank=True,
        verbose_name="Tipo de Alta",
    )

    # Location tracking
    initial_bed = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Leito Inicial",
        help_text="Leito/quarto inicial da internação",
    )
    final_bed = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Leito Final",
        help_text="Último leito/quarto antes da alta",
    )
    ward = models.ForeignKey(
        Ward, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="admissions",
        verbose_name="Ala",
        help_text="Ala onde a internação ocorreu"
    )

    # Clinical data
    admission_diagnosis = models.TextField(
        blank=True,
        verbose_name="Diagnóstico de Admissão",
        help_text="Diagnóstico principal na admissão",
    )
    discharge_diagnosis = models.TextField(
        blank=True,
        verbose_name="Diagnóstico de Alta",
        help_text="Diagnóstico principal na alta",
    )

    # Duration tracking (denormalized for performance)
    stay_duration_hours = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Duração da Internação (horas)",
        help_text="Duração total da internação em horas",
    )
    stay_duration_days = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Duração da Internação (dias)",
        help_text="Duração total da internação em dias",
    )

    # Status tracking
    is_active = models.BooleanField(
        default=True,
        verbose_name="Internação Ativa",
        help_text="Indica se a internação está ativa (não teve alta)",
    )

    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_admissions",
        verbose_name="Criado por",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_admissions",
        verbose_name="Atualizado por",
    )

    class Meta:
        ordering = ["-admission_datetime"]
        verbose_name = "Internação"
        verbose_name_plural = "Internações"
        constraints = [
            models.UniqueConstraint(
                fields=["patient"],
                condition=models.Q(is_active=True),
                name="unique_active_admission_per_patient",
            ),
            models.CheckConstraint(
                check=models.Q(discharge_datetime__isnull=True)
                | models.Q(discharge_datetime__gte=models.F("admission_datetime")),
                name="discharge_after_admission",
            ),
        ]
        indexes = [
            models.Index(fields=["patient", "is_active"]),
            models.Index(fields=["admission_datetime"]),
            models.Index(fields=["discharge_datetime"]),
            models.Index(fields=["admission_type"]),
        ]

    def __str__(self):
        status = "Ativa" if self.is_active else "Finalizada"
        duration = f" ({self.stay_duration_days}d)" if self.stay_duration_days else ""
        return f"{self.patient.name} - {self.admission_datetime.strftime('%d/%m/%Y')} - {status}{duration}"

    def clean(self):
        """Enhanced validation"""
        super().clean()

        # Validate admission datetime
        validate_admission_datetime(self.admission_datetime)

        # Validate discharge datetime
        if self.discharge_datetime:
            validate_discharge_datetime(
                self.discharge_datetime, self.admission_datetime
            )

        # Validate discharge type when discharged
        if self.discharge_datetime and not self.discharge_type:
            raise ValidationError(
                {"discharge_type": "Tipo de alta é obrigatório quando há data de alta"}
            )

        # Validate active status consistency
        if self.discharge_datetime and self.is_active:
            raise ValidationError(
                {"is_active": "Internação não pode estar ativa se há data de alta"}
            )

        # Validate bed information
        if not self.initial_bed and not self.final_bed:
            raise ValidationError(
                "Pelo menos um leito (inicial ou final) deve ser informado"
            )

    def save(self, *args, **kwargs):
        """Override save to calculate duration and update status"""
        # Calculate duration if discharged
        if self.discharge_datetime and self.admission_datetime:
            duration = self.discharge_datetime - self.admission_datetime
            self.stay_duration_hours = int(duration.total_seconds() / 3600)
            self.stay_duration_days = int(duration.days)
            self.is_active = False
        elif not self.discharge_datetime:
            self.stay_duration_hours = None
            self.stay_duration_days = None
            self.is_active = True

        super().save(*args, **kwargs)

    def calculate_current_duration(self):
        """Calculate current stay duration for active admissions"""
        if self.is_active and self.admission_datetime:
            duration = timezone.now() - self.admission_datetime
            return {
                "total_seconds": int(duration.total_seconds()),
                "hours": int(duration.total_seconds() / 3600),
                "days": duration.days,
                "weeks": duration.days // 7,
            }
        return None

    @property
    def duration_display(self):
        """Get formatted duration display for templates"""
        if self.is_active and self.admission_datetime:
            # For active admissions, calculate current duration
            duration = timezone.now() - self.admission_datetime
            days = duration.days
            hours = int(duration.total_seconds() / 3600) % 24
            
            if days > 0:
                return f"{days}d {hours}h"
            else:
                return f"{hours}h"
        elif self.stay_duration_days is not None:
            # For completed admissions, use stored duration
            if self.stay_duration_days > 0:
                hours = (self.stay_duration_hours or 0) % 24
                return f"{self.stay_duration_days}d {hours}h"
            else:
                return f"{self.stay_duration_hours or 0}h"
        else:
            return "-"

    def can_discharge(self):
        """Check if admission can be discharged"""
        return self.is_active and not self.discharge_datetime

    def get_bed_changes(self):
        """Get history of bed changes during this admission"""
        # This could be extended to track bed changes via a separate model
        beds = []
        if self.initial_bed:
            beds.append(("admission", self.initial_bed, self.admission_datetime))
        if (
            self.final_bed
            and self.final_bed != self.initial_bed
            and self.discharge_datetime
        ):
            beds.append(("discharge", self.final_bed, self.discharge_datetime))
        return beds

    def update_discharge_info(self, discharge_datetime, discharge_type, user, **kwargs):
        """Update discharge information with validation"""
        if not self.is_active:
            raise ValidationError("Esta internação já foi finalizada")

        if discharge_datetime <= self.admission_datetime:
            raise ValidationError("Data de alta deve ser posterior à data de admissão")

        self.discharge_datetime = discharge_datetime
        self.discharge_type = discharge_type
        self.final_bed = kwargs.get("final_bed", self.initial_bed)
        self.discharge_diagnosis = kwargs.get("discharge_diagnosis", "")
        self.updated_by = user

        # save() will trigger duration calculation and status update
        self.save()

        # Update patient denormalized fields
        self.patient.refresh_denormalized_fields()

        return self

    def cancel_discharge(self, user):
        """Cancel discharge and reactivate admission"""
        if self.is_active:
            raise ValidationError("Internação já está ativa")

        self.discharge_datetime = None
        self.discharge_type = ""
        self.stay_duration_hours = None
        self.stay_duration_days = None
        self.is_active = True
        self.updated_by = user
        self.save()

        # Update patient status
        self.patient.status = self.patient.Status.INPATIENT
        self.patient.current_admission_id = self.id
        self.patient.bed = self.final_bed or self.initial_bed
        self.patient.updated_by = user
        self.patient.save(
            update_fields=[
                "status",
                "current_admission_id",
                "bed",
                "updated_by",
                "updated_at",
            ]
        )

        return self


class Patient(SoftDeleteModel):
    """Model representing a patient in the system"""

    class Status(models.IntegerChoices):
        OUTPATIENT = 1, "Ambulatorial"
        INPATIENT = 2, "Internado"
        EMERGENCY = 3, "Emergência"
        DISCHARGED = 4, "Alta"
        TRANSFERRED = 5, "Transferido"
        DECEASED = 6, "Óbito"

    class GenderChoices(models.TextChoices):
        MALE = 'M', 'Masculino'
        FEMALE = 'F', 'Feminino'
        OTHER = 'O', 'Outro'
        NOT_INFORMED = 'N', 'Não Informado'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nome Completo")
    birthday = models.DateField(verbose_name="Data de Nascimento")
    gender = models.CharField(
        max_length=1,
        choices=GenderChoices.choices,
        default=GenderChoices.NOT_INFORMED,
        verbose_name="Sexo"
    )
    healthcard_number = models.CharField(
        max_length=60, blank=True, verbose_name="Número do Cartão de Saúde"
    )
    id_number = models.CharField(
        max_length=30, blank=True, verbose_name="Número de Identidade"
    )
    fiscal_number = models.CharField(
        max_length=30, blank=True, verbose_name="Número Fiscal"
    )
    phone = models.CharField(max_length=100, blank=True, verbose_name="Telefone")

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
    ward = models.ForeignKey(
        Ward, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="patients",
        verbose_name="Ala",
        help_text="Ala onde o paciente está localizado"
    )
    last_admission_date = models.DateField(
        null=True, blank=True, verbose_name="Data da Última Admissão"
    )
    last_discharge_date = models.DateField(
        null=True, blank=True, verbose_name="Data da Última Alta"
    )

    # Denormalized record number for performance
    current_record_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Número do Prontuário Atual",
        help_text="Número atual do prontuário (denormalizado para performance)",
    )

    # Enhanced admission/discharge tracking (keep existing fields, add new ones)
    current_admission_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name="ID da Internação Atual",
        help_text="ID da internação ativa (denormalizado para performance)",
    )
    total_admissions_count = models.IntegerField(
        default=0,
        verbose_name="Total de Internações",
        help_text="Número total de internações do paciente",
    )
    total_inpatient_days = models.IntegerField(
        default=0,
        verbose_name="Total de Dias Internado",
        help_text="Total de dias internado ao longo de todas as internações",
    )

    # Tags are now accessed via reverse relationship: patient.patient_tags.all()

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

    # History tracking
    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True),
        cascade_delete_history=False,
    )

    class Meta:
        db_table = 'patients_patient'
        ordering = ["-created_at"]
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        indexes = [
            models.Index(fields=['is_deleted', 'status']),
            models.Index(fields=['is_deleted', 'created_at']),
        ]

    def __str__(self):
        deleted_indicator = " [DELETED]" if self.is_deleted else ""
        return f"{self.name}{deleted_indicator}"

    def get_absolute_url(self):
        return reverse("patients:patient_detail", kwargs={"pk": self.pk})

    @property
    def age(self):
        """Calculate current age in years"""
        today = date.today()
        return today.year - self.birthday.year - ((today.month, today.day) < (self.birthday.month, self.birthday.day))

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
        if self.status in [
            self.Status.INPATIENT,
            self.Status.EMERGENCY,
        ] and previous_status not in [
            self.Status.INPATIENT,
            self.Status.EMERGENCY,
            self.Status.TRANSFERRED,
        ]:
            self.last_admission_date = current_date

        # Set discharge date when moving to discharged
        if (
            self.status == self.Status.DISCHARGED
            and previous_status != self.Status.DISCHARGED
        ):
            self.last_discharge_date = current_date

    def get_current_record_number(self):
        """Get current record number from related model"""
        current_record = self.record_numbers.filter(is_current=True).first()
        return (
            current_record.record_number
            if current_record
            else self.current_record_number
        )

    @property
    def current_record_number_obj(self):
        """Get current record number object from related model"""
        return self.record_numbers.filter(is_current=True).first()

    def get_current_admission(self):
        """Get current active admission"""
        if self.current_admission_id:
            return self.admissions.filter(
                id=self.current_admission_id, is_active=True
            ).first()
        return self.admissions.filter(is_active=True).first()

    def update_ward_from_admission(self):
        """Update patient ward from current admission"""
        current_admission = self.get_current_admission()
        if current_admission and current_admission.ward:
            self.ward = current_admission.ward
            self.save(update_fields=["ward", "updated_at"])

    def get_ward_display(self):
        """Get formatted ward display for templates"""
        if self.ward:
            return f"{self.ward.abbreviation} - {self.ward.name}"
        return "Sem ala definida"

    def update_denormalized_fields(self):
        """Update denormalized fields from related models"""
        # Update current record number
        current_record = self.record_numbers.filter(is_current=True).first()
        if current_record:
            self.current_record_number = current_record.record_number

        # Update admission statistics
        admissions = self.admissions.all()
        self.total_admissions_count = admissions.count()
        self.total_inpatient_days = sum(
            admission.stay_duration_days or 0
            for admission in admissions.filter(stay_duration_days__isnull=False)
        )

        # Update current admission
        current_admission = admissions.filter(is_active=True).first()
        self.current_admission_id = current_admission.id if current_admission else None

        # Update status based on current admission
        if current_admission:
            self.status = self.Status.INPATIENT
        elif not self.status == self.Status.DISCHARGED:
            self.status = self.Status.OUTPATIENT

    def is_currently_admitted(self):
        """Check if patient is currently admitted"""
        return (
            self.current_admission_id is not None
            and self.get_current_admission() is not None
        )

    def update_current_record_number(
        self, record_number, user, reason="", effective_date=None
    ):
        """Update patient's current record number and create history entry"""
        if effective_date is None:
            effective_date = timezone.now()

        # Get current record for history
        current_record = self.record_numbers.filter(is_current=True).first()
        previous_number = current_record.record_number if current_record else ""

        # Deactivate current record
        if current_record:
            current_record.is_current = False
            current_record.updated_by = user
            current_record.save()

        # Create new current record
        new_record = PatientRecordNumber.objects.create(
            patient=self,
            record_number=record_number,
            previous_record_number=previous_number,
            change_reason=reason,
            effective_date=effective_date,
            is_current=True,
            created_by=user,
            updated_by=user,
        )

        # Update denormalized field
        self.current_record_number = record_number
        self.updated_by = user
        self.save(update_fields=["current_record_number", "updated_by", "updated_at"])

        return new_record

    def admit_patient(self, admission_datetime, admission_type, user, **kwargs):
        """Admit patient and create admission record"""
        # Check if patient is already admitted
        if self.is_currently_admitted():
            raise ValidationError("Paciente já está internado")

        # Create admission record
        admission = PatientAdmission.objects.create(
            patient=self,
            admission_datetime=admission_datetime,
            admission_type=admission_type,
            initial_bed=kwargs.get("initial_bed", ""),
            ward=kwargs.get("ward"),
            admission_diagnosis=kwargs.get("admission_diagnosis", ""),
            created_by=user,
            updated_by=user,
        )

        # Update patient status and denormalized fields
        self.status = self.Status.INPATIENT
        self.current_admission_id = admission.id
        self.ward = admission.ward
        self.last_admission_date = (
            admission_datetime.date()
            if isinstance(admission_datetime, timezone.datetime)
            else admission_datetime
        )
        self.bed = admission.initial_bed
        self.total_admissions_count = self.admissions.count()
        self.updated_by = user
        self.save(
            update_fields=[
                "status",
                "current_admission_id",
                "ward",
                "last_admission_date",
                "bed",
                "total_admissions_count",
                "updated_by",
                "updated_at",
            ]
        )

        return admission

    def discharge_patient(self, discharge_datetime, discharge_type, user, **kwargs):
        """Discharge patient and update admission record"""
        import logging

        logger = logging.getLogger(__name__)

        logger.info(
            f"discharge_patient: Starting discharge for patient {self.name} (ID: {self.pk})"
        )
        logger.info(f"discharge_patient: discharge_type={discharge_type}, user={user}")

        current_admission = self.get_current_admission()
        logger.info(f"discharge_patient: current_admission={current_admission}")

        if not current_admission:
            logger.error("discharge_patient: No current admission found")
            raise ValidationError("Paciente não está internado")

        logger.info("discharge_patient: Updating admission record")
        # Update admission record
        current_admission.discharge_datetime = discharge_datetime
        current_admission.discharge_type = discharge_type
        current_admission.final_bed = kwargs.get(
            "final_bed", current_admission.initial_bed
        )
        current_admission.discharge_diagnosis = kwargs.get("discharge_diagnosis", "")
        current_admission.updated_by = user
        current_admission.save()  # This will trigger duration calculation and is_active=False
        logger.info(
            f"discharge_patient: Admission record saved. is_active={current_admission.is_active}"
        )

        logger.info(
            "discharge_patient: Updating patient status and denormalized fields"
        )
        # Update patient status and denormalized fields
        self.status = self.Status.DISCHARGED
        self.current_admission_id = None
        self.last_discharge_date = (
            discharge_datetime.date()
            if isinstance(discharge_datetime, timezone.datetime)
            else discharge_datetime
        )
        self.bed = ""

        # Recalculate total inpatient days
        self.total_inpatient_days = sum(
            admission.stay_duration_days or 0
            for admission in self.admissions.filter(stay_duration_days__isnull=False)
        )

        self.updated_by = user
        self.save(
            update_fields=[
                "status",
                "current_admission_id",
                "last_discharge_date",
                "bed",
                "total_inpatient_days",
                "updated_by",
                "updated_at",
            ]
        )
        logger.info(f"discharge_patient: Patient status updated to {self.status}")

        return current_admission

    def get_admission_history(self):
        """Get ordered admission history"""
        return self.admissions.order_by("-admission_datetime")

    def get_record_number_history(self):
        """Get ordered record number history"""
        return self.record_numbers.order_by("-effective_date")

    def calculate_total_hospital_days(self):
        """Calculate total days spent in hospital across all admissions"""
        completed_admissions = self.admissions.filter(
            discharge_datetime__isnull=False, stay_duration_days__isnull=False
        )
        return sum(admission.stay_duration_days for admission in completed_admissions)

    def get_current_stay_duration(self):
        """Get current stay duration if patient is admitted"""
        current_admission = self.get_current_admission()
        return (
            current_admission.calculate_current_duration()
            if current_admission
            else None
        )

    def refresh_denormalized_fields(self):
        """Refresh all denormalized fields from source data"""
        # Update current record number
        current_record = self.record_numbers.filter(is_current=True).first()
        self.current_record_number = (
            current_record.record_number if current_record else ""
        )

        # Update admission statistics
        admissions = self.admissions.all()
        self.total_admissions_count = admissions.count()
        self.total_inpatient_days = self.calculate_total_hospital_days()

        # Update current admission
        current_admission = admissions.filter(is_active=True).first()
        self.current_admission_id = current_admission.id if current_admission else None

        # Update status based on current state
        if current_admission:
            self.status = self.Status.INPATIENT
            self.bed = current_admission.initial_bed or current_admission.final_bed
        elif self.status == self.Status.INPATIENT:
            # Patient was marked as inpatient but has no active admission
            self.status = self.Status.OUTPATIENT
            self.bed = ""

        self.save(
            update_fields=[
                "current_record_number",
                "total_admissions_count",
                "total_inpatient_days",
                "current_admission_id",
                "status",
                "bed",
                "updated_at",
            ]
        )
