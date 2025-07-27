from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from ..models import Patient, Ward
from apps.events.models import StatusChangeEvent

User = get_user_model()


class StatusChangeViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            profession_type=0  # MEDICAL_DOCTOR
        )
        cls.ward = Ward.objects.create(
            name='Test Ward',
            abbreviation='TW',
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

    def setUp(self):
        self.client = Client()
        self.client.login(username='testuser', password='testpassword')

    def test_admit_patient_view_success(self):
        """Test admitting a patient changes status to inpatient"""
        url = reverse('apps.patients:admit_patient', kwargs={'pk': self.patient.pk})
        response = self.client.post(url, {
            'ward': self.ward.pk,
            'bed': 'A101',
            'reason': 'Patient needs inpatient care'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check patient status changed
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.INPATIENT)
        self.assertEqual(self.patient.ward, self.ward)
        self.assertEqual(self.patient.bed, 'A101')
        
        # Check status change event was created
        self.assertTrue(
            StatusChangeEvent.objects.filter(
                patient=self.patient,
                previous_status=Patient.Status.OUTPATIENT,
                new_status=Patient.Status.INPATIENT
            ).exists()
        )

    def test_discharge_patient_view_success(self):
        """Test discharging a patient changes status to discharged"""
        # First admit the patient
        self.patient.status = Patient.Status.INPATIENT
        self.patient.ward = self.ward
        self.patient.bed = 'A101'
        self.patient.save()
        
        url = reverse('apps.patients:discharge_patient', kwargs={'pk': self.patient.pk})
        response = self.client.post(url, {
            'discharge_reason': 'Patient recovered fully',
            'reason': 'Medical discharge'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check patient status changed
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.DISCHARGED)
        self.assertEqual(self.patient.bed, '')  # Bed should be cleared
        
        # Check status change event was created
        self.assertTrue(
            StatusChangeEvent.objects.filter(
                patient=self.patient,
                previous_status=Patient.Status.INPATIENT,
                new_status=Patient.Status.DISCHARGED
            ).exists()
        )

    def test_emergency_admission_view_success(self):
        """Test emergency admission changes status to emergency"""
        url = reverse('apps.patients:emergency_admission', kwargs={'pk': self.patient.pk})
        response = self.client.post(url, {
            'ward': self.ward.pk,
            'bed': 'ER-01',
            'reason': 'Emergency situation'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check patient status changed
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.EMERGENCY)
        self.assertEqual(self.patient.ward, self.ward)
        self.assertEqual(self.patient.bed, 'ER-01')

    def test_transfer_patient_view_success(self):
        """Test transferring a patient changes status to transferred"""
        url = reverse('apps.patients:transfer_patient', kwargs={'pk': self.patient.pk})
        response = self.client.post(url, {
            'destination': 'Another Hospital',
            'reason': 'Specialized care required'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check patient status changed
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.TRANSFERRED)
        self.assertEqual(self.patient.bed, '')  # Bed should be cleared

    def test_declare_death_view_success(self):
        """Test declaring death changes status to deceased"""
        url = reverse('apps.patients:declare_death', kwargs={'pk': self.patient.pk})
        death_time = timezone.now()
        response = self.client.post(url, {
            'death_time': death_time.strftime('%Y-%m-%dT%H:%M'),
            'reason': 'Heart failure'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check patient status changed
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.DECEASED)
        self.assertEqual(self.patient.bed, '')  # Bed should be cleared

    def test_set_outpatient_view_success(self):
        """Test setting patient to outpatient status"""
        # First admit the patient
        self.patient.status = Patient.Status.INPATIENT
        self.patient.save()
        
        url = reverse('apps.patients:set_outpatient', kwargs={'pk': self.patient.pk})
        response = self.client.post(url, {
            'follow_up_date': '2023-02-01',
            'follow_up_notes': 'Return in 2 weeks',
            'reason': 'Stable for outpatient care'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check patient status changed
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.OUTPATIENT)
        self.assertEqual(self.patient.bed, '')  # Bed should be cleared

    def test_status_change_requires_login(self):
        """Test that status change views require authentication"""
        self.client.logout()
        
        url = reverse('apps.patients:admit_patient', kwargs={'pk': self.patient.pk})
        response = self.client.post(url, {
            'ward': self.ward.pk,
            'bed': 'A101',
            'reason': 'Patient needs inpatient care'
        })
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_status_change_invalid_data(self):
        """Test status change with invalid form data"""
        url = reverse('apps.patients:admit_patient', kwargs={'pk': self.patient.pk})
        response = self.client.post(url, {
            # Missing required ward field
            'bed': 'A101',
            'reason': 'Patient needs inpatient care'
        })
        
        self.assertEqual(response.status_code, 302)  # Still redirects but shows error message
        
        # Patient status should not change
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.OUTPATIENT)


class StatusChangeEventTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_status_change_creates_event(self):
        """Test that changing patient status creates a timeline event"""
        # Change patient status
        self.patient.status = Patient.Status.INPATIENT
        self.patient.updated_by = self.user
        self.patient.save()
        
        # Check that event was created
        event = StatusChangeEvent.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.previous_status, Patient.Status.OUTPATIENT)
        self.assertEqual(event.new_status, Patient.Status.INPATIENT)
        self.assertEqual(event.created_by, self.user)

    def test_no_event_for_unchanged_status(self):
        """Test that no event is created if status doesn't change"""
        original_count = StatusChangeEvent.objects.count()
        
        # Save patient without changing status
        self.patient.name = 'Updated Name'
        self.patient.save()
        
        # No new event should be created
        self.assertEqual(StatusChangeEvent.objects.count(), original_count)

    def test_status_change_event_string_representation(self):
        """Test string representation of status change event"""
        event = StatusChangeEvent.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Status change test",
            created_by=self.user,
            updated_by=self.user,
            previous_status=Patient.Status.OUTPATIENT,
            new_status=Patient.Status.INPATIENT,
            reason="Test status change"
        )
        
        expected = "Status: Ambulatorial → Internado"
        self.assertEqual(str(event), expected)