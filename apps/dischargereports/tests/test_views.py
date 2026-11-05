from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.dischargereports.models import DischargeReport
from apps.patients.models import Patient

User = get_user_model()


class DischargeReportViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.patient = Patient.objects.create(
            name="Test Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_create_view_requires_login(self):
        """Test that create view requires authentication"""
        url = reverse(
            "apps.dischargereports:patient_dischargereport_create",
            kwargs={"patient_id": self.patient.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_create_form_uses_native_date_and_datetime_pickers(self):
        """Create form should render native date/datetime picker inputs."""
        self.client.login(username="testuser", password="testpass123")
        url = reverse(
            "apps.dischargereports:patient_dischargereport_create",
            kwargs={"patient_id": self.patient.pk},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'type="datetime-local"')
        self.assertContains(response, 'type="date"', count=2)

    def test_create_view_accepts_ptbr_date_and_datetime_inputs(self):
        """Create view should accept pt-BR manual date input values."""
        self.client.login(username="testuser", password="testpass123")
        url = reverse(
            "apps.dischargereports:patient_dischargereport_create",
            kwargs={"patient_id": self.patient.pk},
        )

        now = timezone.now()
        data = {
            "patient": self.patient.pk,
            "event_datetime": now.strftime("%d/%m/%Y %H:%M"),
            "description": "Relatório em formato pt-BR",
            "admission_date": "01/01/2024",
            "discharge_date": "05/01/2024",
            "medical_specialty": "Clínica Médica",
            "admission_history": "História",
            "problems_and_diagnosis": "Diagnóstico",
            "exams_list": "Exames",
            "procedures_list": "Procedimentos",
            "inpatient_medical_history": "Evolução",
            "discharge_status": "Estável",
            "discharge_recommendations": "Retorno ambulatorial",
            "save_draft": "Save Draft",
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        report = DischargeReport.all_objects.get(patient=self.patient)
        self.assertEqual(report.admission_date, date(2024, 1, 1))
        self.assertEqual(report.discharge_date, date(2024, 1, 5))

    def test_create_view_saves_draft_by_default(self):
        """Test that create view saves as draft by default"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse(
            "apps.dischargereports:patient_dischargereport_create",
            kwargs={"patient_id": self.patient.pk},
        )

        data = {
            "patient": self.patient.pk,
            "event_datetime": timezone.now().strftime("%Y-%m-%dT%H:%M"),
            "description": "Test report",
            "admission_date": date(2024, 1, 1),
            "discharge_date": date(2024, 1, 5),
            "medical_specialty": "Test Specialty",
            "admission_history": "Test history",
            "problems_and_diagnosis": "Test diagnosis",
            "exams_list": "Test exams",
            "procedures_list": "Test procedures",
            "inpatient_medical_history": "Test medical history",
            "discharge_status": "Test status",
            "discharge_recommendations": "Test recommendations",
            "save_draft": "Save Draft",
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after save

        report = DischargeReport.all_objects.get(patient=self.patient)
        self.assertTrue(report.is_draft)

    def test_create_view_saves_final(self):
        """Test that create view can save as final"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse(
            "apps.dischargereports:patient_dischargereport_create",
            kwargs={"patient_id": self.patient.pk},
        )

        data = {
            "patient": self.patient.pk,
            "event_datetime": timezone.now().strftime("%Y-%m-%dT%H:%M"),
            "description": "Test report",
            "admission_date": date(2024, 1, 1),
            "discharge_date": date(2024, 1, 5),
            "medical_specialty": "Test Specialty",
            "admission_history": "Test history",
            "problems_and_diagnosis": "Test diagnosis",
            "exams_list": "Test exams",
            "procedures_list": "Test procedures",
            "inpatient_medical_history": "Test medical history",
            "discharge_status": "Test status",
            "discharge_recommendations": "Test recommendations",
            "save_final": "Save Final",
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        report = DischargeReport.objects.get(patient=self.patient)
        self.assertFalse(report.is_draft)

    def test_update_form_uses_native_date_and_datetime_pickers(self):
        """Update form should render native date/datetime picker inputs."""
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Draft report",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            is_draft=True,
            created_by=self.user,
            updated_by=self.user,
        )

        self.client.login(username="testuser", password="testpass123")
        url = reverse(
            "apps.dischargereports:dischargereport_update", kwargs={"pk": report.pk}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'type="datetime-local"')
        self.assertContains(response, 'type="date"', count=2)

    def test_update_view_blocks_non_editable(self):
        """Test that update view blocks non-editable reports"""
        # Create final report older than 24 hours
        old_datetime = timezone.now() - timedelta(hours=25)
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=old_datetime,
            description="Old final report",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            is_draft=False,
            created_by=self.user,
            updated_by=self.user,
        )
        # Manually set created_at to simulate old report
        DischargeReport.objects.filter(pk=report.pk).update(created_at=old_datetime)

        self.client.login(username="testuser", password="testpass123")
        url = reverse(
            "apps.dischargereports:dischargereport_update", kwargs={"pk": report.pk}
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # PermissionDenied

    def test_delete_view_allows_draft_and_final_within_window(self):
        """Test that delete view allows draft and recent final deletion"""
        draft_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Draft report",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            is_draft=True,
            created_by=self.user,
            updated_by=self.user,
        )

        final_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Final report",
            admission_date=date(2024, 2, 1),
            discharge_date=date(2024, 2, 5),
            medical_specialty="Test Specialty",
            is_draft=False,
            created_by=self.user,
            updated_by=self.user,
        )

        self.client.login(username="testuser", password="testpass123")

        # Draft can be deleted
        draft_url = reverse(
            "apps.dischargereports:dischargereport_delete",
            kwargs={"pk": draft_report.pk},
        )
        response = self.client.get(draft_url)
        self.assertEqual(response.status_code, 200)

        # Final report can be deleted within window
        final_url = reverse(
            "apps.dischargereports:dischargereport_delete",
            kwargs={"pk": final_report.pk},
        )
        response = self.client.get(final_url)
        self.assertEqual(response.status_code, 200)

    def test_delete_view_blocks_final_outside_window_for_creator(self):
        """Test that delete view blocks finalized reports outside window."""
        old_datetime = timezone.now() - timedelta(hours=25)
        final_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=old_datetime,
            description="Old final report",
            admission_date=date(2024, 2, 1),
            discharge_date=date(2024, 2, 5),
            medical_specialty="Test Specialty",
            is_draft=False,
            created_by=self.user,
            updated_by=self.user,
        )
        DischargeReport.objects.filter(pk=final_report.pk).update(
            created_at=old_datetime
        )

        self.client.login(username="testuser", password="testpass123")
        final_url = reverse(
            "apps.dischargereports:dischargereport_delete",
            kwargs={"pk": final_report.pk},
        )
        response = self.client.get(final_url)
        self.assertEqual(response.status_code, 403)

    def test_delete_view_rejects_permission_override(self):
        """D7: an `events.delete_event` holder cannot override ownership."""
        old_datetime = timezone.now() - timedelta(hours=25)
        final_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=old_datetime,
            description="Old final report",
            admission_date=date(2024, 2, 1),
            discharge_date=date(2024, 2, 5),
            medical_specialty="Test Specialty",
            is_draft=False,
            created_by=self.user,
            updated_by=self.user,
        )
        DischargeReport.objects.filter(pk=final_report.pk).update(
            created_at=old_datetime
        )

        delete_user = User.objects.create_user(
            username="deleteuser",
            email="delete@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
        )
        delete_perm = Permission.objects.get(codename="delete_event")
        delete_user.user_permissions.add(delete_perm)

        self.client.login(username="deleteuser", password="testpass123")
        final_url = reverse(
            "apps.dischargereports:dischargereport_delete",
            kwargs={"pk": final_report.pk},
        )
        response = self.client.get(final_url)
        self.assertEqual(response.status_code, 403)

    def test_detail_view_requires_login(self):
        """Test that detail view requires authentication"""
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Test report",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            created_by=self.user,
            updated_by=self.user,
        )
        url = reverse(
            "apps.dischargereports:dischargereport_detail", kwargs={"pk": report.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_detail_view_works_when_authenticated(self):
        """Test that detail view works when authenticated"""
        self.client.login(username="testuser", password="testpass123")
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Test report",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            created_by=self.user,
            updated_by=self.user,
        )
        url = reverse(
            "apps.dischargereports:dischargereport_detail", kwargs={"pk": report.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Patient")

    def test_pdf_view_requires_login(self):
        """Test that PDF view requires authentication"""
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Test report",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            created_by=self.user,
            updated_by=self.user,
        )
        url = reverse(
            "apps.dischargereports:dischargereport_pdf", kwargs={"pk": report.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_pdf_view_returns_pdf(self):
        """Test that PDF view returns PDF content."""
        self.client.login(username="testuser", password="testpass123")
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Test report",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            problems_and_diagnosis="Test diagnosis",
            admission_history="Test history",
            exams_list="Test exams",
            procedures_list="Test procedures",
            inpatient_medical_history="Test medical history",
            discharge_status="Test status",
            discharge_recommendations="Test recommendations",
            is_draft=False,
            created_by=self.user,
            updated_by=self.user,
        )
        url = reverse(
            "apps.dischargereports:dischargereport_pdf", kwargs={"pk": report.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertGreater(len(response.content), 0)

    def test_list_view_requires_login(self):
        """Test that list view requires authentication"""
        url = reverse("apps.dischargereports:dischargereport_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_list_view_shows_reports(self):
        """Test that list view shows reports"""
        self.client.login(username="testuser", password="testpass123")
        DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Test report",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            created_by=self.user,
            updated_by=self.user,
        )
        url = reverse("apps.dischargereports:dischargereport_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Patient")

    def test_update_view_saves_draft(self):
        """Test that update view can save as draft"""
        self.client.login(username="testuser", password="testpass123")
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Original report",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            is_draft=True,
            created_by=self.user,
            updated_by=self.user,
        )
        url = reverse(
            "apps.dischargereports:dischargereport_update", kwargs={"pk": report.pk}
        )

        data = {
            "patient": self.patient.pk,
            "event_datetime": timezone.now().strftime("%Y-%m-%dT%H:%M"),
            "description": "Updated report",
            "admission_date": date(2024, 1, 1),
            "discharge_date": date(2024, 1, 5),
            "medical_specialty": "Test Specialty",
            "admission_history": "Test history",
            "problems_and_diagnosis": "Test diagnosis",
            "exams_list": "Test exams",
            "procedures_list": "Test procedures",
            "inpatient_medical_history": "Test medical history",
            "discharge_status": "Test status",
            "discharge_recommendations": "Test recommendations",
            "save_draft": "Save Draft",
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        report.refresh_from_db()
        self.assertTrue(report.is_draft)
        self.assertEqual(report.problems_and_diagnosis, "Test diagnosis")

    def test_update_view_saves_final(self):
        """Test that update view can save as final"""
        self.client.login(username="testuser", password="testpass123")
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Original report",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            is_draft=True,
            created_by=self.user,
            updated_by=self.user,
        )
        url = reverse(
            "apps.dischargereports:dischargereport_update", kwargs={"pk": report.pk}
        )

        data = {
            "patient": self.patient.pk,
            "event_datetime": timezone.now().strftime("%Y-%m-%dT%H:%M"),
            "description": "Final report",
            "admission_date": date(2024, 1, 1),
            "discharge_date": date(2024, 1, 5),
            "medical_specialty": "Test Specialty",
            "admission_history": "Test history",
            "problems_and_diagnosis": "Test diagnosis",
            "exams_list": "Test exams",
            "procedures_list": "Test procedures",
            "inpatient_medical_history": "Test medical history",
            "discharge_status": "Test status",
            "discharge_recommendations": "Test recommendations",
            "save_final": "Save Final",
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        report.refresh_from_db()
        self.assertFalse(report.is_draft)
        self.assertEqual(report.problems_and_diagnosis, "Test diagnosis")

    def test_delete_view_deletes_draft(self):
        """Test that delete view actually deletes draft reports"""
        self.client.login(username="testuser", password="testpass123")
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Draft to delete",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            is_draft=True,
            created_by=self.user,
            updated_by=self.user,
        )
        url = reverse(
            "apps.dischargereports:dischargereport_delete", kwargs={"pk": report.pk}
        )

        # Get confirmation page
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Confirm deletion
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        # A never-finalized draft is hard-deleted (design D7): gone from the
        # default manager and from all_objects alike.
        self.assertFalse(DischargeReport.objects.filter(pk=report.pk).exists())
        self.assertFalse(DischargeReport.all_objects.filter(pk=report.pk).exists())


class DischargeReportCollaborativeDraftViewTests(TestCase):
    """S1: collaborating doctor can edit/re-save another doctor's draft."""

    def setUp(self):
        self.client = Client()
        self.creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.collaborator = User.objects.create_user(
            username="collaborator",
            email="collaborator@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.RESIDENT,
        )
        self.nurse = User.objects.create_user(
            username="nurse",
            email="nurse@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.NURSE,
        )
        self.patient = Patient.objects.create(
            name="Collab Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.creator,
            updated_by=self.creator,
        )
        self.report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Collab draft",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            admission_history="h",
            problems_and_diagnosis="d",
            exams_list="e",
            procedures_list="p",
            inpatient_medical_history="m",
            discharge_status="s",
            discharge_recommendations="r",
            is_draft=True,
            created_by=self.creator,
            updated_by=self.creator,
        )

    def _draft_post_data(self, action):
        return {
            "patient": self.patient.pk,
            "event_datetime": timezone.now().strftime("%Y-%m-%dT%H:%M"),
            "description": "Collab draft",
            "admission_date": date(2024, 1, 1),
            "discharge_date": date(2024, 1, 5),
            "medical_specialty": "Test Specialty",
            "admission_history": "h",
            "problems_and_diagnosis": "collab edit",
            "exams_list": "e",
            "procedures_list": "p",
            "inpatient_medical_history": "m",
            "discharge_status": "s",
            "discharge_recommendations": "r",
            action: "x",
        }

    def _create_final_report(self, *, created_at=None):
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Fresh final",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            admission_history="h",
            problems_and_diagnosis="d",
            exams_list="e",
            procedures_list="p",
            inpatient_medical_history="m",
            discharge_status="s",
            discharge_recommendations="r",
            is_draft=False,
            created_by=self.creator,
            updated_by=self.creator,
        )
        if created_at is not None:
            DischargeReport.objects.filter(pk=report.pk).update(created_at=created_at)
            report.refresh_from_db()
        return report

    def _final_post_data(self):
        """POST data as submitted by the final report's "Atualizar" button."""
        return {
            "patient": self.patient.pk,
            "event_datetime": timezone.now().strftime("%Y-%m-%dT%H:%M"),
            "description": "Fresh final",
            "admission_date": date(2024, 1, 1),
            "discharge_date": date(2024, 1, 5),
            "medical_specialty": "Test Specialty",
            "admission_history": "h",
            "problems_and_diagnosis": "corrected diagnosis",
            "exams_list": "e",
            "procedures_list": "p",
            "inpatient_medical_history": "m",
            "discharge_status": "s",
            "discharge_recommendations": "r",
            "update_final": "",
        }

    def test_collaborator_can_open_update_view(self):
        self.client.login(username="collaborator", password="testpass123")
        url = reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": self.report.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_collaborator_can_resave_draft(self):
        self.client.login(username="collaborator", password="testpass123")
        url = reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": self.report.pk},
        )
        response = self.client.post(url, self._draft_post_data("save_draft"))
        self.assertEqual(response.status_code, 302)
        self.report.refresh_from_db()
        self.assertTrue(self.report.is_draft)
        self.assertEqual(self.report.problems_and_diagnosis, "collab edit")

    def test_detail_shows_edit_action_to_collaborator(self):
        self.client.login(username="collaborator", password="testpass123")
        url = reverse(
            "apps.dischargereports:dischargereport_detail",
            kwargs={"pk": self.report.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        update_url = reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": self.report.pk},
        )
        self.assertContains(response, update_url)

    def test_collaborator_can_finalize_draft(self):
        """S2 R1: second doctor finalize flips is_draft to False."""
        self.client.login(username="collaborator", password="testpass123")
        url = reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": self.report.pk},
        )
        response = self.client.post(url, self._draft_post_data("save_final"))
        self.assertEqual(response.status_code, 302)
        self.report.refresh_from_db()
        self.assertFalse(self.report.is_draft)

    def test_non_doctor_cannot_open_update_view(self):
        """S2 R2: nurse gets 403 on draft update GET."""
        self.client.login(username="nurse", password="testpass123")
        url = reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": self.report.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_non_doctor_cannot_submit_update_view(self):
        """S2 R2: nurse gets 403 on draft update POST."""
        self.client.login(username="nurse", password="testpass123")
        url = reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": self.report.pk},
        )
        response = self.client.post(url, self._draft_post_data("save_draft"))
        self.assertEqual(response.status_code, 403)
        self.report.refresh_from_db()
        self.assertTrue(self.report.is_draft)
        self.assertNotEqual(self.report.problems_and_diagnosis, "collab edit")

    def test_detail_hides_edit_action_from_non_doctor(self):
        """S2 R2: no edit action for non-doctor on detail view."""
        self.client.login(username="nurse", password="testpass123")
        url = reverse(
            "apps.dischargereports:dischargereport_detail",
            kwargs={"pk": self.report.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        update_url = reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": self.report.pk},
        )
        self.assertNotContains(response, update_url)

    def test_second_doctor_blocked_on_finalized_report(self):
        """S2 R3: fresh final stays creator-only (collaborator 403)."""
        final_report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Fresh final",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            admission_history="h",
            problems_and_diagnosis="d",
            exams_list="e",
            procedures_list="p",
            inpatient_medical_history="m",
            discharge_status="s",
            discharge_recommendations="r",
            is_draft=False,
            created_by=self.creator,
            updated_by=self.creator,
        )
        self.client.login(username="collaborator", password="testpass123")
        url = reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": final_report.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_unknown_update_action_preserves_state_with_explicit_error(self):
        """R5: a draft POST without an action changes nothing and errors.

        The error names the valid actions so the client can resubmit with
        ``save_draft`` or ``save_final``.
        """
        self.client.login(username="collaborator", password="testpass123")
        url = reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": self.report.pk},
        )
        data = self._draft_post_data("save_draft")
        data.pop("save_draft")

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ação inválida")
        self.assertContains(response, "Salvar Rascunho")
        self.assertContains(response, "Salvar Definitivo")
        self.report.refresh_from_db()
        self.assertTrue(self.report.is_draft)
        self.assertEqual(self.report.problems_and_diagnosis, "d")

    def test_change_event_holder_cannot_open_final_update(self):
        """D7: finals belong to the D6 owner; `events.change_event` adds nothing.

        The pre-supervision rule granted finals editing to ``events.change_event``
        holders inside the window; the owner rule narrows it to the finalizer
        (or the creator for legacy finals without a recorded finalizer).
        """
        fresh_final = self._create_final_report()
        old_final = self._create_final_report(
            created_at=timezone.now() - timedelta(hours=25)
        )
        change_holder = User.objects.create_user(
            username="changefinalholder",
            email="changefinalholder@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.NURSE,
        )
        change_holder.user_permissions.add(
            Permission.objects.get(codename="change_event")
        )
        self.client.login(username="changefinalholder", password="testpass123")

        fresh_url = reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": fresh_final.pk},
        )
        old_url = reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": old_final.pk},
        )

        self.assertEqual(self.client.get(fresh_url).status_code, 403)
        self.assertEqual(self.client.get(old_url).status_code, 403)

    def test_final_update_without_action_keys_preserves_state_with_error(self):
        """R5: a final POST with no recognized action changes nothing.

        The error names the action the finalized-report form offers, so the
        client can resubmit with the "Atualizar" button.
        """
        final_report = self._create_final_report()
        self.client.login(username="creator", password="testpass123")
        url = reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": final_report.pk},
        )
        data = self._final_post_data()
        data.pop("update_final")

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ação inválida")
        self.assertContains(response, 'name="update_final"')
        final_report.refresh_from_db()
        self.assertFalse(final_report.is_draft)
        self.assertEqual(final_report.problems_and_diagnosis, "d")

    def test_final_update_button_saves(self):
        """Normal flow: the final "Atualizar" button updates the report."""
        final_report = self._create_final_report()
        self.client.login(username="creator", password="testpass123")
        url = reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": final_report.pk},
        )

        response = self.client.post(url, self._final_post_data())

        self.assertEqual(response.status_code, 302)
        final_report.refresh_from_db()
        self.assertFalse(final_report.is_draft)
        self.assertEqual(final_report.problems_and_diagnosis, "corrected diagnosis")


class DischargeReportFinalizationWindowViewTests(TestCase):
    """S3: finalizing a draft opens a 24h correction window (design D6)."""

    def setUp(self):
        self.client = Client()
        self.creator = User.objects.create_user(
            username="windowviewcreator",
            email="windowviewcreator@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.finalizer = User.objects.create_user(
            username="windowviewfinalizer",
            email="windowviewfinalizer@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.RESIDENT,
        )
        self.patient = Patient.objects.create(
            name="Window View Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.creator,
            updated_by=self.creator,
        )

    def _create_report(self, *, is_draft, created_at=None, finalized_at=None):
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Window report",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Test Specialty",
            admission_history="h",
            problems_and_diagnosis="d",
            exams_list="e",
            procedures_list="p",
            inpatient_medical_history="m",
            discharge_status="s",
            discharge_recommendations="r",
            is_draft=is_draft,
            created_by=self.creator,
            updated_by=self.creator,
            finalized_at=finalized_at,
            finalized_by=self.finalizer if finalized_at else None,
        )
        if created_at is not None:
            DischargeReport.all_objects.filter(pk=report.pk).update(
                created_at=created_at
            )
            report.refresh_from_db()
        return report

    def _post_data(self, action):
        return {
            "patient": self.patient.pk,
            "event_datetime": timezone.now().strftime("%Y-%m-%dT%H:%M"),
            "description": "Window report",
            "admission_date": date(2024, 1, 1),
            "discharge_date": date(2024, 1, 5),
            "medical_specialty": "Test Specialty",
            "admission_history": "h",
            "problems_and_diagnosis": "corrected",
            "exams_list": "e",
            "procedures_list": "p",
            "inpatient_medical_history": "m",
            "discharge_status": "s",
            "discharge_recommendations": "r",
            action: "x",
        }

    def _create_url(self):
        return reverse(
            "apps.dischargereports:patient_dischargereport_create",
            kwargs={"patient_id": self.patient.pk},
        )

    def _update_url(self, report):
        return reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": report.pk},
        )

    def _detail_url(self, report):
        return reverse(
            "apps.dischargereports:dischargereport_detail",
            kwargs={"pk": report.pk},
        )

    def _delete_url(self, report):
        return reverse(
            "apps.dischargereports:dischargereport_delete",
            kwargs={"pk": report.pk},
        )

    def test_finalizing_an_old_draft_records_the_anchor_and_opens_the_window(self):
        """R2: a collaborator finalizes an old draft; the finalizer owns the
        24h correction window and the creator is locked out."""
        old_draft = self._create_report(
            is_draft=True, created_at=timezone.now() - timedelta(days=3)
        )
        self.client.login(username="windowviewfinalizer", password="testpass123")

        response = self.client.post(
            self._update_url(old_draft), self._post_data("save_final")
        )

        self.assertEqual(response.status_code, 302)
        old_draft.refresh_from_db()
        self.assertFalse(old_draft.is_draft)
        self.assertIsNotNone(old_draft.finalized_at)
        self.assertEqual(old_draft.finalized_by, self.finalizer)
        self.assertEqual(self.client.get(self._update_url(old_draft)).status_code, 200)
        self.client.login(username="windowviewcreator", password="testpass123")
        self.assertEqual(self.client.get(self._update_url(old_draft)).status_code, 403)

    def test_update_button_keeps_the_recorded_anchor(self):
        """R2/R4: editing a final does not restart its correction window."""
        anchored_at = timezone.now() - timedelta(hours=2)
        final = self._create_report(is_draft=False, finalized_at=anchored_at)
        self.client.login(username="windowviewfinalizer", password="testpass123")

        response = self.client.post(
            self._update_url(final), self._post_data("update_final")
        )

        self.assertEqual(response.status_code, 302)
        final.refresh_from_db()
        self.assertEqual(final.finalized_at, anchored_at)

    def test_reverting_retains_the_anchor_and_reanchors_next_finalize(self):
        """S7 R3: save_draft retains both fields as the last-finalization
        record; the next finalize re-anchors the window."""
        first_anchor = timezone.now() - timedelta(hours=1)
        final = self._create_report(is_draft=False, finalized_at=first_anchor)
        self.client.login(username="windowviewfinalizer", password="testpass123")

        response = self.client.post(
            self._update_url(final), self._post_data("save_draft")
        )

        self.assertEqual(response.status_code, 302)
        final.refresh_from_db()
        self.assertTrue(final.is_draft)
        self.assertEqual(final.finalized_at, first_anchor)
        self.assertEqual(final.finalized_by, self.finalizer)
        self.assertTrue(final.can_be_edited_by_user(self.creator))

        response = self.client.post(
            self._update_url(final), self._post_data("save_final")
        )

        self.assertEqual(response.status_code, 302)
        final.refresh_from_db()
        self.assertFalse(final.is_draft)
        self.assertGreater(final.finalized_at, first_anchor)
        self.assertEqual(final.finalized_by, self.finalizer)

    def test_update_denied_after_the_window_for_everyone_window_bound(self):
        """R4: past 24h from finalization the update view denies everyone."""
        expired = self._create_report(
            is_draft=False,
            created_at=timezone.now() - timedelta(days=30),
            finalized_at=timezone.now() - timedelta(hours=25),
        )
        change_holder = User.objects.create_user(
            username="windowviewchanger",
            email="windowviewchanger@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.NURSE,
        )
        change_holder.user_permissions.add(
            Permission.objects.get(codename="change_event")
        )
        url = self._update_url(expired)

        for user in (self.creator, self.finalizer, change_holder):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_old_draft_freshly_finalized_is_editable_and_deletable_by_owner(self):
        """D6/D7: edit and delete share the finalization anchor.

        The pre-supervision rule kept deletion creation-anchored while editing
        re-anchored at finalization; both now follow the D6 owner window.
        """
        old_draft = self._create_report(
            is_draft=True, created_at=timezone.now() - timedelta(days=3)
        )
        self.client.login(username="windowviewcreator", password="testpass123")

        self.client.post(self._update_url(old_draft), self._post_data("save_final"))

        old_draft.refresh_from_db()
        self.assertFalse(old_draft.is_draft)
        self.assertEqual(self.client.get(self._update_url(old_draft)).status_code, 200)
        self.assertEqual(self.client.post(self._delete_url(old_draft)).status_code, 302)
        old_draft.refresh_from_db()
        self.assertTrue(old_draft.is_deleted)

    def test_detail_shows_the_finalization_line_for_finals_only(self):
        """R7: "Finalizado por X em Y" renders for finalized reports only."""
        now = timezone.now()
        final = self._create_report(is_draft=False, finalized_at=now)
        draft = self._create_report(is_draft=True)
        self.client.login(username="windowviewcreator", password="testpass123")

        final_response = self.client.get(self._detail_url(final))
        draft_response = self.client.get(self._detail_url(draft))

        self.assertEqual(final_response.status_code, 200)
        self.assertContains(final_response, "Finalizado por")
        self.assertContains(final_response, self.finalizer.username)
        self.assertContains(
            final_response,
            timezone.localtime(now).strftime("%d/%m/%Y %H:%M"),
        )
        self.assertEqual(draft_response.status_code, 200)
        self.assertNotContains(draft_response, "Finalizado por")

    def test_direct_final_creation_records_the_anchor_and_shows_the_line(self):
        """Spec: finalizing on the create form also records and displays
        the finalization metadata."""
        submitted_at = timezone.now()
        self.client.login(username="windowviewcreator", password="testpass123")

        response = self.client.post(self._create_url(), self._post_data("save_final"))

        self.assertEqual(response.status_code, 302)
        report = DischargeReport.objects.get(patient=self.patient)
        with self.subTest(recorded="saved finalization fields"):
            self.assertFalse(report.is_draft)
            self.assertIsNotNone(report.finalized_at)
            self.assertGreaterEqual(report.finalized_at, submitted_at)
            self.assertEqual(report.finalized_by, self.creator)

        detail_response = self.client.get(self._detail_url(report))
        self.assertEqual(detail_response.status_code, 200)
        with self.subTest(displayed="finalization line on detail"):
            self.assertContains(detail_response, "Finalizado por")
            self.assertContains(detail_response, self.creator.username)
            self.assertContains(
                detail_response,
                timezone.localtime(report.finalized_at).strftime("%d/%m/%Y %H:%M"),
            )
