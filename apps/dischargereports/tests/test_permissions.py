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
            DischargeReport.objects.filter(pk=report.pk).update(
                created_at=created_at
            )
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
                timeline_verdict = self._timeline_permissions(user, report)[
                    "can_edit"
                ]
                with self.subTest(user=user_name, report=report_name):
                    self.assertEqual(expected[case], model_verdict)
                    self.assertEqual(model_verdict, detail_verdict)
                    self.assertEqual(detail_verdict, timeline_verdict)

    def test_three_doors_agree_on_delete_verdicts(self):
        delete_holder = self._create_user_with_permission("delete_event")
        cases = [
            ("creator_fresh_draft", self.creator, self.fresh_draft, True),
            ("collaborator_fresh_draft", self.collaborator, self.fresh_draft, False),
            ("creator_fresh_final", self.creator, self.fresh_final, True),
            ("creator_old_final", self.creator, self.old_final, False),
            ("holder_fresh_draft", delete_holder, self.fresh_draft, True),
            ("holder_old_final", delete_holder, self.old_final, True),
        ]

        for case_name, user, report, expected in cases:
            model_verdict = report.can_be_deleted_by_user(user)
            detail_verdict = views.can_delete_discharge_report(user, report)
            timeline_verdict = self._timeline_permissions(user, report)[
                "can_delete"
            ]
            with self.subTest(case=case_name):
                self.assertEqual(expected, model_verdict)
                self.assertEqual(model_verdict, detail_verdict)
                self.assertEqual(detail_verdict, timeline_verdict)

    def test_change_event_holder_uses_the_single_predicate_on_finals(self):
        """D1: finals keep the shipped window for change_event holders.

        The pre-extraction model rule was ``can_be_edited and (creator or
        events.change_event)``; the shared predicate preserves it and all
        three doors return the same verdict.
        """
        change_holder = self._create_user_with_permission("change_event")
        cases = [
            ("fresh_final", self.fresh_final, True),
            ("old_final", self.old_final, False),
        ]

        self.assertTrue(self.fresh_draft.can_be_edited_by_user(change_holder))
        for case_name, report, expected in cases:
            with self.subTest(case=case_name):
                self.assertEqual(
                    expected, report.can_be_edited_by_user(change_holder)
                )
                self.assertEqual(
                    expected,
                    views.can_edit_discharge_report(change_holder, report),
                )
                self.assertEqual(
                    expected,
                    self._timeline_permissions(change_holder, report)["can_edit"],
                )
