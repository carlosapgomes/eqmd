"""Timeline card duplicate action tests for outpatient prescriptions.

Slice S2 of change ``extend-document-duplication``: the prescription card on
the patient timeline exposes the existing POST-only duplicate endpoint to
users holding ``events.add_event``. Clone semantics live in
``apps.outpatientprescriptions.tests.test_views`` — these tests only cover the
card entry point.
"""

import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.outpatientprescriptions.models import (
    OutpatientPrescription,
    PrescriptionItem,
)
from apps.patients.models import Patient

User = get_user_model()


def grant_event_permissions(user, *codenames):
    """Grant the given events app permissions to a user.

    The test database does not seed the profession groups' permissions, so the
    tests must grant the exact Django permissions enforced by
    PermissionRequiredMixin on the duplicate view.
    """
    perms = Permission.objects.filter(
        content_type__app_label="events", codename__in=codenames
    )
    user.user_permissions.add(*perms)


class PrescriptionTimelineCardDuplicateTest(TestCase):
    """Duplicate control rendered by the timeline prescription card."""

    @classmethod
    def setUpTestData(cls):
        """Set up users, patient and a finalized prescription event."""
        cls.authorized_user = User.objects.create_user(
            username="carddupallowed",
            email="carddupallowed@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        grant_event_permissions(cls.authorized_user, "add_event")

        cls.unauthorized_user = User.objects.create_user(
            username="carddupdenied",
            email="carddupdenied@example.com",
            password="testpass123",
            profession_type=User.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )

        cls.patient = Patient.objects.create(
            name="Card Duplicate Patient",
            birthday="1990-01-01",
            status=1,
            created_by=cls.authorized_user,
            updated_by=cls.authorized_user,
        )

        cls.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now() - timedelta(days=1),
            description="Receita",
            instructions="Take as directed",
            status="finalized",
            prescription_date=timezone.localdate() - timedelta(days=1),
            patient=cls.patient,
            created_by=cls.authorized_user,
            updated_by=cls.authorized_user,
        )
        cls.item = PrescriptionItem.objects.create(
            prescription=cls.prescription,
            drug_name="Card Drug",
            presentation="10mg tablet",
            usage_instructions="Take 1 daily",
            quantity="30",
            order=1,
        )

    def setUp(self):
        """Create a fresh HTTP client per test."""
        self.client = Client()

    def timeline_url(self):
        """Return the patient timeline URL."""
        return reverse(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )

    def duplicate_url(self):
        """Return the duplicate endpoint URL for the card's prescription."""
        return reverse(
            "outpatientprescriptions:outpatientprescription_duplicate",
            kwargs={"pk": self.prescription.pk},
        )

    def timeline_html(self):
        """Load the timeline as the authorized user and return the HTML."""
        self.client.login(username="carddupallowed", password="testpass123")
        return self.client.get(self.timeline_url()).content.decode()

    def test_timeline_prescription_card_renders_duplicate_form(self):
        """R1: authorized viewers get a Duplicar POST form targeting the endpoint."""
        html = self.timeline_html()

        self.assertIn(f'action="{self.duplicate_url()}"', html)
        self.assertIn("csrfmiddlewaretoken", html)
        self.assertIn("bi-files", html)
        self.assertIn("btn-outline-info", html)
        self.assertIn('aria-label="Duplicar receita"', html)
        self.assertIn('title="Criar nova receita baseada nesta"', html)
        self.assertIn("Duplicar", html)

    def test_timeline_prescription_card_duplicate_form_is_inline_post(self):
        """R1/R4: the card control is an inline POST form, never a GET link."""
        html = self.timeline_html()

        self.assertRegex(
            html,
            re.compile(
                rf'<form method="post" action="{re.escape(self.duplicate_url())}"'
                r' class="d-inline">'
            ),
        )
        self.assertNotIn(f'href="{self.duplicate_url()}"', html)

    def test_timeline_prescription_card_hides_duplicate_without_add_event(self):
        """R2: viewers without events.add_event see no duplicate control."""
        self.client.login(username="carddupdenied", password="testpass123")
        response = self.client.get(self.timeline_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ver receita completa")
        self.assertNotContains(response, f'action="{self.duplicate_url()}"')
        self.assertNotContains(response, 'aria-label="Duplicar receita"')

    def test_direct_post_without_add_event_is_denied(self):
        """R2: the view still rejects a direct POST from unauthorized users."""
        self.client.login(username="carddupdenied", password="testpass123")
        count_before = OutpatientPrescription.objects.count()

        response = self.client.post(self.duplicate_url())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(OutpatientPrescription.objects.count(), count_before)

    def test_card_form_action_duplicates_into_draft_and_redirects_to_edit(self):
        """R3: submitting the card form lands on the new draft's edit view."""
        html = self.timeline_html()
        match = re.search(
            r'<form method="post" action="([^"]+)" class="d-inline">', html
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), self.duplicate_url())

        response = self.client.post(match.group(1))

        self.assertEqual(response.status_code, 302)
        copy = OutpatientPrescription.objects.exclude(pk=self.prescription.pk).get()
        self.assertEqual(copy.status, "draft")
        self.assertEqual(response.url, copy.get_edit_url())
