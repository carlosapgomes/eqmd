"""Timeline permission tests for discharge report events (S1 R2/R3).

The patient timeline's bulk permission check must dispatch discharge-report
events to the discharge-report service predicate (design D2). The generic
event predicate is creator-only, so it hides the edit action from
collaborating doctors viewing another author's draft.
"""

from datetime import date, timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.dischargereports.models import DischargeReport
from apps.events.models import Event
from apps.events.views import PatientEventsTimelineView
from apps.patients.models import Patient

User = get_user_model()


class DischargeReportTimelinePermissionTests(TestCase):
    """R2/R3: timeline edit/delete flags for discharge reports."""

    def setUp(self):
        self.creator = User.objects.create_user(
            username="timelinecreator",
            email="timelinecreator@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.collaborator = User.objects.create_user(
            username="timelinecollaborator",
            email="timelinecollaborator@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.RESIDENT,
        )
        self.nurse = User.objects.create_user(
            username="timelinenurse",
            email="timelinenurse@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.NURSE,
        )
        self.patient = Patient.objects.create(
            name="Timeline Discharge Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.creator,
            updated_by=self.creator,
        )

    def _create_report(self, *, is_draft, created_at=None):
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Draft" if is_draft else "Final",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Cardiologia",
            admission_history="history",
            problems_and_diagnosis="diagnosis",
            exams_list="exams",
            procedures_list="procedures",
            inpatient_medical_history="inpatient history",
            discharge_status="status",
            discharge_recommendations="recommendations",
            is_draft=is_draft,
            created_by=self.creator,
            updated_by=self.creator,
        )
        if created_at is not None:
            DischargeReport.objects.filter(pk=report.pk).update(created_at=created_at)
            report.refresh_from_db()
        return report

    def _timeline_response(self, user):
        self.client.force_login(user)
        return self.client.get(
            reverse(
                "apps.patients:patient_events_timeline",
                kwargs={"patient_id": self.patient.pk},
            )
        )

    def _timeline_permissions(self, user, event):
        view = PatientEventsTimelineView()
        view.request = SimpleNamespace(user=user)
        return view._bulk_permission_check([event])[0]

    def _update_url(self, report):
        return reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": report.pk},
        )

    def test_collaborator_sees_edit_action_on_other_author_draft(self):
        """R2: timeline renders the update URL for a collaborating doctor."""
        report = self._create_report(is_draft=True)

        response = self._timeline_response(self.collaborator)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"event-{report.pk}-title")
        self.assertContains(response, self._update_url(report))

    def test_non_doctor_does_not_see_edit_action_on_draft(self):
        """R2: timeline hides the update URL from a non-doctor."""
        report = self._create_report(is_draft=True)

        response = self._timeline_response(self.nurse)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"event-{report.pk}-title")
        self.assertNotContains(response, self._update_url(report))

    def test_creator_sees_edit_action_on_own_draft(self):
        """Preserved behavior: the author keeps the timeline edit action."""
        report = self._create_report(is_draft=True)

        response = self._timeline_response(self.creator)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self._update_url(report))

    def test_expired_final_hides_edit_from_collaborator(self):
        """R3: an old final shows no edit action in the timeline."""
        report = self._create_report(
            is_draft=False,
            created_at=timezone.now() - timedelta(hours=25),
        )

        response = self._timeline_response(self.collaborator)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"event-{report.pk}-title")
        self.assertNotContains(response, self._update_url(report))

    def test_bulk_check_dispatches_delete_for_discharge_drafts(self):
        """R2: a delete-permission holder gets can_delete from the service."""
        report = self._create_report(is_draft=True)
        delete_holder = User.objects.create_user(
            username="timelinedeleter",
            email="timelinedeleter@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.NURSE,
        )
        delete_holder.user_permissions.add(
            Permission.objects.get(codename="delete_event")
        )

        permissions = self._timeline_permissions(delete_holder, report)

        self.assertTrue(permissions["can_delete"])
        self.assertEqual(permissions["event"], report)

    def test_other_event_types_keep_the_generic_predicate(self):
        """Dispatch must not leak into other event types (sensitive scope)."""
        note = Event.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Daily note by creator",
            event_type=Event.DAILY_NOTE_EVENT,
            created_by=self.creator,
            updated_by=self.creator,
        )

        creator_permissions = self._timeline_permissions(self.creator, note)
        collaborator_permissions = self._timeline_permissions(self.collaborator, note)

        self.assertTrue(creator_permissions["can_edit"])
        self.assertFalse(collaborator_permissions["can_edit"])


class DischargeReportFinalizationAnchorTimelineTests(TestCase):
    """S3 R2/R4: the timeline follows the finalization anchor."""

    def setUp(self):
        self.creator = User.objects.create_user(
            username="anchortimelinecreator",
            email="anchortimelinecreator@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.finalizer = User.objects.create_user(
            username="anchortimelinefinalizer",
            email="anchortimelinefinalizer@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.RESIDENT,
        )
        self.patient = Patient.objects.create(
            name="Anchor Timeline Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.creator,
            updated_by=self.creator,
        )

    def _create_finalized_old_draft(self, *, finalized_at):
        report = DischargeReport.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Finalized old draft",
            admission_date=date(2024, 1, 1),
            discharge_date=date(2024, 1, 5),
            medical_specialty="Cardiologia",
            admission_history="history",
            problems_and_diagnosis="diagnosis",
            exams_list="exams",
            procedures_list="procedures",
            inpatient_medical_history="inpatient history",
            discharge_status="status",
            discharge_recommendations="recommendations",
            is_draft=False,
            created_by=self.creator,
            updated_by=self.creator,
            finalized_at=finalized_at,
            finalized_by=self.finalizer,
        )
        DischargeReport.objects.filter(pk=report.pk).update(
            created_at=timezone.now() - timedelta(days=3)
        )
        report.refresh_from_db()
        return report

    def _timeline_response(self, user):
        self.client.force_login(user)
        return self.client.get(
            reverse(
                "apps.patients:patient_events_timeline",
                kwargs={"patient_id": self.patient.pk},
            )
        )

    def _update_url(self, report):
        return reverse(
            "apps.dischargereports:dischargereport_update",
            kwargs={"pk": report.pk},
        )

    def test_finalizer_sees_edit_on_freshly_finalized_old_draft(self):
        """R2: the timeline card shows edit to the finalizer inside the window."""
        report = self._create_finalized_old_draft(finalized_at=timezone.now())

        response = self._timeline_response(self.finalizer)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"event-{report.pk}-title")
        self.assertContains(response, self._update_url(report))

    def test_expired_finalization_anchor_hides_edit_from_finalizer(self):
        """R4: the timeline hides edit once the finalization window expired."""
        report = self._create_finalized_old_draft(
            finalized_at=timezone.now() - timedelta(hours=25)
        )

        response = self._timeline_response(self.finalizer)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"event-{report.pk}-title")
        self.assertNotContains(response, self._update_url(report))
