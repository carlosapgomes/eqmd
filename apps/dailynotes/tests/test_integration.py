"""
Integration tests for DailyNote features.

Tests patient integration, search/filtering, dashboard widgets,
print features, and core CRUD flows — aligned to the current
domain model (Ward, simplified permissions, actual URL routes).
"""

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from apps.patients.models import Patient
from apps.dailynotes.models import DailyNote
from apps.dailynotes.templatetags.dailynote_tags import (
    recent_dailynotes_widget,
    dailynotes_count_today,
    dailynotes_count_week,
)

User = get_user_model()


class DailyNoteIntegrationTestCase(TestCase):
    """Base test case with common setup for integration tests."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data shared across tests."""
        from django.contrib.auth.models import Permission

        cls.doctor = User.objects.create_user(
            username="doctor",
            email="doctor@test.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            first_name="Dr.",
            last_name="Test",
        )
        cls.nurse = User.objects.create_user(
            username="nurse",
            email="nurse@test.com",
            password="testpass123",
            profession_type=User.NURSE,
        )

        # Clear password-change-required flag and terms acceptance
        User.objects.filter(pk__in=[cls.doctor.pk, cls.nurse.pk]).update(
            password_change_required=False,
            terms_accepted=True,
        )

        # Grant event permissions to both users
        event_permissions = Permission.objects.filter(
            codename__in=["view_event", "add_event", "change_event", "delete_event"]
        )
        cls.doctor.user_permissions.set(event_permissions)
        cls.nurse.user_permissions.set(event_permissions)

        cls.patient1 = Patient.objects.create(
            name="Patient One",
            birthday="1980-01-01",
            status=Patient.Status.INPATIENT,
            bed="101",
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )
        cls.patient2 = Patient.objects.create(
            name="Patient Two",
            birthday="1975-06-15",
            status=Patient.Status.OUTPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        """Set up per-test data."""
        now = timezone.now()

        self.dailynote1 = DailyNote.objects.create(
            patient=self.patient1,
            content="Patient is stable. No major changes.",
            event_datetime=now - timedelta(hours=2),
            created_by=self.doctor,
            updated_by=self.doctor,
        )
        self.dailynote2 = DailyNote.objects.create(
            patient=self.patient2,
            content="Patient improving. Continue treatment.",
            event_datetime=now - timedelta(hours=1),
            created_by=self.nurse,
            updated_by=self.nurse,
        )
        self.dailynote3 = DailyNote.objects.create(
            patient=self.patient1,
            content="Patient condition worsened. Adjust medication.",
            event_datetime=now - timedelta(days=1),
            created_by=self.doctor,
            updated_by=self.doctor,
        )

        self.client = Client()


# ---------------------------------------------------------------------------
# Patient-specific daily note views
# ---------------------------------------------------------------------------
class PatientDailyNoteCreateTests(DailyNoteIntegrationTestCase):
    """Test patient-specific daily note creation view."""

    def test_patient_dailynote_create_get(self):
        """GET for patient-specific daily note create view returns 200."""
        self.client.login(username="doctor", password="testpass123")
        url = reverse(
            "dailynotes:patient_dailynote_create",
            kwargs={"patient_pk": self.patient1.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient1.name)

    def test_patient_dailynote_create_post(self):
        """POST creates a new daily note for the patient."""
        self.client.login(username="doctor", password="testpass123")
        url = reverse(
            "dailynotes:patient_dailynote_create",
            kwargs={"patient_pk": self.patient1.pk},
        )
        # Use localtime to match form's timezone interpretation
        past_dt = timezone.localtime(timezone.now() - timedelta(hours=1))
        response = self.client.post(url, {
            "event_datetime": past_dt.strftime("%Y-%m-%dT%H:%M"),
            "content": "New evolution note with enough characters.",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            DailyNote.objects.filter(
                patient=self.patient1,
                content="New evolution note with enough characters.",
            ).exists()
        )


# ---------------------------------------------------------------------------
# Detail, Update, Delete, Duplicate views
# ---------------------------------------------------------------------------
class DailyNoteCRUDIntegrationTests(DailyNoteIntegrationTestCase):
    """Integration tests for core CRUD views."""

    def test_dailynote_detail_view(self):
        """Detail view returns 200 and displays note content."""
        self.client.login(username="doctor", password="testpass123")
        url = reverse(
            "dailynotes:dailynote_detail",
            kwargs={"pk": self.dailynote1.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.dailynote1.content)

    def test_dailynote_update_view_creator_allowed_within_window(self):
        """Creator can access update view within the edit time window."""
        self.client.login(username="doctor", password="testpass123")
        url = reverse(
            "dailynotes:dailynote_update",
            kwargs={"pk": self.dailynote1.pk},
        )
        response = self.client.get(url)
        # Doctor is creator and note was just created → edit allowed
        self.assertEqual(response.status_code, 200)

    def test_dailynote_delete_view_creator_allowed_within_window(self):
        """Creator can access delete view within the delete time window."""
        self.client.login(username="doctor", password="testpass123")
        url = reverse(
            "dailynotes:dailynote_delete",
            kwargs={"pk": self.dailynote1.pk},
        )
        response = self.client.get(url)
        # Doctor is creator and note was just created → delete allowed
        self.assertEqual(response.status_code, 200)

    def test_dailynote_duplicate_view_allowed_with_permission(self):
        """Duplicate view loads for authenticated user with add_event permission."""
        self.client.login(username="doctor", password="testpass123")
        url = reverse(
            "dailynotes:dailynote_duplicate",
            kwargs={"pk": self.dailynote1.pk},
        )
        response = self.client.get(url)
        # Doctor has add_event permission and can access patient → allowed
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# Print / PDF
# ---------------------------------------------------------------------------
class PrintRouteRemovedTests(DailyNoteIntegrationTestCase):
    """Verify that the legacy print route has been removed."""

    def test_dailynote_print_route_no_reverse(self):
        """Reversing 'dailynote_print' raises NoReverseMatch."""
        from django.urls import NoReverseMatch

        with self.assertRaises(NoReverseMatch):
            reverse(
                "dailynotes:dailynote_print",
                kwargs={"pk": self.dailynote1.pk},
            )

    def test_dailynote_print_url_returns_404(self):
        """Direct GET to <pk>/print/ returns 404 (route removed)."""
        self.client.login(username="doctor", password="testpass123")
        url = f"/dailynotes/{self.dailynote1.pk}/print/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @patch("apps.dailynotes.views.DailyNotePDFGenerator")
    def test_dailynote_pdf_view_success(self, mock_pdf_cls):
        """PDF download returns 200 with PDF content on success."""
        from io import BytesIO

        mock_buffer = BytesIO(b"%PDF-fake-content")
        mock_pdf_cls.return_value.generate_from_dailynote.return_value = mock_buffer

        self.client.login(username="doctor", password="testpass123")
        url = reverse(
            "dailynotes:dailynote_pdf",
            kwargs={"pk": self.dailynote1.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    @patch(
        "apps.dailynotes.views.DailyNotePDFGenerator",
        side_effect=Exception("PDF engine failure"),
    )
    def test_dailynote_pdf_view_error_returns_500(self, mock_pdf_cls):
        """PDF download returns 500 when PDF generation fails."""
        # mock_pdf_cls is the class itself; instantiating it returns a regular
        # object, but the view calls DailyNotePDFGenerator() then
        # .generate_from_dailynote().  We make the constructor raise so the
        # generic except clause in the view is triggered.
        mock_pdf_cls.side_effect = Exception("PDF engine failure")

        self.client.login(username="doctor", password="testpass123")
        url = reverse(
            "dailynotes:dailynote_pdf",
            kwargs={"pk": self.dailynote1.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# Dashboard widgets (template tags)
# ---------------------------------------------------------------------------
class DashboardIntegrationTests(DailyNoteIntegrationTestCase):
    """Test dashboard widget integration."""

    def _make_request_context(self, user):
        """Build a minimal request context for template tags."""
        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        return {"request": request}

    def test_recent_dailynotes_widget(self):
        """Widget returns recent daily notes."""
        context = self._make_request_context(self.doctor)
        result = recent_dailynotes_widget(context, limit=5)
        self.assertIn("recent_dailynotes", result)
        # At least the 3 notes we created should be visible
        self.assertGreaterEqual(len(result["recent_dailynotes"]), 3)

    def test_dailynotes_count_today(self):
        """Tag counts today's notes correctly."""
        context = self._make_request_context(self.doctor)
        count = dailynotes_count_today(context)
        # dailynote1 and dailynote2 are within today; dailynote3 is yesterday
        self.assertEqual(count, 2)

    def test_dailynotes_count_week(self):
        """Tag counts this week's notes correctly."""
        context = self._make_request_context(self.doctor)
        count = dailynotes_count_week(context)
        self.assertGreaterEqual(count, 3)


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------
class UnauthenticatedAccessTests(DailyNoteIntegrationTestCase):
    """Ensure unauthenticated users are redirected to login."""

    def test_detail_requires_login(self):
        url = reverse(
            "dailynotes:dailynote_detail",
            kwargs={"pk": self.dailynote1.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_create_denies_unauthenticated(self):
        url = reverse(
            "dailynotes:patient_dailynote_create",
            kwargs={"patient_pk": self.patient1.pk},
        )
        response = self.client.get(url)
        # PatientDailyNoteCreateView.dispatch checks can_access_patient
        # before LoginRequiredMixin, so AnonymousUser gets PermissionDenied (403)
        self.assertEqual(response.status_code, 403)

    def test_print_route_is_not_registered(self):
        """Legacy print route is not registered — reversing raises NoReverseMatch."""
        from django.urls import NoReverseMatch

        with self.assertRaises(NoReverseMatch):
            reverse(
                "dailynotes:dailynote_print",
                kwargs={"pk": self.dailynote1.pk},
            )
