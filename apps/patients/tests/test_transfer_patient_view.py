from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.patients.models import Patient, PatientAdmission, Ward


User = get_user_model()


class TransferPatientViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="transfer_user",
            email="transfer@example.com",
            password="testpassword",
            profession_type=0,
        )
        self.user.password_change_required = False
        self.user.terms_accepted = True
        self.user.terms_accepted_at = timezone.now()
        self.user.save(
            update_fields=["password_change_required", "terms_accepted", "terms_accepted_at"]
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.origin_ward = Ward.objects.create(
            name="Origem",
            abbreviation="ORG",
            created_by=self.user,
            updated_by=self.user,
        )
        self.destination_ward = Ward.objects.create(
            name="Destino",
            abbreviation="DST",
            created_by=self.user,
            updated_by=self.user,
        )
        self.patient = Patient.objects.create(
            name="Paciente Transferencia",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            ward=self.origin_ward,
            bed="A101",
            created_by=self.user,
            updated_by=self.user,
        )
        self.admission = PatientAdmission.objects.create(
            patient=self.patient,
            admission_datetime=timezone.now(),
            admission_type=PatientAdmission.AdmissionType.EMERGENCY,
            ward=self.origin_ward,
            initial_bed="A101",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_transfer_updates_patient_and_admission_bed(self):
        response = self.client.post(
            reverse("apps.patients:transfer_patient", kwargs={"pk": self.patient.pk}),
            {
                "ward": str(self.destination_ward.pk),
                "bed": "B202",
                "transfer_reason": "Mudanca de ala",
                "reason": "Mudanca de ala",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.patient.refresh_from_db()
        self.admission.refresh_from_db()

        self.assertEqual(self.patient.ward, self.destination_ward)
        self.assertEqual(self.patient.bed, "B202")
        self.assertEqual(self.admission.ward, self.destination_ward)
        self.assertEqual(self.admission.final_bed, "B202")
