"""
Failing tests for DrugTemplate model refactoring.
These tests will fail until the model is refactored with new fields.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.drugtemplates.models import DrugTemplate

User = get_user_model()


class DrugTemplateRefactoredModelTest(TestCase):
    """Tests for the refactored DrugTemplate model with separate fields."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_drugtemplate_has_concentration_field(self):
        """Test that DrugTemplate has concentration field."""
        # This will fail until model is refactored
        drug_template = DrugTemplate(
            name='Paracetamol',
            concentration='500.0 mg',
            pharmaceutical_form='comprimido',
            usage_instructions='Tomar 1 comprimido de 8 em 8 horas',
            creator=self.user
        )
        
        # Should not raise AttributeError when concentration field exists
        self.assertEqual(drug_template.concentration, '500.0 mg')

    def test_drugtemplate_has_pharmaceutical_form_field(self):
        """Test that DrugTemplate has pharmaceutical_form field."""
        # This will fail until model is refactored
        drug_template = DrugTemplate(
            name='Amoxicilina',
            concentration='875.0 mg',
            pharmaceutical_form='comprimido',
            usage_instructions='Tomar 1 comprimido de 12 em 12 horas',
            creator=self.user
        )
        
        # Should not raise AttributeError when pharmaceutical_form field exists
        self.assertEqual(drug_template.pharmaceutical_form, 'comprimido')

    def test_drugtemplate_has_is_imported_field(self):
        """Test that DrugTemplate has is_imported field."""
        # This will fail until model is refactored
        drug_template = DrugTemplate(
            name='Iodeto de potássio',
            concentration='130.0 mg',
            pharmaceutical_form='comprimido',
            creator=self.user,
            is_imported=True
        )
        
        # Should not raise AttributeError when is_imported field exists
        self.assertTrue(drug_template.is_imported)

    def test_drugtemplate_has_import_source_field(self):
        """Test that DrugTemplate has import_source field."""
        # This will fail until model is refactored
        drug_template = DrugTemplate(
            name='Sulfato de gentamicina',
            concentration='40 mg/mL',
            pharmaceutical_form='solução injetável',
            creator=self.user,
            is_imported=True,
            import_source='MERGED_medications.csv'
        )
        
        # Should not raise AttributeError when import_source field exists
        self.assertEqual(drug_template.import_source, 'MERGED_medications.csv')

    def test_drugtemplate_usage_instructions_optional_for_imported(self):
        """Test that usage_instructions is optional for imported drugs."""
        # This will fail until model validation is updated
        drug_template = DrugTemplate(
            name='abatacepte',
            concentration='125 mg/mL',
            pharmaceutical_form='solução injetável',
            creator=self.user,
            is_imported=True,
            usage_instructions=''  # Empty for imported drug
        )
        
        # Should not raise ValidationError for imported drugs without usage instructions
        drug_template.clean()

    def test_drugtemplate_usage_instructions_required_for_user_created(self):
        """Test that usage_instructions is required for user-created drugs."""
        # This will fail until model validation is updated
        drug_template = DrugTemplate(
            name='Custom Drug',
            concentration='250 mg',
            pharmaceutical_form='comprimido',
            creator=self.user,
            is_imported=False,
            usage_instructions=''  # Empty for user-created drug
        )
        
        # Should raise ValidationError for user-created drugs without usage instructions
        with self.assertRaises(ValidationError) as cm:
            drug_template.clean()
        self.assertIn('usage_instructions', cm.exception.message_dict)

    def test_drugtemplate_presentation_property_backward_compatibility(self):
        """Test that presentation property maintains backward compatibility."""
        # This will fail until presentation property is implemented
        drug_template = DrugTemplate(
            name='Dipirona',
            concentration='500 mg',
            pharmaceutical_form='comprimido',
            usage_instructions='Tomar conforme orientação médica',
            creator=self.user
        )
        
        # Should return combined concentration and form
        expected_presentation = '500 mg comprimido'
        self.assertEqual(drug_template.presentation, expected_presentation)

    def test_drugtemplate_default_values_for_import_fields(self):
        """Test default values for new import-related fields."""
        # This will fail until model is refactored
        drug_template = DrugTemplate.objects.create(
            name='Test Drug',
            concentration='100 mg',
            pharmaceutical_form='cápsula',
            usage_instructions='Test instructions',
            creator=self.user
        )
        
        # Default values should be set correctly
        self.assertFalse(drug_template.is_imported)  # Should default to False
        self.assertIsNone(drug_template.import_source)  # Should default to None/null

    def test_drugtemplate_model_indexes_for_new_fields(self):
        """Test that model has proper indexes for new fields."""
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Check if indexes exist for new fields in PostgreSQL
            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'drugtemplates_drugtemplate'
                AND indexname LIKE '%drugtpl_%'
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            
            # Should have indexes for new fields (using the shortened names from models.py)
            self.assertTrue(any('conc' in idx for idx in indexes), 
                           f"No concentration index found in: {indexes}")
            self.assertTrue(any('form' in idx for idx in indexes),
                           f"No pharmaceutical_form index found in: {indexes}")
            self.assertTrue(any('imported' in idx for idx in indexes),
                           f"No is_imported index found in: {indexes}")
            self.assertTrue(any('source' in idx for idx in indexes),
                           f"No import_source index found in: {indexes}")
            
            # Check composite indexes too
            self.assertTrue(any('imp_name' in idx for idx in indexes),
                           f"No imported+name composite index found in: {indexes}")
            self.assertTrue(any('name_conc' in idx for idx in indexes),
                           f"No name+concentration composite index found in: {indexes}")

    def test_drugtemplate_name_trigram_index_exists(self):
        """Test that trigram index exists for accent-insensitive name search."""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'drugtemplates_drugtemplate'
            """)
            indexes = [row[0] for row in cursor.fetchall()]

        self.assertIn(
            'drugtpl_name_trgm_idx',
            indexes,
            f"Trigram index not found in: {indexes}",
        )

    def test_drugtemplate_str_method_unchanged(self):
        """Test that __str__ method still works after refactoring."""
        # This will fail until model is refactored
        drug_template = DrugTemplate.objects.create(
            name='Atenolol',
            concentration='25 mg',
            pharmaceutical_form='comprimido',
            usage_instructions='Tomar 1 pela manhã',
            creator=self.user
        )
        
        # __str__ method should still return the name
        self.assertEqual(str(drug_template), 'Atenolol')

    def test_drugtemplate_clean_method_validates_concentration(self):
        """Test that clean method validates concentration field."""
        # This will fail until model validation is updated
        drug_template = DrugTemplate(
            name='Test Drug',
            concentration='',  # Empty concentration
            pharmaceutical_form='comprimido',
            usage_instructions='Test',
            creator=self.user
        )
        
        # Should raise ValidationError for empty concentration
        with self.assertRaises(ValidationError) as cm:
            drug_template.clean()
        self.assertIn('concentration', cm.exception.message_dict)

    def test_drugtemplate_clean_method_validates_pharmaceutical_form(self):
        """Test that clean method validates pharmaceutical_form field."""
        # This will fail until model validation is updated
        drug_template = DrugTemplate(
            name='Test Drug',
            concentration='100 mg',
            pharmaceutical_form='',  # Empty form
            usage_instructions='Test',
            creator=self.user
        )
        
        # Should raise ValidationError for empty pharmaceutical_form
        with self.assertRaises(ValidationError) as cm:
            drug_template.clean()
        self.assertIn('pharmaceutical_form', cm.exception.message_dict)
