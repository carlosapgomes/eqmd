"""Tests for the read-only ``audit_clinical_identity`` command.

R2: report the three clinical-identity gap kinds grouped and readable,
with exempt users (superusers and ``User Managers`` members) absent.
R3: the command must not modify any database row.
"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.accounts.tests.factories import (
    DoctorFactory,
    NurseFactory,
    SuperUserFactory,
    UserFactory,
)

User = get_user_model()

NULL_PROFESSION_HEADER = "Active users without profession_type"
GROUP_DRIFT_HEADER = "Profession groups missing expected permissions"
NO_GROUP_HEADER = "Non-exempt users in no profession group"


class AuditClinicalIdentityCommandTests(TestCase):
    """R2/R3: grouped read-only report of clinical identity gaps."""

    def setUp(self):
        call_command("setup_groups", verbosity=0)

        self.gap_user = UserFactory(username="gap.user", profession_type=None)
        self.exempt_superuser = SuperUserFactory(
            username="exempt.superuser", profession_type=None
        )
        self.exempt_manager = UserFactory(
            username="exempt.manager", profession_type=None
        )
        self.exempt_manager.groups.add(Group.objects.get(name="User Managers"))

        self.grouped_doctor = DoctorFactory(username="grouped.doctor")
        self.ungrouped_nurse = NurseFactory(username="ungrouped.nurse")
        self.ungrouped_nurse.groups.clear()

        # Simulate permission drift: an existing group loses its set.
        Group.objects.get(name="Nurses").permissions.clear()

        self.report = self._run_audit()

    def _run_audit(self):
        output = StringIO()
        call_command("audit_clinical_identity", stdout=output)
        return output.getvalue()

    def _section(self, header, next_header=None, report=None):
        report = self.report if report is None else report
        start = report.index(header)
        if next_header is None:
            return report[start:]
        end = report.index(next_header)
        return report[start:end]

    def test_reports_null_profession_users_excluding_exempt_users(self):
        section = self._section(NULL_PROFESSION_HEADER, GROUP_DRIFT_HEADER)

        self.assertIn("gap.user", section)
        self.assertNotIn("exempt.superuser", section)
        self.assertNotIn("exempt.manager", section)
        self.assertNotIn("grouped.doctor", section)

    def test_reports_profession_groups_missing_expected_permissions(self):
        section = self._section(GROUP_DRIFT_HEADER, NO_GROUP_HEADER)

        self.assertIn("Nurses", section)
        self.assertIn("patients.add_patient", section)
        self.assertNotIn("Medical Doctors", section)

    def test_reports_non_exempt_users_in_no_profession_group(self):
        section = self._section(NO_GROUP_HEADER)

        self.assertIn("gap.user", section)
        self.assertIn("ungrouped.nurse", section)
        self.assertNotIn("grouped.doctor", section)
        self.assertNotIn("exempt.superuser", section)
        self.assertNotIn("exempt.manager", section)

    def test_reports_inactive_non_exempt_users_in_no_profession_group(self):
        UserFactory(
            username="inactive.ungrouped", profession_type=None, is_active=False
        )
        SuperUserFactory(
            username="inactive.superuser", profession_type=None, is_active=False
        )
        inactive_manager = UserFactory(
            username="inactive.manager", profession_type=None, is_active=False
        )
        inactive_manager.groups.add(Group.objects.get(name="User Managers"))

        report = self._run_audit()
        no_group_section = self._section(NO_GROUP_HEADER, report=report)
        null_profession_section = self._section(
            NULL_PROFESSION_HEADER, GROUP_DRIFT_HEADER, report=report
        )

        self.assertIn("inactive.ungrouped", no_group_section)
        self.assertNotIn("inactive.ungrouped", null_profession_section)
        self.assertNotIn("inactive.superuser", report)
        self.assertNotIn("inactive.manager", report)

    def test_audit_modifies_zero_rows(self):
        counts_before = self._row_counts()

        with CaptureQueriesContext(connection) as queries:
            call_command("audit_clinical_identity", stdout=StringIO())

        self.assertEqual(self._row_counts(), counts_before)
        write_statements = [
            query["sql"]
            for query in queries.captured_queries
            if query["sql"].lstrip().lower().startswith(
                ("insert", "update", "delete")
            )
        ]
        self.assertEqual(write_statements, [])

    def _row_counts(self):
        return {
            "users": User.objects.count(),
            "groups": Group.objects.count(),
            "permissions": Permission.objects.count(),
            "user_groups": User.groups.through.objects.count(),
            "group_permissions": Group.permissions.through.objects.count(),
        }
