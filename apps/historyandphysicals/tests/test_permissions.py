from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

# Hospital model removed after the single-hospital refactor: every
# authenticated user can access all patients (apps/core/permissions/utils.py).
from apps.core.permissions import can_access_patient, can_delete_event, can_edit_event
from apps.patients.models import Patient

from ..models import HistoryAndPhysical

User = get_user_model()


def grant_event_permissions(user, *codenames):
    """Grant the given events app permissions to a user.

    The test database does not seed the profession groups' permissions, so
    view tests must grant the exact Django permissions enforced by
    PermissionRequiredMixin on the detail/create/update/delete/duplicate views.
    """
    perms = Permission.objects.filter(
        content_type__app_label="events", codename__in=codenames
    )
    user.user_permissions.add(*perms)


class HistoryAndPhysicalPermissionsTest(TestCase):
    """Test permissions for HistoryAndPhysical operations."""

    def setUp(self):
        """Set up test data."""
        # Lifecycle gates cleared so the core middleware does not redirect
        # (NavigationReadyUserFactory contract).
        self.doctor = User.objects.create_user(
            username="doctor",
            email="doctor@test.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )

        self.nurse = User.objects.create_user(
            username="nurse",
            email="nurse@test.com",
            password="testpass123",
            profession_type=User.NURSE,
            password_change_required=False,
            terms_accepted=True,
        )

        self.student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            profession_type=User.STUDENT,
            password_change_required=False,
            terms_accepted=True,
        )

        # View tests exercise the PermissionRequiredMixin views.
        grant_event_permissions(
            self.doctor, "view_event", "add_event", "change_event", "delete_event"
        )

        # Create patients
        self.inpatient = Patient.objects.create(
            name="Inpatient Test",
            birthday="1990-01-01",
            status=Patient.Status.INPATIENT,
            created_by=self.doctor,
            updated_by=self.doctor,
        )

        self.outpatient = Patient.objects.create(
            name="Outpatient Test",
            birthday="1985-01-01",
            status=Patient.Status.OUTPATIENT,
            created_by=self.doctor,
            updated_by=self.doctor,
        )

        # Create history and physicals
        self.recent_historyandphysical = HistoryAndPhysical.objects.create(
            event_datetime=timezone.now(),
            description="Recent History and Physical",
            content="Recent content.",
            patient=self.inpatient,
            created_by=self.doctor,
            updated_by=self.doctor,
        )

        self.old_historyandphysical = HistoryAndPhysical.objects.create(
            event_datetime=timezone.now()
            - timezone.timedelta(hours=25),  # More than 24 hours old
            description="Old History and Physical",
            content="Old content.",
            patient=self.inpatient,
            created_by=self.doctor,
            updated_by=self.doctor,
        )
        # The edit/delete window is measured from created_at, so simulate an
        # old record (same pattern as apps/events test_soft_delete).
        HistoryAndPhysical.objects.filter(pk=self.old_historyandphysical.pk).update(
            created_at=timezone.now() - timezone.timedelta(hours=25)
        )
        self.old_historyandphysical.refresh_from_db()

    def test_doctor_can_access_all_patients(self):
        """Test that doctors can access all patients (single-hospital setup)."""
        # Doctor should be able to access inpatient
        self.assertTrue(can_access_patient(self.doctor, self.inpatient))

        # Doctor should be able to access outpatient
        self.assertTrue(can_access_patient(self.doctor, self.outpatient))

    def test_nurse_can_access_all_patients(self):
        """Test that nurses can access all patients (single-hospital setup)."""
        # Nurse should be able to access inpatient
        self.assertTrue(can_access_patient(self.nurse, self.inpatient))

        # Nurse should be able to access outpatient
        self.assertTrue(can_access_patient(self.nurse, self.outpatient))

    def test_student_can_access_all_patients(self):
        """Test that students can access all patients (single-hospital setup)."""
        # The single-hospital refactor removed the student-outpatient-only
        # restriction; every authenticated user can access every patient.
        self.assertTrue(can_access_patient(self.student, self.inpatient))

        self.assertTrue(can_access_patient(self.student, self.outpatient))

    def test_can_edit_recent_historyandphysical(self):
        """Test that users can edit recent history and physicals (within 24 hours)."""
        # Creator should be able to edit recent history and physical
        self.assertTrue(can_edit_event(self.doctor, self.recent_historyandphysical))

        # Only the creator can edit an event (creator-only contract); another
        # doctor cannot, regardless of profession.
        other_doctor = User.objects.create_user(
            username="otherdoc",
            email="otherdoc@test.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        self.assertFalse(can_edit_event(other_doctor, self.recent_historyandphysical))

    def test_cannot_edit_old_historyandphysical(self):
        """Test that users cannot edit old history and physicals (older than 24 hours)."""
        # Even creator should not be able to edit old history and physical
        self.assertFalse(can_edit_event(self.doctor, self.old_historyandphysical))

    def test_can_delete_recent_historyandphysical(self):
        """Test that users can delete recent history and physicals."""
        # Creator should be able to delete recent history and physical
        self.assertTrue(can_delete_event(self.doctor, self.recent_historyandphysical))

    def test_cannot_delete_old_historyandphysical(self):
        """Test that users cannot delete old history and physicals."""
        # Even creator should not be able to delete old history and physical
        self.assertFalse(can_delete_event(self.doctor, self.old_historyandphysical))

    def test_view_permissions_in_detail_view(self):
        """Test that detail view properly checks permissions."""
        client = Client()

        # Login as doctor
        client.login(username="doctor", password="testpass123")

        url = reverse(
            "apps.historyandphysicals:historyandphysical_detail",
            kwargs={"pk": self.recent_historyandphysical.pk},
        )
        response = client.get(url)

        self.assertEqual(response.status_code, 200)

        # Login as student and try to access inpatient's history and physical
        client.login(username="student", password="testpass123")

        response = client.get(url)
        # Student lacks events.view_event -> PermissionRequiredMixin redirects
        self.assertIn(response.status_code, [403, 302])

    def test_create_permissions(self):
        """Test create permissions for history and physicals."""
        client = Client()

        # Doctor should be able to create
        client.login(username="doctor", password="testpass123")

        url = reverse(
            "apps.historyandphysicals:historyandphysical_create",
            kwargs={"patient_pk": self.inpatient.pk},
        )

        form_data = {
            "event_datetime": timezone.localtime(
                timezone.now() - timezone.timedelta(hours=1)
            ).strftime("%Y-%m-%dT%H:%M"),
            "content": "New history and physical content with enough characters.",
        }

        response = client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Successful redirect

        # Student should not be able to create for inpatient (no add_event)
        client.login(username="student", password="testpass123")

        response = client.get(url)
        self.assertIn(response.status_code, [403, 302])

    def test_update_permissions(self):
        """Test update permissions for history and physicals."""
        client = Client()

        # Doctor should be able to update recent history and physical
        client.login(username="doctor", password="testpass123")

        url = reverse(
            "apps.historyandphysicals:historyandphysical_update",
            kwargs={"pk": self.recent_historyandphysical.pk},
        )

        form_data = {
            "event_datetime": timezone.localtime(
                self.recent_historyandphysical.event_datetime
            ).strftime("%Y-%m-%dT%H:%M"),
            "content": "Updated history and physical content with enough characters.",
        }

        response = client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Successful redirect

        # Should not be able to update old history and physical
        url = reverse(
            "apps.historyandphysicals:historyandphysical_update",
            kwargs={"pk": self.old_historyandphysical.pk},
        )

        response = client.get(url)
        self.assertIn(response.status_code, [403, 302])

    def test_delete_permissions(self):
        """Test delete permissions for history and physicals."""
        client = Client()

        # Doctor should be able to delete recent history and physical
        client.login(username="doctor", password="testpass123")

        url = reverse(
            "apps.historyandphysicals:historyandphysical_delete",
            kwargs={"pk": self.recent_historyandphysical.pk},
        )

        response = client.get(url)
        self.assertEqual(response.status_code, 200)  # Can access delete page

        # Should not be able to delete old history and physical
        url = reverse(
            "apps.historyandphysicals:historyandphysical_delete",
            kwargs={"pk": self.old_historyandphysical.pk},
        )

        response = client.get(url)
        self.assertIn(response.status_code, [403, 302])

    def test_duplicate_permissions(self):
        """Test duplicate permissions for history and physicals."""
        client = Client()

        # Doctor should be able to duplicate history and physical
        client.login(username="doctor", password="testpass123")

        url = reverse(
            "apps.historyandphysicals:historyandphysical_duplicate",
            kwargs={"pk": self.recent_historyandphysical.pk},
        )

        response = client.get(url)
        self.assertEqual(response.status_code, 200)  # Can access duplicate page

        # Student should not be able to duplicate (no add_event permission)
        client.login(username="student", password="testpass123")

        response = client.get(url)
        self.assertIn(response.status_code, [403, 302])

    def test_print_permissions(self):
        """Test print permissions for history and physicals."""
        client = Client()

        # Doctor should be able to print
        client.login(username="doctor", password="testpass123")

        url = reverse(
            "apps.historyandphysicals:historyandphysical_print",
            kwargs={"pk": self.recent_historyandphysical.pk},
        )

        response = client.get(url)
        self.assertEqual(response.status_code, 200)

        # Single-hospital setup: any authenticated user can access all patients,
        # so the student can print too (the print view only requires login and
        # patient access).
        client.login(username="student", password="testpass123")

        response = client.get(url)
        self.assertEqual(response.status_code, 200)

        # Anonymous users are still denied (login required)
        client.logout()
        response = client.get(url)
        self.assertEqual(response.status_code, 302)
