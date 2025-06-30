from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError, ImproperlyConfigured
from datetime import date
from apps.patients.models import Patient
from apps.events.models import Event
from apps.drugtemplates.models import DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem
from .models import OutpatientPrescription, PrescriptionItem

User = get_user_model()


class OutpatientPrescriptionModelTest(TestCase):
    """Test cases for OutpatientPrescription model."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_outpatient_prescription_creation(self):
        """Test creating an outpatient prescription."""
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Take 2 tablets twice daily',
            status='draft',
            prescription_date=date.today(),
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(prescription.instructions, 'Take 2 tablets twice daily')
        self.assertEqual(prescription.status, 'draft')
        self.assertEqual(prescription.prescription_date, date.today())
        self.assertEqual(prescription.patient, self.patient)
        self.assertEqual(prescription.created_by, self.user)
        self.assertTrue(prescription.id)

    def test_outpatient_prescription_event_type_auto_set(self):
        """Test that event_type is automatically set to OUTPT_PRESCRIPTION_EVENT."""
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(prescription.event_type, Event.OUTPT_PRESCRIPTION_EVENT)

    def test_outpatient_prescription_default_values(self):
        """Test default values for prescription fields."""
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        # Test default status is 'draft'
        self.assertEqual(prescription.status, 'draft')
        
        # Test default prescription_date is today (using timezone-aware date)
        self.assertEqual(prescription.prescription_date, timezone.now().date())

    def test_outpatient_prescription_status_choices(self):
        """Test status field choices."""
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            status='finalized',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(prescription.status, 'finalized')

    def test_outpatient_prescription_str_representation(self):
        """Test string representation of outpatient prescription."""
        prescription_date = date.today()
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            prescription_date=prescription_date,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        expected_str = f"Receita - {self.patient.name} - {prescription_date.strftime('%d/%m/%Y')}"
        self.assertEqual(str(prescription), expected_str)

    def test_outpatient_prescription_inheritance_from_event(self):
        """Test that OutpatientPrescription properly inherits from Event."""
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        # Check that it's an instance of Event
        self.assertIsInstance(prescription, Event)

        # Check that it has Event fields
        self.assertTrue(hasattr(prescription, 'event_type'))
        self.assertTrue(hasattr(prescription, 'event_datetime'))
        self.assertTrue(hasattr(prescription, 'description'))
        self.assertTrue(hasattr(prescription, 'patient'))
        self.assertTrue(hasattr(prescription, 'created_by'))
        self.assertTrue(hasattr(prescription, 'created_at'))
        self.assertTrue(hasattr(prescription, 'updated_at'))
        self.assertTrue(hasattr(prescription, 'updated_by'))

        # Check that it has OutpatientPrescription specific fields
        self.assertTrue(hasattr(prescription, 'instructions'))
        self.assertTrue(hasattr(prescription, 'status'))
        self.assertTrue(hasattr(prescription, 'prescription_date'))

    def test_outpatient_prescription_meta_configuration(self):
        """Test Meta class configuration."""
        self.assertEqual(OutpatientPrescription._meta.verbose_name, "Receita Ambulatorial")
        self.assertEqual(OutpatientPrescription._meta.verbose_name_plural, "Receitas Ambulatoriais")
        self.assertEqual(OutpatientPrescription._meta.ordering, ["-prescription_date", "-event_datetime"])

    def test_get_absolute_url_method(self):
        """Test that get_absolute_url method exists and works."""
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        # Since URLs aren't configured yet, we expect this to raise an exception
        # but the method should exist
        self.assertTrue(hasattr(prescription, 'get_absolute_url'))
        self.assertTrue(callable(prescription.get_absolute_url))

    def test_get_edit_url_method(self):
        """Test that get_edit_url method exists and works."""
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        # Since URLs aren't configured yet, we expect this to raise an exception
        # but the method should exist
        self.assertTrue(hasattr(prescription, 'get_edit_url'))
        self.assertTrue(callable(prescription.get_edit_url))

    def test_save_method_override(self):
        """Test that save method properly sets event_type."""
        prescription = OutpatientPrescription(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        # Event type should be None before saving
        self.assertIsNone(prescription.event_type)

        # Save the prescription
        prescription.save()

        # Event type should be set after saving
        self.assertEqual(prescription.event_type, Event.OUTPT_PRESCRIPTION_EVENT)

    def test_verbose_field_names(self):
        """Test that fields have proper verbose names."""
        prescription = OutpatientPrescription()
        
        # Check verbose names
        self.assertEqual(
            prescription._meta.get_field('instructions').verbose_name,
            'Instruções'
        )
        self.assertEqual(
            prescription._meta.get_field('status').verbose_name,
            'Status'
        )
        self.assertEqual(
            prescription._meta.get_field('prescription_date').verbose_name,
            'Data da Receita'
        )

    def test_field_help_text(self):
        """Test that instructions field has proper help text."""
        prescription = OutpatientPrescription()
        
        self.assertEqual(
            prescription._meta.get_field('instructions').help_text,
            'Instruções gerais da receita'
        )


class DataIndependenceTest(TestCase):
    """Test cases for data independence between prescriptions and templates."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_prescription_item_copy_from_drug_template(self):
        """Test that PrescriptionItem.copy_from_drug_template creates independent data."""
        # Create drug template
        drug_template = DrugTemplate.objects.create(
            name='Test Drug',
            presentation='10mg tablet',
            usage_instructions='Take 1 tablet daily',
            creator=self.user,
            is_public=True
        )

        # Create prescription
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        # Create prescription item and copy from template
        item = PrescriptionItem(prescription=prescription, quantity='30', order=1)
        item.copy_from_drug_template(drug_template)
        item.save()

        # Verify data was copied
        self.assertEqual(item.drug_name, 'Test Drug')
        self.assertEqual(item.presentation, '10mg tablet')
        self.assertEqual(item.usage_instructions, 'Take 1 tablet daily')
        self.assertEqual(item.source_template, drug_template)

        # Modify the template
        drug_template.name = 'Modified Drug'
        drug_template.presentation = '20mg tablet'
        drug_template.usage_instructions = 'Take 2 tablets daily'
        drug_template.save()

        # Refresh prescription item from database
        item.refresh_from_db()

        # Verify prescription item data was NOT changed
        self.assertEqual(item.drug_name, 'Test Drug')
        self.assertEqual(item.presentation, '10mg tablet')
        self.assertEqual(item.usage_instructions, 'Take 1 tablet daily')

    def test_prescription_copy_from_prescription_template(self):
        """Test that OutpatientPrescription.copy_from_prescription_template creates independent data."""
        # Create prescription template with items
        prescription_template = PrescriptionTemplate.objects.create(
            name='Test Template',
            creator=self.user,
            is_public=True
        )

        template_item1 = PrescriptionTemplateItem.objects.create(
            template=prescription_template,
            drug_name='Drug A',
            presentation='5mg tablet',
            usage_instructions='Take 1 daily',
            quantity='30',
            order=1
        )

        template_item2 = PrescriptionTemplateItem.objects.create(
            template=prescription_template,
            drug_name='Drug B',
            presentation='10mg capsule',
            usage_instructions='Take 2 daily',
            quantity='60',
            order=2
        )

        # Create prescription and copy from template
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        prescription.copy_from_prescription_template(prescription_template)

        # Verify items were created
        items = prescription.items.all().order_by('order')
        self.assertEqual(items.count(), 2)

        item1 = items[0]
        self.assertEqual(item1.drug_name, 'Drug A')
        self.assertEqual(item1.presentation, '5mg tablet')
        self.assertEqual(item1.usage_instructions, 'Take 1 daily')
        self.assertEqual(item1.quantity, '30')
        self.assertEqual(item1.order, 1)

        item2 = items[1]
        self.assertEqual(item2.drug_name, 'Drug B')
        self.assertEqual(item2.presentation, '10mg capsule')  
        self.assertEqual(item2.usage_instructions, 'Take 2 daily')
        self.assertEqual(item2.quantity, '60')
        self.assertEqual(item2.order, 2)

        # Modify template items
        template_item1.drug_name = 'Modified Drug A'
        template_item1.presentation = '15mg tablet'
        template_item1.usage_instructions = 'Take 3 daily'
        template_item1.quantity = '90'
        template_item1.save()

        template_item2.drug_name = 'Modified Drug B'
        template_item2.presentation = '20mg capsule'
        template_item2.usage_instructions = 'Take 4 daily' 
        template_item2.quantity = '120'
        template_item2.save()

        # Refresh prescription items from database
        item1.refresh_from_db()
        item2.refresh_from_db()

        # Verify prescription items were NOT changed
        self.assertEqual(item1.drug_name, 'Drug A')
        self.assertEqual(item1.presentation, '5mg tablet')
        self.assertEqual(item1.usage_instructions, 'Take 1 daily')
        self.assertEqual(item1.quantity, '30')

        self.assertEqual(item2.drug_name, 'Drug B')
        self.assertEqual(item2.presentation, '10mg capsule')
        self.assertEqual(item2.usage_instructions, 'Take 2 daily')
        self.assertEqual(item2.quantity, '60')

    def test_template_deletion_preserves_prescription_data(self):
        """Test that deleting templates doesn't affect prescription data."""
        # Create drug template
        drug_template = DrugTemplate.objects.create(
            name='Test Drug',
            presentation='10mg tablet',
            usage_instructions='Take 1 tablet daily',
            creator=self.user,
            is_public=True
        )

        # Create prescription with item from template
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test Prescription',
            instructions='Test instructions',
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        item = PrescriptionItem(prescription=prescription, quantity='30', order=1)
        item.copy_from_drug_template(drug_template)
        item.save()

        # Delete the template
        drug_template.delete()

        # Refresh prescription item from database
        item.refresh_from_db()

        # Verify prescription item data is still intact
        self.assertEqual(item.drug_name, 'Test Drug')
        self.assertEqual(item.presentation, '10mg tablet')
        self.assertEqual(item.usage_instructions, 'Take 1 tablet daily')
        # source_template should be None after deletion due to SET_NULL
        self.assertIsNone(item.source_template)
