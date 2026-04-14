"""
Tests for DailyNote PDF download view.

Verifies authentication, content type, safe filename, and patient access control.
"""

from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.dailynotes.models import DailyNote
from apps.events.models import Event
from apps.patients.models import Patient


class DailyNotePDFViewTest(TestCase):
    """Tests for the DailyNotePDFView endpoint."""

    @classmethod
    def setUpTestData(cls):
        cls.user = EqmdCustomUser.objects.create_user(
            username="testdoctor",
            email="testdoctor@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            first_name="Test",
            last_name="Doctor",
        )
        cls.other_user = EqmdCustomUser.objects.create_user(
            username="otherdoctor",
            email="otherdoctor@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            first_name="Other",
            last_name="Doctor",
        )
        # Grant view_event permission
        event_ct = ContentType.objects.get_for_model(Event)
        cls.user.user_permissions.add(
            Permission.objects.get(content_type=event_ct, codename="view_event"),
        )
        cls.patient = Patient.objects.create(
            name="PDF Test Patient",
            birthday="1990-01-01",
            created_by=cls.user,
            updated_by=cls.user,
        )
        cls.dailynote = DailyNote.objects.create(
            patient=cls.patient,
            description="PDF view test note",
            content="Content for PDF generation.",
            event_datetime=timezone.now(),
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client.login(username="testdoctor", password="testpass123")
        self.url = reverse(
            "dailynotes:dailynote_pdf", kwargs={"pk": self.dailynote.pk}
        )

    def test_pdf_view_requires_authentication(self):
        """Unauthenticated users should be redirected to login."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_pdf_view_returns_application_pdf_response(self):
        """Authenticated users with access should get application/pdf."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertGreater(len(response.content), 0)

    def test_pdf_view_uses_safe_attachment_filename(self):
        """The response should have a safe Content-Disposition attachment filename."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        cd = response["Content-Disposition"]
        self.assertIn("attachment", cd)
        self.assertIn("filename=", cd)
        self.assertIn(".pdf", cd)

    def test_pdf_view_denies_access_when_user_cannot_access_patient(self):
        """The PDF view should return 403 when patient access is denied."""
        self.client.login(username="otherdoctor", password="testpass123")

        with patch("apps.dailynotes.views.can_access_patient", return_value=False):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)
