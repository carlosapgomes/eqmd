from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.events.models import AdmissionEvent, DischargeEvent, StatusChangeEvent

from ..models import Patient, PatientAdmission, Ward

User = get_user_model()


class StatusChangeViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Navigation-ready fixture: users must have accepted terms and not be
        # forced through the password-change flow or every request is
        # redirected by the lifecycle middleware.
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword",
            profession_type=0,  # MEDICAL_DOCTOR
            terms_accepted=True,
            password_change_required=False,
        )
        cls.ward = Ward.objects.create(
            name="Test Ward",
            abbreviation="TW",
            created_by=cls.user,
            updated_by=cls.user,
        )
        cls.destination_ward = Ward.objects.create(
            name="Destination Ward",
            abbreviation="DST",
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client = Client()
        self.client.login(username="testuser", password="testpassword")
        # Fresh patient per test so status-change scenarios are self-contained
        # and do not depend on the order tests run in.
        self.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1980-01-01",
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_admit_patient_view_success(self):
        """Test admitting a patient changes status to inpatient"""
        url = reverse("apps.patients:admit_patient", kwargs={"pk": self.patient.pk})
        response = self.client.post(
            url,
            {
                "admission_datetime": timezone.localtime(timezone.now()).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "admission_type": PatientAdmission.AdmissionType.SCHEDULED,
                "ward": self.ward.pk,
                "bed": "A101",
                "reason": "Patient needs inpatient care",
            },
        )

        self.assertEqual(response.status_code, 302)  # Redirect after success

        # Check patient status changed
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.INPATIENT)
        self.assertEqual(self.patient.ward, self.ward)
        self.assertEqual(self.patient.bed, "A101")

        # The admission view flow records the status change through the
        # admission timeline event (see patient signals), not a status event
        self.assertTrue(AdmissionEvent.objects.filter(patient=self.patient).exists())
        self.assertFalse(
            StatusChangeEvent.objects.filter(patient=self.patient).exists()
        )

    def test_discharge_patient_view_success(self):
        """Test discharging a patient changes status to outpatient"""
        # Admit the patient with an active admission record first
        self.patient.status = Patient.Status.INPATIENT
        self.patient.ward = self.ward
        self.patient.bed = "A101"
        self.patient.save()
        PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(days=1),
            admission_type=PatientAdmission.AdmissionType.SCHEDULED,
            initial_bed="A101",
            ward=self.ward,
            admission_diagnosis="Test diagnosis",
            created_by=self.user,
            updated_by=self.user,
        )

        url = reverse("apps.patients:discharge_patient", kwargs={"pk": self.patient.pk})
        response = self.client.post(
            url,
            {
                "discharge_datetime": timezone.localtime(timezone.now()).strftime(
                    "%Y-%m-%dT%H:%M"
                ),
                "discharge_type": PatientAdmission.DischargeType.MEDICAL,
                "discharge_reason": "Patient recovered fully",
                "reason": "Medical discharge",
            },
        )

        self.assertEqual(response.status_code, 302)  # Redirect after success

        # Check patient status changed
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.OUTPATIENT)
        self.assertEqual(self.patient.bed, "")  # Bed should be cleared
        self.assertIsNone(self.patient.ward)  # Ward should be cleared

        # Check discharge timeline event was created (the discharge view
        # flow records the status change through DischargeEvent, not a
        # StatusChangeEvent; see patient signals)
        self.assertTrue(DischargeEvent.objects.filter(patient=self.patient).exists())
        self.assertFalse(
            StatusChangeEvent.objects.filter(
                patient=self.patient,
                previous_status=Patient.Status.INPATIENT,
                new_status=Patient.Status.OUTPATIENT,
            ).exists()
        )

    def test_emergency_admission_view_success(self):
        """Test emergency admission changes status to emergency"""
        url = reverse(
            "apps.patients:emergency_admission", kwargs={"pk": self.patient.pk}
        )
        response = self.client.post(
            url, {"ward": self.ward.pk, "bed": "ER-01", "reason": "Emergency situation"}
        )

        self.assertEqual(response.status_code, 302)  # Redirect after success

        # Check patient status changed
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.EMERGENCY)
        self.assertEqual(self.patient.ward, self.ward)
        self.assertEqual(self.patient.bed, "ER-01")

    def test_transfer_patient_view_success(self):
        """Test internal transfer updates location without changing status"""
        # Internal transfers are available for inpatients and keep the status
        self.patient.status = Patient.Status.INPATIENT
        self.patient.ward = self.ward
        self.patient.bed = "A101"
        self.patient.save()
        admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now() - timedelta(hours=1),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            initial_bed="A101",
            ward=self.ward,
            admission_diagnosis="Test diagnosis",
            created_by=self.user,
            updated_by=self.user,
        )

        # A transfer is not a status change, so no new status event is created
        status_events_before = StatusChangeEvent.objects.filter(
            patient=self.patient
        ).count()

        url = reverse("apps.patients:transfer_patient", kwargs={"pk": self.patient.pk})
        response = self.client.post(
            url,
            {
                "ward": self.destination_ward.pk,
                "bed": "B202",
                "transfer_reason": "Specialized care required",
                "reason": "Specialized care required",
            },
        )

        self.assertEqual(response.status_code, 302)  # Redirect after success

        # Location is updated but the status is preserved (internal transfer)
        self.patient.refresh_from_db()
        admission.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.INPATIENT)
        self.assertEqual(self.patient.ward, self.destination_ward)
        self.assertEqual(self.patient.bed, "B202")
        self.assertEqual(admission.ward, self.destination_ward)
        self.assertEqual(admission.final_bed, "B202")

        # A transfer is not a status change, so no new status event is created
        self.assertEqual(
            StatusChangeEvent.objects.filter(patient=self.patient).count(),
            status_events_before,
        )

    def test_declare_death_view_success(self):
        """Test declaring death changes status to deceased"""
        url = reverse("apps.patients:declare_death", kwargs={"pk": self.patient.pk})
        death_time = timezone.now()
        response = self.client.post(
            url,
            {
                "death_time": death_time.strftime("%Y-%m-%dT%H:%M"),
                "reason": "Heart failure",
            },
        )

        self.assertEqual(response.status_code, 302)  # Redirect after success

        # Check patient status changed
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.DECEASED)
        self.assertEqual(self.patient.bed, "")  # Bed should be cleared

    def test_set_outpatient_view_success(self):
        """Test setting patient to outpatient status"""
        # First admit the patient
        self.patient.status = Patient.Status.INPATIENT
        self.patient.save()

        url = reverse("apps.patients:set_outpatient", kwargs={"pk": self.patient.pk})
        response = self.client.post(
            url,
            {
                "follow_up_date": "2023-02-01",
                "follow_up_notes": "Return in 2 weeks",
                "reason": "Stable for outpatient care",
            },
        )

        self.assertEqual(response.status_code, 302)  # Redirect after success

        # Check patient status changed
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.OUTPATIENT)
        self.assertEqual(self.patient.bed, "")  # Bed should be cleared

    def test_status_change_requires_login(self):
        """Test that status change views require authentication"""
        self.client.logout()

        url = reverse("apps.patients:admit_patient", kwargs={"pk": self.patient.pk})
        response = self.client.post(
            url,
            {
                "ward": self.ward.pk,
                "bed": "A101",
                "reason": "Patient needs inpatient care",
            },
        )

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_status_change_invalid_data(self):
        """Test status change with invalid form data"""
        url = reverse("apps.patients:admit_patient", kwargs={"pk": self.patient.pk})
        response = self.client.post(
            url,
            {
                # Missing required ward field
                "bed": "A101",
                "reason": "Patient needs inpatient care",
            },
        )

        self.assertEqual(
            response.status_code, 302
        )  # Still redirects but shows error message

        # Patient status should not change
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.status, Patient.Status.OUTPATIENT)


class StatusChangeEventTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword",
            password_change_required=False,
            terms_accepted=True,
        )
        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1980-01-01",
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user,
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
        self.patient.name = "Updated Name"
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
            reason="Test status change",
        )

        expected = "Status: Ambulatorial → Internado"
        self.assertEqual(str(event), expected)
