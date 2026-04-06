from datetime import timedelta

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient, PatientAdmission, Ward


class PatientDetailAdmissionActionTargetsTests(TestCase):
    """Ensure admission action buttons target the modal IDs used by JavaScript."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = EqmdCustomUser.objects.create_user(
            username='doctor-detail-actions',
            email='doctor-detail-actions@test.com',
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
            name='Action Target Ward',
            abbreviation='ATW',
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        cls.patient = Patient.objects.create(
            name='Patient With Admission Actions',
            birthday='1985-01-01',
            status=Patient.Status.INPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        cls.discharged_admission = PatientAdmission.objects.create(
            patient=cls.patient,
            admission_datetime=timezone.now() - timedelta(days=2),
            discharge_datetime=timezone.now() - timedelta(hours=1),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            discharge_type=PatientAdmission.DischargeType.MEDICAL,
            initial_bed='A01',
            final_bed='A01',
            ward=cls.ward,
            admission_diagnosis='Old diagnosis',
            discharge_diagnosis='Recovered',
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        cls.active_admission = PatientAdmission.objects.create(
            patient=cls.patient,
            admission_datetime=timezone.now() - timedelta(hours=2),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            initial_bed='B02',
            ward=cls.ward,
            admission_diagnosis='Current diagnosis',
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        self.client.force_login(self.doctor)

    def test_patient_detail_uses_js_modal_targets_for_admission_actions(self):
        response = self.client.get(
            reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-bs-target="#editAdmissionModal"')
        self.assertContains(response, 'data-bs-target="#editDischargeModal"')
        self.assertContains(response, 'data-bs-target="#cancelDischargeModal"')
        self.assertContains(response, 'data-bs-target="#discharge_patientModal"')

        self.assertNotContains(response, 'data-bs-target="#edit_admissionModal"')
        self.assertNotContains(response, 'data-bs-target="#edit_dischargeModal"')
        self.assertNotContains(response, 'data-bs-target="#cancel_dischargeModal"')
