from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from ..models import Patient, PatientRecordNumber, PatientAdmission

User = get_user_model()

class RecordNumberViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com',
            profession='doctor'
        )
        self.client = Client()
        self.client.force_login(self.user)
        
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_record_number_create_view(self):
        """Test creating record number via view"""
        url = reverse('patients:record_number_create', kwargs={'patient_id': self.patient.pk})
        
        # GET request should show form
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Novo Número de Prontuário')
        
        # POST request should create record
        data = {
            'record_number': 'REC001',
            'change_reason': 'Initial setup',
            'effective_date': timezone.now().strftime('%Y-%m-%dT%H:%M')
        }
        response = self.client.post(url, data)
        
        # Should redirect to patient detail
        self.assertRedirects(response, reverse('patients:patient_detail', kwargs={'pk': self.patient.pk}))
        
        # Check record was created
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, 'REC001')
    
    def test_quick_record_number_update(self):
        """Test quick record number update"""
        url = reverse('patients:quick_record_number_update', kwargs={'patient_id': self.patient.pk})
        
        data = {
            'record_number': 'QUICK123',
            'change_reason': 'Quick update'
        }
        response = self.client.post(url, data)
        
        # Should redirect to patient detail
        self.assertRedirects(response, reverse('patients:patient_detail', kwargs={'pk': self.patient.pk}))
        
        # Check record was updated
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.current_record_number, 'QUICK123')
    
    def test_record_number_update_view(self):
        """Test updating existing record number"""
        # Create initial record
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            created_by=self.user,
            updated_by=self.user
        )
        
        url = reverse('patients:record_number_update', kwargs={'pk': record.pk})
        
        # GET request should show form with existing data
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'REC001')
        
        # POST request should update record
        data = {
            'record_number': 'REC001_UPDATED',
            'change_reason': 'Updated reason',
            'effective_date': record.effective_date.strftime('%Y-%m-%dT%H:%M')
        }
        response = self.client.post(url, data)
        
        # Should redirect to patient detail
        self.assertRedirects(response, reverse('patients:patient_detail', kwargs={'pk': self.patient.pk}))
        
        # Check record was updated
        record.refresh_from_db()
        self.assertEqual(record.record_number, 'REC001_UPDATED')
        self.assertEqual(record.change_reason, 'Updated reason')
    
    def test_record_number_delete_view(self):
        """Test deleting record number"""
        # Create record
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            is_current=False,  # Only non-current records should be deletable
            created_by=self.user,
            updated_by=self.user
        )
        
        url = reverse('patients:record_number_delete', kwargs={'pk': record.pk})
        
        # GET request should show confirmation
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirmar Exclusão')
        
        # POST request should delete record
        response = self.client.post(url)
        
        # Should redirect to patient detail
        self.assertRedirects(response, reverse('patients:patient_detail', kwargs={'pk': self.patient.pk}))
        
        # Check record was deleted
        self.assertFalse(PatientRecordNumber.objects.filter(pk=record.pk).exists())

class AdmissionViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com',
            profession='doctor'
        )
        self.client = Client()
        self.client.force_login(self.user)
        
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_admission_create_view(self):
        """Test creating admission via view"""
        url = reverse('patients:admit_patient', kwargs={'patient_id': self.patient.pk})
        
        # GET request should show form
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nova Internação')
        
        # POST request should create admission
        data = {
            'admission_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'admission_type': 'emergency',
            'initial_bed': 'A101',
            'admission_diagnosis': 'Emergency condition'
        }
        response = self.client.post(url, data)
        
        # Should redirect to patient detail
        self.assertRedirects(response, reverse('patients:patient_detail', kwargs={'pk': self.patient.pk}))
        
        # Check admission was created
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.INPATIENT)
        self.assertTrue(self.patient.is_currently_admitted())
    
    def test_quick_admission(self):
        """Test quick admission"""
        url = reverse('patients:quick_admit_patient', kwargs={'patient_id': self.patient.pk})
        
        data = {
            'admission_type': 'emergency',
            'initial_bed': 'A101',
            'admission_diagnosis': 'Quick admission'
        }
        response = self.client.post(url, data)
        
        # Should redirect to patient detail
        self.assertRedirects(response, reverse('patients:patient_detail', kwargs={'pk': self.patient.pk}))
        
        # Check admission was created
        self.patient.refresh_from_db()
        self.assertTrue(self.patient.is_currently_admitted())
        
        admission = self.patient.get_current_admission()
        self.assertEqual(admission.admission_type, 'emergency')
        self.assertEqual(admission.initial_bed, 'A101')
    
    def test_discharge_view(self):
        """Test discharging patient via view"""
        # First admit patient
        admission = self.patient.admit_patient(
            admission_datetime=timezone.now() - timedelta(days=2),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user,
            initial_bed='A101'
        )
        
        url = reverse('patients:discharge_patient', kwargs={'pk': admission.pk})
        
        # GET request should show discharge form
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alta Hospitalar')
        
        # POST request should discharge patient
        data = {
            'discharge_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'discharge_type': 'medical',
            'final_bed': 'A101',
            'discharge_diagnosis': 'Condition resolved'
        }
        response = self.client.post(url, data)
        
        # Should redirect to patient detail
        self.assertRedirects(response, reverse('patients:patient_detail', kwargs={'pk': self.patient.pk}))
        
        # Check patient was discharged
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.OUTPATIENT)
        self.assertIsNone(self.patient.ward)
        self.assertFalse(self.patient.is_currently_admitted())
    
    def test_quick_discharge(self):
        """Test quick discharge"""
        # First admit patient
        admission = self.patient.admit_patient(
            admission_datetime=timezone.now() - timedelta(days=1),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user
        )
        
        url = reverse('patients:quick_discharge_patient', kwargs={'admission_id': admission.pk})
        
        data = {
            'discharge_type': 'medical',
            'discharge_diagnosis': 'Quick discharge'
        }
        response = self.client.post(url, data)
        
        # Should redirect to patient detail
        self.assertRedirects(response, reverse('patients:patient_detail', kwargs={'pk': self.patient.pk}))
        
        # Check patient was discharged
        self.patient.refresh_from_db()
        self.assertFalse(self.patient.is_currently_admitted())
        
        admission.refresh_from_db()
        self.assertEqual(admission.discharge_type, 'medical')
        self.assertFalse(admission.is_active)
    
    def test_cannot_admit_already_admitted_patient(self):
        """Test view prevents admitting already admitted patient"""
        # First admit patient
        self.patient.admit_patient(
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            user=self.user
        )
        
        url = reverse('patients:admit_patient', kwargs={'patient_id': self.patient.pk})
        
        data = {
            'admission_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'admission_type': 'scheduled',
            'initial_bed': 'B101'
        }
        response = self.client.post(url, data)
        
        # Should show form with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'já está internado')
    
    def test_permission_required(self):
        """Test that proper permissions are required"""
        # Create user without permissions
        no_perm_user = User.objects.create_user(
            username='noperm', 
            email='noperm@example.com',
            profession='student'
        )
        
        # Remove all permissions
        no_perm_user.user_permissions.clear()
        no_perm_user.groups.clear()
        
        self.client.force_login(no_perm_user)
        
        # Should get permission denied for record number creation
        url = reverse('patients:record_number_create', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        
        # Should get permission denied for admission creation
        url = reverse('patients:admit_patient', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)