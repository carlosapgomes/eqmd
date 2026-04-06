from datetime import timedelta

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient, PatientAdmission, Ward


class AdmissionModalViewsSmokeTests(TestCase):
    """Smoke tests for the AJAX admission/discharge modal views used in the UI."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = EqmdCustomUser.objects.create_user(
            username='doctor-modal-smoke',
            email='doctor-modal-smoke@test.com',
            password='testpass123',
            profession_type=0,
            terms_accepted=True,
            password_change_required=False,
        )

        patient_content_type = ContentType.objects.get_for_model(Patient)
        view_patient_permission = Permission.objects.get(
            content_type=patient_content_type,
            codename='view_patient',
        )
        cls.doctor.user_permissions.add(view_patient_permission)

        cls.ward = Ward.objects.create(
            name='Modal Smoke Ward',
            abbreviation='MSW',
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        cls.active_patient = Patient.objects.create(
            name='Modal Active Patient',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        cls.discharged_patient = Patient.objects.create(
            name='Modal Discharged Patient',
            birthday='1988-05-10',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        cls.discharged_admission = PatientAdmission.objects.create(
            patient=cls.discharged_patient,
            admission_datetime=timezone.now() - timedelta(days=3),
            discharge_datetime=timezone.now() - timedelta(hours=20),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            initial_bed='A10',
            final_bed='A10',
            ward=cls.ward,
            admission_diagnosis='Resolved issue',
            discharge_diagnosis='Recovered',
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        cls.active_admission = PatientAdmission.objects.create(
            patient=cls.active_patient,
            admission_datetime=timezone.now() - timedelta(hours=3),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            initial_bed='B20',
            ward=cls.ward,
            admission_diagnosis='Needs observation',
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        self.client.force_login(self.doctor)

    def test_edit_admission_modal_view_renders(self):
        response = self.client.get(
            reverse(
                'patients:edit_admission_data',
                kwargs={
                    'patient_id': self.active_patient.pk,
                    'admission_id': self.active_admission.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar Dados da Internação')

    def test_edit_admission_modal_post_redirects_to_patient_detail(self):
        response = self.client.post(
            reverse(
                'patients:edit_admission_data',
                kwargs={
                    'patient_id': self.active_patient.pk,
                    'admission_id': self.active_admission.pk,
                },
            ),
            {
                'admission_datetime': self.active_admission.admission_datetime.strftime('%Y-%m-%dT%H:%M'),
                'admission_type': PatientAdmission.AdmissionType.EMERGENCY,
                'initial_bed': 'B21',
                'ward': self.ward.pk,
                'admission_diagnosis': 'Updated observation',
            },
        )

        self.assertRedirects(
            response,
            reverse('patients:patient_detail', kwargs={'pk': self.active_patient.pk}),
        )

    def test_edit_discharge_modal_view_renders(self):
        response = self.client.get(
            reverse(
                'patients:edit_discharge_data',
                kwargs={
                    'patient_id': self.discharged_patient.pk,
                    'admission_id': self.discharged_admission.pk,
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar Dados da Alta')

    def test_edit_discharge_modal_post_redirects_to_patient_detail(self):
        response = self.client.post(
            reverse(
                'patients:edit_discharge_data',
                kwargs={
                    'patient_id': self.discharged_patient.pk,
                    'admission_id': self.discharged_admission.pk,
                },
            ),
            {
                'discharge_datetime': self.discharged_admission.discharge_datetime.strftime('%Y-%m-%dT%H:%M'),
                'discharge_type': PatientAdmission.DischargeType.MEDICAL,
                'final_bed': 'A11',
                'discharge_diagnosis': 'Updated discharge summary',
            },
        )

        self.assertRedirects(
            response,
            reverse('patients:patient_detail', kwargs={'pk': self.discharged_patient.pk}),
        )

    def test_cancel_discharge_redirects_to_patient_detail_and_reactivates_admission(self):
        response = self.client.post(
            reverse(
                'patients:cancel_discharge',
                kwargs={
                    'patient_id': self.discharged_patient.pk,
                    'admission_id': self.discharged_admission.pk,
                },
            )
        )

        self.assertRedirects(
            response,
            reverse('patients:patient_detail', kwargs={'pk': self.discharged_patient.pk}),
        )

        self.discharged_admission.refresh_from_db()
        self.discharged_patient.refresh_from_db()
        self.assertTrue(self.discharged_admission.is_active)
        self.assertIsNone(self.discharged_admission.discharge_datetime)
        self.assertEqual(self.discharged_admission.discharge_type, '')
        self.assertEqual(self.discharged_patient.current_admission_id, self.discharged_admission.pk)
