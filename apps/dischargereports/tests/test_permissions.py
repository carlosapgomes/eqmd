"""Single discharge-report edit/delete predicate (S1 R1/R4).

The model methods, the detail view helper and the patient timeline bulk check
must return the same verdict for every user/report pair (design D1/D2). The
predicate itself lives in ``apps.dischargereports.services.permissions``.
"""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone

from apps.core.permissions import can_delete_event, can_edit_event
from apps.dischargereports import views
from apps.dischargereports.models import DischargeReport
from apps.events.views import PatientEventsTimelineView
from apps.patients.models import Patient

User = get_user_model()


class SingleDischargeReportPredicateTests(TestCase):
    """R1/R4: one predicate serving the model, the helper and the timeline."""

    def setUp(self):
        self.creator = User.objects.create_user(
            username="predicatecreator",
            email="predicatecreator@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.collaborator = User.objects.create_user(
            username="predicatecollaborator",
            email="predicatecollaborator@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.RESIDENT,
        )
        self.non_doctor = User.objects.create_user(
            username="predicatenurse",
            email="predicatenurse@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.NURSE,
        )
        self.patient = Patient.objects.create(
            name="Predicate Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.creator,
            updated_by=self.creator,
        )
        now = timezone.now()
        self.fresh_draft = self._create_report(is_draft=True)
        self.old_draft = self._create_report(
            is_draft=True, created_at=now - timedelta(hours=25)
        )
        self.fresh_final = self._create_report(is_draft=False)
        self.old_final = self._create_report(
            is_draft=False, created_at=now - timedelta(hours=25)
        )

    def _create_report(self, *, is_draft, created_at=None, **extra):
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
            **extra,
        )
        if created_at is not None:
            DischargeReport.objects.filter(pk=report.pk).update(created_at=created_at)
            report.refresh_from_db()
        return report

    def _timeline_permissions(self, user, event):
        view = PatientEventsTimelineView()
        view.request = SimpleNamespace(user=user)
        return view._bulk_permission_check([event])[0]

    def _create_user_with_permission(self, codename):
        user = User.objects.create_user(
            username=f"holder{codename}",
            email=f"holder{codename}@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.NURSE,
        )
        user.user_permissions.add(Permission.objects.get(codename=codename))
        return user

    # -- R1: the service owns the predicates --------------------------------

    def test_service_module_owns_the_predicates(self):
        from apps.dischargereports.services import permissions as service_permissions

        self.assertIs(
            views.can_edit_discharge_report,
            service_permissions.can_edit_discharge_report,
        )
        self.assertIs(
            views.can_delete_discharge_report,
            service_permissions.can_delete_discharge_report,
        )

    def test_model_delegates_edit_predicate_to_service(self):
        with patch(
            "apps.dischargereports.services.permissions.can_edit_discharge_report",
            return_value=True,
        ) as service_edit:
            verdict = self.fresh_draft.can_be_edited_by_user(self.non_doctor)

        self.assertTrue(verdict)
        service_edit.assert_called_once_with(self.non_doctor, self.fresh_draft)

    def test_model_delegates_delete_predicate_to_service(self):
        with patch(
            "apps.dischargereports.services.permissions.can_delete_discharge_report",
            return_value=True,
        ) as service_delete:
            verdict = self.fresh_draft.can_be_deleted_by_user(self.non_doctor)

        self.assertTrue(verdict)
        service_delete.assert_called_once_with(self.non_doctor, self.fresh_draft)

    # -- R4: three-door equivalence matrix ---------------------------------

    def test_three_doors_agree_on_edit_verdicts(self):
        users = {
            "creator": self.creator,
            "collaborator": self.collaborator,
            "non_doctor": self.non_doctor,
        }
        reports = {
            "fresh_draft": self.fresh_draft,
            "old_draft": self.old_draft,
            "fresh_final": self.fresh_final,
            "old_final": self.old_final,
        }
        expected = {
            ("creator", "fresh_draft"): True,
            ("creator", "old_draft"): True,
            ("creator", "fresh_final"): True,
            ("creator", "old_final"): False,
            ("collaborator", "fresh_draft"): True,
            ("collaborator", "old_draft"): True,
            ("collaborator", "fresh_final"): False,
            # fresh_final has no recorded finalizer: the creator owns it.
            ("collaborator", "old_final"): False,
            ("non_doctor", "fresh_draft"): False,
            ("non_doctor", "old_draft"): False,
            ("non_doctor", "fresh_final"): False,
            ("non_doctor", "old_final"): False,
        }

        for user_name, user in users.items():
            for report_name, report in reports.items():
                case = (user_name, report_name)
                model_verdict = report.can_be_edited_by_user(user)
                detail_verdict = views.can_edit_discharge_report(user, report)
                timeline_verdict = self._timeline_permissions(user, report)["can_edit"]
                with self.subTest(user=user_name, report=report_name):
                    self.assertEqual(expected[case], model_verdict)
                    self.assertEqual(model_verdict, detail_verdict)
                    self.assertEqual(detail_verdict, timeline_verdict)

    def test_three_doors_agree_on_delete_verdicts(self):
        delete_holder = self._create_user_with_permission("delete_event")
        cases = [
            ("creator_fresh_draft", self.creator, self.fresh_draft, True),
            # D7: a doctor/resident with access may clear any human draft.
            ("collaborator_fresh_draft", self.collaborator, self.fresh_draft, True),
            ("creator_fresh_final", self.creator, self.fresh_final, True),
            ("creator_old_final", self.creator, self.old_final, False),
            # D7: drafts belong to the creator or a doctor/resident, not to
            # delete-permission holders.
            ("holder_fresh_draft", delete_holder, self.fresh_draft, False),
            # D6/D7: the delete_event override is removed for finals too.
            ("holder_old_final", delete_holder, self.old_final, False),
        ]

        for case_name, user, report, expected in cases:
            model_verdict = report.can_be_deleted_by_user(user)
            detail_verdict = views.can_delete_discharge_report(user, report)
            timeline_verdict = self._timeline_permissions(user, report)["can_delete"]
            with self.subTest(case=case_name):
                self.assertEqual(expected, model_verdict)
                self.assertEqual(model_verdict, detail_verdict)
                self.assertEqual(detail_verdict, timeline_verdict)

    def test_change_event_holder_has_no_override_on_drafts_or_finals(self):
        """D7: ownership follows state; `change_event` grants nothing extra.

        Draft editing belongs to the creator or a doctor/resident, and finals
        belong to the D6 owner inside the window -- a permission holder who is
        neither is denied by all three doors.
        """
        change_holder = self._create_user_with_permission("change_event")
        reports = {
            "fresh_draft": self.fresh_draft,
            "old_draft": self.old_draft,
            "fresh_final": self.fresh_final,
            "old_final": self.old_final,
        }

        for case_name, report in reports.items():
            with self.subTest(case=case_name):
                self.assertFalse(report.can_be_edited_by_user(change_holder))
                self.assertFalse(
                    views.can_edit_discharge_report(change_holder, report)
                )
                self.assertFalse(
                    self._timeline_permissions(change_holder, report)["can_edit"]
                )


class DraftAwareDischargePredicateTests(TestCase):
    """R3: discharge predicates implement the generic draft/owner rules.

    Drafts: creator or any doctor/resident with patient access (no permission
    holders). Finals: the D6 owner only, inside the 24h anchor window, with no
    ``delete_event`` override.
    """

    def setUp(self):
        self.creator = User.objects.create_user(
            username="draftawarecreator",
            email="draftawarecreator@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.finalizer = User.objects.create_user(
            username="draftawarefinalizer",
            email="draftawarefinalizer@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.RESIDENT,
        )
        self.other_doctor = User.objects.create_user(
            username="draftawareotherdoctor",
            email="draftawareotherdoctor@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.patient = Patient.objects.create(
            name="Draft Aware Patient",
            birthday=date(1990, 1, 1),
            gender=Patient.GenderChoices.MALE,
            created_by=self.creator,
            updated_by=self.creator,
        )
        self.draft = self._create_report(is_draft=True)
        self.final = self._create_report(
            is_draft=False,
            created_at=timezone.now() - timedelta(days=30),
            finalized_at=timezone.now(),
            finalized_by=self.finalizer,
        )

    def _create_report(self, *, is_draft, created_at=None, **extra):
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
            **extra,
        )
        if created_at is not None:
            DischargeReport.objects.filter(pk=report.pk).update(created_at=created_at)
            report.refresh_from_db()
        return report

    def _user_with_permission(self, codename):
        user = User.objects.create_user(
            username=f"draftawareholder{codename}",
            email=f"draftawareholder{codename}@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            profession_type=User.NURSE,
        )
        user.user_permissions.add(Permission.objects.get(codename=codename))
        return user

    def test_final_is_finalizer_only_for_edit_and_delete(self):
        self.assertTrue(views.can_edit_discharge_report(self.finalizer, self.final))
        self.assertTrue(views.can_delete_discharge_report(self.finalizer, self.final))
        self.assertFalse(views.can_edit_discharge_report(self.creator, self.final))
        self.assertFalse(views.can_delete_discharge_report(self.creator, self.final))
        self.assertFalse(
            views.can_edit_discharge_report(self.other_doctor, self.final)
        )
        self.assertFalse(
            views.can_delete_discharge_report(self.other_doctor, self.final)
        )

    def test_draft_ignores_permission_holders(self):
        change_holder = self._user_with_permission("change_event")
        delete_holder = self._user_with_permission("delete_event")

        self.assertFalse(views.can_edit_discharge_report(change_holder, self.draft))
        self.assertFalse(views.can_delete_discharge_report(delete_holder, self.draft))

    def test_predicates_match_the_generic_event_rule(self):
        """R3: the service is the generic rule plus the patient access gate."""
        users = {
            "creator": self.creator,
            "finalizer": self.finalizer,
            "other_doctor": self.other_doctor,
        }
        reports = {"draft": self.draft, "final": self.final}

        for user_name, user in users.items():
            for report_name, report in reports.items():
                with self.subTest(user=user_name, report=report_name):
                    self.assertEqual(
                        can_edit_event(user, report),
                        views.can_edit_discharge_report(user, report),
                    )
                    self.assertEqual(
                        can_delete_event(user, report),
                        views.can_delete_discharge_report(user, report),
                    )
