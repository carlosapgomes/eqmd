"""
Tests for report template permission service.
"""

from django.test import TestCase

from apps.accounts.models import EqmdCustomUser
from apps.reports.services.permissions import can_manage_report_templates


class TemplatePermissionsTest(TestCase):
    """Tests for can_manage_report_templates permission function."""

    def setUp(self):
        """Set up test users with different roles."""
        self.admin_user = EqmdCustomUser.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=False
        )
        self.superuser = EqmdCustomUser.objects.create_user(
            username='superuser',
            email='superuser@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        self.doctor = EqmdCustomUser.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR
        )
        self.resident = EqmdCustomUser.objects.create_user(
            username='resident',
            email='resident@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.RESIDENT
        )
        self.nurse = EqmdCustomUser.objects.create_user(
            username='nurse',
            email='nurse@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.NURSE
        )
        self.anonymous_user = None

    def test_admin_can_manage_templates(self):
        """Admin users can manage report templates."""
        self.assertTrue(can_manage_report_templates(self.admin_user))
        self.assertTrue(can_manage_report_templates(self.superuser))

    def test_doctor_can_manage_templates(self):
        """Doctors can manage report templates."""
        self.assertTrue(can_manage_report_templates(self.doctor))

    def test_resident_can_manage_templates(self):
        """Residents can manage report templates."""
        self.assertTrue(can_manage_report_templates(self.resident))

    def test_nurse_cannot_manage_templates(self):
        """Nurses cannot manage report templates."""
        self.assertFalse(can_manage_report_templates(self.nurse))

    def test_unauthenticated_cannot_manage_templates(self):
        """Unauthenticated users cannot manage report templates."""
        self.assertFalse(can_manage_report_templates(self.anonymous_user))
