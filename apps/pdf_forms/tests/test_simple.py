"""
Simple tests to verify basic functionality works.
"""
from django.test import TestCase
from apps.pdf_forms.tests.factories import PDFFormTemplateFactory, PDFFormSubmissionFactory
from apps.pdf_forms.models import PDFFormTemplate, PDFFormSubmission


class SimplePDFFormTests(TestCase):
    """Simple tests to verify basic model functionality works."""

    def test_create_pdf_template(self):
        """Test creating a basic PDF template."""
        template = PDFFormTemplateFactory()
        self.assertIsNotNone(template.id)
        self.assertTrue(template.is_active)
        self.assertIsNotNone(template.name)
        self.assertIsNotNone(template.created_by)

    def test_pdf_template_string_representation(self):
        """Test string representation works."""
        template = PDFFormTemplateFactory(name="Test Form")
        self.assertEqual(str(template), "Test Form")

    def test_create_pdf_submission(self):
        """Test creating a basic PDF submission."""
        submission = PDFFormSubmissionFactory()
        self.assertIsNotNone(submission.id)
        self.assertIsNotNone(submission.form_template)
        self.assertIsNotNone(submission.patient)
        self.assertIsNotNone(submission.created_by)

    def test_pdf_submission_string_representation(self):
        """Test PDF submission string representation."""
        submission = PDFFormSubmissionFactory()
        expected = f"{submission.form_template.name} - {submission.patient.name}"
        self.assertEqual(str(submission), expected)