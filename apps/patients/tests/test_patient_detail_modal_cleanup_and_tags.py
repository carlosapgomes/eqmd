from datetime import timedelta

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import AllowedTag, Patient, PatientAdmission, Tag, Ward


class PatientDetailModalCleanupAndTagsTests(TestCase):
    """Regression tests for non-admission patient detail modals and guarded tag JS."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = EqmdCustomUser.objects.create_user(
            username='doctor-detail-cleanup',
            email='doctor-detail-cleanup@test.com',
            password='testpass123',
            profession_type=0,
            terms_accepted=True,
            password_change_required=False,
        )
        cls.viewer = EqmdCustomUser.objects.create_user(
            username='viewer-detail-cleanup',
            email='viewer-detail-cleanup@test.com',
            password='testpass123',
            profession_type=2,
            terms_accepted=True,
            password_change_required=False,
        )

        patient_content_type = ContentType.objects.get_for_model(Patient)
        view_patient_permission = Permission.objects.get(
            content_type=patient_content_type,
            codename='view_patient',
        )
        change_patient_permission = Permission.objects.get(
            content_type=patient_content_type,
            codename='change_patient',
        )
        cls.doctor.user_permissions.add(view_patient_permission, change_patient_permission)
        cls.viewer.user_permissions.add(view_patient_permission)

        cls.ward = Ward.objects.create(
            name='Cleanup Ward',
            abbreviation='CLN',
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        cls.patient = Patient.objects.create(
            name='Patient With Other Modals',
            birthday='1985-01-01',
            status=Patient.Status.INPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        PatientAdmission.objects.create(
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

        PatientAdmission.objects.create(
            patient=cls.patient,
            admission_datetime=timezone.now() - timedelta(hours=2),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            initial_bed='B02',
            ward=cls.ward,
            admission_diagnosis='Current diagnosis',
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

        cls.allowed_tag = AllowedTag.objects.create(
            name='Cleanup Tag',
            color='#0055aa',
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        Tag.objects.create(
            allowed_tag=cls.allowed_tag,
            patient=cls.patient,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        self.client.force_login(self.doctor)

    def test_patient_detail_other_modal_buttons_match_existing_modal_ids(self):
        response = self.client.get(
            reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-bs-target="#updateRecordNumberModal"')
        self.assertContains(response, 'id="updateRecordNumberModal"')
        self.assertContains(response, 'data-bs-target="#addTagModal"')
        self.assertContains(response, 'id="addTagModal"')
        self.assertContains(response, 'data-bs-target="#manageTagsModal"')
        self.assertContains(response, 'id="manageTagsModal"')
        self.assertContains(response, 'data-bs-target="#transfer_patientModal"')
        self.assertContains(response, 'id="transfer_patientModal"')
        self.assertContains(response, 'data-bs-target="#set_outpatientModal"')
        self.assertContains(response, 'id="set_outpatientModal"')
        self.assertContains(response, 'data-bs-target="#declare_deathModal"')
        self.assertContains(response, 'id="declare_deathModal"')
        self.assertNotContains(response, 'id="admissionModal"')
        self.assertNotContains(response, 'id="dischargeModal"')

    def test_view_only_patient_detail_uses_guarded_tag_management_script(self):
        self.client.force_login(self.viewer)

        response = self.client.get(
            reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'const canManageTags = false;')
        self.assertContains(response, 'if (canManageTags && addTagModal)')
        self.assertContains(response, 'if (canManageTags && addTagButton)')
        self.assertNotContains(response, 'data-bs-target="#addTagModal"')
        self.assertNotContains(response, 'data-bs-target="#manageTagsModal"')
