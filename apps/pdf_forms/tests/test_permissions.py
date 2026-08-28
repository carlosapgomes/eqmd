from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone

from apps.pdf_forms.models import PDFFormSubmission
from apps.pdf_forms.permissions import (
    can_delete_pdf_submission,
    can_edit_pdf_submission,
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

    def test_can_edit_pdf_submission_creator_within_time_window(self):
        """Test editing is allowed for creator within 24 hours."""
        # Create submission less than 24 hours ago
        recent_submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            created_at=timezone.now() - timedelta(hours=1),
        )

        with patch("apps.pdf_forms.permissions.can_access_patient", return_value=True):
            result = can_edit_pdf_submission(self.user, recent_submission)
            self.assertTrue(result)

    def test_can_edit_pdf_submission_creator_after_time_window(self):
        """Test editing is denied for creator after 24 hours."""
        # Create submission more than 24 hours ago (auto_now_add ignores the
        # factory value, so backdate it with a queryset update).
        old_submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
        )
        PDFFormSubmission.objects.filter(pk=old_submission.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        old_submission.refresh_from_db()

        with patch("apps.pdf_forms.permissions.can_access_patient", return_value=True):
            result = can_edit_pdf_submission(self.user, old_submission)
            self.assertFalse(result)

    def test_can_edit_pdf_submission_non_creator(self):
        """Test editing is denied for non-creator."""
        other_user = UserFactory()

        with patch("apps.pdf_forms.permissions.can_access_patient", return_value=True):
            result = can_edit_pdf_submission(other_user, self.submission)
            self.assertFalse(result)

    def test_can_edit_pdf_submission_superuser(self):
        """Test editing is allowed for superuser regardless of time."""
        superuser = UserFactory(is_superuser=True)

        # Create submission more than 24 hours ago (auto_now_add ignores the
        # factory value, so backdate it with a queryset update).
        old_submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
        )
        PDFFormSubmission.objects.filter(pk=old_submission.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        old_submission.refresh_from_db()

        with patch("apps.pdf_forms.permissions.can_access_patient", return_value=True):
            result = can_edit_pdf_submission(superuser, old_submission)
            self.assertTrue(result)

    def test_can_edit_pdf_submission_no_patient_access(self):
        """Test editing is denied when user has no patient access."""
        with patch("apps.pdf_forms.permissions.can_access_patient", return_value=False):
            result = can_edit_pdf_submission(self.user, self.submission)
            self.assertFalse(result)

    def test_can_delete_pdf_submission_same_as_edit(self):
        """Test that delete permissions follow the same rules as edit permissions."""
        # Test creator within time window
        recent_submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            created_at=timezone.now() - timedelta(hours=1),
        )

        with patch("apps.pdf_forms.permissions.can_access_patient", return_value=True):
            edit_result = can_edit_pdf_submission(self.user, recent_submission)
            delete_result = can_delete_pdf_submission(self.user, recent_submission)
            self.assertEqual(edit_result, delete_result)
            self.assertTrue(delete_result)

    def test_can_delete_pdf_submission_superuser(self):
        """Test that superuser can always delete."""
        superuser = UserFactory(is_superuser=True)

        with patch("apps.pdf_forms.permissions.can_access_patient", return_value=True):
            result = can_delete_pdf_submission(superuser, self.submission)
            self.assertTrue(result)

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
