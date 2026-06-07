"""
Tests for PDF form timeline card behavior:
- Duplicate action visibility for enabled hospital templates.
- No duplicate action for non-enabled hospital or APAC/AIH templates.
- View and download actions always present.
"""

from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.accounts.models import EqmdCustomUser
from apps.patients.models import Patient
from apps.events.models import Event
from apps.pdf_forms.models import PDFFormTemplate, PDFFormSubmission


# Minimal valid PDF content for test templates
_MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n"
    b"<<\n"
    b"/Type /Catalog\n"
    b"/Pages 2 0 R\n"
    b">>\n"
    b"endobj\n"
    b"2 0 obj\n"
    b"<<\n"
    b"/Type /Pages\n"
    b"/Kids []\n"
    b"/Count 0\n"
    b">>\n"
    b"endobj\n"
    b"xref\n"
    b"0 3\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000061 00000 n \n"
    b"trailer\n"
    b"<<\n"
    b"/Size 3\n"
    b"/Root 1 0 R\n"
    b">>\n"
    b"startxref\n"
    b"115\n"
    b"%%EOF\n"
)


class PDFFormTimelineCardTests(TestCase):
    """Tests for PDF form timeline card rendering and duplicate action visibility."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data: user, patient, templates, and submissions."""
        cls.user = EqmdCustomUser.objects.create_user(
            username="pdftimeline_user",
            email="pdftimeline@example.com",
            password="testpassword",
            password_change_required=False,
            terms_accepted=True,
        )

        # Grant view_patient permission
        patient_ct = ContentType.objects.get_for_model(Patient)
        view_patient_perm = Permission.objects.get(
            content_type=patient_ct,
            codename="view_patient",
        )
        cls.user.user_permissions.add(view_patient_perm)

        # Grant add_event permission (required for duplicate action visibility)
        event_ct = ContentType.objects.get_for_model(Event)
        add_event_perm = Permission.objects.get(
            content_type=event_ct,
            codename="add_event",
        )
        cls.user.user_permissions.add(add_event_perm)

        cls.patient = Patient.objects.create(
            name="PDF Timeline Patient",
            birthday=date(1980, 1, 1),
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user,
        )

        # Minimal PDF file for template creation
        def _make_pdf(name):
            return SimpleUploadedFile(name, _MINIMAL_PDF, content_type="application/pdf")

        # Hospital template with duplication enabled
        cls.hospital_enabled_template = PDFFormTemplate(
            name="Hospital Duplication Enabled",
            form_type="HOSPITAL",
            allow_duplication=True,
            is_active=True,
            pdf_file=_make_pdf("hospital_enabled.pdf"),
            form_fields={"test_field": {"type": "text", "label": "Test"}},
            created_by=cls.user,
        )
        cls.hospital_enabled_template._skip_validation = True
        cls.hospital_enabled_template.save()

        # Hospital template with duplication disabled
        cls.hospital_disabled_template = PDFFormTemplate(
            name="Hospital Duplication Disabled",
            form_type="HOSPITAL",
            allow_duplication=False,
            is_active=True,
            pdf_file=_make_pdf("hospital_disabled.pdf"),
            form_fields={"test_field": {"type": "text", "label": "Test"}},
            created_by=cls.user,
        )
        cls.hospital_disabled_template._skip_validation = True
        cls.hospital_disabled_template.save()

        # APAC template (should never show duplicate)
        cls.apac_template = PDFFormTemplate(
            name="APAC National Form",
            form_type="APAC",
            allow_duplication=False,
            is_active=True,
            pdf_file=_make_pdf("apac.pdf"),
            form_fields={"test_field": {"type": "text", "label": "Test"}},
            created_by=cls.user,
        )
        cls.apac_template._skip_validation = True
        cls.apac_template.save()

        # Submissions
        cls.hospital_enabled_submission = PDFFormSubmission.objects.create(
            form_template=cls.hospital_enabled_template,
            patient=cls.patient,
            description="Hospital Enabled Form",
            event_datetime=timezone.now(),
            event_type=Event.PDF_FORM_EVENT,
            form_data={"test_field": "value1"},
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.hospital_disabled_submission = PDFFormSubmission.objects.create(
            form_template=cls.hospital_disabled_template,
            patient=cls.patient,
            description="Hospital Disabled Form",
            event_datetime=timezone.now(),
            event_type=Event.PDF_FORM_EVENT,
            form_data={"test_field": "value2"},
            created_by=cls.user,
            updated_by=cls.user,
        )

        cls.apac_submission = PDFFormSubmission.objects.create(
            form_template=cls.apac_template,
            patient=cls.patient,
            description="APAC Form",
            event_datetime=timezone.now(),
            event_type=Event.PDF_FORM_EVENT,
            form_data={"test_field": "value3"},
            created_by=cls.user,
            updated_by=cls.user,
        )

    def setUp(self):
        """Log in the test user."""
        self.client.login(username="pdftimeline_user", password="testpassword")

    def _get_timeline_response(self):
        """Helper to fetch the patient timeline page."""
        url = reverse(
            "apps.patients:patient_events_timeline",
            kwargs={"patient_id": self.patient.pk},
        )
        return self.client.get(url)

    # --- Positive duplicate tests ---

    def test_timeline_pdf_form_card_shows_duplicate_for_enabled_hospital_template(self):
        """Hospital template with allow_duplication=True shows a duplicate button."""
        response = self._get_timeline_response()
        self.assertEqual(response.status_code, 200)

        duplicate_url = reverse(
            "pdf_forms:submission_duplicate",
            kwargs={"pk": self.hospital_enabled_submission.pk},
        )
        self.assertContains(response, duplicate_url)

    # --- Negative duplicate tests ---

    def test_timeline_pdf_form_card_hides_duplicate_for_hospital_template_without_opt_in(self):
        """Hospital template with allow_duplication=False does NOT show duplicate button."""
        response = self._get_timeline_response()
        self.assertEqual(response.status_code, 200)

        duplicate_url = reverse(
            "pdf_forms:submission_duplicate",
            kwargs={"pk": self.hospital_disabled_submission.pk},
        )
        self.assertNotContains(response, duplicate_url)

    def test_timeline_pdf_form_card_hides_duplicate_for_apac_template(self):
        """APAC templates never show duplicate action regardless of flag."""
        response = self._get_timeline_response()
        self.assertEqual(response.status_code, 200)

        duplicate_url = reverse(
            "pdf_forms:submission_duplicate",
            kwargs={"pk": self.apac_submission.pk},
        )
        self.assertNotContains(response, duplicate_url)

    # --- View and download actions ---

    def test_timeline_pdf_form_card_shows_view_and_download_for_apac_template(self):
        """APAC submissions still show view details and PDF download actions."""
        response = self._get_timeline_response()
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()

        # View details link
        detail_url = reverse(
            "pdf_forms:submission_detail",
            kwargs={"pk": self.apac_submission.pk},
        )
        self.assertIn(detail_url, content)

        # PDF download URL
        download_url = reverse(
            "pdf_forms:pdf_download",
            kwargs={"submission_id": self.apac_submission.pk},
        )
        self.assertIn(download_url, content)
