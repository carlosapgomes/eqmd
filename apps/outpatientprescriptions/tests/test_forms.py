from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.patients.models import Patient
from apps.drugtemplates.models import DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem
from apps.outpatientprescriptions.models import OutpatientPrescription, PrescriptionItem
from apps.outpatientprescriptions.forms.prescription_forms import (
    OutpatientPrescriptionForm,
    PrescriptionItemForm,
    PrescriptionItemFormSet,
    PrescriptionItemFormSetHelper
)

User = get_user_model()


class OutpatientPrescriptionFormTest(TestCase):
    """Test cases for OutpatientPrescriptionForm."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Doctor
        )


        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Test prescription for patient',
            'instructions': 'Take all medications as prescribed',
            'status': 'draft',
            'prescription_date': timezone.now().date()
        }
        
        form = OutpatientPrescriptionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_form_missing_required_fields(self):
        """Test form with missing required fields."""
        form_data = {}
        form = OutpatientPrescriptionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        
        # Check that required fields are in errors
        self.assertIn('patient', form.errors)
        self.assertIn('event_datetime', form.errors)
        self.assertIn('description', form.errors)
        self.assertIn('instructions', form.errors)

    def test_form_default_prescription_date(self):
        """Test that form sets default prescription date to today for new instances."""
        form = OutpatientPrescriptionForm(user=self.user)
        expected_date = timezone.now().date()
        self.assertEqual(form.fields['prescription_date'].initial, expected_date)

    def test_form_save_sets_creator(self):
        """Test that form save method sets creator correctly."""
        form_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Test prescription',
            'instructions': 'Test instructions',
            'status': 'draft',
            'prescription_date': timezone.now().date()
        }
        
        form = OutpatientPrescriptionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        prescription = form.save(commit=False)
        prescription.updated_by = self.user  # Set updated_by field
        prescription.save()
        self.assertEqual(prescription.created_by, self.user)
        self.assertEqual(prescription.patient, self.patient)

    def test_form_widget_classes(self):
        """Test that form widgets have correct CSS classes."""
        form = OutpatientPrescriptionForm(user=self.user)
        
        # Check that widgets have Bootstrap classes
        self.assertIn('form-control', form.fields['patient'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['event_datetime'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['description'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['instructions'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['status'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['prescription_date'].widget.attrs['class'])

    def test_form_field_labels(self):
        """Test that form fields have correct labels."""
        form = OutpatientPrescriptionForm(user=self.user)
        
        self.assertEqual(form.fields['patient'].label, 'Paciente')
        self.assertEqual(form.fields['event_datetime'].label, 'Data e Hora')
        self.assertEqual(form.fields['description'].label, 'Descrição')
        self.assertEqual(form.fields['instructions'].label, 'Instruções Gerais')
        self.assertEqual(form.fields['status'].label, 'Status')
        self.assertEqual(form.fields['prescription_date'].label, 'Data da Receita')

    def test_form_help_texts(self):
        """Test that form fields have correct help texts."""
        form = OutpatientPrescriptionForm(user=self.user)
        
        self.assertEqual(
            form.fields['instructions'].help_text,
            'Instruções gerais que se aplicam a toda a receita'
        )
        self.assertEqual(
            form.fields['description'].help_text,
            'Descrição breve do motivo da prescrição'
        )
        self.assertEqual(
            form.fields['prescription_date'].help_text,
            'Data em que a receita será emitida'
        )

    def test_form_status_choices(self):
        """Test that status field has correct choices."""
        form_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Test prescription',
            'instructions': 'Test instructions',
            'status': 'finalized',
            'prescription_date': timezone.now().date()
        }
        
        form = OutpatientPrescriptionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        prescription = form.save()
        self.assertEqual(prescription.status, 'finalized')


class PrescriptionItemFormTest(TestCase):
    """Test cases for PrescriptionItemForm."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Doctor
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            patient=cls.patient,
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.drug_template = DrugTemplate.objects.create(
            name='Test Drug',
            presentation='10mg tablet',
            usage_instructions='Take 1 tablet daily',
            creator=cls.user,
            is_public=True
        )

    def test_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            'drug_name': 'Paracetamol',
            'presentation': '500mg comprimidos',
            'usage_instructions': 'Tomar 1 comprimido de 8 em 8 horas',
            'quantity': '21 comprimidos',
            'order': 1,
            'source_template': '',  # Empty source template
        }
        
        form = PrescriptionItemForm(data=form_data, user=self.user)
        if not form.is_valid():
            print("Form errors:", form.errors)
        self.assertTrue(form.is_valid())

    def test_form_missing_required_fields(self):
        """Test form with missing required fields."""
        form_data = {}
        form = PrescriptionItemForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        
        # Check that required fields are in errors
        self.assertIn('drug_name', form.errors)
        self.assertIn('presentation', form.errors)
        self.assertIn('usage_instructions', form.errors)
        self.assertIn('quantity', form.errors)

    def test_form_field_labels(self):
        """Test that form fields have correct labels."""
        form = PrescriptionItemForm(user=self.user)
        
        self.assertEqual(form.fields['drug_name'].label, 'Medicamento')
        self.assertEqual(form.fields['presentation'].label, 'Apresentação')
        self.assertEqual(form.fields['usage_instructions'].label, 'Instruções de Uso')
        self.assertEqual(form.fields['quantity'].label, 'Quantidade')

    def test_form_widget_classes(self):
        """Test that form widgets have correct CSS classes."""
        form = PrescriptionItemForm(user=self.user)
        
        # Check that widgets have Bootstrap classes
        self.assertIn('form-control', form.fields['drug_name'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['presentation'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['usage_instructions'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['quantity'].widget.attrs['class'])

    def test_clean_order_method(self):
        """Test clean_order method sets minimum value to 1."""
        form_data = {
            'drug_name': 'Test Drug',
            'presentation': '10mg tablet',
            'usage_instructions': 'Take daily',
            'quantity': '30',
            'order': -1,  # Invalid negative order
            'source_template': '',
        }
        
        form = PrescriptionItemForm(data=form_data, user=self.user)
        if not form.is_valid():
            print("Form errors:", form.errors)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['order'], 1)

    def test_clean_order_none_value(self):
        """Test clean_order method handles None value."""
        form_data = {
            'drug_name': 'Test Drug',
            'presentation': '10mg tablet',
            'usage_instructions': 'Take daily',
            'quantity': '30',
            'source_template': '',
            # order not provided, will be None
        }
        
        form = PrescriptionItemForm(data=form_data, user=self.user)
        if not form.is_valid():
            print("Form errors:", form.errors)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['order'], 1)

    def test_drug_template_field_with_user(self):
        """Test that drug_template field is updated with user context."""
        form = PrescriptionItemForm(user=self.user)
        
        # Check that drug_template field exists
        self.assertIn('drug_template', form.fields)
        self.assertEqual(form.fields['drug_template'].label, 'Template de Medicamento')

    def test_form_widget_placeholders(self):
        """Test that form widgets have correct placeholders."""
        form = PrescriptionItemForm(user=self.user)
        
        self.assertEqual(
            form.fields['drug_name'].widget.attrs['placeholder'],
            'Nome do medicamento'
        )
        self.assertEqual(
            form.fields['presentation'].widget.attrs['placeholder'],
            'Ex: 500mg comprimidos, 120ml xarope'
        )
        self.assertEqual(
            form.fields['usage_instructions'].widget.attrs['placeholder'],
            'Ex: Tomar 1 comprimido de 8 em 8 horas por 7 dias'
        )
        self.assertEqual(
            form.fields['quantity'].widget.attrs['placeholder'],
            'Ex: 21 comprimidos, 1 frasco'
        )


class PrescriptionItemFormSetTest(TestCase):
    """Test cases for PrescriptionItemFormSet."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Doctor
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            patient=cls.patient,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_formset_creation(self):
        """Test creating a formset."""
        formset = PrescriptionItemFormSet(instance=self.prescription)
        
        # Check formset properties
        self.assertEqual(formset.model, PrescriptionItem)
        self.assertTrue(formset.can_delete)
        self.assertEqual(formset.min_num, 1)
        self.assertEqual(formset.extra, 1)

    def test_formset_valid_data(self):
        """Test formset with valid data."""
        formset_data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-drug_name': 'Paracetamol',
            'form-0-presentation': '500mg comprimidos',
            'form-0-usage_instructions': 'Tomar 1 comprimido de 8 em 8 horas',
            'form-0-quantity': '21 comprimidos',
            'form-0-order': '1',
            
            'form-1-drug_name': 'Ibuprofeno',
            'form-1-presentation': '400mg comprimidos',
            'form-1-usage_instructions': 'Tomar 1 comprimido de 8 em 8 horas se dor',
            'form-1-quantity': '20 comprimidos',
            'form-1-order': '2',
        }
        
        formset = PrescriptionItemFormSet(
            data=formset_data,
            instance=self.prescription
        )
        
        self.assertTrue(formset.is_valid())

    def test_formset_minimum_forms_validation(self):
        """Test that formset requires at least one form."""
        formset_data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            # Empty form data - should fail validation
            'form-0-drug_name': '',
            'form-0-presentation': '',
            'form-0-usage_instructions': '',
            'form-0-quantity': '',
            'form-0-order': '1',
        }
        
        formset = PrescriptionItemFormSet(
            data=formset_data,
            instance=self.prescription
        )
        
        self.assertFalse(formset.is_valid())

    def test_formset_delete_functionality(self):
        """Test formset delete functionality."""
        # Create an existing item
        item = PrescriptionItem.objects.create(
            prescription=self.prescription,
            drug_name='Test Drug',
            presentation='10mg tablet',
            usage_instructions='Take daily',
            quantity='30',
            order=1
        )
        
        formset_data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-id': str(item.pk),
            'form-0-drug_name': 'Test Drug',
            'form-0-presentation': '10mg tablet',
            'form-0-usage_instructions': 'Take daily',
            'form-0-quantity': '30',
            'form-0-order': '1',
            'form-0-DELETE': 'on',  # Mark for deletion
        }
        
        formset = PrescriptionItemFormSet(
            data=formset_data,
            instance=self.prescription
        )
        
        # Note: This might not validate due to min_num constraint
        # The actual deletion happens during save
        if formset.is_valid():
            formset.save()
            
        # Check if item was marked for deletion
        self.assertTrue(any(form in formset.deleted_forms for form in formset))


class PrescriptionItemFormSetHelperTest(TestCase):
    """Test cases for PrescriptionItemFormSetHelper."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Doctor
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            patient=cls.patient,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_get_formset_with_user(self):
        """Test get_formset_with_user method."""
        formset = PrescriptionItemFormSetHelper.get_formset_with_user(
            self.user,
            instance=self.prescription
        )
        
        # Check that formset was created
        self.assertIsNotNone(formset)
        
        # Check that user was passed to forms
        for form in formset:
            self.assertEqual(form.user, self.user)

    def test_prepare_formset_data(self):
        """Test prepare_formset_data method."""
        formset = PrescriptionItemFormSet(instance=self.prescription)
        formset_data = PrescriptionItemFormSetHelper.prepare_formset_data(formset)
        
        # Check that all expected keys are present
        expected_keys = ['formset', 'management_form', 'empty_form', 'can_delete']
        for key in expected_keys:
            self.assertIn(key, formset_data)
        
        # Check values
        self.assertEqual(formset_data['formset'], formset)
        self.assertEqual(formset_data['management_form'], formset.management_form)
        self.assertEqual(formset_data['empty_form'], formset.empty_form)
        self.assertEqual(formset_data['can_delete'], formset.can_delete)


class FormIntegrationTest(TestCase):
    """Integration tests for forms working together."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Doctor
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_complete_prescription_creation_workflow(self):
        """Test complete workflow of creating prescription with items."""
        # Create prescription form
        prescription_form_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Test prescription for complete workflow',
            'instructions': 'Take all medications as prescribed',
            'status': 'draft',
            'prescription_date': timezone.now().date()
        }
        
        prescription_form = OutpatientPrescriptionForm(
            data=prescription_form_data,
            user=self.user
        )
        
        self.assertTrue(prescription_form.is_valid())
        prescription = prescription_form.save(commit=False)
        prescription.updated_by = self.user
        prescription.save()
        
        # Create formset with items
        formset_data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-drug_name': 'Paracetamol',
            'form-0-presentation': '500mg comprimidos',
            'form-0-usage_instructions': 'Tomar 1 comprimido de 8 em 8 horas',
            'form-0-quantity': '21 comprimidos',
            'form-0-order': '1',
            
            'form-1-drug_name': 'Ibuprofeno',
            'form-1-presentation': '400mg comprimidos',
            'form-1-usage_instructions': 'Tomar 1 comprimido se dor',
            'form-1-quantity': '10 comprimidos',
            'form-1-order': '2',
        }
        
        formset = PrescriptionItemFormSet(
            data=formset_data,
            instance=prescription
        )
        
        self.assertTrue(formset.is_valid())
        formset.save()
        
        # Verify everything was created correctly
        self.assertEqual(prescription.items.count(), 2)
        
        items = prescription.items.all().order_by('order')
        item1 = items[0]
        self.assertEqual(item1.drug_name, 'Paracetamol')
        self.assertEqual(item1.order, 1)
        
        item2 = items[1]
        self.assertEqual(item2.drug_name, 'Ibuprofeno')
        self.assertEqual(item2.order, 2)