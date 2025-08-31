"""
Integration tests for admission edit views.

This module tests the admission edit view endpoints to ensure they properly
handle permissions, form validation, and data updates.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from apps.patients.models import Patient, PatientAdmission, Ward
from apps.patients.forms import EditAdmissionForm, EditDischargeForm
from apps.accounts.models import EqmdCustomUser


User = get_user_model()


class AdmissionEditViewTests(TestCase):
    """Test admission edit view functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create users with different profession types
        self.doctor = EqmdCustomUser.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=0,  # MEDICAL_DOCTOR
            terms_accepted=True,
            password_change_required=False
        )
        
        self.resident = EqmdCustomUser.objects.create_user(
            username='resident',
            email='resident@test.com',
            password='testpass123',
            profession_type=1,  # RESIDENT
            terms_accepted=True,
            password_change_required=False
        )
        
        self.nurse = EqmdCustomUser.objects.create_user(
            username='nurse',
            email='nurse@test.com',
            password='testpass123',
            profession_type=2,  # NURSE
            terms_accepted=True,
            password_change_required=False
        )
        
        self.student = EqmdCustomUser.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            profession_type=4,  # STUDENT
            terms_accepted=True,
            password_change_required=False
        )
        
        # Create a ward
        self.ward = Ward.objects.create(
            name='Test Ward',
            abbreviation='TW',
            description='Test description',
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Create patients for different test scenarios
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        self.patient2 = Patient.objects.create(
            name='Test Patient 2',
            birthday='1985-06-15',
            status=Patient.Status.INPATIENT,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Create active admission (within 24h for creator permission)
        self.active_admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(hours=1),
            admission_type='regular',
            initial_bed='A01',
            ward=self.ward,
            admission_diagnosis='Test diagnosis',
            created_by=self.nurse,
            updated_by=self.nurse
        )
        
        # Create old active admission (beyond 24h) - use different patient
        self.old_active_admission = PatientAdmission.objects.create(
            patient=self.patient2,
            admission_datetime=timezone.now() - timedelta(hours=25),
            admission_type='regular',
            initial_bed='A02',
            ward=self.ward,
            admission_diagnosis='Test old diagnosis',
            created_by=self.nurse,
            updated_by=self.nurse
        )
        
        self.patient3 = Patient.objects.create(
            name='Test Patient 3',
            birthday='1988-03-10',
            status=Patient.Status.DISCHARGED,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        self.patient4 = Patient.objects.create(
            name='Test Patient 4',
            birthday='1992-12-05',
            status=Patient.Status.DISCHARGED,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Create discharged admission (within 24h)
        self.discharged_admission = PatientAdmission.objects.create(
            patient=self.patient3,
            admission_datetime=timezone.now() - timedelta(hours=48),
            admission_type='regular',
            initial_bed='A03',
            ward=self.ward,
            admission_diagnosis='Test discharged diagnosis',
            discharge_datetime=timezone.now() - timedelta(hours=1),
            discharge_type='improved',
            final_bed='A03',
            discharge_diagnosis='Discharged diagnosis',
            created_by=self.nurse,
            updated_by=self.nurse
        )
        
        # Create old discharged admission (beyond 24h)
        self.old_discharged_admission = PatientAdmission.objects.create(
            patient=self.patient4,
            admission_datetime=timezone.now() - timedelta(hours=72),
            admission_type='regular',
            initial_bed='A04',
            ward=self.ward,
            admission_diagnosis='Test old discharged diagnosis',
            discharge_datetime=timezone.now() - timedelta(hours=25),
            discharge_type='improved',
            final_bed='A04',
            discharge_diagnosis='Old discharged diagnosis',
            created_by=self.nurse,
            updated_by=self.nurse
        )

    def test_edit_admission_data_get_success_doctor(self):
        """Doctor can access edit admission data form."""
        self.client.login(email='doctor@test.com', password='testpass123')
        
        url = reverse('apps.patients:edit_admission_data', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': self.active_admission.pk
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar Dados da Internação')
        self.assertIsInstance(response.context['form'], EditAdmissionForm)

    def test_edit_admission_data_get_success_creator_within_24h(self):
        """Creator can access edit admission data form within 24h."""
        self.client.login(email='nurse@test.com', password='testpass123')
        
        url = reverse('apps.patients:edit_admission_data', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': self.active_admission.pk
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_edit_admission_data_get_permission_denied_creator_after_24h(self):
        """Creator cannot access edit admission data form after 24h."""
        self.client.login(email='nurse@test.com', password='testpass123')
        
        url = reverse('apps.patients:edit_admission_data', kwargs={
            'patient_id': self.patient2.pk,
            'admission_id': self.old_active_admission.pk
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_edit_admission_data_get_permission_denied_non_creator(self):
        """Non-creator non-doctor cannot access edit admission data form."""
        self.client.login(email='student@test.com', password='testpass123')
        
        url = reverse('apps.patients:edit_admission_data', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': self.active_admission.pk
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_edit_admission_data_get_permission_denied_discharged_admission(self):
        """Cannot access edit form for discharged admission."""
        self.client.login(email='doctor@test.com', password='testpass123')
        
        url = reverse('apps.patients:edit_admission_data', kwargs={
            'patient_id': self.patient3.pk,
            'admission_id': self.discharged_admission.pk
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_edit_admission_data_post_success(self):
        """Successful admission data edit."""
        self.client.login(email='doctor@test.com', password='testpass123')
        
        url = reverse('apps.patients:edit_admission_data', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': self.active_admission.pk
        })
        
        new_diagnosis = 'Updated diagnosis'
        response = self.client.post(url, {
            'admission_datetime': self.active_admission.admission_datetime.strftime('%Y-%m-%dT%H:%M'),
            'admission_type': 'emergency',
            'initial_bed': 'B01',
            'ward': self.ward.pk,
            'admission_diagnosis': new_diagnosis
        })
        
        # Should redirect to patient detail
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('apps.patients:patient_detail', kwargs={'pk': self.patient.pk}))
        
        # Check data was updated
        self.active_admission.refresh_from_db()
        self.assertEqual(self.active_admission.admission_diagnosis, new_diagnosis)
        self.assertEqual(self.active_admission.admission_type, 'emergency')
        self.assertEqual(self.active_admission.initial_bed, 'B01')
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('sucesso' in str(message) for message in messages))

    def test_edit_admission_data_post_invalid_form(self):
        """Edit admission data with invalid form data."""
        self.client.login(email='doctor@test.com', password='testpass123')
        
        url = reverse('apps.patients:edit_admission_data', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': self.active_admission.pk
        })
        
        # Submit invalid data (missing required field)
        response = self.client.post(url, {
            'admission_datetime': '',  # Invalid - required field
            'admission_type': 'emergency',
            'initial_bed': 'B01',
            'ward': self.ward.pk,
            'admission_diagnosis': 'Updated diagnosis'
        })
        
        # Should stay on same page with form errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Erro ao atualizar')
        
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Erro' in str(message) for message in messages))


class DischargeEditViewTests(TestCase):
    """Test discharge edit view functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create users
        self.doctor = EqmdCustomUser.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=0,  # MEDICAL_DOCTOR
            terms_accepted=True,
            password_change_required=False
        )
        
        self.nurse = EqmdCustomUser.objects.create_user(
            username='nurse',
            email='nurse@test.com',
            password='testpass123',
            profession_type=2,  # NURSE
            terms_accepted=True,
            password_change_required=False
        )
        
        # Create ward and patient
        self.ward = Ward.objects.create(
            name='Test Ward',
            abbreviation='TW',
            description='Test description',
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Create discharged admission (within 24h)
        self.discharged_admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(hours=48),
            admission_type='regular',
            initial_bed='A01',
            ward=self.ward,
            admission_diagnosis='Test diagnosis',
            discharge_datetime=timezone.now() - timedelta(hours=1),
            discharge_type='improved',
            final_bed='A01',
            discharge_diagnosis='Discharged diagnosis',
            created_by=self.nurse,
            updated_by=self.nurse
        )
        
        # Create old discharged admission (beyond 24h)
        self.old_discharged_admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(hours=72),
            admission_type='regular',
            initial_bed='A02',
            ward=self.ward,
            admission_diagnosis='Test old diagnosis',
            discharge_datetime=timezone.now() - timedelta(hours=25),
            discharge_type='improved',
            final_bed='A02',
            discharge_diagnosis='Old discharged diagnosis',
            created_by=self.nurse,
            updated_by=self.nurse
        )

    def test_edit_discharge_data_get_success_doctor_within_24h(self):
        """Doctor can access edit discharge data form within 24h."""
        self.client.login(email='doctor@test.com', password='testpass123')
        
        url = reverse('apps.patients:edit_discharge_data', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': self.discharged_admission.pk
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar Dados da Alta')
        self.assertIsInstance(response.context['form'], EditDischargeForm)

    def test_edit_discharge_data_get_permission_denied_nurse(self):
        """Nurse cannot access edit discharge data form."""
        self.client.login(email='nurse@test.com', password='testpass123')
        
        url = reverse('apps.patients:edit_discharge_data', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': self.discharged_admission.pk
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_edit_discharge_data_get_permission_denied_after_24h(self):
        """Cannot access edit discharge data form after 24h."""
        self.client.login(email='doctor@test.com', password='testpass123')
        
        url = reverse('apps.patients:edit_discharge_data', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': self.old_discharged_admission.pk
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_edit_discharge_data_post_success(self):
        """Successful discharge data edit."""
        self.client.login(email='doctor@test.com', password='testpass123')
        
        url = reverse('apps.patients:edit_discharge_data', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': self.discharged_admission.pk
        })
        
        new_diagnosis = 'Updated discharge diagnosis'
        response = self.client.post(url, {
            'discharge_datetime': self.discharged_admission.discharge_datetime.strftime('%Y-%m-%dT%H:%M'),
            'discharge_type': 'transferred',
            'final_bed': 'B01',
            'discharge_diagnosis': new_diagnosis
        })
        
        # Should redirect to patient detail
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('apps.patients:patient_detail', kwargs={'pk': self.patient.pk}))
        
        # Check data was updated
        self.discharged_admission.refresh_from_db()
        self.assertEqual(self.discharged_admission.discharge_diagnosis, new_diagnosis)
        self.assertEqual(self.discharged_admission.discharge_type, 'transferred')
        self.assertEqual(self.discharged_admission.final_bed, 'B01')


class CancelDischargeViewTests(TestCase):
    """Test cancel discharge view functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create users
        self.doctor = EqmdCustomUser.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=0,  # MEDICAL_DOCTOR
            terms_accepted=True,
            password_change_required=False
        )
        
        self.resident = EqmdCustomUser.objects.create_user(
            username='resident',
            email='resident@test.com',
            password='testpass123',
            profession_type=1,  # RESIDENT
            terms_accepted=True,
            password_change_required=False
        )
        
        self.nurse = EqmdCustomUser.objects.create_user(
            username='nurse',
            email='nurse@test.com',
            password='testpass123',
            profession_type=2,  # NURSE
            terms_accepted=True,
            password_change_required=False
        )
        
        # Create ward and patient
        self.ward = Ward.objects.create(
            name='Test Ward',
            abbreviation='TW',
            description='Test description',
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.DISCHARGED,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Create discharged admission (within 24h)
        self.discharged_admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(hours=48),
            admission_type='regular',
            initial_bed='A01',
            ward=self.ward,
            admission_diagnosis='Test diagnosis',
            discharge_datetime=timezone.now() - timedelta(hours=1),
            discharge_type='improved',
            final_bed='A01',
            discharge_diagnosis='Discharged diagnosis',
            created_by=self.nurse,
            updated_by=self.nurse
        )

    def test_cancel_discharge_success_doctor(self):
        """Doctor can successfully cancel discharge within 24h."""
        self.client.login(email='doctor@test.com', password='testpass123')
        
        url = reverse('apps.patients:cancel_discharge', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': self.discharged_admission.pk
        })
        
        response = self.client.post(url)
        
        # Should redirect to patient detail
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('apps.patients:patient_detail', kwargs={'pk': self.patient.pk}))
        
        # Check discharge was cancelled
        self.discharged_admission.refresh_from_db()
        self.assertIsNone(self.discharged_admission.discharge_datetime)
        self.assertIsNone(self.discharged_admission.discharge_type)
        self.assertIsNone(self.discharged_admission.final_bed)
        self.assertIsNone(self.discharged_admission.discharge_diagnosis)
        
        # Check patient status updated
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, 'admitted')
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('cancelada com sucesso' in str(message) for message in messages))

    def test_cancel_discharge_success_resident(self):
        """Resident can successfully cancel discharge within 24h."""
        self.client.login(email='resident@test.com', password='testpass123')
        
        url = reverse('apps.patients:cancel_discharge', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': self.discharged_admission.pk
        })
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

    def test_cancel_discharge_permission_denied_nurse(self):
        """Nurse cannot cancel discharge."""
        self.client.login(email='nurse@test.com', password='testpass123')
        
        url = reverse('apps.patients:cancel_discharge', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': self.discharged_admission.pk
        })
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_cancel_discharge_get_method_not_allowed(self):
        """GET method should not be allowed for cancel discharge."""
        self.client.login(email='doctor@test.com', password='testpass123')
        
        url = reverse('apps.patients:cancel_discharge', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': self.discharged_admission.pk
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


class AdmissionEditViewsEdgeCaseTests(TestCase):
    """Test edge cases for admission edit views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        self.doctor = EqmdCustomUser.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=0,  # MEDICAL_DOCTOR
            terms_accepted=True,
            password_change_required=False
        )
        
        self.ward = Ward.objects.create(
            name='Test Ward',
            abbreviation='TW',
            description='Test description',
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.doctor,
            updated_by=self.doctor
        )

    def test_edit_admission_404_invalid_patient(self):
        """Edit admission with invalid patient ID returns 404."""
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now(),
            admission_type='regular',
            initial_bed='A01',
            ward=self.ward,
            admission_diagnosis='Test',
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        self.client.login(email='doctor@test.com', password='testpass123')
        
        from uuid import uuid4
        url = reverse('apps.patients:edit_admission_data', kwargs={
            'patient_id': uuid4(),  # Invalid patient ID
            'admission_id': admission.pk
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_edit_admission_404_invalid_admission(self):
        """Edit admission with invalid admission ID returns 404."""
        self.client.login(email='doctor@test.com', password='testpass123')
        
        from uuid import uuid4
        url = reverse('apps.patients:edit_admission_data', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': uuid4()  # Invalid admission ID
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_access_redirects_to_login(self):
        """Unauthenticated users are redirected to login."""
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now(),
            admission_type='regular',
            initial_bed='A01',
            ward=self.ward,
            admission_diagnosis='Test',
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        url = reverse('apps.patients:edit_admission_data', kwargs={
            'patient_id': self.patient.pk,
            'admission_id': admission.pk
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)