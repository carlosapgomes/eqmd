import os
from unittest.mock import patch, MagicMock
from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from apps.pdf_forms.models import PDFFormTemplate

User = get_user_model()


class CreateSamplePDFFormsCommandTests(TestCase):
    """Test the create_sample_pdf_forms management command."""

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )

    def test_command_handle_no_superuser(self):
        """Test command fails when no superuser exists."""
        # Delete any existing superusers
        User.objects.filter(is_superuser=True).delete()
        
        with patch('apps.pdf_forms.management.commands.create_sample_pdf_forms.Command.stdout') as mock_stdout:
            call_command('create_sample_pdf_forms')
            mock_stdout.write.assert_any_call(
                '\x1b[31mNo superuser found. Create one first.\x1b[0m'
            )

    def test_command_handle_with_superuser(self):
        """Test command creates templates when superuser exists."""
        initial_count = PDFFormTemplate.objects.count()
        
        with patch('apps.pdf_forms.management.commands.create_sample_pdf_forms.Command.stdout') as mock_stdout:
            call_command('create_sample_pdf_forms')
            
            # Check templates were created
            self.assertEqual(PDFFormTemplate.objects.count(), initial_count + 2)
            
            # Verify first template
            transfusion_template = PDFFormTemplate.objects.get(name='Solicitação de Transfusão')
            self.assertEqual(transfusion_template.description, 'Formulário para solicitação de transfusão sanguínea')
            self.assertEqual(transfusion_template.created_by, self.admin_user)
            self.assertTrue(transfusion_template.hospital_specific)
            self.assertTrue(transfusion_template.is_active)
            
            # Verify second template
            icu_template = PDFFormTemplate.objects.get(name='Transferência para UTI')
            self.assertEqual(icu_template.description, 'Formulário para solicitação de transferência para UTI')
            self.assertEqual(icu_template.created_by, self.admin_user)
            
            # Check output messages
            mock_stdout.write.assert_any_call(
                '\x1b[32mCreated template: Solicitação de Transfusão\x1b[0m'
            )
            mock_stdout.write.assert_any_call(
                '\x1b[32mCreated template: Transferência para UTI\x1b[0m'
            )
            mock_stdout.write.assert_any_call(
                '\x1b[32mCreated 2 new PDF form templates\x1b[0m'
            )

    def test_command_handle_templates_already_exist(self):
        """Test command handles existing templates gracefully."""
        # Create one template first
        PDFFormTemplate.objects.create(
            name='Solicitação de Transfusão',
            description='Existing template',
            form_fields={'test': 'field'},
            created_by=self.admin_user
        )
        
        initial_count = PDFFormTemplate.objects.count()
        
        with patch('apps.pdf_forms.management.commands.create_sample_pdf_forms.Command.stdout') as mock_stdout:
            call_command('create_sample_pdf_forms')
            
            # Should only create one new template
            self.assertEqual(PDFFormTemplate.objects.count(), initial_count + 1)
            
            # Check output includes warning for existing template
            mock_stdout.write.assert_any_call(
                '\x1b[33mTemplate already exists: Solicitação de Transfusão\x1b[0m'
            )
            mock_stdout.write.assert_any_call(
                '\x1b[32mCreated template: Transferência para UTI\x1b[0m'
            )

    def test_command_transfusion_template_fields(self):
        """Test transfusion template has correct field configuration."""
        call_command('create_sample_pdf_forms')
        
        template = PDFFormTemplate.objects.get(name='Solicitação de Transfusão')
        fields = template.form_fields
        
        # Check required fields exist
        self.assertIn('patient_name', fields)
        self.assertIn('blood_type', fields)
        self.assertIn('units_requested', fields)
        self.assertIn('clinical_indication', fields)
        
        # Check field properties
        self.assertEqual(fields['patient_name']['type'], 'text')
        self.assertEqual(fields['patient_name']['required'], True)
        self.assertEqual(fields['patient_name']['label'], 'Nome do Paciente')
        self.assertEqual(fields['patient_name']['x'], 4.5)
        self.assertEqual(fields['patient_name']['y'], 8.5)
        
        # Check blood type field
        self.assertEqual(fields['blood_type']['type'], 'choice')
        self.assertEqual(fields['blood_type']['choices'], ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'])
        
        # Check clinical indication textarea
        self.assertEqual(fields['clinical_indication']['type'], 'textarea')
        self.assertEqual(fields['clinical_indication']['height'], 3.0)

    def test_command_icu_template_fields(self):
        """Test ICU template has correct field configuration."""
        call_command('create_sample_pdf_forms')
        
        template = PDFFormTemplate.objects.get(name='Transferência para UTI')
        fields = template.form_fields
        
        # Check required fields exist
        self.assertIn('patient_name', fields)
        self.assertIn('current_location', fields)
        self.assertIn('requested_icu', fields)
        self.assertIn('life_support', fields)
        
        # Check field properties
        self.assertEqual(fields['patient_name']['type'], 'text')
        self.assertEqual(fields['current_location']['max_length'], 50)
        self.assertEqual(fields['requested_icu']['type'], 'choice')
        self.assertEqual(fields['requested_icu']['choices'], ['UTI Geral', 'UTI Cardiológica', 'UTI Neurológica', 'UTI Pediátrica', 'UTI COVID'])
        
        # Check boolean field
        self.assertEqual(fields['life_support']['type'], 'boolean')
        self.assertEqual(fields['life_support']['required'], False)

    def test_command_help_text(self):
        """Test command has correct help text."""
        command_path = 'apps.pdf_forms.management.commands.create_sample_pdf_forms.Command'
        Command = __import__(command_path, fromlist=['Command']).Command
        
        self.assertEqual(Command.help, 'Create sample PDF form templates for testing')

    def test_command_uses_existing_superuser(self):
        """Test command uses existing superuser when available."""
        # Create another superuser
        other_admin = User.objects.create_user(
            username='otheradmin',
            email='other@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True
        )
        
        # Delete the original superuser from setUp
        User.objects.filter(id=self.admin_user.id).delete()
        
        call_command('create_sample_pdf_forms')
        
        # Templates should be created by the other admin
        templates = PDFFormTemplate.objects.all()
        for template in templates:
            self.assertEqual(template.created_by, other_admin)

    @patch('apps.pdf_forms.management.commands.create_sample_pdf_forms.PDFFormTemplate.objects.get_or_create')
    def test_command_database_error_handling(self, mock_get_or_create):
        """Test command handles database errors gracefully."""
        mock_get_or_create.side_effect = Exception("Database error")
        
        with patch('apps.pdf_forms.management.commands.create_sample_pdf_forms.Command.stdout') as mock_stdout:
            call_command('create_sample_pdf_forms')
            
            # Should not crash but should show error
            mock_stdout.write.assert_any_call(
                '\x1b[31mNo superuser found. Create one first.\x1b[0m'
            )