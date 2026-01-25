from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from ..models import DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem
from ..forms import DrugTemplateForm

User = get_user_model()


class DrugTemplateModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_drug_template_creation(self):
        """Test creating a drug template instance."""
        drug_template = DrugTemplate.objects.create(
            name='Paracetamol',
            presentation='500mg comprimidos',
            usage_instructions='Tomar 1 comprimido de 8 em 8 horas',
            creator=self.user,
            is_public=True
        )

        self.assertEqual(drug_template.name, 'Paracetamol')
        self.assertEqual(drug_template.presentation, '500mg comprimidos')
        self.assertEqual(drug_template.usage_instructions, 'Tomar 1 comprimido de 8 em 8 horas')
        self.assertEqual(drug_template.creator, self.user)
        self.assertTrue(drug_template.is_public)
        self.assertIsNotNone(drug_template.created_at)
        self.assertIsNotNone(drug_template.updated_at)

    def test_drug_template_str_method(self):
        """Test string representation of drug template."""
        drug_template = DrugTemplate.objects.create(
            name='Ibuprofeno',
            presentation='400mg comprimidos',
            usage_instructions='Tomar 1 comprimido de 8 em 8 horas',
            creator=self.user
        )

        self.assertEqual(str(drug_template), 'Ibuprofeno')

    def test_drug_template_get_absolute_url(self):
        """Test get_absolute_url method."""
        drug_template = DrugTemplate.objects.create(
            name='Dipirona',
            presentation='500mg comprimidos',
            usage_instructions='Tomar 1 comprimido de 6 em 6 horas',
            creator=self.user
        )

        expected_url = reverse('drugtemplates:detail', kwargs={'pk': drug_template.pk})
        self.assertEqual(drug_template.get_absolute_url(), expected_url)

    def test_drug_template_default_values(self):
        """Test default values for drug template fields."""
        drug_template = DrugTemplate.objects.create(
            name='Aspirina',
            presentation='100mg comprimidos',
            usage_instructions='Tomar 1 comprimido por dia',
            creator=self.user
        )

        self.assertFalse(drug_template.is_public)  # Default should be False

    def test_drug_template_clean_method_valid(self):
        """Test clean method with valid data."""
        drug_template = DrugTemplate(
            name='Amoxicilina',
            presentation='875mg comprimidos',
            usage_instructions='Tomar 1 comprimido de 12 em 12 horas',
            creator=self.user
        )

        # Should not raise ValidationError
        drug_template.clean()

    def test_drug_template_clean_method_empty_name(self):
        """Test clean method with empty name."""
        drug_template = DrugTemplate(
            name='',
            presentation='500mg comprimidos',
            usage_instructions='Tomar 1 comprimido',
            creator=self.user
        )

        with self.assertRaises(ValidationError) as cm:
            drug_template.clean()
        self.assertIn('name', cm.exception.message_dict)

    def test_drug_template_clean_method_whitespace_name(self):
        """Test clean method with whitespace-only name."""
        drug_template = DrugTemplate(
            name='   ',
            presentation='500mg comprimidos',
            usage_instructions='Tomar 1 comprimido',
            creator=self.user
        )

        with self.assertRaises(ValidationError) as cm:
            drug_template.clean()
        self.assertIn('name', cm.exception.message_dict)

    def test_drug_template_clean_method_empty_presentation(self):
        """Test clean method with empty presentation."""
        drug_template = DrugTemplate(
            name='Paracetamol',
            presentation='',
            usage_instructions='Tomar 1 comprimido',
            creator=self.user
        )

        with self.assertRaises(ValidationError) as cm:
            drug_template.clean()
        self.assertIn('presentation', cm.exception.message_dict)

    def test_drug_template_clean_method_whitespace_presentation(self):
        """Test clean method with whitespace-only presentation."""
        drug_template = DrugTemplate(
            name='Paracetamol',
            presentation='   ',
            usage_instructions='Tomar 1 comprimido',
            creator=self.user
        )

        with self.assertRaises(ValidationError) as cm:
            drug_template.clean()
        self.assertIn('presentation', cm.exception.message_dict)

    def test_drug_template_clean_method_empty_usage_instructions(self):
        """Test clean method with empty usage instructions."""
        drug_template = DrugTemplate(
            name='Paracetamol',
            presentation='500mg comprimidos',
            usage_instructions='',
            creator=self.user
        )

        with self.assertRaises(ValidationError) as cm:
            drug_template.clean()
        self.assertIn('usage_instructions', cm.exception.message_dict)

    def test_drug_template_clean_method_whitespace_usage_instructions(self):
        """Test clean method with whitespace-only usage instructions."""
        drug_template = DrugTemplate(
            name='Paracetamol',
            presentation='500mg comprimidos',
            usage_instructions='   ',
            creator=self.user
        )

        with self.assertRaises(ValidationError) as cm:
            drug_template.clean()
        self.assertIn('usage_instructions', cm.exception.message_dict)

    def test_drug_template_meta_options(self):
        """Test Meta class options."""
        DrugTemplate.objects.create(
            name='Zebra Drug',
            presentation='500mg',
            usage_instructions='Test',
            creator=self.user
        )
        DrugTemplate.objects.create(
            name='Alpha Drug',
            presentation='250mg',
            usage_instructions='Test',
            creator=self.user
        )

        # Test ordering by name
        templates = list(DrugTemplate.objects.all())
        self.assertEqual(templates[0].name, 'Alpha Drug')
        self.assertEqual(templates[1].name, 'Zebra Drug')

    def test_drug_template_related_name(self):
        """Test related_name for creator foreign key."""
        drug_template = DrugTemplate.objects.create(
            name='Test Drug',
            presentation='500mg',
            usage_instructions='Test instructions',
            creator=self.user
        )

        # Test that the related_name works
        self.assertIn(drug_template, self.user.drug_templates.all())

    def test_drug_template_cascade_delete(self):
        """Test that deleting a user cascades to their drug templates."""
        drug_template = DrugTemplate.objects.create(
            name='Test Drug',
            presentation='500mg',
            usage_instructions='Test instructions',
            creator=self.user
        )

        template_id = drug_template.id
        self.user.delete()

        # Drug template should be deleted when user is deleted
        self.assertFalse(DrugTemplate.objects.filter(id=template_id).exists())


class DrugTemplateFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_drug_template_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            'name': 'Paracetamol',
            'presentation': '500mg comprimidos',
            'usage_instructions': 'Tomar 1 comprimido de 8 em 8 horas para dor ou febre',
            'is_public': True
        }
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_drug_template_form_missing_required_fields(self):
        """Test form with missing required fields."""
        form_data = {}
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('presentation', form.errors)
        self.assertIn('usage_instructions', form.errors)

    def test_drug_template_form_duplicate_name_validation(self):
        """Test that duplicate names by same user are prevented."""
        # Create an existing drug template
        DrugTemplate.objects.create(
            name='Paracetamol',
            presentation='250mg',
            usage_instructions='Test',
            creator=self.user
        )

        # Try to create another with same name
        form_data = {
            'name': 'Paracetamol',  # Same name
            'presentation': '500mg comprimidos',
            'usage_instructions': 'Tomar 1 comprimido de 8 em 8 horas para dor ou febre',
            'is_public': False
        }
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('já possui um template', str(form.errors['name']))

    def test_drug_template_form_duplicate_name_case_insensitive(self):
        """Test that duplicate name validation is case insensitive."""
        # Create an existing drug template
        DrugTemplate.objects.create(
            name='paracetamol',
            presentation='250mg',
            usage_instructions='Test',
            creator=self.user
        )

        # Try to create another with same name but different case
        form_data = {
            'name': 'PARACETAMOL',  # Same name, different case
            'presentation': '500mg comprimidos',
            'usage_instructions': 'Tomar 1 comprimido de 8 em 8 horas para dor ou febre',
            'is_public': False
        }
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_drug_template_form_short_usage_instructions(self):
        """Test validation for short usage instructions."""
        form_data = {
            'name': 'Paracetamol',
            'presentation': '500mg comprimidos',
            'usage_instructions': 'Short',  # Less than 10 characters
            'is_public': False
        }
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('usage_instructions', form.errors)
        self.assertIn('pelo menos 10 caracteres', str(form.errors['usage_instructions']))

    def test_drug_template_form_whitespace_trimming(self):
        """Test that whitespace is properly trimmed and validated."""
        form_data = {
            'name': '   ',  # Only whitespace
            'presentation': '   ',  # Only whitespace
            'usage_instructions': '   ',  # Only whitespace
            'is_public': False
        }
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('presentation', form.errors)
        self.assertIn('usage_instructions', form.errors)

    def test_drug_template_form_save_sets_creator(self):
        """Test that form save method sets creator correctly."""
        form_data = {
            'name': 'Paracetamol',
            'presentation': '500mg comprimidos',
            'usage_instructions': 'Tomar 1 comprimido de 8 em 8 horas para dor ou febre',
            'is_public': True
        }
        form = DrugTemplateForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

        drug_template = form.save()
        self.assertEqual(drug_template.creator, self.user)
        self.assertEqual(drug_template.name, 'Paracetamol')

    def test_drug_template_form_widget_classes(self):
        """Test that form widgets have correct CSS classes."""
        form = DrugTemplateForm(user=self.user)

        # Check that widgets have Bootstrap classes
        self.assertIn('form-control', form.fields['name'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['presentation'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['usage_instructions'].widget.attrs['class'])
        self.assertIn('markdown-editor', form.fields['usage_instructions'].widget.attrs['class'])
        self.assertIn('form-check-input', form.fields['is_public'].widget.attrs['class'])

        # Check markdown editor attributes
        self.assertEqual(
            form.fields['usage_instructions'].widget.attrs['data-easymde'],
            'true'
        )


class PrescriptionTemplateModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_prescription_template_creation(self):
        """Test creating a prescription template instance."""
        prescription_template = PrescriptionTemplate.objects.create(
            name='Template de Hipertensão',
            creator=self.user,
            is_public=True
        )

        self.assertEqual(prescription_template.name, 'Template de Hipertensão')
        self.assertEqual(prescription_template.creator, self.user)
        self.assertTrue(prescription_template.is_public)
        self.assertIsNotNone(prescription_template.created_at)
        self.assertIsNotNone(prescription_template.updated_at)

    def test_prescription_template_str_method(self):
        """Test string representation of prescription template."""
        prescription_template = PrescriptionTemplate.objects.create(
            name='Template de Diabetes',
            creator=self.user
        )

        self.assertEqual(str(prescription_template), 'Template de Diabetes')

    def test_prescription_template_get_absolute_url(self):
        """Test get_absolute_url method."""
        prescription_template = PrescriptionTemplate.objects.create(
            name='Template de Gripe',
            creator=self.user
        )

        expected_url = f"/drugtemplates/prescription-templates/{prescription_template.pk}/"
        self.assertEqual(prescription_template.get_absolute_url(), expected_url)

    def test_prescription_template_default_values(self):
        """Test default values for prescription template fields."""
        prescription_template = PrescriptionTemplate.objects.create(
            name='Template Teste',
            creator=self.user
        )

        self.assertFalse(prescription_template.is_public)  # Default should be False

    def test_prescription_template_clean_method_valid(self):
        """Test clean method with valid data."""
        prescription_template = PrescriptionTemplate(
            name='Template Válido',
            creator=self.user
        )

        # Should not raise ValidationError
        prescription_template.clean()

    def test_prescription_template_clean_method_empty_name(self):
        """Test clean method with empty name."""
        prescription_template = PrescriptionTemplate(
            name='',
            creator=self.user
        )

        with self.assertRaises(ValidationError) as cm:
            prescription_template.clean()
        self.assertIn('name', cm.exception.message_dict)

    def test_prescription_template_clean_method_whitespace_name(self):
        """Test clean method with whitespace-only name."""
        prescription_template = PrescriptionTemplate(
            name='   ',
            creator=self.user
        )

        with self.assertRaises(ValidationError) as cm:
            prescription_template.clean()
        self.assertIn('name', cm.exception.message_dict)

    def test_prescription_template_meta_options(self):
        """Test Meta class options."""
        PrescriptionTemplate.objects.create(
            name='Zebra Template',
            creator=self.user
        )
        PrescriptionTemplate.objects.create(
            name='Alpha Template',
            creator=self.user
        )

        # Test ordering by name
        templates = list(PrescriptionTemplate.objects.all())
        self.assertEqual(templates[0].name, 'Alpha Template')
        self.assertEqual(templates[1].name, 'Zebra Template')

    def test_prescription_template_related_name(self):
        """Test related_name for creator foreign key."""
        prescription_template = PrescriptionTemplate.objects.create(
            name='Test Template',
            creator=self.user
        )

        # Test that the related_name works
        self.assertIn(prescription_template, self.user.prescription_templates.all())

    def test_prescription_template_cascade_delete(self):
        """Test that deleting a user cascades to their prescription templates."""
        prescription_template = PrescriptionTemplate.objects.create(
            name='Test Template',
            creator=self.user
        )

        template_id = prescription_template.id
        self.user.delete()

        # Prescription template should be deleted when user is deleted
        self.assertFalse(PrescriptionTemplate.objects.filter(id=template_id).exists())


class PrescriptionTemplateItemModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.prescription_template = PrescriptionTemplate.objects.create(
            name='Template de Hipertensão',
            creator=self.user
        )

    def test_prescription_template_item_creation(self):
        """Test creating a prescription template item instance."""
        item = PrescriptionTemplateItem.objects.create(
            template=self.prescription_template,
            drug_name='Losartana',
            presentation='50mg comprimidos',
            usage_instructions='Tomar 1 comprimido pela manhã',
            quantity='30 comprimidos',
            order=1
        )

        self.assertEqual(item.template, self.prescription_template)
        self.assertEqual(item.drug_name, 'Losartana')
        self.assertEqual(item.presentation, '50mg comprimidos')
        self.assertEqual(item.usage_instructions, 'Tomar 1 comprimido pela manhã')
        self.assertEqual(item.quantity, '30 comprimidos')
        self.assertEqual(item.order, 1)
        self.assertIsNotNone(item.created_at)
        self.assertIsNotNone(item.updated_at)

    def test_prescription_template_item_str_method(self):
        """Test string representation of prescription template item."""
        item = PrescriptionTemplateItem.objects.create(
            template=self.prescription_template,
            drug_name='Atenolol',
            presentation='25mg comprimidos',
            usage_instructions='Tomar 1 comprimido pela manhã',
            quantity='30 comprimidos',
            order=1
        )

        self.assertEqual(str(item), 'Atenolol - 25mg comprimidos')

    def test_prescription_template_item_default_order(self):
        """Test default value for order field."""
        item = PrescriptionTemplateItem.objects.create(
            template=self.prescription_template,
            drug_name='Hidroclorotiazida',
            presentation='25mg comprimidos',
            usage_instructions='Tomar 1 comprimido pela manhã',
            quantity='30 comprimidos'
        )

        self.assertEqual(item.order, 0)  # Default should be 0

    def test_prescription_template_item_clean_method_valid(self):
        """Test clean method with valid data."""
        item = PrescriptionTemplateItem(
            template=self.prescription_template,
            drug_name='Captopril',
            presentation='25mg comprimidos',
            usage_instructions='Tomar 1 comprimido de 12 em 12 horas',
            quantity='60 comprimidos',
            order=1
        )

        # Should not raise ValidationError
        item.clean()

    def test_prescription_template_item_clean_method_empty_drug_name(self):
        """Test clean method with empty drug_name."""
        item = PrescriptionTemplateItem(
            template=self.prescription_template,
            drug_name='',
            presentation='25mg comprimidos',
            usage_instructions='Tomar 1 comprimido',
            quantity='30 comprimidos'
        )

        with self.assertRaises(ValidationError) as cm:
            item.clean()
        self.assertIn('drug_name', cm.exception.message_dict)

    def test_prescription_template_item_clean_method_whitespace_drug_name(self):
        """Test clean method with whitespace-only drug_name."""
        item = PrescriptionTemplateItem(
            template=self.prescription_template,
            drug_name='   ',
            presentation='25mg comprimidos',
            usage_instructions='Tomar 1 comprimido',
            quantity='30 comprimidos'
        )

        with self.assertRaises(ValidationError) as cm:
            item.clean()
        self.assertIn('drug_name', cm.exception.message_dict)

    def test_prescription_template_item_clean_method_empty_presentation(self):
        """Test clean method with empty presentation."""
        item = PrescriptionTemplateItem(
            template=self.prescription_template,
            drug_name='Enalapril',
            presentation='',
            usage_instructions='Tomar 1 comprimido',
            quantity='30 comprimidos'
        )

        with self.assertRaises(ValidationError) as cm:
            item.clean()
        self.assertIn('presentation', cm.exception.message_dict)

    def test_prescription_template_item_clean_method_empty_usage_instructions(self):
        """Test clean method with empty usage_instructions."""
        item = PrescriptionTemplateItem(
            template=self.prescription_template,
            drug_name='Enalapril',
            presentation='10mg comprimidos',
            usage_instructions='',
            quantity='30 comprimidos'
        )

        with self.assertRaises(ValidationError) as cm:
            item.clean()
        self.assertIn('usage_instructions', cm.exception.message_dict)

    def test_prescription_template_item_clean_method_empty_quantity(self):
        """Test clean method with empty quantity."""
        item = PrescriptionTemplateItem(
            template=self.prescription_template,
            drug_name='Enalapril',
            presentation='10mg comprimidos',
            usage_instructions='Tomar 1 comprimido pela manhã',
            quantity=''
        )

        with self.assertRaises(ValidationError) as cm:
            item.clean()
        self.assertIn('quantity', cm.exception.message_dict)

    def test_prescription_template_item_meta_options(self):
        """Test Meta class options."""
        PrescriptionTemplateItem.objects.create(
            template=self.prescription_template,
            drug_name='Zebra Drug',
            presentation='10mg',
            usage_instructions='Test',
            quantity='30',
            order=2
        )
        PrescriptionTemplateItem.objects.create(
            template=self.prescription_template,
            drug_name='Alpha Drug',
            presentation='20mg',
            usage_instructions='Test',
            quantity='30',
            order=1
        )

        # Test ordering by template, order, drug_name
        items = list(PrescriptionTemplateItem.objects.all())
        self.assertEqual(items[0].order, 1)  # Should be ordered by order first
        self.assertEqual(items[1].order, 2)

    def test_prescription_template_item_foreign_key_relationship(self):
        """Test foreign key relationship with PrescriptionTemplate."""
        item = PrescriptionTemplateItem.objects.create(
            template=self.prescription_template,
            drug_name='Metformina',
            presentation='850mg comprimidos',
            usage_instructions='Tomar 1 comprimido antes das refeições',
            quantity='90 comprimidos',
            order=1
        )

        # Test that the relationship works
        self.assertIn(item, self.prescription_template.items.all())

    def test_prescription_template_item_cascade_delete(self):
        """Test that deleting a prescription template cascades to its items."""
        item = PrescriptionTemplateItem.objects.create(
            template=self.prescription_template,
            drug_name='Glibenclamida',
            presentation='5mg comprimidos',
            usage_instructions='Tomar 1 comprimido antes do café da manhã',
            quantity='30 comprimidos',
            order=1
        )

        item_id = item.id
        self.prescription_template.delete()

        # Item should be deleted when template is deleted
        self.assertFalse(PrescriptionTemplateItem.objects.filter(id=item_id).exists())


class PrescriptionTemplateIntegrationTest(TestCase):
    """Integration tests for PrescriptionTemplate and PrescriptionTemplateItem."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_prescription_template_with_multiple_items(self):
        """Test prescription template with multiple items."""
        template = PrescriptionTemplate.objects.create(
            name='Template Completo de Hipertensão',
            creator=self.user,
            is_public=True
        )

        # Create multiple items
        item1 = PrescriptionTemplateItem.objects.create(
            template=template,
            drug_name='Losartana',
            presentation='50mg comprimidos',
            usage_instructions='Tomar 1 comprimido pela manhã',
            quantity='30 comprimidos',
            order=1
        )

        item2 = PrescriptionTemplateItem.objects.create(
            template=template,
            drug_name='Hidroclorotiazida',
            presentation='25mg comprimidos',
            usage_instructions='Tomar 1 comprimido pela manhã',
            quantity='30 comprimidos',
            order=2
        )

        # Test that template has all items
        self.assertEqual(template.items.count(), 2)
        self.assertIn(item1, template.items.all())
        self.assertIn(item2, template.items.all())

        # Test ordering
        ordered_items = list(template.items.all())
        self.assertEqual(ordered_items[0].order, 1)
        self.assertEqual(ordered_items[1].order, 2)

    def test_prescription_template_items_ordering(self):
        """Test that prescription template items are properly ordered."""
        template = PrescriptionTemplate.objects.create(
            name='Template com Ordem',
            creator=self.user
        )

        # Create items in reverse order
        item3 = PrescriptionTemplateItem.objects.create(
            template=template,
            drug_name='Terceiro',
            presentation='10mg',
            usage_instructions='Terceiro medicamento',
            quantity='30',
            order=3
        )

        item1 = PrescriptionTemplateItem.objects.create(
            template=template,
            drug_name='Primeiro',
            presentation='10mg',
            usage_instructions='Primeiro medicamento',
            quantity='30',
            order=1
        )

        item2 = PrescriptionTemplateItem.objects.create(
            template=template,
            drug_name='Segundo',
            presentation='10mg',
            usage_instructions='Segundo medicamento',
            quantity='30',
            order=2
        )

        # Test that items are returned in correct order
        ordered_items = list(template.items.all())
        self.assertEqual(len(ordered_items), 3)
        self.assertEqual(ordered_items[0], item1)
        self.assertEqual(ordered_items[1], item2)
        self.assertEqual(ordered_items[2], item3)
