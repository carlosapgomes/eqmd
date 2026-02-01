from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()


class TestReportTemplateModel(TestCase):
    """Test cases for the ReportTemplate model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    def test_reporttemplate_valid_placeholders_saves(self):
        """Test that a template with valid placeholders saves successfully."""
        from apps.reports.models import ReportTemplate

        template = ReportTemplate(
            name="Valid Template",
            markdown_body="Patient: {{patient_name}}, Doctor: {{doctor_name}}",
            created_by=self.user,
            updated_by=self.user,
        )
        template.full_clean()  # This calls clean() for validation
        template.save()

        saved_template = ReportTemplate.objects.get(pk=template.pk)
        self.assertEqual(saved_template.name, "Valid Template")
        self.assertEqual(
            saved_template.markdown_body,
            "Patient: {{patient_name}}, Doctor: {{doctor_name}}"
        )
        self.assertTrue(saved_template.is_active)

    def test_reporttemplate_rejects_unknown_placeholder(self):
        """Test that a template with unknown placeholders is rejected."""
        from apps.reports.models import ReportTemplate

        template = ReportTemplate(
            name="Invalid Template",
            markdown_body="Patient: {{patient_name}}, {{unknown_placeholder}}",
            created_by=self.user,
            updated_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            template.full_clean()

        # Check that the error mentions unknown placeholders
        error_message = str(context.exception)
        self.assertIn("Unknown placeholders", error_message)
        self.assertIn("unknown_placeholder", error_message)

    def test_reporttemplate_requires_patient_name(self):
        """Test that templates missing patient_name are rejected."""
        from apps.reports.models import ReportTemplate

        # Missing patient_name
        template = ReportTemplate(
            name="Missing Name Template",
            markdown_body="Record: {{patient_record_number}}",
            created_by=self.user,
            updated_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            template.full_clean()

        error_message = str(context.exception)
        self.assertIn("Missing required placeholders", error_message)
        self.assertIn("patient_name", error_message)

        # Missing both
        template3 = ReportTemplate(
            name="Missing Both Template",
            markdown_body="No required placeholders here",
            created_by=self.user,
            updated_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            template3.full_clean()

        error_message = str(context.exception)
        self.assertIn("Missing required placeholders", error_message)

    def test_reporttemplate_defaults_is_active_true(self):
        """Test that is_active defaults to True."""
        from apps.reports.models import ReportTemplate

        template = ReportTemplate(
            name="Default Active Template",
            markdown_body="Patient: {{patient_name}}",
            created_by=self.user,
            updated_by=self.user,
        )
        template.full_clean()
        template.save()

        saved_template = ReportTemplate.objects.get(pk=template.pk)
        self.assertTrue(saved_template.is_active)

    def test_reporttemplate_str_returns_name(self):
        """Test that __str__ returns the template name."""
        from apps.reports.models import ReportTemplate

        template = ReportTemplate(
            name="Test Template Name",
            markdown_body="Patient: {{patient_name}}",
            created_by=self.user,
            updated_by=self.user,
        )
        template.full_clean()
        template.save()

        self.assertEqual(str(template), "Test Template Name")

    def test_reporttemplate_with_page_break_saves(self):
        """Test that a template with page_break placeholder saves successfully."""
        from apps.reports.models import ReportTemplate

        template = ReportTemplate(
            name="Template with Page Break",
            markdown_body=(
                "Patient: {{patient_name}}, Record: {{patient_record_number}}\n"
                "{{page_break}}\n"
                "Additional information"
            ),
            created_by=self.user,
            updated_by=self.user,
        )
        template.full_clean()
        template.save()

        saved_template = ReportTemplate.objects.get(pk=template.pk)
        self.assertIn("{{page_break}}", saved_template.markdown_body)

    def test_reporttemplate_can_be_inactive(self):
        """Test that a template can be set to inactive."""
        from apps.reports.models import ReportTemplate

        template = ReportTemplate(
            name="Inactive Template",
            markdown_body="Patient: {{patient_name}}",
            is_active=False,
            created_by=self.user,
            updated_by=self.user,
        )
        template.full_clean()
        template.save()

        saved_template = ReportTemplate.objects.get(pk=template.pk)
        self.assertFalse(saved_template.is_active)

    def test_reporttemplate_defaults_is_public_false(self):
        """Test that is_public defaults to False."""
        from apps.reports.models import ReportTemplate

        template = ReportTemplate(
            name="Private Template",
            markdown_body="Patient: {{patient_name}}",
            created_by=self.user,
            updated_by=self.user,
        )
        template.full_clean()
        template.save()

        saved_template = ReportTemplate.objects.get(pk=template.pk)
        self.assertFalse(saved_template.is_public)

    def test_reporttemplate_can_be_public(self):
        """Test that a template can be set to public."""
        from apps.reports.models import ReportTemplate

        template = ReportTemplate(
            name="Public Template",
            markdown_body="Patient: {{patient_name}}",
            is_public=True,
            created_by=self.user,
            updated_by=self.user,
        )
        template.full_clean()
        template.save()

        saved_template = ReportTemplate.objects.get(pk=template.pk)
        self.assertTrue(saved_template.is_public)

    def test_reporttemplate_has_timestamps(self):
        """Test that created_at and updated_at are set automatically."""
        from apps.reports.models import ReportTemplate

        template = ReportTemplate(
            name="Timestamp Template",
            markdown_body="Patient: {{patient_name}}",
            created_by=self.user,
            updated_by=self.user,
        )
        template.full_clean()
        template.save()

        saved_template = ReportTemplate.objects.get(pk=template.pk)
        self.assertIsNotNone(saved_template.created_at)
        self.assertIsNotNone(saved_template.updated_at)

    def test_reporttemplate_has_uuid_pk(self):
        """Test that the primary key is a UUID."""
        from apps.reports.models import ReportTemplate
        import uuid

        template = ReportTemplate(
            name="UUID Template",
            markdown_body="Patient: {{patient_name}}",
            created_by=self.user,
            updated_by=self.user,
        )
        template.full_clean()
        template.save()

        saved_template = ReportTemplate.objects.get(pk=template.pk)
        self.assertIsInstance(saved_template.id, uuid.UUID)
