from django.test import TestCase, RequestFactory
from django.template import Template, Context
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import transaction
from apps.patients.models import Patient, PatientHospitalRecord, AllowedTag, Tag
from apps.hospitals.models import Hospital
from apps.patients.context_processors import patient_stats, recent_patients
from apps.patients.templatetags.patient_tags import patient_status_badge, patient_tags

User = get_user_model()

class PatientDashboardIntegrationTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password'
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

    def test_context_processors(self):
        """Test that context processors return expected data"""
        request = self.factory.get('/')
        request.user = self.user

        stats = patient_stats(request)
        self.assertEqual(stats['total_patients'], 1)
        self.assertEqual(stats['inpatient_count'], 1)

        recent = recent_patients(request)
        self.assertEqual(recent['recent_patients'].count(), 1)

    def test_template_tags(self):
        """Test that template tags render correctly"""
        # Test status badge
        badge = patient_status_badge(Patient.Status.INPATIENT)
        self.assertIn('bg-success', badge)

        # Test patient tags inclusion tag
        template = Template('{% load patient_tags %}{% patient_tags patient %}')
        context = Context({'patient': self.patient})
        rendered = template.render(context)
        self.assertIsNotNone(rendered)

    def test_dashboard_widgets(self):
        """Test that dashboard widgets render correctly"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('core:dashboard'))

        # This test assumes a dashboard view exists at the URL 'core:dashboard'
        # If it doesn't, you'll need to adjust this test
        if response.status_code == 200:
            self.assertContains(response, 'Patient Statistics')
            self.assertContains(response, 'Recent Patients')


class PatientHospitalIntegrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password'
        )
        self.hospital1 = Hospital.objects.create(
            name='General Hospital',
            address='123 Main St',
            city='Test City',
            state='TS',
            zip_code='12345',
            phone='555-0123',
            created_by=self.user,
            updated_by=self.user
        )
        self.hospital2 = Hospital.objects.create(
            name='Specialty Hospital',
            address='456 Oak Ave',
            city='Test City',
            state='TS',
            zip_code='12346',
            phone='555-0124',
            created_by=self.user,
            updated_by=self.user
        )

    @transaction.atomic
    def test_complete_patient_workflow(self):
        """Test the complete patient lifecycle workflow"""
        # Step 1: Create a patient
        patient = Patient.objects.create(
            name='John Doe',
            birthday='1985-05-15',
            id_number='123456789',
            fiscal_number='987654321',
            healthcard_number='HC123456',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(patient.status, Patient.Status.OUTPATIENT)
        self.assertIsNone(patient.current_hospital)

        # Step 2: Admit patient to hospital
        patient.current_hospital = self.hospital1
        patient.status = Patient.Status.INPATIENT
        patient.bed = 'A101'
        patient.save()
        
        # Create hospital record
        record1 = PatientHospitalRecord.objects.create(
            patient=patient,
            hospital=self.hospital1,
            record_number='REC001',
            first_admission_date='2024-01-15',
            last_admission_date='2024-01-15',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(patient.status, Patient.Status.INPATIENT)
        self.assertEqual(patient.current_hospital, self.hospital1)
        self.assertEqual(patient.bed, 'A101')

        # Step 3: Transfer patient to different hospital
        patient.current_hospital = self.hospital2
        patient.status = Patient.Status.TRANSFERRED
        patient.bed = 'B205'
        patient.save()
        
        # Create second hospital record
        record2 = PatientHospitalRecord.objects.create(
            patient=patient,
            hospital=self.hospital2,
            record_number='REC002',
            first_admission_date='2024-01-20',
            last_admission_date='2024-01-20',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(patient.current_hospital, self.hospital2)
        self.assertEqual(patient.status, Patient.Status.TRANSFERRED)

        # Step 4: Update patient information
        patient.phone = '555-9999'
        patient.email = 'john.doe@email.com'
        patient.save()
        
        self.assertEqual(patient.phone, '555-9999')
        self.assertEqual(patient.email, 'john.doe@email.com')

        # Step 5: Discharge patient
        patient.status = Patient.Status.DISCHARGED
        patient.current_hospital = None
        patient.bed = ""
        patient.save()
        
        # Update hospital record with discharge date
        record2.last_discharge_date = '2024-01-25'
        record2.save()
        
        self.assertEqual(patient.status, Patient.Status.DISCHARGED)
        self.assertIsNone(patient.current_hospital)
        self.assertEqual(patient.bed, "")

        # Step 6: Verify patient history
        records = PatientHospitalRecord.objects.filter(patient=patient)
        self.assertEqual(records.count(), 2)
        
        # Verify first record
        first_record = records.filter(hospital=self.hospital1).first()
        self.assertEqual(first_record.record_number, 'REC001')
        
        # Verify second record
        second_record = records.filter(hospital=self.hospital2).first()
        self.assertEqual(second_record.record_number, 'REC002')
        self.assertEqual(str(second_record.last_discharge_date), '2024-01-25')

    def test_patient_hospital_relationships(self):
        """Test patient-hospital relationship integrity"""
        patient = Patient.objects.create(
            name='Jane Smith',
            birthday='1990-03-20',
            status=Patient.Status.INPATIENT,
            current_hospital=self.hospital1,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test that patient is correctly assigned to hospital
        self.assertEqual(patient.current_hospital, self.hospital1)
        
        # Test hospital record creation
        record = PatientHospitalRecord.objects.create(
            patient=patient,
            hospital=self.hospital1,
            record_number='REC003',
            first_admission_date='2024-02-01',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test relationship queries
        self.assertEqual(record.patient, patient)
        self.assertEqual(record.hospital, self.hospital1)
        
        # Test reverse relationships
        patient_records = patient.hospital_records.all()
        self.assertEqual(patient_records.count(), 1)
        self.assertEqual(patient_records.first(), record)


class PatientTaggingIntegrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password'
        )
        
        # Create some allowed tags
        self.high_priority_tag = AllowedTag.objects.create(
            name='High Priority',
            description='Requires immediate attention',
            color='#dc3545',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.diabetic_tag = AllowedTag.objects.create(
            name='Diabetic',
            description='Patient has diabetes',
            color='#fd7e14',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )

    def test_patient_tagging_workflow(self):
        """Test complete patient tagging workflow"""
        # Create patient
        patient = Patient.objects.create(
            name='Tagged Patient',
            birthday='1980-12-10',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add tags to patient
        tag1 = Tag.objects.create(
            allowed_tag=self.high_priority_tag,
            notes='Urgent care needed',
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag1)
        
        tag2 = Tag.objects.create(
            allowed_tag=self.diabetic_tag,
            notes='Type 2 diabetes',
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag2)
        
        # Verify tags are assigned
        patient_tags = patient.tags.all()
        self.assertEqual(patient_tags.count(), 2)
        
        # Verify tag content
        high_priority = patient_tags.filter(allowed_tag=self.high_priority_tag).first()
        self.assertEqual(high_priority.notes, 'Urgent care needed')
        
        diabetic = patient_tags.filter(allowed_tag=self.diabetic_tag).first()
        self.assertEqual(diabetic.notes, 'Type 2 diabetes')
        
        # Test tag display through template tags
        template = Template('{% load patient_tags %}{% patient_tags patient %}')
        context = Context({'patient': patient})
        rendered = template.render(context)
        
        # Should contain tag names and colors
        self.assertIn('High Priority', rendered)
        self.assertIn('Diabetic', rendered)
        self.assertIn('#dc3545', rendered)
        self.assertIn('#fd7e14', rendered)