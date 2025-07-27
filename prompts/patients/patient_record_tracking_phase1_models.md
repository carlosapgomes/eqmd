# Phase 1: Core Models and Database Schema

## Overview

Create the foundational models for patient record tracking with proper relationships, constraints, and denormalized fields for performance. Since this is a greenfield project, we'll add the models directly without migration concerns.

## Step-by-Step Implementation

### Step 1.1: Create PatientRecordNumber Model

**File**: `apps/patients/models.py`

```python
class PatientRecordNumber(models.Model):
    """Model for tracking patient record number changes with full history"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'Patient', 
        on_delete=models.CASCADE, 
        related_name="record_numbers",
        verbose_name="Paciente"
    )
    
    # Record number tracking
    record_number = models.CharField(
        max_length=50, 
        verbose_name="Número do Prontuário",
        help_text="Número do prontuário do paciente no hospital"
    )
    is_current = models.BooleanField(
        default=True, 
        verbose_name="Atual",
        help_text="Indica se este é o número de prontuário atual"
    )
    
    # Change tracking
    previous_record_number = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name="Número Anterior",
        help_text="Número de prontuário anterior (se houver)"
    )
    change_reason = models.TextField(
        blank=True, 
        verbose_name="Motivo da Alteração",
        help_text="Razão para a mudança do número do prontuário"
    )
    effective_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Data de Vigência",
        help_text="Data em que o número passou a ser válido"
    )
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_record_numbers",
        verbose_name="Criado por"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_record_numbers",
        verbose_name="Atualizado por"
    )
    
    class Meta:
        ordering = ['-effective_date', '-created_at']
        verbose_name = "Número de Prontuário"
        verbose_name_plural = "Números de Prontuário"
        constraints = [
            models.UniqueConstraint(
                fields=['patient'], 
                condition=models.Q(is_current=True),
                name='unique_current_record_per_patient'
            )
        ]
        indexes = [
            models.Index(fields=['patient', 'is_current']),
            models.Index(fields=['record_number']),
            models.Index(fields=['effective_date']),
        ]
    
    def __str__(self):
        status = " (Atual)" if self.is_current else ""
        return f"{self.patient.name} - {self.record_number}{status}"
    
    def clean(self):
        """Validate record number data"""
        super().clean()
        
        # Ensure record number is not empty
        if not self.record_number or not self.record_number.strip():
            raise ValidationError({'record_number': 'Número do prontuário é obrigatório'})
        
        # Validate current record uniqueness
        if self.is_current:
            existing_current = PatientRecordNumber.objects.filter(
                patient=self.patient,
                is_current=True
            ).exclude(pk=self.pk)
            
            if existing_current.exists():
                raise ValidationError({
                    'is_current': 'Já existe um número de prontuário atual para este paciente'
                })
```

### Step 1.2: Create PatientAdmission Model

**File**: `apps/patients/models.py`

```python
class PatientAdmission(models.Model):
    """Model for tracking patient admission and discharge events"""
    
    class AdmissionType(models.TextChoices):
        EMERGENCY = 'emergency', 'Emergência'
        SCHEDULED = 'scheduled', 'Programada'
        TRANSFER = 'transfer', 'Transferência'
        READMISSION = 'readmission', 'Reinternação'
    
    class DischargeType(models.TextChoices):
        MEDICAL = 'medical', 'Alta Médica'
        ADMINISTRATIVE = 'administrative', 'Alta Administrativa'
        TRANSFER_OUT = 'transfer_out', 'Transferência'
        EVASION = 'evasion', 'Evasão'
        DEATH = 'death', 'Óbito'
        REQUEST = 'request', 'A Pedido'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'Patient',
        on_delete=models.CASCADE,
        related_name="admissions",
        verbose_name="Paciente"
    )
    
    # Admission data
    admission_datetime = models.DateTimeField(
        verbose_name="Data/Hora de Admissão",
        help_text="Data e hora da admissão hospitalar"
    )
    admission_type = models.CharField(
        max_length=20,
        choices=AdmissionType.choices,
        default=AdmissionType.SCHEDULED,
        verbose_name="Tipo de Admissão"
    )
    
    # Discharge data
    discharge_datetime = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Data/Hora de Alta",
        help_text="Data e hora da alta hospitalar"
    )
    discharge_type = models.CharField(
        max_length=20,
        choices=DischargeType.choices,
        blank=True,
        verbose_name="Tipo de Alta"
    )
    
    # Location tracking
    initial_bed = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="Leito Inicial",
        help_text="Leito/quarto inicial da internação"
    )
    final_bed = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="Leito Final",
        help_text="Último leito/quarto antes da alta"
    )
    
    # Clinical data
    admission_diagnosis = models.TextField(
        blank=True,
        verbose_name="Diagnóstico de Admissão",
        help_text="Diagnóstico principal na admissão"
    )
    discharge_diagnosis = models.TextField(
        blank=True,
        verbose_name="Diagnóstico de Alta",
        help_text="Diagnóstico principal na alta"
    )
    
    # Duration tracking (denormalized for performance)
    stay_duration_hours = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="Duração da Internação (horas)",
        help_text="Duração total da internação em horas"
    )
    stay_duration_days = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="Duração da Internação (dias)",
        help_text="Duração total da internação em dias"
    )
    
    # Status tracking
    is_active = models.BooleanField(
        default=True,
        verbose_name="Internação Ativa",
        help_text="Indica se a internação está ativa (não teve alta)"
    )
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_admissions",
        verbose_name="Criado por"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_admissions",
        verbose_name="Atualizado por"
    )
    
    class Meta:
        ordering = ['-admission_datetime']
        verbose_name = "Internação"
        verbose_name_plural = "Internações"
        constraints = [
            models.UniqueConstraint(
                fields=['patient'], 
                condition=models.Q(is_active=True),
                name='unique_active_admission_per_patient'
            ),
            models.CheckConstraint(
                check=models.Q(discharge_datetime__isnull=True) | 
                      models.Q(discharge_datetime__gte=models.F('admission_datetime')),
                name='discharge_after_admission'
            )
        ]
        indexes = [
            models.Index(fields=['patient', 'is_active']),
            models.Index(fields=['admission_datetime']),
            models.Index(fields=['discharge_datetime']),
            models.Index(fields=['admission_type']),
        ]
    
    def __str__(self):
        status = "Ativa" if self.is_active else "Finalizada"
        duration = f" ({self.stay_duration_days}d)" if self.stay_duration_days else ""
        return f"{self.patient.name} - {self.admission_datetime.strftime('%d/%m/%Y')} - {status}{duration}"
    
    def clean(self):
        """Validate admission data"""
        super().clean()
        
        # Validate discharge datetime
        if self.discharge_datetime and self.discharge_datetime <= self.admission_datetime:
            raise ValidationError({
                'discharge_datetime': 'Data de alta deve ser posterior à data de admissão'
            })
        
        # Validate discharge type when discharged
        if self.discharge_datetime and not self.discharge_type:
            raise ValidationError({
                'discharge_type': 'Tipo de alta é obrigatório quando há data de alta'
            })
        
        # Validate active status consistency
        if self.discharge_datetime and self.is_active:
            raise ValidationError({
                'is_active': 'Internação não pode estar ativa se há data de alta'
            })
    
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
                'hours': int(duration.total_seconds() / 3600),
                'days': duration.days
            }
        return None
```

### Step 1.3: Add Denormalized Fields to Patient Model

**File**: `apps/patients/models.py` - Update Patient model

```python
# Add these fields to the existing Patient model

class Patient(models.Model):
    # ... existing fields ...
    
    # Denormalized record number for performance
    current_record_number = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name="Número do Prontuário Atual",
        help_text="Número atual do prontuário (denormalizado para performance)"
    )
    
    # Enhanced admission/discharge tracking (keep existing fields, add new ones)
    current_admission_id = models.UUIDField(
        null=True, 
        blank=True,
        verbose_name="ID da Internação Atual",
        help_text="ID da internação ativa (denormalizado para performance)"
    )
    total_admissions_count = models.IntegerField(
        default=0,
        verbose_name="Total de Internações",
        help_text="Número total de internações do paciente"
    )
    total_inpatient_days = models.IntegerField(
        default=0,
        verbose_name="Total de Dias Internado",
        help_text="Total de dias internado ao longo de todas as internações"
    )
    
    # ... rest of existing fields ...
    
    # Add these methods to Patient model
    
    def get_current_record_number(self):
        """Get current record number from related model"""
        current_record = self.record_numbers.filter(is_current=True).first()
        return current_record.record_number if current_record else self.current_record_number
    
    def get_current_admission(self):
        """Get current active admission"""
        if self.current_admission_id:
            return self.admissions.filter(id=self.current_admission_id, is_active=True).first()
        return self.admissions.filter(is_active=True).first()
    
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
        return self.current_admission_id is not None and self.get_current_admission() is not None
```

### Step 1.4: Create Initial Database Tables

**Commands to run:**

```bash
# Create migrations for new models
uv run python manage.py makemigrations patients

# Apply migration to create tables
uv run python manage.py migrate
```

### Step 1.5: Update Admin Interfaces

**File**: `apps/patients/admin.py`

```python
from .models import Patient, PatientRecordNumber, PatientAdmission, AllowedTag, Tag

@admin.register(PatientRecordNumber)
class PatientRecordNumberAdmin(admin.ModelAdmin):
    list_display = ['patient', 'record_number', 'is_current', 'effective_date', 'created_by']
    list_filter = ['is_current', 'effective_date', 'created_at']
    search_fields = ['patient__name', 'record_number', 'previous_record_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informações do Prontuário', {
            'fields': ('patient', 'record_number', 'is_current')
        }),
        ('Histórico de Mudanças', {
            'fields': ('previous_record_number', 'change_reason', 'effective_date')
        }),
        ('Auditoria', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(PatientAdmission)
class PatientAdmissionAdmin(admin.ModelAdmin):
    list_display = ['patient', 'admission_datetime', 'discharge_datetime', 'admission_type', 'is_active', 'stay_duration_days']
    list_filter = ['admission_type', 'discharge_type', 'is_active', 'admission_datetime']
    search_fields = ['patient__name', 'admission_diagnosis', 'discharge_diagnosis']
    readonly_fields = ['stay_duration_hours', 'stay_duration_days', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informações da Internação', {
            'fields': ('patient', 'admission_datetime', 'admission_type', 'initial_bed')
        }),
        ('Informações da Alta', {
            'fields': ('discharge_datetime', 'discharge_type', 'final_bed', 'is_active')
        }),
        ('Diagnósticos', {
            'fields': ('admission_diagnosis', 'discharge_diagnosis')
        }),
        ('Duração', {
            'fields': ('stay_duration_hours', 'stay_duration_days'),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

# Update existing PatientAdmin
class PatientAdmin(admin.ModelAdmin):
    # ... existing configuration ...
    
    # Add new fields to list_display
    list_display = [..., 'current_record_number', 'total_admissions_count', 'is_currently_admitted']
    
    # Add new fields to fieldsets
    fieldsets = (
        # ... existing fieldsets ...
        ('Informações do Prontuário', {
            'fields': ('current_record_number',),
            'classes': ('collapse',)
        }),
        ('Estatísticas de Internação', {
            'fields': ('total_admissions_count', 'total_inpatient_days', 'current_admission_id'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [..., 'current_record_number', 'total_admissions_count', 'total_inpatient_days', 'current_admission_id']
```

## Validation and Testing

### Step 1.6: Update Sample Data Command

**File**: `apps/core/management/commands/populate_sample_data.py` - Add record tracking to sample data

```python
# Add imports at the top
from apps.patients.models import Patient, AllowedTag, Tag, PatientRecordNumber, PatientAdmission

# Update create_patients method
def create_patients(self):
    self.stdout.write('Creating patients...')
    
    self.patients = []
    
    # Create 20 patients with mixed statuses
    for i in range(20):
        is_inpatient = i < 10  # First 10 are inpatients
        patient = self.create_patient(is_inpatient)
        if patient:
            self.patients.append(patient)
    
    self.stdout.write(f'Created {len(self.patients)} patients total')

# Update create_patient method
def create_patient(self, is_inpatient):
    if self.dry_run:
        status = 'inpatient' if is_inpatient else 'outpatient'
        self.stdout.write(f'Would create {status} patient with record number and admission history')
        return None
        
    creator = random.choice(self.users)
    
    # Generate realistic patient data
    gender = random.choice(['M', 'F'])
    if gender == 'M':
        first_name = fake.first_name_male()
    else:
        first_name = fake.first_name_female()
    
    last_name = fake.last_name()
    name = f'{first_name} {last_name}'
    
    # Determine status
    if is_inpatient:
        status = random.choice([Patient.Status.INPATIENT, Patient.Status.EMERGENCY])
    else:
        status = random.choice([Patient.Status.OUTPATIENT, Patient.Status.DISCHARGED])
    
    patient = Patient.objects.create(
        name=name,
        birthday=fake.date_of_birth(minimum_age=18, maximum_age=90),
        healthcard_number=f'SUS{random.randint(100000000, 999999999)}',
        id_number=fake.rg(),
        fiscal_number=fake.cpf(),
        phone=fake.phone_number(),
        address=fake.street_address(),
        city=fake.city(),
        state=fake.state_abbr(),
        zip_code=fake.postcode(),
        status=status,
        bed=f'Leito {random.randint(1, 50)}' if is_inpatient else '',
        created_by=creator,
        updated_by=creator,
    )
    
    # Create record number history (1-3 record numbers per patient)
    num_records = random.randint(1, 3)
    for record_idx in range(num_records):
        is_current = (record_idx == num_records - 1)  # Last one is current
        record_number = f'REC{patient.id.hex[:8].upper()}{record_idx:02d}'
        
        # Calculate effective date (older records have earlier dates)
        days_back = (num_records - record_idx - 1) * random.randint(30, 180)
        effective_date = timezone.now() - timedelta(days=days_back)
        
        previous_number = ''
        if record_idx > 0:
            previous_number = f'REC{patient.id.hex[:8].upper()}{record_idx-1:02d}'
        
        change_reasons = [
            'Registro inicial',
            'Transferência entre setores',
            'Migração de sistema',
            'Correção de dados',
            'Política hospitalar'
        ]
        
        PatientRecordNumber.objects.create(
            patient=patient,
            record_number=record_number,
            previous_record_number=previous_number,
            change_reason=random.choice(change_reasons) if record_idx > 0 else 'Registro inicial',
            effective_date=effective_date,
            is_current=is_current,
            created_by=creator,
            updated_by=creator
        )
        
        # Update patient's denormalized field
        if is_current:
            patient.current_record_number = record_number
    
    # Create admission history (0-4 admissions per patient)
    num_admissions = random.randint(0, 4)
    total_days = 0
    
    for admission_idx in range(num_admissions):
        is_active = (admission_idx == num_admissions - 1) and is_inpatient
        
        # Calculate admission date (older admissions have earlier dates)
        if admission_idx == 0:
            admission_date = timezone.now() - timedelta(days=random.randint(1, 365))
        else:
            # Subsequent admissions are after previous discharge
            admission_date = timezone.now() - timedelta(days=random.randint(1, 180))
        
        admission_types = list(PatientAdmission.AdmissionType.values)
        admission_type = random.choice(admission_types)
        
        initial_bed = f'Leito {random.randint(1, 50)}'
        
        admission_diagnoses = [
            'Pneumonia adquirida na comunidade',
            'Infarto agudo do miocárdio',
            'Acidente vascular cerebral',
            'Insuficiência cardíaca congestiva',
            'Diabetes mellitus descompensado',
            'Hipertensão arterial sistêmica',
            'Gastroenterite aguda',
            'Fratura de fêmur',
            'Apendicite aguda',
            'Bronquite aguda'
        ]
        
        discharge_diagnoses = [
            'Pneumonia tratada, paciente estável',
            'Infarto tratado, função cardíaca preservada',
            'AVC sem sequelas motoras',
            'Insuficiência cardíaca compensada',
            'Diabetes controlado',
            'Pressão arterial controlada',
            'Gastroenterite resolvida',
            'Fratura reduzida e fixada',
            'Apendicectomia sem complicações',
            'Bronquite resolvida'
        ]
        
        admission = PatientAdmission.objects.create(
            patient=patient,
            admission_datetime=admission_date,
            admission_type=admission_type,
            initial_bed=initial_bed,
            admission_diagnosis=random.choice(admission_diagnoses),
            is_active=is_active,
            created_by=creator,
            updated_by=creator
        )
        
        # If not active, add discharge information
        if not is_active:
            stay_days = random.randint(1, 30)
            discharge_date = admission_date + timedelta(days=stay_days)
            
            discharge_types = list(PatientAdmission.DischargeType.values)
            discharge_type = random.choice(discharge_types)
            
            admission.discharge_datetime = discharge_date
            admission.discharge_type = discharge_type
            admission.final_bed = initial_bed if random.random() < 0.7 else f'Leito {random.randint(1, 50)}'
            admission.discharge_diagnosis = random.choice(discharge_diagnoses)
            admission.save()  # This will trigger duration calculation
            
            total_days += stay_days
        else:
            # For active admission, update patient current admission
            patient.current_admission_id = admission.id
            patient.bed = initial_bed
    
    # Update patient denormalized fields
    patient.total_admissions_count = num_admissions
    patient.total_inpatient_days = total_days
    patient.save()
    
    # Assign random tags (existing logic)
    if self.allowed_tags:
        num_tags = random.randint(0, 3)
        selected_allowed_tags = random.sample(self.allowed_tags, min(num_tags, len(self.allowed_tags)))
        
        for allowed_tag in selected_allowed_tags:
            tag = Tag.objects.create(
                allowed_tag=allowed_tag,
                notes=f'Tag aplicada ao paciente {patient.name}',
                created_by=creator,
                updated_by=creator,
            )
            patient.tags.add(tag)
    
    return patient

# Add to display_completion_message method
def display_completion_message(self):
    if self.dry_run:
        self.stdout.write(self.style.SUCCESS('\\nDRY RUN COMPLETED - No data will be created'))
        return
        
    # ... existing code ...
    
    # Add record tracking statistics
    self.stdout.write(f'Created {PatientRecordNumber.objects.count()} patient record numbers')
    self.stdout.write(f'Created {PatientAdmission.objects.count()} patient admissions')
    
    # Show admission statistics
    active_admissions = PatientAdmission.objects.filter(is_active=True).count()
    self.stdout.write(f'Active admissions: {active_admissions}')
    
    # ... rest of existing code ...
```

### Step 1.7: Create Basic Model Tests

**File**: `apps/patients/tests/test_record_tracking_models.py`

```python
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from ..models import Patient, PatientRecordNumber, PatientAdmission

User = get_user_model()

class PatientRecordNumberTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_create_record_number(self):
        """Test creating a new record number"""
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(record.record_number, 'REC001')
        self.assertTrue(record.is_current)
    
    def test_unique_current_record_constraint(self):
        """Test that only one current record can exist per patient"""
        PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # This should raise an error
        with self.assertRaises(ValidationError):
            record2 = PatientRecordNumber(
                patient=self.patient,
                record_number='REC002',
                is_current=True,
                created_by=self.user,
                updated_by=self.user
            )
            record2.full_clean()

class PatientAdmissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_create_admission(self):
        """Test creating a new admission"""
        admission_time = timezone.now()
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=admission_time,
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(admission.admission_type, 'emergency')
        self.assertTrue(admission.is_active)
        self.assertIsNone(admission.discharge_datetime)
    
    def test_discharge_patient(self):
        """Test discharging a patient and duration calculation"""
        admission_time = timezone.now() - timedelta(days=3)
        discharge_time = timezone.now()
        
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=admission_time,
            discharge_datetime=discharge_time,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertFalse(admission.is_active)
        self.assertEqual(admission.stay_duration_days, 3)
        self.assertGreater(admission.stay_duration_hours, 72)
```

## Success Criteria

- ✅ PatientRecordNumber model created with proper constraints
- ✅ PatientAdmission model created with duration calculations
- ✅ Denormalized fields added to Patient model
- ✅ Database migrations created and applied successfully
- ✅ Admin interfaces configured for new models
- ✅ Basic model tests passing
- ✅ Unique constraints enforced (one current record, one active admission per patient)
- ✅ Proper audit trail fields on all models

## Next Phase

Continue to **Phase 2: Event Integration and Timeline** to integrate the new models with the existing Event system for timeline visibility.