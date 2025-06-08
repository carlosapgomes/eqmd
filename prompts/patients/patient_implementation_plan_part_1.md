# Patients App Implementation Plan - Part 1: Core Setup and Models

## Vertical Slice 1: Initial App Setup and Patient Model

### Step 1: App Configuration and Basic Setup

1. Add the app to INSTALLED_APPS in config/settings.py
2. Verify app configuration:
   - Check app is properly registered in Django
   - Verify app structure is correct
   - Run Django shell to confirm app is recognized

   ```bash
   python manage.py shell -c "from django.conf import settings; print('apps.patients' in settings.INSTALLED_APPS)"
   ```

### Step 2: Create Patient Model

1. Create the Patient model in apps/patients/models.py:

   ```python
   import uuid
   from django.db import models
   from django.conf import settings
   from taggit.managers import TaggableManager
   from taggit.models import TagBase, GenericTaggedItemBase

   class AllowedTag(TagBase):
       """Custom tag model that restricts tags to predefined values"""
       class Meta:
           verbose_name = "Tag"
           verbose_name_plural = "Tags"

   class UUIDTaggedItem(GenericTaggedItemBase):
       """Custom tagged item model that works with UUID primary keys"""
       tag = models.ForeignKey(
           AllowedTag,
           on_delete=models.CASCADE,
           related_name="%(app_label)s_%(class)s_items",
       )

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
       ward = models.ForeignKey(
           "hospitals.Ward",
           on_delete=models.SET_NULL,
           null=True,
           blank=True,
           related_name="patients",
           verbose_name="Enfermaria",
       )
       bed = models.CharField(max_length=20, blank=True, verbose_name="Leito/Cama")
       last_admission_date = models.DateField(null=True, blank=True, verbose_name="Data da Última Admissão")
       last_discharge_date = models.DateField(null=True, blank=True, verbose_name="Data da Última Alta")

       # Tags
       tags = TaggableManager(through=UUIDTaggedItem, blank=True)

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
   ```

### Step 3: Create PatientHospitalRecord Model

1. Add the PatientHospitalRecord model:

   ```python
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
   ```

### Step 4: Create and Apply Migrations

1. Run makemigrations to create migration files:

   ```bash
   python manage.py makemigrations patients
   ```

2. Apply migrations to create database tables:

   ```bash
   python manage.py migrate patients
   ```

3. Verify migrations applied correctly:

   ```bash
   python manage.py showmigrations patients
   ```

### Step 5: Basic Admin Integration

1. Create apps/patients/admin.py:

   ```python
   from django.contrib import admin
   from .models import Patient, PatientHospitalRecord, AllowedTag, UUIDTaggedItem

   @admin.register(AllowedTag)
   class AllowedTagAdmin(admin.ModelAdmin):
       list_display = ('name', 'slug')
       search_fields = ('name',)
       prepopulated_fields = {'slug': ('name',)}

   @admin.register(Patient)
   class PatientAdmin(admin.ModelAdmin):
       list_display = ('name', 'birthday', 'status', 'current_hospital', 'created_at')
       list_filter = ('status', 'current_hospital')
       search_fields = ('name', 'id_number', 'fiscal_number', 'healthcard_number')
       readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')

       def save_model(self, request, obj, form, change):
           if not change:  # If creating a new object
               obj.created_by = request.user
           obj.updated_by = request.user
           super().save_model(request, obj, form, change)

   @admin.register(PatientHospitalRecord)
   class PatientHospitalRecordAdmin(admin.ModelAdmin):
       list_display = ('patient', 'hospital', 'record_number', 'created_at')
       list_filter = ('hospital',)
       search_fields = ('patient__name', 'record_number')
       readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')

       def save_model(self, request, obj, form, change):
           if not change:  # If creating a new object
               obj.created_by = request.user
           obj.updated_by = request.user
           super().save_model(request, obj, form, change)
   ```

### Step 6: Test Basic Functionality

1. Create test directory structure:

   ```bash
   mkdir -p apps/patients/tests
   touch apps/patients/tests/__init__.py
   ```

2. Create test_models.py:

   ```python
   from django.test import TestCase
   from django.contrib.auth import get_user_model
   from apps.patients.models import Patient, PatientHospitalRecord, AllowedTag
   from apps.hospitals.models import Hospital

   User = get_user_model()

   class PatientModelTest(TestCase):
       @classmethod
       def setUpTestData(cls):
           # Create a test user
           cls.user = User.objects.create_user(
               username='testuser',
               email='test@example.com',
               password='testpass123'
           )

           # Create a test hospital
           cls.hospital = Hospital.objects.create(
               name='Test Hospital',
               short_name='TH',
               created_by=cls.user,
               updated_by=cls.user
           )

           # Create a test tag
           cls.tag = AllowedTag.objects.create(
               name='Test Tag',
               slug='test-tag'
           )

           # Create a test patient
           cls.patient = Patient.objects.create(
               name='John Doe',
               birthday='1990-01-01',
               status=Patient.Status.OUTPATIENT,
               created_by=cls.user,
               updated_by=cls.user
           )

           # Add tag to patient
           cls.patient.tags.add(cls.tag)

           # Create a test hospital record
           cls.record = PatientHospitalRecord.objects.create(
               patient=cls.patient,
               hospital=cls.hospital,
               record_number='12345',
               created_by=cls.user,
               updated_by=cls.user
           )

       def test_patient_creation(self):
           """Test that a patient can be created with required fields"""
           self.assertEqual(self.patient.name, 'John Doe')
           self.assertEqual(self.patient.status, Patient.Status.OUTPATIENT)
           self.assertEqual(str(self.patient), 'John Doe')

       def test_patient_tags(self):
           """Test that tags can be added to a patient"""
           self.assertEqual(self.patient.tags.count(), 1)
           self.assertEqual(self.patient.tags.first().name, 'Test Tag')

       def test_hospital_record_creation(self):
           """Test that a hospital record can be created for a patient"""
           self.assertEqual(self.record.patient, self.patient)
           self.assertEqual(self.record.hospital, self.hospital)
           self.assertEqual(self.record.record_number, '12345')
           self.assertEqual(str(self.record), 'John Doe - Test Hospital (12345)')

       def test_patient_hospital_relationship(self):
           """Test the relationship between patient and hospital records"""
           self.assertEqual(self.patient.hospital_records.count(), 1)
           self.assertEqual(self.hospital.patient_records.count(), 1)
   ```

3. Run the tests:

   ```bash
   python manage.py test apps.patients.tests.test_models
   ```
