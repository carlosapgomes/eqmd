from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.pdf_forms.models import PDFFormTemplate

User = get_user_model()


class CreateSamplePDFFormsCommandTests(TestCase):
    """Test the create_sample_pdf_forms management command."""

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            is_superuser=True,
            is_staff=True,
        )

    def test_command_handle_no_superuser(self):
        """Test command reports when no superuser exists."""
        # Delete any existing superusers
        User.objects.filter(is_superuser=True).delete()

        out = StringIO()
        call_command("create_sample_pdf_forms", stdout=out)

        self.assertIn(
            "No superuser found. Create one first.",
            out.getvalue(),
        )

    def test_command_handle_with_superuser(self):
        """Test command creates templates when superuser exists."""
        initial_count = PDFFormTemplate.objects.count()

        out = StringIO()
        call_command("create_sample_pdf_forms", stdout=out)

        # Check templates were created
        self.assertEqual(PDFFormTemplate.objects.count(), initial_count + 2)

        # Verify first template
        transfusion_template = PDFFormTemplate.objects.get(
            name="Solicitação de Transfusão"
        )
        self.assertEqual(
            transfusion_template.description,
            "Formulário para solicitação de transfusão sanguínea",
        )
        self.assertEqual(transfusion_template.created_by, self.admin_user)
        self.assertTrue(transfusion_template.hospital_specific)
        self.assertTrue(transfusion_template.is_active)

        # Verify second template
        icu_template = PDFFormTemplate.objects.get(name="Transferência para UTI")
        self.assertEqual(
            icu_template.description,
            "Formulário para solicitação de transferência para UTI",
        )
        self.assertEqual(icu_template.created_by, self.admin_user)

        # Check output messages
        self.assertIn("Created template: Solicitação de Transfusão", out.getvalue())
        self.assertIn("Created template: Transferência para UTI", out.getvalue())
        self.assertIn("Created 2 new PDF form templates", out.getvalue())

    def test_command_handle_templates_already_exist(self):
        """Test command handles existing templates gracefully."""
        # Create one template first (factory provides a valid PDF and config)
        from apps.pdf_forms.tests.factories import PDFFormTemplateFactory

        PDFFormTemplateFactory(
            name="Solicitação de Transfusão",
            description="Existing template",
            created_by=self.admin_user,
        )

        initial_count = PDFFormTemplate.objects.count()

        out = StringIO()
        call_command("create_sample_pdf_forms", stdout=out)

        # Should only create one new template
        self.assertEqual(PDFFormTemplate.objects.count(), initial_count + 1)

        # Check output includes warning for existing template
        self.assertIn(
            "Template already exists: Solicitação de Transfusão",
            out.getvalue(),
        )
        self.assertIn("Created template: Transferência para UTI", out.getvalue())

    def test_command_transfusion_template_fields(self):
        """Test transfusion template has correct field configuration."""
        call_command("create_sample_pdf_forms")

        template = PDFFormTemplate.objects.get(name="Solicitação de Transfusão")
        fields = template.form_fields

        # Check required fields exist
        self.assertIn("patient_name", fields)
        self.assertIn("blood_type", fields)
        self.assertIn("units_requested", fields)
        self.assertIn("clinical_indication", fields)

        # Check field properties
        self.assertEqual(fields["patient_name"]["type"], "text")
        self.assertEqual(fields["patient_name"]["required"], True)
        self.assertEqual(fields["patient_name"]["label"], "Nome do Paciente")
        self.assertEqual(fields["patient_name"]["x"], 4.5)
        self.assertEqual(fields["patient_name"]["y"], 8.5)

        # Check blood type field
        self.assertEqual(fields["blood_type"]["type"], "choice")
        self.assertEqual(
            fields["blood_type"]["choices"],
            ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
        )

        # Check clinical indication textarea
        self.assertEqual(fields["clinical_indication"]["type"], "textarea")
        self.assertEqual(fields["clinical_indication"]["height"], 3.0)

    def test_command_icu_template_fields(self):
        """Test ICU template has correct field configuration."""
        call_command("create_sample_pdf_forms")

        template = PDFFormTemplate.objects.get(name="Transferência para UTI")
        fields = template.form_fields

        # Check required fields exist
        self.assertIn("patient_name", fields)
        self.assertIn("current_location", fields)
        self.assertIn("requested_icu", fields)
        self.assertIn("life_support", fields)

        # Check field properties
        self.assertEqual(fields["patient_name"]["type"], "text")
        self.assertEqual(fields["current_location"]["max_length"], 50)
        self.assertEqual(fields["requested_icu"]["type"], "choice")
        self.assertEqual(
            fields["requested_icu"]["choices"],
            [
                "UTI Geral",
                "UTI Cardiológica",
                "UTI Neurológica",
                "UTI Pediátrica",
                "UTI COVID",
            ],
        )

        # Check boolean field
        self.assertEqual(fields["life_support"]["type"], "boolean")
        self.assertEqual(fields["life_support"]["required"], False)

    def test_command_help_text(self):
        """Test command has correct help text."""
        from apps.pdf_forms.management.commands.create_sample_pdf_forms import (
            Command,
        )

        self.assertEqual(Command.help, "Create sample PDF form templates for testing")

    def test_command_uses_existing_superuser(self):
        """Test command uses existing superuser when available."""
        # Create another superuser
        other_admin = User.objects.create_user(
            username="otheradmin",
            email="other@test.com",
            password="testpass123",
            is_superuser=True,
            is_staff=True,
        )

        # Delete the original superuser from setUp
        User.objects.filter(id=self.admin_user.id).delete()

        call_command("create_sample_pdf_forms")

        # Templates should be created by the other admin
        templates = PDFFormTemplate.objects.all()
        for template in templates:
            self.assertEqual(template.created_by, other_admin)

    @patch(
        "apps.pdf_forms.management.commands.create_sample_pdf_forms.PDFFormTemplate.objects.get_or_create"
    )
    def test_command_database_error_handling(self, mock_get_or_create):
        """Test command propagates database errors (no silent swallowing)."""
        mock_get_or_create.side_effect = RuntimeError("Database error")

        # The command does not catch persistence errors; they surface to the
        # caller instead of producing misleading output.
        with self.assertRaises(RuntimeError):
            call_command("create_sample_pdf_forms")
