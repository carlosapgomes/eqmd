"""
Failing tests for form validation updates.
These tests will fail until forms are updated for new fields and validation logic.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.drugtemplates.forms import DrugTemplateForm

User = get_user_model()


class DrugTemplateFormRefactoredTest(TestCase):
    """Tests for updated DrugTemplateForm with new fields."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            profession='DR'
        )

    def test_form_has_concentration_field(self):
        """Test that form includes concentration field."""
        # This will fail until form is updated
        form = DrugTemplateForm(user=self.user)
        
        self.assertIn('concentration', form.fields)
        self.assertEqual(form.fields['concentration'].label, 'Concentração')
        self.assertTrue(form.fields['concentration'].required)

    def test_form_has_pharmaceutical_form_field(self):
        """Test that form includes pharmaceutical_form field."""
        # This will fail until form is updated
        form = DrugTemplateForm(user=self.user)
        
        self.assertIn('pharmaceutical_form', form.fields)
        self.assertEqual(form.fields['pharmaceutical_form'].label, 'Forma Farmacêutica')
        self.assertTrue(form.fields['pharmaceutical_form'].required)

    def test_form_removes_old_presentation_field(self):
        """Test that form no longer includes old presentation field."""
        # This will fail until form is updated
        form = DrugTemplateForm(user=self.user)
        
        # Old presentation field should be removed
        self.assertNotIn('presentation', form.fields)

    def test_form_valid_with_new_fields(self):
        """Test form validation with new separate fields."""
        # This will fail until form is updated
        form_data = {
            'name': 'Paracetamol',
            'concentration': '500 mg',
            'pharmaceutical_form': 'comprimido',
            'usage_instructions': 'Tomar 1 comprimido de 8 em 8 horas para dor ou febre',
            'is_public': True
        }
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_form_requires_concentration_field(self):
        """Test that concentration field is required."""
        # This will fail until form is updated
        form_data = {
            'name': 'Test Drug',
            'concentration': '',  # Empty concentration
            'pharmaceutical_form': 'comprimido',
            'usage_instructions': 'Test instructions',
            'is_public': False
        }
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('concentration', form.errors)

    def test_form_requires_pharmaceutical_form_field(self):
        """Test that pharmaceutical_form field is required."""
        # This will fail until form is updated
        form_data = {
            'name': 'Test Drug',
            'concentration': '100 mg',
            'pharmaceutical_form': '',  # Empty form
            'usage_instructions': 'Test instructions',
            'is_public': False
        }
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('pharmaceutical_form', form.errors)

    def test_form_validates_concentration_format(self):
        """Test that form validates concentration format."""
        # This will fail until form validation is implemented
        invalid_concentrations = [
            'invalid concentration',
            '???',
            '',
            '   ',
        ]
        
        for invalid_concentration in invalid_concentrations:
            with self.subTest(concentration=invalid_concentration):
                form_data = {
                    'name': 'Test Drug',
                    'concentration': invalid_concentration,
                    'pharmaceutical_form': 'comprimido',
                    'usage_instructions': 'Test instructions',
                    'is_public': False
                }
                form = DrugTemplateForm(data=form_data, user=self.user)
                self.assertFalse(
                    form.is_valid(),
                    f"Form should be invalid for concentration: {invalid_concentration}"
                )

    def test_form_validates_pharmaceutical_form_format(self):
        """Test that form validates pharmaceutical form format."""
        # This will fail until form validation is implemented
        invalid_forms = [
            '',
            '   ',
            '???',
        ]
        
        for invalid_form in invalid_forms:
            with self.subTest(form=invalid_form):
                form_data = {
                    'name': 'Test Drug',
                    'concentration': '100 mg',
                    'pharmaceutical_form': invalid_form,
                    'usage_instructions': 'Test instructions',
                    'is_public': False
                }
                form = DrugTemplateForm(data=form_data, user=self.user)
                self.assertFalse(
                    form.is_valid(),
                    f"Form should be invalid for pharmaceutical_form: {invalid_form}"
                )

    def test_form_normalizes_field_values(self):
        """Test that form normalizes field values."""
        # This will fail until form normalization is implemented
        form_data = {
            'name': '  Paracetamol  ',
            'concentration': '  500,0 mg  ',  # Comma decimal
            'pharmaceutical_form': '  COMPRIMIDO  ',  # Uppercase
            'usage_instructions': 'Tomar conforme orientação médica',
            'is_public': False
        }
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        cleaned_data = form.cleaned_data
        self.assertEqual(cleaned_data['name'], 'Paracetamol')  # Trimmed
        self.assertEqual(cleaned_data['concentration'], '500.0 mg')  # Normalized decimal
        self.assertEqual(cleaned_data['pharmaceutical_form'], 'comprimido')  # Lowercase

    def test_form_duplicate_validation_with_new_fields(self):
        """Test duplicate validation considers new fields combination."""
        # This will fail until duplicate validation is updated
        from apps.drugtemplates.models import DrugTemplate
        
        # Create existing template
        existing = DrugTemplate.objects.create(
            name='Paracetamol',
            concentration='500 mg',
            pharmaceutical_form='comprimido',
            usage_instructions='Existing instructions',
            creator=self.user
        )
        
        # Try to create duplicate with same name and concentration
        form_data = {
            'name': 'Paracetamol',
            'concentration': '500 mg',
            'pharmaceutical_form': 'comprimido',
            'usage_instructions': 'New instructions',
            'is_public': False
        }
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertTrue(
            'name' in form.errors or 
            'concentration' in form.errors or
            '__all__' in form.errors
        )

    def test_form_allows_same_name_different_concentration(self):
        """Test that same drug name with different concentration is allowed."""
        # This will fail until validation logic is updated
        from apps.drugtemplates.models import DrugTemplate
        
        # Create existing template
        existing = DrugTemplate.objects.create(
            name='Paracetamol',
            concentration='500 mg',
            pharmaceutical_form='comprimido',
            usage_instructions='Existing instructions',
            creator=self.user
        )
        
        # Create different concentration - should be allowed
        form_data = {
            'name': 'Paracetamol',
            'concentration': '750 mg',  # Different concentration
            'pharmaceutical_form': 'comprimido',
            'usage_instructions': 'Different strength instructions',
            'is_public': False
        }
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_form_widget_classes_for_new_fields(self):
        """Test that new fields have appropriate widget classes."""
        # This will fail until form widgets are configured
        form = DrugTemplateForm(user=self.user)
        
        # Check concentration field widget
        concentration_widget = form.fields['concentration'].widget
        self.assertIn('form-control', concentration_widget.attrs.get('class', ''))
        
        # Check pharmaceutical form field widget  
        form_widget = form.fields['pharmaceutical_form'].widget
        self.assertIn('form-control', form_widget.attrs.get('class', ''))

    def test_form_help_text_for_new_fields(self):
        """Test that new fields have helpful help text."""
        # This will fail until form help text is added
        form = DrugTemplateForm(user=self.user)
        
        # Should have help text for concentration
        concentration_help = form.fields['concentration'].help_text
        self.assertIn('mg', concentration_help.lower())
        
        # Should have help text for pharmaceutical form
        form_help = form.fields['pharmaceutical_form'].help_text
        self.assertIn('comprimido', form_help.lower() or 
                     'cápsula' in form_help.lower() or
                     'solução' in form_help.lower())

    def test_form_save_method_sets_new_fields(self):
        """Test that form save method properly sets new fields."""
        # This will fail until form save method is updated
        form_data = {
            'name': 'Form Save Test',
            'concentration': '250 mg',
            'pharmaceutical_form': 'cápsula',
            'usage_instructions': 'Save test instructions',
            'is_public': True
        }
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        drug_template = form.save()
        
        # Check that new fields are properly saved
        self.assertEqual(drug_template.concentration, '250 mg')
        self.assertEqual(drug_template.pharmaceutical_form, 'cápsula')
        self.assertEqual(drug_template.creator, self.user)
        self.assertFalse(drug_template.is_imported)  # Should default to False
        self.assertIsNone(drug_template.import_source)


class DrugTemplateImportFormTest(TestCase):
    """Tests for forms related to imported drug templates."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_form_handles_imported_drug_editing(self):
        """Test that form handles editing of imported drugs differently."""
        # This will fail until imported drug handling is implemented
        from apps.drugtemplates.models import DrugTemplate
        
        # Create imported drug
        system_user = User.objects.create_user(
            username='system',
            email='system@hospital.internal'
        )
        imported_drug = DrugTemplate.objects.create(
            name='Imported Drug',
            concentration='100 mg',
            pharmaceutical_form='comprimido',
            creator=system_user,
            is_imported=True,
            import_source='Test'
        )
        
        # Form should handle imported drugs differently
        form = DrugTemplateForm(instance=imported_drug, user=self.user)
        
        # Core imported fields should be readonly or disabled
        self.assertTrue(
            form.fields['name'].disabled or
            'readonly' in form.fields['name'].widget.attrs or
            form.fields['name'].widget.attrs.get('readonly') is True
        )
        self.assertTrue(
            form.fields['concentration'].disabled or
            'readonly' in form.fields['concentration'].widget.attrs or
            form.fields['concentration'].widget.attrs.get('readonly') is True
        )

    def test_form_allows_usage_instructions_for_imported(self):
        """Test that usage instructions can be added to imported drugs."""
        # This will fail until imported drug editing is implemented
        from apps.drugtemplates.models import DrugTemplate
        
        # Create imported drug without usage instructions
        system_user = User.objects.create_user(
            username='system', 
            email='system@hospital.internal'
        )
        imported_drug = DrugTemplate.objects.create(
            name='Imported Drug',
            concentration='200 mg',
            pharmaceutical_form='cápsula',
            creator=system_user,
            is_imported=True,
            usage_instructions=''  # Empty initially
        )
        
        # Should allow adding usage instructions
        form_data = {
            'name': 'Imported Drug',  # Readonly but present
            'concentration': '200 mg',  # Readonly but present
            'pharmaceutical_form': 'cápsula',  # Readonly but present
            'usage_instructions': 'Added by user for imported drug',
            'is_public': True
        }
        form = DrugTemplateForm(data=form_data, instance=imported_drug, user=self.user)
        
        # Should be valid and allow usage instructions update
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        
        updated_drug = form.save()
        self.assertEqual(
            updated_drug.usage_instructions, 
            'Added by user for imported drug'
        )