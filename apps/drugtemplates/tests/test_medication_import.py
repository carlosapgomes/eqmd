"""
Failing tests for medication import functionality.
These tests will fail until the import management command is implemented.
"""

import tempfile
import os
from io import StringIO
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from apps.drugtemplates.models import DrugTemplate

User = get_user_model()


class MedicationImportCommandTest(TestCase):
    """Tests for the import_medications_csv management command."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create test CSV content
        self.csv_content = """Denominação Comum Brasileira (DCB),Concentração/Composição,Forma Farmacêutica
Iodeto de potássio,130.0 mg,comprimido
Sulfato de gentamicina,40 mg/mL,solução injetável
abatacepte,125 mg/mL,solução injetável
acetato de ciproterona,50.0 mg,comprimido
acetato de desmopressina,"0,1 mg",comprimido"""

    def create_temp_csv_file(self, content=None):
        """Helper method to create temporary CSV file."""
        if content is None:
            content = self.csv_content
            
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        temp_file.write(content)
        temp_file.close()
        return temp_file.name

    def test_import_medications_csv_command_exists(self):
        """Test that import_medications_csv command exists."""
        # This will fail until management command is created
        try:
            call_command('import_medications_csv', '--help')
        except CommandError as e:
            self.fail(f"Command import_medications_csv does not exist: {e}")

    def test_import_medications_csv_with_valid_file(self):
        """Test importing medications from valid CSV file."""
        # This will fail until management command is implemented
        csv_file = self.create_temp_csv_file()
        
        try:
            out = StringIO()
            call_command('import_medications_csv', csv_file, stdout=out)
            
            # Should create DrugTemplate records
            imported_drugs = DrugTemplate.objects.filter(is_imported=True)
            self.assertEqual(imported_drugs.count(), 5)
            
            # Check specific imported drug
            iodeto = DrugTemplate.objects.get(
                name='Iodeto de potássio',
                concentration='130.0 mg'
            )
            self.assertEqual(iodeto.pharmaceutical_form, 'comprimido')
            self.assertTrue(iodeto.is_imported)
            self.assertEqual(iodeto.import_source, 'CSV Import')
            
            # Usage instructions should be empty for imported drugs
            self.assertEqual(iodeto.usage_instructions, '')
            
        finally:
            os.unlink(csv_file)

    def test_import_medications_csv_with_invalid_file(self):
        """Test importing from non-existent CSV file."""
        # This will fail until management command is implemented
        with self.assertRaises(CommandError):
            call_command('import_medications_csv', 'nonexistent.csv')

    def test_import_medications_csv_with_malformed_csv(self):
        """Test importing from malformed CSV file."""
        # This will fail until management command is implemented
        malformed_content = """Invalid,CSV,Content
Missing,Header
Incomplete"""
        
        csv_file = self.create_temp_csv_file(malformed_content)
        
        try:
            with self.assertRaises(CommandError):
                call_command('import_medications_csv', csv_file)
        finally:
            os.unlink(csv_file)

    def test_import_medications_csv_duplicate_handling(self):
        """Test that duplicate medications are handled correctly."""
        # This will fail until management command is implemented
        csv_file = self.create_temp_csv_file()
        
        try:
            # First import
            call_command('import_medications_csv', csv_file)
            first_count = DrugTemplate.objects.filter(is_imported=True).count()
            
            # Second import (duplicates)
            out = StringIO()
            call_command('import_medications_csv', csv_file, stdout=out)
            second_count = DrugTemplate.objects.filter(is_imported=True).count()
            
            # Should not create duplicates
            self.assertEqual(first_count, second_count)
            
            # Should report skipped duplicates
            output = out.getvalue()
            self.assertIn('skipped', output.lower())
            
        finally:
            os.unlink(csv_file)

    def test_import_medications_csv_creates_system_user(self):
        """Test that import creates/uses system user as creator."""
        # This will fail until management command is implemented
        csv_file = self.create_temp_csv_file()
        
        try:
            call_command('import_medications_csv', csv_file)
            
            # Should create system user if it doesn't exist
            system_user = User.objects.get(username='system')
            self.assertEqual(system_user.email, 'system@hospital.internal')
            self.assertTrue(system_user.is_active)
            
            # Imported drugs should be created by system user
            imported_drug = DrugTemplate.objects.filter(is_imported=True).first()
            self.assertEqual(imported_drug.creator, system_user)
            
        finally:
            os.unlink(csv_file)

    def test_import_medications_csv_statistics_reporting(self):
        """Test that import command reports statistics."""
        # This will fail until management command is implemented
        csv_file = self.create_temp_csv_file()
        
        try:
            out = StringIO()
            call_command('import_medications_csv', csv_file, stdout=out)
            
            output = out.getvalue()
            
            # Should report statistics
            self.assertIn('imported', output.lower())
            self.assertIn('5', output)  # Number of records
            self.assertIn('skipped', output.lower())
            self.assertIn('errors', output.lower())
            
        finally:
            os.unlink(csv_file)

    def test_import_medications_csv_validation_errors(self):
        """Test that import handles validation errors correctly."""
        # This will fail until management command is implemented
        invalid_content = """Denominação Comum Brasileira (DCB),Concentração/Composição,Forma Farmacêutica
,130.0 mg,comprimido
Valid Drug,50 mg,
Another Valid Drug,25 mg,comprimido"""
        
        csv_file = self.create_temp_csv_file(invalid_content)
        
        try:
            out = StringIO()
            call_command('import_medications_csv', csv_file, stdout=out)
            
            # Should import only valid records
            imported_count = DrugTemplate.objects.filter(is_imported=True).count()
            self.assertEqual(imported_count, 1)  # Only "Another Valid Drug"
            
            # Should report errors
            output = out.getvalue()
            self.assertIn('error', output.lower())
            
        finally:
            os.unlink(csv_file)

    def test_import_medications_csv_with_dry_run_option(self):
        """Test import command with --dry-run option."""
        # This will fail until management command is implemented
        csv_file = self.create_temp_csv_file()
        
        try:
            out = StringIO()
            call_command('import_medications_csv', csv_file, '--dry-run', stdout=out)
            
            # Should not create any records
            imported_count = DrugTemplate.objects.filter(is_imported=True).count()
            self.assertEqual(imported_count, 0)
            
            # Should report what would be imported
            output = out.getvalue()
            self.assertIn('dry run', output.lower())
            self.assertIn('would import', output.lower())
            
        finally:
            os.unlink(csv_file)

    def test_import_medications_csv_normalizes_field_values(self):
        """Test that import normalizes and sanitizes field values."""
        # This will fail until management command is implemented
        content_with_variations = """Denominação Comum Brasileira (DCB),Concentração/Composição,Forma Farmacêutica
  Paracetamol  ,"500,0 mg  ",  comprimido  
DIPIRONA,1000 MG,SOLUÇÃO INJETÁVEL"""
        
        csv_file = self.create_temp_csv_file(content_with_variations)
        
        try:
            call_command('import_medications_csv', csv_file)
            
            # Should normalize field values
            paracetamol = DrugTemplate.objects.get(name='Paracetamol')
            self.assertEqual(paracetamol.concentration, '500.0 mg')  # Normalized decimal
            self.assertEqual(paracetamol.pharmaceutical_form, 'comprimido')  # Trimmed
            
            dipirona = DrugTemplate.objects.get(name='Dipirona')  # Normalized case
            self.assertEqual(dipirona.concentration, '1000 mg')
            self.assertEqual(dipirona.pharmaceutical_form, 'solução injetável')  # Normalized case
            
        finally:
            os.unlink(csv_file)