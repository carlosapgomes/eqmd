from django.test import TestCase
from django.contrib.auth import get_user_model
from ..models import Patient, PatientHospitalRecord, AllowedTag
from ..forms import PatientForm, PatientHospitalRecordForm, PatientHospitalRecordNestedForm
from apps.hospitals.models import Hospital

User = get_user_model()


class PatientFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

    def test_patient_form_valid(self):
        form = PatientForm({
            'name': 'Test Patient',
            'birthday': '1990-01-01',
            'status': Patient.Status.OUTPATIENT,
        })
        self.assertTrue(form.is_valid())

    def test_patient_form_invalid(self):
        # Missing required field (name)
        form = PatientForm({
            'birthday': '1990-01-01',
            'status': Patient.Status.OUTPATIENT,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_patient_form_has_hospital_record_form(self):
        form = PatientForm()
        self.assertIsNotNone(form.hospital_record_form)
        self.assertIsInstance(form.hospital_record_form, PatientHospitalRecordNestedForm)


class HospitalRecordFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_hospital_record_form_valid(self):
        form = PatientHospitalRecordForm({
            'patient': self.patient.id,
            'hospital': self.hospital.id,
            'record_number': 'REC123',
            'first_admission_date': '2023-01-01',
        })
        self.assertTrue(form.is_valid())

    def test_hospital_record_form_invalid(self):
        # Missing required field (patient)
        form = PatientHospitalRecordForm({
            'record_number': 'REC123',
            'first_admission_date': '2023-01-01',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('patient', form.errors)


class PatientFormWithHospitalRecordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_patient_form_with_hospital_record_data(self):
        """Test patient form with hospital record data"""
        hospital_record_data = {
            'hospital_record-hospital': str(self.hospital.id),
            'hospital_record-record_number': 'REC123',
            'hospital_record-first_admission_date': '2023-01-01',
        }
        
        form = PatientForm(
            data={
                'name': 'Test Patient',
                'birthday': '1990-01-01',
                'status': Patient.Status.INPATIENT,
                'current_hospital': self.hospital.id,
            },
            hospital_record_data=hospital_record_data
        )
        
        self.assertTrue(form.is_valid())
        self.assertIsNotNone(form.hospital_record_form)
        self.assertTrue(form.hospital_record_form.has_changed())

    def test_patient_form_hospital_record_validation(self):
        """Test hospital record validation within patient form"""
        hospital_record_data = {
            'hospital': str(self.hospital.id),
            # Missing required record_number
        }
        
        form = PatientForm(
            data={
                'name': 'Test Patient',
                'birthday': '1990-01-01',
                'status': Patient.Status.INPATIENT,
                'current_hospital': self.hospital.id,
            },
            hospital_record_data=hospital_record_data
        )
        
        # Form should still be valid as hospital record fields are optional
        self.assertTrue(form.is_valid())

    def test_patient_form_save_with_hospital_record(self):
        """Test saving patient with hospital record"""
        hospital_record_data = {
            'hospital_record-hospital': str(self.hospital.id),
            'hospital_record-record_number': 'REC123',
            'hospital_record-first_admission_date': '2023-01-01',
        }
        
        form = PatientForm(
            data={
                'name': 'Test Patient',
                'birthday': '1990-01-01',
                'status': Patient.Status.INPATIENT,
                'current_hospital': self.hospital.id,
            },
            hospital_record_data=hospital_record_data
        )
        
        self.assertTrue(form.is_valid())
        # Set required user fields
        form.instance.created_by = self.user
        form.instance.updated_by = self.user
        form.current_user = self.user
        patient = form.save()
        
        # Check that hospital record was created
        self.assertTrue(
            PatientHospitalRecord.objects.filter(
                patient=patient,
                hospital=self.hospital,
                record_number='REC123'
            ).exists()
        )

    def test_nested_hospital_record_form(self):
        """Test the nested hospital record form"""
        form = PatientHospitalRecordNestedForm(
            data={
                'hospital': self.hospital.id,
                'record_number': 'REC456',
                'first_admission_date': '2023-02-01',
            },
            prefix='hospital_record'
        )
        
        self.assertTrue(form.is_valid())
        # All fields should be optional in nested form
        for field in form.fields.values():
            self.assertFalse(field.required)


class HospitalRecordAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            profession_type=0  # MEDICAL_DOCTOR
        )
        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user,
            updated_by=cls.user
        )
        # Associate user with hospital
        cls.user.hospitals.add(cls.hospital)
        
        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.INPATIENT,
            current_hospital=cls.hospital,
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        self.client.login(username='testuser', password='testpassword')

    def test_patient_hospital_records_api(self):
        """Test API endpoint for getting patient hospital records"""
        # Create a hospital record
        record = PatientHospitalRecord.objects.create(
            patient=self.patient,
            hospital=self.hospital,
            record_number='REC123',
            created_by=self.user,
            updated_by=self.user
        )
        
        response = self.client.get(f'/patients/api/{self.patient.id}/hospital-records/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['records']), 1)
        self.assertEqual(data['records'][0]['record_number'], 'REC123')
        self.assertEqual(data['records'][0]['hospital']['name'], 'Test Hospital')

    def test_hospital_record_by_hospital_api_exists(self):
        """Test API endpoint for getting specific hospital record"""
        # Create a hospital record
        record = PatientHospitalRecord.objects.create(
            patient=self.patient,
            hospital=self.hospital,
            record_number='REC456',
            created_by=self.user,
            updated_by=self.user
        )
        
        response = self.client.get(
            f'/patients/api/hospital-record/{self.hospital.id}/?patient_id={self.patient.id}'
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['exists'])
        self.assertEqual(data['record']['record_number'], 'REC456')

    def test_hospital_record_by_hospital_api_not_exists(self):
        """Test API endpoint when hospital record doesn't exist"""
        response = self.client.get(
            f'/patients/api/hospital-record/{self.hospital.id}/?patient_id={self.patient.id}'
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertFalse(data['exists'])
        self.assertIsNone(data['record'])

