# Patients App Implementation Plan - Part 2: Model Methods and Admin Customization

## Vertical Slice 2: Patient Model Methods and Admin Customization

### Step 1: Implement Patient Model Methods

1. Add helper methods to Patient model:

   ```python
   # Add these methods to the Patient model in apps/patients/models.py

   def set_record_number(self, hospital, record_number, user):
       """Set or update patient's record number at specified hospital"""
       record, created = PatientHospitalRecord.objects.get_or_create(
           patient=self,
           hospital=hospital,
           defaults={
               "record_number": record_number,
               "created_by": user,
               "updated_by": user,
           },
       )

       if not created:
           record.record_number = record_number
           record.updated_by = user
           record.save(update_fields=["record_number", "updated_by", "updated_at"])

       return record

   def admit_to_hospital(
       self,
       hospital,
       ward=None,
       bed=None,
       record_number=None,
       admission_date=None,
       user=None,
   ):
       """Admit patient to a hospital, with optional ward/bed assignment"""
       if admission_date is None:
           from django.utils import timezone
           admission_date = timezone.now().date()

       # Update patient status and location
       self.status = self.Status.INPATIENT
       self.current_hospital = hospital
       self.ward = ward
       self.bed = bed or ""
       self.last_admission_date = admission_date

       if user:
           self.updated_by = user

       self.save()

       # Update hospital record if record number provided
       if record_number and user:
           self.set_record_number(hospital, record_number, user)

       return self

   def discharge(self, discharge_date=None, user=None):
       """Discharge patient from current hospital"""
       if discharge_date is None:
           from django.utils import timezone
           discharge_date = timezone.now().date()

       # Update patient status and discharge date
       self.status = self.Status.DISCHARGED
       self.last_discharge_date = discharge_date

       # Clear current location
       self.ward = None
       self.bed = ""

       if user:
           self.updated_by = user

       self.save()

       # Update hospital record if exists
       if self.current_hospital:
           try:
               record = PatientHospitalRecord.objects.get(
                   patient=self, hospital=self.current_hospital
               )
               record.last_discharge_date = discharge_date

               if user:
                   record.updated_by = user

               record.save(update_fields=["last_discharge_date", "updated_by", "updated_at"])
           except PatientHospitalRecord.DoesNotExist:
               pass

       # Keep current_hospital for reference until next admission
       return self

   def transfer(
       self,
       to_hospital,
       ward=None,
       bed=None,
       record_number=None,
       transfer_date=None,
       user=None,
   ):
       """Transfer patient to another hospital"""
       if transfer_date is None:
           from django.utils import timezone
           transfer_date = timezone.now().date()

       # First discharge from current hospital
       if self.current_hospital and self.current_hospital != to_hospital:
           self.discharge(discharge_date=transfer_date, user=user)

       # Then admit to new hospital
       self.status = self.Status.TRANSFERRED
       self.admit_to_hospital(
           hospital=to_hospital,
           ward=ward,
           bed=bed,
           record_number=record_number,
           admission_date=transfer_date,
           user=user,
       )

       return self
   ```

### Step 2: Add Model Methods Tests

1. Update test_models.py to test the new methods:

   ```python
   # Add these test methods to PatientModelTest in apps/patients/tests/test_models.py

   def test_set_record_number(self):
       """Test setting a record number for a patient at a hospital"""
       # Create a new hospital
       new_hospital = Hospital.objects.create(
           name='Second Hospital',
           short_name='SH',
           created_by=self.user,
           updated_by=self.user
       )

       # Set record number
       record = self.patient.set_record_number(new_hospital, '67890', self.user)

       # Verify record was created
       self.assertEqual(record.hospital, new_hospital)
       self.assertEqual(record.record_number, '67890')
       self.assertEqual(self.patient.hospital_records.count(), 2)

       # Test updating existing record
       updated_record = self.patient.set_record_number(self.hospital, 'UPDATED', self.user)
       self.assertEqual(updated_record.record_number, 'UPDATED')
       self.assertEqual(self.patient.hospital_records.count(), 2)  # Count should remain the same

   def test_admit_to_hospital(self):
       """Test admitting a patient to a hospital"""
       # Create a new patient
       new_patient = Patient.objects.create(
           name='Jane Doe',
           birthday='1995-05-05',
           status=Patient.Status.OUTPATIENT,
           created_by=self.user,
           updated_by=self.user
       )

       # Create a ward
       ward = Ward.objects.create(
           name='Test Ward',
           hospital=self.hospital,
           created_by=self.user,
           updated_by=self.user
       )

       # Admit patient
       new_patient.admit_to_hospital(
           hospital=self.hospital,
           ward=ward,
           bed='101A',
           record_number='ABC123',
           user=self.user
       )

       # Verify patient status and location
       self.assertEqual(new_patient.status, Patient.Status.INPATIENT)
       self.assertEqual(new_patient.current_hospital, self.hospital)
       self.assertEqual(new_patient.ward, ward)
       self.assertEqual(new_patient.bed, '101A')
       self.assertIsNotNone(new_patient.last_admission_date)

       # Verify hospital record was created
       record = new_patient.hospital_records.get(hospital=self.hospital)
       self.assertEqual(record.record_number, 'ABC123')

   def test_discharge(self):
       """Test discharging a patient from a hospital"""
       # First admit the patient
       self.patient.admit_to_hospital(
           hospital=self.hospital,
           bed='202B',
           user=self.user
       )

       # Then discharge
       self.patient.discharge(user=self.user)

       # Verify patient status and location
       self.assertEqual(self.patient.status, Patient.Status.DISCHARGED)
       self.assertIsNone(self.patient.ward)
       self.assertEqual(self.patient.bed, '')
       self.assertIsNotNone(self.patient.last_discharge_date)

       # Verify hospital record was updated
       record = self.patient.hospital_records.get(hospital=self.hospital)
       self.assertIsNotNone(record.last_discharge_date)

   def test_transfer(self):
       """Test transferring a patient to another hospital"""
       # Create a new hospital
       new_hospital = Hospital.objects.create(
           name='Transfer Hospital',
           short_name='TH2',
           created_by=self.user,
           updated_by=self.user
       )

       # Create a ward in the new hospital
       new_ward = Ward.objects.create(
           name='Transfer Ward',
           hospital=new_hospital,
           created_by=self.user,
           updated_by=self.user
       )

       # First admit the patient to original hospital
       self.patient.admit_to_hospital(
           hospital=self.hospital,
           user=self.user
       )

       # Then transfer to new hospital
       self.patient.transfer(
           to_hospital=new_hospital,
           ward=new_ward,
           bed='303C',
           record_number='TRANSFER123',
           user=self.user
       )

       # Verify patient status and location
       self.assertEqual(self.patient.status, Patient.Status.TRANSFERRED)
       self.assertEqual(self.patient.current_hospital, new_hospital)
       self.assertEqual(self.patient.ward, new_ward)
       self.assertEqual(self.patient.bed, '303C')

       # Verify hospital records
       original_record = self.patient.hospital_records.get(hospital=self.hospital)
       new_record = self.patient.hospital_records.get(hospital=new_hospital)

       self.assertIsNotNone(original_record.last_discharge_date)
       self.assertEqual(new_record.record_number, 'TRANSFER123')
   ```

2. Run the tests to verify the methods work correctly:

   ```bash
   python manage.py test apps.patients.tests.test_models
   ```

### Step 3: Verify Basic Model Methods

1. Test model methods through Django shell:

   ```bash
   python manage.py shell -c "from apps.patients.models import Patient; from apps.hospitals.models import Hospital; from django.contrib.auth import get_user_model; User = get_user_model(); user = User.objects.first(); hospital = Hospital.objects.first(); patient = Patient.objects.create(name='Test Patient', birthday='1980-01-01', status=Patient.Status.OUTPATIENT, created_by=user, updated_by=user); patient.admit_to_hospital(hospital, user=user); print(f'Patient admitted to {patient.current_hospital}')"
   ```

2. Test discharge method:

   ```bash
   python manage.py shell -c "from apps.patients.models import Patient; patient = Patient.objects.get(name='Test Patient'); patient.discharge(user=patient.created_by); print(f'Patient status: {patient.get_status_display()}')"
   ```

### Step 4: Enhance Admin Interface

1. Update Patient admin with fieldsets and inlines:

   ```python
   # Update PatientAdmin in apps/patients/admin.py

   from django.utils.translation import gettext_lazy as _

   class PatientHospitalRecordInline(admin.TabularInline):
       model = PatientHospitalRecord
       extra = 0
       readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')

       def has_delete_permission(self, request, obj=None):
           return False

   @admin.register(Patient)
   class PatientAdmin(admin.ModelAdmin):
       list_display = ('name', 'birthday', 'status', 'current_hospital', 'created_at')
       list_filter = ('status', 'current_hospital', 'tags')
       search_fields = ('name', 'id_number', 'fiscal_number', 'healthcard_number')
       readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')
       inlines = [PatientHospitalRecordInline]

       fieldsets = (
           (None, {
               'fields': ('name', 'birthday', 'status')
           }),
           (_('Identification'), {
               'fields': ('healthcard_number', 'id_number', 'fiscal_number')
           }),
           (_('Contact Information'), {
               'fields': ('phone', 'address', 'city', 'state', 'zip_code')
           }),
           (_('Hospital Information'), {
               'fields': ('current_hospital', 'ward', 'bed',
                         'last_admission_date', 'last_discharge_date')
           }),
           (_('Tags'), {
               'fields': ('tags',)
           }),
           (_('System Information'), {
               'classes': ('collapse',),
               'fields': ('created_at', 'created_by', 'updated_at', 'updated_by')
           }),
       )

       def save_model(self, request, obj, form, change):
           if not change:  # If creating a new object
               obj.created_by = request.user
           obj.updated_by = request.user
           super().save_model(request, obj, form, change)

       def save_formset(self, request, form, formset, change):
           instances = formset.save(commit=False)
           for instance in instances:
               if not instance.pk:  # If creating a new object
                   instance.created_by = request.user
               instance.updated_by = request.user
               instance.save()
           formset.save_m2m()
   ```

2. Add custom admin actions:

   ```python
   # Add these actions to PatientAdmin in apps/patients/admin.py

   from django.contrib import messages

   @admin.action(description=_("Discharge selected patients"))
   def discharge_patients(modeladmin, request, queryset):
       """Admin action to discharge multiple patients at once"""
       count = 0
       for patient in queryset:
           if patient.status == Patient.Status.INPATIENT:
               patient.discharge(user=request.user)
               count += 1

       if count:
           messages.success(request, _(f"{count} patients were successfully discharged."))
       else:
           messages.warning(request, _("No inpatients were found in the selection."))

   @admin.action(description=_("Mark as emergency patients"))
   def mark_as_emergency(modeladmin, request, queryset):
       """Admin action to mark patients as emergency"""
       updated = queryset.update(
           status=Patient.Status.EMERGENCY,
           updated_by=request.user
       )
       messages.success(request, _(f"{updated} patients were marked as emergency."))

   # Add these actions to the actions list in PatientAdmin
   actions = [discharge_patients, mark_as_emergency]
   ```

3. Enhance PatientHospitalRecord admin:

   ```python
   # Update PatientHospitalRecordAdmin in apps/patients/admin.py

   @admin.register(PatientHospitalRecord)
   class PatientHospitalRecordAdmin(admin.ModelAdmin):
       list_display = ('patient', 'hospital', 'record_number', 'first_admission_date', 'last_discharge_date', 'created_at')
       list_filter = ('hospital', 'first_admission_date', 'last_discharge_date')
       search_fields = ('patient__name', 'record_number')
       readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')

       fieldsets = (
           (None, {
               'fields': ('patient', 'hospital', 'record_number')
           }),
           (_('Dates'), {
               'fields': ('first_admission_date', 'last_admission_date', 'last_discharge_date')
           }),
           (_('System Information'), {
               'classes': ('collapse',),
               'fields': ('created_at', 'created_by', 'updated_at', 'updated_by')
           }),
       )

       def save_model(self, request, obj, form, change):
           if not change:  # If creating a new object
               obj.created_by = request.user
           obj.updated_by = request.user
           super().save_model(request, obj, form, change)
   ```

4. Enhance AllowedTag admin:

   ```python
   # Update AllowedTagAdmin in apps/patients/admin.py

   @admin.register(AllowedTag)
   class AllowedTagAdmin(admin.ModelAdmin):
       list_display = ('name', 'slug')
       search_fields = ('name',)
       prepopulated_fields = {'slug': ('name',)}

       def get_queryset(self, request):
           return super().get_queryset(request).annotate(
               patient_count=models.Count('tagged_items__content_object')
           )

       def patient_count(self, obj):
           return obj.patient_count
       patient_count.short_description = _("Patients")
       patient_count.admin_order_field = 'patient_count'

       list_display = ('name', 'slug', 'patient_count')
   ```

### Step 5: Test Admin Customizations

1. Create admin test file:

   ```python
   # Create apps/patients/tests/test_admin.py

   from django.test import TestCase, Client
   from django.urls import reverse
   from django.contrib.auth import get_user_model
   from apps.patients.models import Patient, PatientHospitalRecord, AllowedTag
   from apps.hospitals.models import Hospital

   User = get_user_model()

   class PatientAdminTest(TestCase):
       @classmethod
       def setUpTestData(cls):
           # Create a superuser
           cls.admin_user = User.objects.create_superuser(
               username='admin',
               email='admin@example.com',
               password='adminpass123'
           )

           # Create a test hospital
           cls.hospital = Hospital.objects.create(
               name='Test Hospital',
               short_name='TH',
               created_by=cls.admin_user,
               updated_by=cls.admin_user
           )

           # Create test patients
           cls.patient1 = Patient.objects.create(
               name='John Doe',
               birthday='1990-01-01',
               status=Patient.Status.INPATIENT,
               current_hospital=cls.hospital,
               created_by=cls.admin_user,
               updated_by=cls.admin_user
           )

           cls.patient2 = Patient.objects.create(
               name='Jane Smith',
               birthday='1985-05-15',
               status=Patient.Status.OUTPATIENT,
               created_by=cls.admin_user,
               updated_by=cls.admin_user
           )

           # Create a test tag
           cls.tag = AllowedTag.objects.create(
               name='Test Tag',
               slug='test-tag'
           )

           # Add tag to patient
           cls.patient1.tags.add(cls.tag)

       def setUp(self):
           self.client = Client()
           self.client.login(username='admin', password='adminpass123')

       def test_patient_admin_list(self):
           """Test that the patient admin list view works"""
           url = reverse('admin:patients_patient_changelist')
           response = self.client.get(url)
           self.assertEqual(response.status_code, 200)
           self.assertContains(response, 'John Doe')
           self.assertContains(response, 'Jane Smith')

       def test_patient_admin_detail(self):
           """Test that the patient admin detail view works"""
           url = reverse('admin:patients_patient_change', args=[self.patient1.pk])
           response = self.client.get(url)
           self.assertEqual(response.status_code, 200)
           self.assertContains(response, 'John Doe')
           self.assertContains(response, 'Test Hospital')

       def test_discharge_action(self):
           """Test the discharge admin action"""
           url = reverse('admin:patients_patient_changelist')
           data = {
               'action': 'discharge_patients',
               '_selected_action': [self.patient1.pk],
           }
           response = self.client.post(url, data, follow=True)
           self.assertEqual(response.status_code, 200)

           # Refresh patient from database
           self.patient1.refresh_from_db()
           self.assertEqual(self.patient1.status, Patient.Status.DISCHARGED)

       def test_mark_as_emergency_action(self):
           """Test the mark as emergency admin action"""
           url = reverse('admin:patients_patient_changelist')
           data = {
               'action': 'mark_as_emergency',
               '_selected_action': [self.patient2.pk],
           }
           response = self.client.post(url, data, follow=True)
           self.assertEqual(response.status_code, 200)

           # Refresh patient from database
           self.patient2.refresh_from_db()
           self.assertEqual(self.patient2.status, Patient.Status.EMERGENCY)
   ```

2. Run the admin tests:

   ```bash
   python manage.py test apps.patients.tests.test_admin
   ```

### Step 6: Verify Admin Interface Manually

1. Run the development server:

   ```bash
   python manage.py runserver
   ```

2. Access the admin interface at <http://localhost:8000/admin/>
3. Verify that the Patient admin shows the configured fieldsets
4. Test the custom admin actions:
   - Select a patient and use the "Discharge selected patients" action
   - Select a patient and use the "Mark as emergency patients" action
5. Verify that the PatientHospitalRecord inline works correctly in the Patient admin
6. Check that the AllowedTag admin shows the patient count

### Step 7: Add Model Method Documentation

1. Add docstrings to all model methods:

   ```python
   # Update docstrings in apps/patients/models.py

   class Patient(models.Model):
       """
       Model representing a patient in the system.

       This model stores all patient information including personal details,
       current hospital status, and relationships to hospitals and wards.
       """
       # ... existing code ...

       def set_record_number(self, hospital, record_number, user):
           """
           Set or update patient's record number at specified hospital.

           Args:
               hospital: The Hospital object where the record is being set
               record_number: The record number string to set
               user: The User object making the change

           Returns:
               The PatientHospitalRecord object (created or updated)
           """
           # ... existing code ...

       def admit_to_hospital(self, hospital, ward=None, bed=None, record_number=None, admission_date=None, user=None):
           """
           Admit patient to a hospital, with optional ward/bed assignment.

           Args:
               hospital: The Hospital object where the patient is being admitted
               ward: Optional Ward object for the patient's location
               bed: Optional bed identifier string
               record_number: Optional record number to set/update
               admission_date: Optional date of admission (defaults to today)
               user: Optional User object making the change

           Returns:
               The updated Patient object
           """
           # ... existing code ...

       def discharge(self, discharge_date=None, user=None):
           """
           Discharge patient from current hospital.

           Args:
               discharge_date: Optional date of discharge (defaults to today)
               user: Optional User object making the change

           Returns:
               The updated Patient object
           """
           # ... existing code ...

       def transfer(self, to_hospital, ward=None, bed=None, record_number=None, transfer_date=None, user=None):
           """
           Transfer patient to another hospital.

           This method handles both the discharge from the current hospital
           and the admission to the new hospital.

           Args:
               to_hospital: The Hospital object where the patient is being transferred
               ward: Optional Ward object for the patient's new location
               bed: Optional bed identifier string
               record_number: Optional record number to set/update at the new hospital
               transfer_date: Optional date of transfer (defaults to today)
               user: Optional User object making the change

           Returns:
               The updated Patient object
           """
           # ... existing code ...
   ```

### Step 8: Add Model Method Validation

1. Add validation to model methods:

   ```python
   # Update methods in apps/patients/models.py

   from django.core.exceptions import ValidationError

   def admit_to_hospital(self, hospital, ward=None, bed=None, record_number=None, admission_date=None, user=None):
       """Admit patient to a hospital, with optional ward/bed assignment"""
       if admission_date is None:
           from django.utils import timezone
           admission_date = timezone.now().date()

       # Validate ward belongs to hospital
       if ward and ward.hospital != hospital:
           raise ValidationError(
               f"Ward {ward.name} does not belong to hospital {hospital.name}"
           )

       # Update patient status and location
       self.status = self.Status.INPATIENT
       self.current_hospital = hospital
       self.ward = ward
       self.bed = bed or ""
       self.last_admission_date = admission_date

       if user:
           self.updated_by = user

       self.save()

       # Update hospital record if record number provided
       if record_number and user:
           self.set_record_number(hospital, record_number, user)

       return self

   def transfer(self, to_hospital, ward=None, bed=None, record_number=None, transfer_date=None, user=None):
       """Transfer patient to another hospital"""
       if transfer_date is None:
           from django.utils import timezone
           transfer_date = timezone.now().date()

       # Validate ward belongs to destination hospital
       if ward and ward.hospital != to_hospital:
           raise ValidationError(
               f"Ward {ward.name} does not belong to hospital {to_hospital.name}"
           )

       # First discharge from current hospital
       if self.current_hospital and self.current_hospital != to_hospital:
           self.discharge(discharge_date=transfer_date, user=user)

       # Then admit to new hospital
       self.status = self.Status.TRANSFERRED
       self.admit_to_hospital(
           hospital=to_hospital,
           ward=ward,
           bed=bed,
           record_number=record_number,
           admission_date=transfer_date,
           user=user,
       )

       return self
   ```

2. Add validation tests:

   ```python
   # Add to apps/patients/tests/test_models.py

   def test_admit_validation(self):
       """Test validation when admitting a patient"""
       # Create a second hospital
       second_hospital = Hospital.objects.create(
           name='Second Hospital',
           short_name='SH',
           created_by=self.user,
           updated_by=self.user
       )

       # Create a ward in the second hospital
       ward = Ward.objects.create(
           name='Test Ward',
           hospital=second_hospital,
           created_by=self.user,
           updated_by=self.user
       )

       # Try to admit to first hospital with ward from second hospital
       with self.assertRaises(ValidationError):
           self.patient.admit_to_hospital(
               hospital=self.hospital,
               ward=ward,
               user=self.user
           )

   def test_transfer_validation(self):
       """Test validation when transferring a patient"""
       # Create two hospitals
       hospital1 = Hospital.objects.create(
           name='Hospital 1',
           short_name='H1',
           created_by=self.user,
           updated_by=self.user
       )

       hospital2 = Hospital.objects.create(
           name='Hospital 2',
           short_name='H2',
           created_by=self.user,
           updated_by=self.user
       )

       # Create a ward in hospital1
       ward1 = Ward.objects.create(
           name='Ward 1',
           hospital=hospital1,
           created_by=self.user,
           updated_by=self.user
       )

       # Try to transfer to hospital2 with ward from hospital1
       with self.assertRaises(ValidationError):
           self.patient.transfer(
               to_hospital=hospital2,
               ward=ward1,
               user=self.user
           )
   ```

3. Run the tests to verify validation works:

   ```bash
   python manage.py test apps.patients.tests.test_models
   ```

```

This file covers the second part of the implementation plan, focusing on model methods and admin customization for the patients app. It includes:

1. Implementation of key patient model methods (admit_to_hospital, discharge, transfer, set_record_number)
2. Tests for these model methods
3. Enhanced admin interface with fieldsets, inlines, and custom actions
4. Admin tests to verify the customizations work correctly
5. Documentation and validation for the model methods

The file builds on Part 1 but doesn't introduce dependencies on future parts. Each step is designed to be executable in sequence, with verification steps to ensure everything works correctly before moving on.



```
