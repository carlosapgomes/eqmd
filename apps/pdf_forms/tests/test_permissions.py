from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone

from apps.core.permissions.utils import can_delete_event, can_edit_event
from apps.pdf_forms.models import PDFFormSubmission
from apps.pdf_forms.permissions import (
    check_pdf_download_access,
    check_pdf_form_access,
    check_pdf_form_creation,
    check_pdf_form_template_access,
    check_pdf_form_template_management,
)
from apps.pdf_forms.tests.factories import (
    DoctorFactory,
    NurseFactory,
    PatientFactory,
    PDFFormSubmissionFactory,
    PDFFormTemplateFactory,
    UserFactory,
)

User = get_user_model()


class PDFFormPermissionTests(TestCase):
    """Test PDF form permission functions."""

    def setUp(self):
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)
        self.submission = PDFFormSubmissionFactory(
            form_template=self.template, patient=self.patient, created_by=self.user
        )

    def test_check_pdf_form_access_allowed(self):
        """Test that PDF form access is allowed when patient access is granted."""
        with patch("apps.pdf_forms.permissions.can_access_patient", return_value=True):
            result = check_pdf_form_access(self.user, self.patient)
            self.assertTrue(result)

    def test_check_pdf_form_access_denied(self):
        """Test that PDF form access is denied when patient access is denied."""
        with patch("apps.pdf_forms.permissions.can_access_patient", return_value=False):
            with self.assertRaises(PermissionDenied) as context:
                check_pdf_form_access(self.user, self.patient)

            self.assertIn(
                "don't have permission to access this patient's PDF forms",
                str(context.exception),
            )

    def test_check_pdf_form_creation_allowed(self):
        """Test that PDF form creation is allowed when patient access is granted."""
        with patch("apps.pdf_forms.permissions.can_access_patient", return_value=True):
            result = check_pdf_form_creation(self.user, self.patient)
            self.assertTrue(result)

    def test_check_pdf_form_creation_denied(self):
        """Test that PDF form creation is denied when patient access is denied."""
        with patch("apps.pdf_forms.permissions.can_access_patient", return_value=False):
            with self.assertRaises(PermissionDenied) as context:
                check_pdf_form_creation(self.user, self.patient)

            self.assertIn(
                "don't have permission to access this patient's PDF forms",
                str(context.exception),
            )

    def test_check_pdf_form_template_access_authenticated(self):
        """Test that template access is allowed for authenticated users."""
        result = check_pdf_form_template_access(self.user)
        self.assertTrue(result)

    def test_check_pdf_form_template_access_anonymous(self):
        """Test that template access is denied for anonymous users."""
        anonymous_user = AnonymousUser()
        result = check_pdf_form_template_access(anonymous_user)
        self.assertFalse(result)

    def test_check_pdf_form_template_management_superuser(self):
        """Test that template management is allowed for superusers."""
        superuser = UserFactory(is_superuser=True)
        result = check_pdf_form_template_management(superuser)
        self.assertTrue(result)

    def test_check_pdf_form_template_management_regular_user(self):
        """Test that template management is denied for regular users."""
        with self.assertRaises(PermissionDenied) as context:
            check_pdf_form_template_management(self.user)

        self.assertIn(
            "Only administrators can manage PDF form templates", str(context.exception)
        )

    def test_check_pdf_download_access_allowed(self):
        """Test that PDF download is allowed with proper permissions and valid data."""
        with patch(
            "apps.pdf_forms.permissions.check_pdf_form_access", return_value=True
        ):
            result = check_pdf_download_access(self.user, self.submission)
            self.assertTrue(result)

    def test_check_pdf_download_access_denied_patient_access(self):
        """Test that PDF download is denied when patient access is denied."""
        # check_pdf_form_access raises PermissionDenied when patient access is
        # denied; simulate that real enforcement instead of a False return.
        with patch(
            "apps.pdf_forms.permissions.check_pdf_form_access",
            side_effect=PermissionDenied(
                "You don't have permission to access this patient's PDF forms"
            ),
        ):
            with self.assertRaises(PermissionDenied) as context:
                check_pdf_download_access(self.user, self.submission)

            self.assertIn(
                "don't have permission to access this patient's PDF forms",
                str(context.exception),
            )

    def test_check_pdf_download_access_missing_form_data(self):
        """Test that PDF download is denied when form data is missing."""
        self.submission.form_data = None

        with patch(
            "apps.pdf_forms.permissions.check_pdf_form_access", return_value=True
        ):
            with self.assertRaises(PermissionDenied) as context:
                check_pdf_download_access(self.user, self.submission)

            self.assertIn(
                "Cannot generate PDF: form data is missing", str(context.exception)
            )

    def test_check_pdf_download_access_invalid_form_data_structure(self):
        """Test that PDF download is denied when form data has invalid structure."""
        self.submission.form_data = "not_a_dictionary"

        with patch(
            "apps.pdf_forms.permissions.check_pdf_form_access", return_value=True
        ):
            with self.assertRaises(PermissionDenied) as context:
                check_pdf_download_access(self.user, self.submission)

            self.assertIn(
                "Cannot generate PDF: invalid form data structure",
                str(context.exception),
            )

    def test_generic_predicate_allows_the_creator_within_the_window(self):
        """Editing a definitive submission follows the 24h owner window."""
        recent_submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
        )

        self.assertTrue(can_edit_event(self.user, recent_submission))

    def test_generic_predicate_denies_the_creator_after_the_window(self):
        old_submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
        )
        PDFFormSubmission.objects.filter(pk=old_submission.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        old_submission.refresh_from_db()

        self.assertFalse(can_edit_event(self.user, old_submission))

    def test_generic_predicate_denies_a_non_creator(self):
        other_user = UserFactory()

        self.assertFalse(can_edit_event(other_user, self.submission))

    def test_generic_predicate_gives_superusers_no_view_level_override(self):
        """The removed helper's superuser override must not survive."""
        superuser = UserFactory(is_superuser=True)
        old_submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
        )
        PDFFormSubmission.objects.filter(pk=old_submission.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        old_submission.refresh_from_db()

        self.assertFalse(can_edit_event(superuser, old_submission))

    def test_generic_predicate_denies_a_draft_reader_without_patient_access(self):
        draft = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            is_draft=True,
        )

        with patch(
            "apps.core.permissions.utils.can_access_patient", return_value=False
        ):
            self.assertFalse(can_edit_event(UserFactory(), draft))

    def test_generic_delete_predicate_matches_the_edit_predicate(self):
        recent_submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
        )

        self.assertTrue(can_delete_event(self.user, recent_submission))
        self.assertEqual(
            can_edit_event(self.user, recent_submission),
            can_delete_event(self.user, recent_submission),
        )

    def test_generic_predicates_allow_a_draft_author_without_time_limit(self):
        """Drafts belong to the supervision rule: author, no time limit."""
        old_draft = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            is_draft=True,
        )
        PDFFormSubmission.objects.filter(pk=old_draft.pk).update(
            created_at=timezone.now() - timedelta(days=30)
        )
        old_draft.refresh_from_db()

        self.assertTrue(can_edit_event(self.user, old_draft))
        self.assertTrue(can_delete_event(self.user, old_draft))

    def test_permission_functions_edge_cases(self):
        """Test edge cases for permission functions."""
        # Test with None user
        with self.assertRaises(PermissionDenied):
            check_pdf_form_template_management(None)

        # Test with None patient
        with patch("apps.pdf_forms.permissions.can_access_patient") as mock_access:
            check_pdf_form_access(self.user, None)
            mock_access.assert_called_once_with(self.user, None)

        # Test with None submission
        with self.assertRaises(PermissionDenied):
            check_pdf_download_access(self.user, None)

    def test_permission_functions_with_different_user_types(self):
        """Test permission functions with different user types."""
        doctor = DoctorFactory()
        nurse = NurseFactory()

        # All users should have the same basic access patterns
        with patch("apps.pdf_forms.permissions.can_access_patient", return_value=True):
            for user_type in [doctor, nurse]:
                # Basic access should work
                self.assertTrue(check_pdf_form_access(user_type, self.patient))
                self.assertTrue(check_pdf_form_creation(user_type, self.patient))

                # But template management should be denied
                with self.assertRaises(PermissionDenied):
                    check_pdf_form_template_management(user_type)
