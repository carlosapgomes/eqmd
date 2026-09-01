"""Pending temporary-record dashboard tests (slice 003).

Staff-only list of patients whose current record number is still a
system-generated temporary: oldest first, with pending age, the creation
reason and an aggregate count by creator.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user

from ..models import Patient
from ..services.temporary_record import generate_temporary_record_number
from .test_patient_record_constraint_database import (
    _create_doctor,
    _create_patient,
    _create_record,
)

DASHBOARD_URL = reverse("patients:temporary_record_list")
LOGIN_URL = "/accounts/login/"


def _backdate(patient: Patient, days_ago: int) -> None:
    """Move created_at back deterministically (auto_now_add ignores updates)."""
    Patient.objects.filter(pk=patient.pk).update(
        created_at=timezone.now() - timedelta(days=days_ago)
    )


def _temporary_patient(user, name: str, days_ago: int = 0) -> Patient:
    """Create a patient whose current number is a generated temporary."""
    number = generate_temporary_record_number()
    patient = _create_patient(user, name=name)
    _create_record(patient, number, user)
    patient.current_record_number = number
    patient.save(update_fields=["current_record_number"])
    if days_ago:
        _backdate(patient, days_ago)
    return patient


def _definitive_patient(user, name: str, number: str = "REC001") -> Patient:
    """Create a control patient with a definitive record number."""
    patient = _create_patient(user, name=name)
    _create_record(patient, number, user)
    patient.current_record_number = number
    patient.save(update_fields=["current_record_number"])
    return patient


class TemporaryRecordDashboardAccessTests(TestCase):
    """R1/R2 access gate: only staff reaches the pending dashboard."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = create_navigation_user(
            username="dashboardstaff",
            email="dashboardstaff@example.com",
            password="testpassword",
            is_staff=True,
        )
        cls.creator = _create_doctor("dashboarddoc")
        cls.temporary = _temporary_patient(cls.creator, "Pending Temporary")
        cls.definitive = _definitive_patient(cls.creator, "Definitive Control")

    def test_staff_sees_only_pending_temporaries(self):
        """Staff gets 200; temporaries are listed, definitives are not."""
        self.client.force_login(self.staff)
        response = self.client.get(DASHBOARD_URL)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "patients/temporary_record_list.html")
        self.assertContains(response, self.temporary.name)
        self.assertContains(response, self.temporary.current_record_number)
        self.assertNotContains(response, self.definitive.name)

    def test_non_staff_is_denied(self):
        """Authenticated non-staff gets access denied.

        UserPassesTestMixin/AccessMixin raises PermissionDenied (403) for
        authenticated users; the observed framework behavior is fixed here.
        """
        self.client.force_login(self.creator)
        response = self.client.get(DASHBOARD_URL)

        # Access is fully denied: no patient data is rendered at all.
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(self.temporary.name, response.content.decode())

    def test_anonymous_redirects_to_login(self):
        """Anonymous visitors are sent to the login page."""
        response = self.client.get(DASHBOARD_URL)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(LOGIN_URL))


class TemporaryRecordDashboardContentTests(TestCase):
    """R1 ordering, soft-delete exclusion, pending age and creator aggregate."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = create_navigation_user(
            username="dashboardstaff2",
            email="dashboardstaff2@example.com",
            password="testpassword",
            is_staff=True,
        )
        cls.creator_a = _create_doctor("creatorone")
        cls.creator_b = _create_doctor("creatortwo")
        cls.oldest = _temporary_patient(cls.creator_a, "Oldest Pending", days_ago=5)
        cls.newest = _temporary_patient(cls.creator_b, "Newest Pending", days_ago=1)
        cls.extra_for_a = _temporary_patient(
            cls.creator_a, "Extra Pending A", days_ago=2
        )

    def setUp(self):
        self.client.force_login(self.staff)

    def test_oldest_pending_appears_first(self):
        """Rows are ordered by created_at ascending (oldest pending first)."""
        response = self.client.get(DASHBOARD_URL)

        self.assertEqual(response.status_code, 200)
        patients = list(response.context["patients"])
        self.assertEqual(
            [patient.pk for patient in patients],
            [self.oldest.pk, self.extra_for_a.pk, self.newest.pk],
        )
        self.assertContains(response, self.oldest.name)

    def test_soft_deleted_temporary_is_excluded(self):
        """Soft-deleted temporaries never appear on the dashboard."""
        self.extra_for_a.delete()

        response = self.client.get(DASHBOARD_URL)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.extra_for_a.name)
        self.assertEqual(
            {patient.pk for patient in response.context["patients"]},
            {self.oldest.pk, self.newest.pk},
        )

    def test_pending_days_is_integer_from_created_at(self):
        """Pending age is the whole day count since the patient creation."""
        response = self.client.get(DASHBOARD_URL)

        patient = response.context["patients"].get(pk=self.oldest.pk)
        self.assertEqual(patient.pending_days, 5)

    def test_aggregate_by_creator_counts_from_same_queryset(self):
        """Creator aggregate counts pending rows, sorted by count desc."""
        response = self.client.get(DASHBOARD_URL)

        aggregate = dict(response.context["aggregate_by_creator"])
        self.assertEqual(aggregate[self.creator_a.username], 2)
        self.assertEqual(aggregate[self.creator_b.username], 1)

        counts = [count for _, count in response.context["aggregate_by_creator"]]
        self.assertEqual(counts, sorted(counts, reverse=True))
