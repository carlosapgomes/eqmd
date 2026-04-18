"""
Permission tests for DailyNote app.

Tests comprehensive permission system integration including:
- Different user roles (doctor, nurse, student, etc.)
- Time-based edit/delete restrictions
- Unauthorized access attempts
- View-level permission enforcement

Aligned to simplified permission model (no Hospital/current_hospital).
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from apps.dailynotes.models import DailyNote
from apps.dailynotes.forms import DailyNoteForm
from apps.patients.models import Patient

User = get_user_model()


class DailyNotePermissionTestMixin:
    """Mixin providing common setUp for permission tests."""

    @classmethod
    def setUpTestData(cls):
        cls.doctor = User.objects.create_user(
            username="doctor",
            email="doctor@test.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
        )
        cls.nurse = User.objects.create_user(
            username="nurse",
            email="nurse@test.com",
            password="testpass123",
            profession_type=User.NURSE,
        )
        cls.student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            profession_type=User.STUDENT,
        )
        # Clear password-change-required flag and terms acceptance
        User.objects.filter(
            pk__in=[cls.doctor.pk, cls.nurse.pk, cls.student.pk]
        ).update(password_change_required=False, terms_accepted=True)

        # Grant event permissions to doctor and nurse
        from django.contrib.auth.models import Permission
        event_permissions = Permission.objects.filter(
            codename__in=["view_event", "add_event", "change_event", "delete_event"]
        )
        cls.doctor.user_permissions.set(event_permissions)
        cls.nurse.user_permissions.set(event_permissions)
        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor,
        )

    def setUp(self):
        self.client = Client()


# ---------------------------------------------------------------------------
# Form-level permission tests
# ---------------------------------------------------------------------------
class DailyNoteFormPermissionTests(DailyNotePermissionTestMixin, TestCase):
    """Test permission enforcement in forms."""

    def test_form_creation_with_user(self):
        """Form can be instantiated with a user."""
        form = DailyNoteForm(user=self.doctor)
        self.assertIsNotNone(form)
        self.assertIn("content", form.fields)
        self.assertIn("event_datetime", form.fields)

    def test_form_valid_data(self):
        """Form is valid with correct data."""
        form_data = {
            "event_datetime": timezone.localtime(timezone.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
            "content": "Test content with enough characters.",
        }
        form = DailyNoteForm(data=form_data, user=self.doctor)
        self.assertTrue(form.is_valid())

    def test_form_rejects_future_datetime(self):
        """Form rejects event_datetime in the future."""
        form_data = {
            "event_datetime": (timezone.now() + timedelta(days=1)).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "content": "Test content with enough characters.",
        }
        form = DailyNoteForm(data=form_data, user=self.doctor)
        self.assertFalse(form.is_valid())
        self.assertIn("event_datetime", form.errors)

    def test_form_rejects_short_content(self):
        """Form rejects content shorter than 10 characters."""
        form_data = {
            "event_datetime": timezone.localtime(timezone.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
            "content": "Short",
        }
        form = DailyNoteForm(data=form_data, user=self.doctor)
        self.assertFalse(form.is_valid())
        self.assertIn("content", form.errors)

    def test_form_save_sets_created_by(self):
        """Form save sets created_by and updated_by from user."""
        form_data = {
            "event_datetime": timezone.localtime(timezone.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
            "content": "Test content with enough characters for save.",
        }
        form = DailyNoteForm(data=form_data, user=self.doctor)
        self.assertTrue(form.is_valid())
        form.instance.patient = self.patient
        dailynote = form.save()
        self.assertEqual(dailynote.created_by, self.doctor)
        self.assertEqual(dailynote.updated_by, self.doctor)


# ---------------------------------------------------------------------------
# View-level permission tests
# ---------------------------------------------------------------------------
class DailyNoteViewPermissionTests(DailyNotePermissionTestMixin, TestCase):
    """Test permission enforcement in views."""

    def setUp(self):
        super().setUp()
        self.dailynote = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            content="Test content for view permission tests.",
            created_by=self.doctor,
            updated_by=self.doctor,
        )

    # -- detail view --

    def test_detail_view_authenticated(self):
        """Authenticated user can view daily note detail."""
        self.client.login(username="doctor", password="testpass123")
        response = self.client.get(
            reverse("dailynotes:dailynote_detail", kwargs={"pk": self.dailynote.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_view_context_has_edit_permission_flags(self):
        """Detail view context includes edit/delete permission flags."""
        self.client.login(username="doctor", password="testpass123")
        response = self.client.get(
            reverse("dailynotes:dailynote_detail", kwargs={"pk": self.dailynote.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("can_edit_dailynote", response.context)
        self.assertIn("can_delete_dailynote", response.context)

    # -- update view --

    def test_update_view_creator_within_window(self):
        """Creator can access update view within edit window."""
        self.client.login(username="doctor", password="testpass123")
        response = self.client.get(
            reverse("dailynotes:dailynote_update", kwargs={"pk": self.dailynote.pk})
        )
        # Just created, so doctor should be allowed
        self.assertEqual(response.status_code, 200)

    @patch("apps.dailynotes.views.can_edit_event", return_value=False)
    def test_update_view_denied_when_edit_permission_false(self, _mock):
        """Update view returns 403 when can_edit_event is False."""
        self.client.login(username="doctor", password="testpass123")
        response = self.client.get(
            reverse("dailynotes:dailynote_update", kwargs={"pk": self.dailynote.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_update_view_denied_for_non_creator(self):
        """Non-creator cannot access update view (can_edit_event returns False)."""
        self.client.login(username="nurse", password="testpass123")
        response = self.client.get(
            reverse("dailynotes:dailynote_update", kwargs={"pk": self.dailynote.pk})
        )
        self.assertEqual(response.status_code, 403)

    # -- delete view --

    def test_delete_view_creator_within_window(self):
        """Creator can access delete view within delete window."""
        self.client.login(username="doctor", password="testpass123")
        response = self.client.get(
            reverse("dailynotes:dailynote_delete", kwargs={"pk": self.dailynote.pk})
        )
        self.assertEqual(response.status_code, 200)

    @patch("apps.dailynotes.views.can_delete_event", return_value=False)
    def test_delete_view_denied_when_delete_permission_false(self, _mock):
        """Delete view returns 403 when can_delete_event is False."""
        self.client.login(username="doctor", password="testpass123")
        response = self.client.get(
            reverse("dailynotes:dailynote_delete", kwargs={"pk": self.dailynote.pk})
        )
        self.assertEqual(response.status_code, 403)

    # -- duplicate view --

    def test_duplicate_view_requires_add_permission(self):
        """Duplicate view requires events.add_event permission."""
        # Student without permission → 403
        self.client.login(username="student", password="testpass123")
        response = self.client.get(
            reverse("dailynotes:dailynote_duplicate", kwargs={"pk": self.dailynote.pk})
        )
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# Time-based permission tests
# ---------------------------------------------------------------------------
class DailyNoteTimeBasedPermissionTests(DailyNotePermissionTestMixin, TestCase):
    """Test time-based edit/delete restrictions."""

    def test_edit_denied_for_old_note(self):
        """Cannot edit a note older than 24 hours."""
        old_note = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=25),
            content="Old note content for time-based permission test.",
            created_by=self.doctor,
            updated_by=self.doctor,
        )
        # Force created_at into the past
        DailyNote.objects.filter(pk=old_note.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        old_note.refresh_from_db()

        self.client.login(username="doctor", password="testpass123")
        response = self.client.get(
            reverse("dailynotes:dailynote_update", kwargs={"pk": old_note.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_delete_denied_for_old_note(self):
        """Cannot delete a note older than 24 hours."""
        old_note = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now() - timedelta(hours=25),
            content="Old note content for delete time-based test.",
            created_by=self.doctor,
            updated_by=self.doctor,
        )
        DailyNote.objects.filter(pk=old_note.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        old_note.refresh_from_db()

        self.client.login(username="doctor", password="testpass123")
        response = self.client.get(
            reverse("dailynotes:dailynote_delete", kwargs={"pk": old_note.pk})
        )
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# Unauthenticated access tests
# ---------------------------------------------------------------------------
class DailyNoteUnauthenticatedAccessTests(TestCase):
    """Test that unauthenticated users cannot access any daily note views."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        User.objects.filter(pk=cls.user.pk).update(
            password_change_required=False, terms_accepted=True
        )
        cls.patient = Patient.objects.create(
            name="Test Patient",
            birthday="1990-01-01",
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user,
        )
        cls.dailynote = DailyNote.objects.create(
            patient=cls.patient,
            event_datetime=timezone.now(),
            content="Test content for unauthenticated access tests.",
            created_by=cls.user,
            updated_by=cls.user,
        )

    def test_detail_redirects_to_login(self):
        response = self.client.get(
            reverse("dailynotes:dailynote_detail", kwargs={"pk": self.dailynote.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_create_denies_unauthenticated(self):
        response = self.client.get(
            reverse(
                "dailynotes:patient_dailynote_create",
                kwargs={"patient_pk": self.patient.pk},
            )
        )
        # PatientDailyNoteCreateView.dispatch checks can_access_patient
        # before LoginRequiredMixin, so AnonymousUser gets PermissionDenied (403)
        self.assertEqual(response.status_code, 403)

    def test_update_redirects_to_login(self):
        response = self.client.get(
            reverse("dailynotes:dailynote_update", kwargs={"pk": self.dailynote.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_delete_redirects_to_login(self):
        response = self.client.get(
            reverse("dailynotes:dailynote_delete", kwargs={"pk": self.dailynote.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_duplicate_denies_unauthenticated(self):
        response = self.client.get(
            reverse("dailynotes:dailynote_duplicate", kwargs={"pk": self.dailynote.pk})
        )
        # DailyNoteDuplicateView.dispatch checks can_access_patient
        # before LoginRequiredMixin, so AnonymousUser gets PermissionDenied (403)
        self.assertEqual(response.status_code, 403)

    def test_print_redirects_to_login(self):
        response = self.client.get(
            reverse("dailynotes:dailynote_print", kwargs={"pk": self.dailynote.pk})
        )
        self.assertEqual(response.status_code, 302)
