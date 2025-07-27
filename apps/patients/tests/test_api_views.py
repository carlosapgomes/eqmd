from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json

from ..models import Patient, PatientRecordNumber, PatientAdmission

User = get_user_model()

class PatientAPITests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.profession = 'doctor'
        self.user.save()
        
        # Grant necessary permissions by creating them if they don't exist
        models = [Patient, PatientRecordNumber, PatientAdmission]
        permissions = ['view_patient', 'view_patientrecordnumber', 'view_patientadmission']
        
        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            for action in ['view']:
                perm, created = Permission.objects.get_or_create(
                    codename=f'{action}_{model._meta.model_name}',
                    name=f'Can {action} {model._meta.verbose_name}',
                    content_type=content_type,
                )
                self.user.user_permissions.add(perm)
        
        self.client = Client()
        self.client.force_login(self.user)

        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday=timezone.now().date() - timedelta(days=365*30),
            created_by=self.user,
            updated_by=self.user
        )

    def test_patient_record_numbers_api(self):
        """Test patient record numbers API endpoint"""
        # Create record numbers
        record1 = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC001',
            is_current=False,
            created_by=self.user,
            updated_by=self.user
        )
        record2 = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='REC002',
            is_current=True,
            previous_record_number='REC001',
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:api_patient_record_numbers', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['patient_id'], str(self.patient.pk))
        self.assertEqual(data['current_record_number'], 'REC002')
        self.assertEqual(len(data['records']), 2)

        # Check current record is first
        self.assertTrue(data['records'][0]['is_current'])
        self.assertEqual(data['records'][0]['record_number'], 'REC002')

    def test_record_number_lookup_api(self):
        """Test record number lookup API"""
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='LOOKUP123',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:api_record_number_lookup', kwargs={'record_number': 'LOOKUP123'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['found'])
        self.assertEqual(data['patient']['id'], str(self.patient.pk))
        self.assertEqual(data['patient']['name'], self.patient.name)

    def test_patient_admissions_api(self):
        """Test patient admissions API endpoint"""
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=2),
            admission_type='emergency',
            initial_bed='A101',
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:api_patient_admissions', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['patient_id'], str(self.patient.pk))
        self.assertTrue(data['is_currently_admitted'])
        self.assertEqual(len(data['admissions']), 1)

        admission_data = data['admissions'][0]
        self.assertEqual(admission_data['admission_type'], 'emergency')
        self.assertEqual(admission_data['initial_bed'], 'A101')
        self.assertTrue(admission_data['is_active'])

    def test_patient_search_api(self):
        """Test enhanced patient search API"""
        # Create record number for search
        PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='SEARCH456',
            is_current=True,
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:api_patient_search')

        # Search by name
        response = self.client.get(url, {'q': 'Test Patient'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)

        # Search by record number
        response = self.client.get(url, {'q': 'SEARCH456'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['current_record_number'], 'SEARCH456')

    def test_record_number_lookup_historical(self):
        """Test lookup for historical record numbers"""
        # Create historical record
        record = PatientRecordNumber.objects.create(
            patient=self.patient,
            record_number='HIST001',
            is_current=False,
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:api_record_number_lookup', kwargs={'record_number': 'HIST001'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['found'])
        self.assertTrue(data['is_historical'])
        self.assertEqual(data['patient']['historical_record_number'], 'HIST001')

    def test_record_number_lookup_not_found(self):
        """Test lookup for non-existent record number"""
        url = reverse('patients:api_record_number_lookup', kwargs={'record_number': 'NONEXISTENT'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['found'])

    def test_admission_detail_api(self):
        """Test admission detail API"""
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=1),
            admission_type='scheduled',
            initial_bed='B201',
            admission_diagnosis='Test diagnosis',
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:api_admission_detail', kwargs={'admission_id': admission.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['id'], str(admission.pk))
        self.assertEqual(data['patient']['id'], str(self.patient.pk))
        self.assertEqual(data['admission_type'], 'scheduled')
        self.assertEqual(data['initial_bed'], 'B201')
        self.assertFalse('discharge_datetime' in data)

    def test_admission_detail_discharged(self):
        """Test admission detail API for discharged patient"""
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=5),
            admission_type='emergency',
            initial_bed='A101',
            discharge_datetime=timezone.now() - timedelta(days=1),
            discharge_type='medical',
            final_bed='A101',
            discharge_diagnosis='Recovered',
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:api_admission_detail', kwargs={'admission_id': admission.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['discharge_type'], 'medical')
        self.assertEqual(data['stay_duration_days'], 4)

    def test_patient_search_pagination(self):
        """Test patient search API pagination"""
        # Create multiple patients
        for i in range(25):
            Patient.objects.create(
                name=f'Test Patient {i}',
                birthday=timezone.now().date() - timedelta(days=365*30),
                created_by=self.user,
                updated_by=self.user
            )

        url = reverse('patients:api_patient_search')
        response = self.client.get(url, {'q': 'Test', 'per_page': 10, 'page': 1})

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(len(data['results']), 10)
        self.assertEqual(data['total'], 26)  # 25 created + 1 from setUp
        self.assertEqual(data['total_pages'], 3)
        self.assertTrue(data['has_next'])
        self.assertFalse(data['has_previous'])

    def test_permission_denied(self):
        """Test permission checks on API endpoints"""
        # Create user without permissions
        no_perm_user = User.objects.create_user(
            username='noperm',
            email='noperm@example.com',
            password='testpass123'
        )
        no_perm_user.profession = 'student'
        no_perm_user.save()
        self.client.force_login(no_perm_user)

        # User doesn't have view_patient permission by default

        url = reverse('patients:api_patient_record_numbers', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission denied')

    def test_empty_search(self):
        """Test empty search query"""
        url = reverse('patients:api_patient_search')
        response = self.client.get(url, {'q': ''})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['results'], [])
        self.assertEqual(data['total'], 0)