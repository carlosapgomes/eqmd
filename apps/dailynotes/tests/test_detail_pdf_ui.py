"""
Tests for Daily Note detail page PDF UI.

Verifies that the detail page includes the PDF download action,
loads the pdf-download.js script, and does NOT expose a legacy print
fallback.
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.dailynotes.models import DailyNote
from apps.events.models import Event
from apps.patients.models import Patient


class DailyNoteDetailPDFUITest(TestCase):
    """Tests for PDF-related UI elements on the daily note detail page."""

    @classmethod
    def setUpTestData(cls):
        cls.user = EqmdCustomUser.objects.create_user(
            username="detaildoctor",
            email="detaildoctor@example.com",
            password="testpass123",
            password_change_required=False,
            terms_accepted=True,
            first_name="Detail",
            last_name="Doctor",
        )
        # Grant view_event permission
        event_ct = ContentType.objects.get_for_model(Event)
        cls.user.user_permissions.add(
            Permission.objects.get(content_type=event_ct, codename="view_event"),
        )
        cls.patient = Patient.objects.create(
            name="Detail UI Test Patient",
            birthday="1985-06-15",
            created_by=cls.user,
            updated_by=cls.user,
        )
        cls.dailynote = DailyNote.objects.create(
            patient=cls.patient,
            description="Detail page PDF UI test",
            content="Content for detail page test.",
            event_datetime=timezone.now(),
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        self.client.login(username="detaildoctor", password="testpass123")
        self.url = reverse(
            "dailynotes:dailynote_detail", kwargs={"pk": self.dailynote.pk}
        )

    def test_detail_page_shows_pdf_action_for_daily_note(self):
        """The detail page should contain a PDF download button."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pdf-download-btn")

    def test_detail_page_has_pdf_actions_in_desktop_and_mobile_sections(self):
        """Both desktop and mobile sections should have PDF buttons."""
        response = self.client.get(self.url)
        content = response.content.decode()

        # Count pdf-download-btn occurrences – should be at least 2 (desktop + mobile)
        count = content.count("pdf-download-btn")
        self.assertGreaterEqual(count, 2, "Expected PDF buttons in both desktop and mobile sections")

    def test_detail_page_pdf_action_points_to_daily_note_pdf_url(self):
        """The PDF button should reference the daily note PDF URL."""
        pdf_url = reverse(
            "dailynotes:dailynote_pdf", kwargs={"pk": self.dailynote.pk}
        )
        response = self.client.get(self.url)
        self.assertContains(response, f'data-pdf-url="{pdf_url}')

    def test_detail_page_has_no_legacy_print_action(self):
        """The legacy print route must not exist and the page must not link to it."""
        from django.urls import NoReverseMatch

        # Route must not resolve
        with self.assertRaises(NoReverseMatch):
            reverse("dailynotes:dailynote_print", kwargs={"pk": self.dailynote.pk})

        # No /print/ path fragments in the rendered HTML
        response = self.client.get(self.url)
        self.assertNotContains(response, "/print/")

    def test_detail_page_has_no_print_icon_or_label(self):
        """No printer icon or 'Imprimir' label should appear on the page."""
        response = self.client.get(self.url)
        self.assertNotContains(response, "bi-printer")
        self.assertNotContains(response, "Imprimir")

    def test_detail_page_loads_pdf_download_javascript(self):
        """The page should load the pdf-download.js script."""
        response = self.client.get(self.url)
        self.assertContains(response, "pdf-download.js")
