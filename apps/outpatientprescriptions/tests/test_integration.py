from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from datetime import date, timedelta
from unittest.mock import patch

from apps.hospitals.models import Hospital
from apps.patients.models import Patient
from apps.drugtemplates.models import DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem
from apps.outpatientprescriptions.models import OutpatientPrescription, PrescriptionItem
from apps.sample_content.models import SampleContent
from apps.events.models import Event

User = get_user_model()


class OutpatientPrescriptionWorkflowTest(TestCase):
    """Integration tests for complete outpatient prescription workflows."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.doctor = User.objects.create_user(
            username='doctor1',
            email='doctor1@example.com',
            password='testpass123',
            profession=1,  # Doctor
            first_name='Dr. John',
            last_name='Smith'
        )
        
        cls.resident = User.objects.create_user(
            username='resident1',
            email='resident1@example.com',
            password='testpass123',
            profession=2,  # Resident
            first_name='Dr. Jane',
            last_name='Doe'
        )

        cls.hospital = Hospital.objects.create(
            name='Integration Test Hospital',
            created_by=cls.doctor,
            updated_by=cls.doctor
        )

        cls.patient = Patient.objects.create(
            name='Integration Test Patient',
            birthday='1985-06-15',
            status=1,  # Outpatient
            created_by=cls.doctor,
            updated_by=cls.doctor
        )

        # Create drug templates
        cls.drug_template1 = DrugTemplate.objects.create(
            name='Paracetamol',
            presentation='500mg comprimidos',
            usage_instructions='Tomar 1 comprimido de 8 em 8 horas em caso de dor ou febre',
            creator=cls.doctor,
            is_public=True
        )

        cls.drug_template2 = DrugTemplate.objects.create(
            name='Ibuprofeno',
            presentation='400mg comprimidos',
            usage_instructions='Tomar 1 comprimido de 8 em 8 horas em caso de dor e inflamação',
            creator=cls.doctor,
            is_public=True
        )

        # Create prescription template
        cls.prescription_template = PrescriptionTemplate.objects.create(
            name='Template para Dor e Febre',
            creator=cls.doctor,
            is_public=True
        )

        PrescriptionTemplateItem.objects.create(
            template=cls.prescription_template,
            drug_name=cls.drug_template1.name,
            presentation=cls.drug_template1.presentation,
            usage_instructions=cls.drug_template1.usage_instructions,
            quantity='20 comprimidos',
            order=1
        )

        PrescriptionTemplateItem.objects.create(
            template=cls.prescription_template,
            drug_name=cls.drug_template2.name,
            presentation=cls.drug_template2.presentation,
            usage_instructions=cls.drug_template2.usage_instructions,
            quantity='15 comprimidos',
            order=2
        )

        # Create sample content
        cls.sample_content = SampleContent.objects.create(
            title='Instruções Padrão para Receitas',
            content='Tomar todos os medicamentos conforme prescrito. Em caso de dúvidas, procurar orientação médica.',
            event_type=Event.OUTPT_PRESCRIPTION_EVENT,
            created_by=cls.doctor,
            updated_by=cls.doctor
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()

    def _setup_session(self, user):
        """Helper method to set up user session with hospital context."""
        self.client.login(username=user.username, password='testpass123')
        session = self.client.session
        session['selected_hospital_id'] = self.hospital.id
        session.save()

    def test_complete_prescription_creation_workflow(self):
        """Test complete workflow from creation to finalization."""
        self._setup_session(self.doctor)

        # Step 1: Access creation form
        response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_create'))
        self.assertEqual(response.status_code, 200)
        
        # Verify form context
        self.assertIn('form', response.context)
        self.assertIn('formset', response.context)
        self.assertIn('sample_contents', response.context)

        # Step 2: Create prescription with items
        create_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Prescrição para dor e febre',
            'instructions': 'Tomar todos os medicamentos conforme orientação médica',
            'status': 'draft',
            'prescription_date': date.today(),
            
            # Formset data
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-drug_name': 'Paracetamol',
            'form-0-presentation': '500mg comprimidos',
            'form-0-usage_instructions': 'Tomar 1 comprimido de 8 em 8 horas se dor ou febre',
            'form-0-quantity': '20 comprimidos',
            'form-0-order': '1',
            
            'form-1-drug_name': 'Ibuprofeno',
            'form-1-presentation': '400mg comprimidos',
            'form-1-usage_instructions': 'Tomar 1 comprimido de 8 em 8 horas se dor intensa',
            'form-1-quantity': '15 comprimidos',
            'form-1-order': '2',
        }
        
        response = self.client.post(
            reverse('outpatientprescriptions:outpatientprescription_create'),
            create_data
        )
        
        # Should redirect after creation
        self.assertEqual(response.status_code, 302)
        
        # Verify prescription was created
        prescription = OutpatientPrescription.objects.get(
            description='Prescrição para dor e febre'
        )
        self.assertEqual(prescription.status, 'draft')
        self.assertEqual(prescription.patient, self.patient)
        self.assertEqual(prescription.created_by, self.doctor)
        self.assertEqual(prescription.items.count(), 2)

        # Step 3: View prescription details
        with patch('apps.core.permissions.utils.can_access_patient', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_detail',
                       kwargs={'pk': prescription.pk})
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['outpatientprescription'], prescription)

        # Step 4: Update prescription status to finalized
        with patch('apps.core.permissions.utils.can_edit_event', return_value=True):
            # Get existing items for formset
            items = prescription.items.all().order_by('order')
            
            update_data = {
                'patient': self.patient.pk,
                'event_datetime': prescription.event_datetime,
                'description': prescription.description,
                'instructions': prescription.instructions,
                'status': 'finalized',  # Change to finalized
                'prescription_date': prescription.prescription_date,
                
                # Formset data for existing items
                'form-TOTAL_FORMS': '2',
                'form-INITIAL_FORMS': '2',
                'form-MIN_NUM_FORMS': '1',
                'form-MAX_NUM_FORMS': '1000',
                
                'form-0-id': str(items[0].pk),
                'form-0-drug_name': items[0].drug_name,
                'form-0-presentation': items[0].presentation,
                'form-0-usage_instructions': items[0].usage_instructions,
                'form-0-quantity': items[0].quantity,
                'form-0-order': items[0].order,
                
                'form-1-id': str(items[1].pk),
                'form-1-drug_name': items[1].drug_name,
                'form-1-presentation': items[1].presentation,
                'form-1-usage_instructions': items[1].usage_instructions,
                'form-1-quantity': items[1].quantity,
                'form-1-order': items[1].order,
            }
            
            response = self.client.post(
                reverse('outpatientprescriptions:outpatientprescription_update',
                       kwargs={'pk': prescription.pk}),
                update_data
            )
            
            self.assertEqual(response.status_code, 302)

        # Step 5: Verify finalized status
        prescription.refresh_from_db()
        self.assertEqual(prescription.status, 'finalized')

        # Step 6: Print prescription
        with patch('apps.core.permissions.utils.can_access_patient', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_print',
                       kwargs={'pk': prescription.pk})
            )
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'outpatientprescriptions/outpatientprescription_print.html')

    def test_prescription_template_integration_workflow(self):
        """Test workflow using prescription templates."""
        self._setup_session(self.doctor)

        # Step 1: Create prescription using template data (simulated)
        # In real implementation, this would happen via JavaScript/AJAX
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description=f'Receita baseada em template: {self.prescription_template.name}',
            instructions='Instruções gerais da receita',
            status='draft',
            prescription_date=date.today(),
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor
        )

        # Step 2: Copy items from template
        prescription.copy_from_prescription_template(self.prescription_template)

        # Step 3: Verify items were copied correctly
        items = prescription.items.all().order_by('order')
        self.assertEqual(items.count(), 2)
        
        item1 = items[0]
        self.assertEqual(item1.drug_name, 'Paracetamol')
        self.assertEqual(item1.presentation, '500mg comprimidos')
        self.assertEqual(item1.quantity, '20 comprimidos')
        
        item2 = items[1]
        self.assertEqual(item2.drug_name, 'Ibuprofeno')
        self.assertEqual(item2.presentation, '400mg comprimidos')
        self.assertEqual(item2.quantity, '15 comprimidos')

        # Step 4: Verify data independence
        # Modify template item
        template_item = self.prescription_template.items.first()
        original_drug_name = template_item.drug_name
        template_item.drug_name = 'Modified Drug Name'
        template_item.save()

        # Prescription items should remain unchanged
        item1.refresh_from_db()
        self.assertEqual(item1.drug_name, original_drug_name)

    def test_drug_template_usage_count_workflow(self):
        """Test that drug template usage count is updated correctly."""
        self._setup_session(self.doctor)

        # Step 1: Check initial usage count
        initial_count = self.drug_template1.usage_count
        
        # Step 2: Create prescription item using drug template
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Test prescription for usage count',
            instructions='Test instructions',
            status='draft',
            prescription_date=date.today(),
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor
        )

        # Create item and copy from template
        item = PrescriptionItem(
            prescription=prescription,
            quantity='30 comprimidos',
            order=1
        )
        item.copy_from_drug_template(self.drug_template1)
        item.save()

        # Step 3: Verify usage count was incremented
        self.drug_template1.refresh_from_db()
        self.assertEqual(self.drug_template1.usage_count, initial_count + 1)

        # Step 4: Verify item references template
        self.assertEqual(item.source_template, self.drug_template1)

    def test_multi_user_prescription_workflow(self):
        """Test workflow with multiple users (doctor and resident)."""
        # Step 1: Doctor creates prescription
        self._setup_session(self.doctor)
        
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Prescription by doctor',
            instructions='Doctor instructions',
            status='draft',
            prescription_date=date.today(),
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor
        )

        PrescriptionItem.objects.create(
            prescription=prescription,
            drug_name='Doctor Drug',
            presentation='10mg tablet',
            usage_instructions='Take as needed',
            quantity='30',
            order=1
        )

        # Step 2: Resident views prescription (if they have access)
        self._setup_session(self.resident)
        
        with patch('apps.core.permissions.utils.can_access_patient', return_value=True):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_detail',
                       kwargs={'pk': prescription.pk})
            )
            self.assertEqual(response.status_code, 200)

        # Step 3: Test permission restrictions
        with patch('apps.core.permissions.utils.can_edit_event', return_value=False):
            response = self.client.get(
                reverse('outpatientprescriptions:outpatientprescription_update',
                       kwargs={'pk': prescription.pk})
            )
            self.assertEqual(response.status_code, 404)

    def test_prescription_search_and_filtering_workflow(self):
        """Test search and filtering functionality workflow."""
        self._setup_session(self.doctor)

        # Step 1: Create multiple prescriptions
        prescription1 = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Antibiotics prescription',
            instructions='Complete the course',
            status='finalized',
            prescription_date=date.today(),
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor
        )

        prescription2 = OutpatientPrescription.objects.create(
            event_datetime=timezone.now() - timedelta(days=1),
            description='Pain relief prescription',
            instructions='Take as needed',
            status='draft',
            prescription_date=date.today() - timedelta(days=1),
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor
        )

        # Step 2: Test search functionality
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_list'),
            {'search': 'Antibiotics'}
        )
        self.assertEqual(response.status_code, 200)
        prescriptions = response.context['prescriptions']
        self.assertIn(prescription1, prescriptions)

        # Step 3: Test status filter
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_list'),
            {'status': 'finalized'}
        )
        self.assertEqual(response.status_code, 200)
        prescriptions = response.context['prescriptions']
        for prescription in prescriptions:
            self.assertEqual(prescription.status, 'finalized')

        # Step 4: Test date filter
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_list'),
            {
                'date_start': (date.today() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'date_end': date.today().strftime('%Y-%m-%d')
            }
        )
        self.assertEqual(response.status_code, 200)

    def test_prescription_deletion_cascade_workflow(self):
        """Test that prescription deletion properly cascades to items."""
        self._setup_session(self.doctor)

        # Step 1: Create prescription with items
        prescription = OutpatientPrescription.objects.create(
            event_datetime=timezone.now(),
            description='Prescription for deletion test',
            instructions='Test instructions',
            status='draft',
            prescription_date=date.today(),
            patient=self.patient,
            created_by=self.doctor,
            updated_by=self.doctor
        )

        item1 = PrescriptionItem.objects.create(
            prescription=prescription,
            drug_name='Test Drug 1',
            presentation='10mg tablet',
            usage_instructions='Take 1 daily',
            quantity='30',
            order=1
        )

        item2 = PrescriptionItem.objects.create(
            prescription=prescription,
            drug_name='Test Drug 2',
            presentation='20mg tablet',
            usage_instructions='Take 2 daily',
            quantity='60',
            order=2
        )

        prescription_id = prescription.id
        item1_id = item1.id
        item2_id = item2.id

        # Step 2: Delete prescription
        with patch('apps.core.permissions.utils.can_delete_event', return_value=True):
            response = self.client.post(
                reverse('outpatientprescriptions:outpatientprescription_delete',
                       kwargs={'pk': prescription.pk})
            )
            self.assertEqual(response.status_code, 302)

        # Step 3: Verify prescription and items were deleted
        self.assertFalse(OutpatientPrescription.objects.filter(id=prescription_id).exists())
        self.assertFalse(PrescriptionItem.objects.filter(id=item1_id).exists())
        self.assertFalse(PrescriptionItem.objects.filter(id=item2_id).exists())


class PrescriptionListPerformanceTest(TestCase):
    """Test performance aspects of prescription lists."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data with multiple prescriptions."""
        cls.user = User.objects.create_user(
            username='perfuser',
            email='perf@example.com',
            password='testpass123',
            profession=1  # Doctor
        )

        cls.hospital = Hospital.objects.create(
            name='Performance Test Hospital',
            created_by=cls.user,
            updated_by=cls.user
        )

        # Create multiple patients
        cls.patients = []
        for i in range(10):
            patient = Patient.objects.create(
                name=f'Patient {i}',
                birthday='1990-01-01',
                status=1,
                created_by=cls.user,
                updated_by=cls.user
            )
            cls.patients.append(patient)

        # Create multiple prescriptions
        for i, patient in enumerate(cls.patients):
            OutpatientPrescription.objects.create(
                event_datetime=timezone.now() - timedelta(days=i),
                description=f'Prescription {i}',
                instructions=f'Instructions {i}',
                status='draft' if i % 2 == 0 else 'finalized',
                prescription_date=date.today() - timedelta(days=i),
                patient=patient,
                created_by=cls.user,
                updated_by=cls.user
            )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username='perfuser', password='testpass123')
        session = self.client.session
        session['selected_hospital_id'] = self.hospital.id
        session.save()

    def test_list_view_query_count(self):
        """Test that list view doesn't generate excessive queries."""
        with self.assertNumQueries(10):  # Adjust based on actual query optimization
            response = self.client.get(reverse('outpatientprescriptions:outpatientprescription_list'))
            self.assertEqual(response.status_code, 200)

    def test_pagination_performance(self):
        """Test pagination performance."""
        # Test first page
        response = self.client.get(
            reverse('outpatientprescriptions:outpatientprescription_list'),
            {'page': 1}
        )
        self.assertEqual(response.status_code, 200)
        
        # Test that pagination context is available
        self.assertIn('is_paginated', response.context)
        self.assertIn('page_obj', response.context)


class PrescriptionFormValidationWorkflowTest(TestCase):
    """Test form validation workflows."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='validuser',
            email='valid@example.com',
            password='testpass123',
            profession=1  # Doctor
        )

        cls.hospital = Hospital.objects.create(
            name='Validation Test Hospital',
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.patient = Patient.objects.create(
            name='Validation Test Patient',
            birthday='1990-01-01',
            status=1,
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username='validuser', password='testpass123')
        session = self.client.session
        session['selected_hospital_id'] = self.hospital.id
        session.save()

    def test_form_validation_error_workflow(self):
        """Test complete workflow with form validation errors."""
        # Step 1: Submit form with missing required fields
        invalid_data = {
            'patient': '',  # Missing patient
            'description': '',  # Missing description
            'instructions': 'Some instructions',
            'status': 'draft',
            'prescription_date': date.today(),
            
            # Valid formset data
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-drug_name': 'Test Drug',
            'form-0-presentation': '10mg tablet',
            'form-0-usage_instructions': 'Take daily',
            'form-0-quantity': '30',
            'form-0-order': '1',
        }
        
        response = self.client.post(
            reverse('outpatientprescriptions:outpatientprescription_create'),
            invalid_data
        )
        
        # Step 2: Should stay on form page with errors
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'patient', 'This field is required.')
        self.assertFormError(response, 'form', 'description', 'This field is required.')

        # Step 3: Submit with invalid formset
        invalid_formset_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Valid description',
            'instructions': 'Valid instructions',
            'status': 'draft',
            'prescription_date': date.today(),
            
            # Invalid formset data
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-drug_name': '',  # Missing required field
            'form-0-presentation': '',  # Missing required field
            'form-0-usage_instructions': '',  # Missing required field
            'form-0-quantity': '',  # Missing required field
            'form-0-order': '1',
        }
        
        response = self.client.post(
            reverse('outpatientprescriptions:outpatientprescription_create'),
            invalid_formset_data
        )
        
        # Should stay on form page with formset errors
        self.assertEqual(response.status_code, 200)
        formset = response.context['formset']
        self.assertFalse(formset.is_valid())

        # Step 4: Submit with valid data
        valid_data = {
            'patient': self.patient.pk,
            'event_datetime': timezone.now(),
            'description': 'Valid prescription',
            'instructions': 'Valid instructions',
            'status': 'draft',
            'prescription_date': date.today(),
            
            # Valid formset data
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '1',
            'form-MAX_NUM_FORMS': '1000',
            
            'form-0-drug_name': 'Valid Drug',
            'form-0-presentation': '10mg tablet',
            'form-0-usage_instructions': 'Take as prescribed',
            'form-0-quantity': '30 tablets',
            'form-0-order': '1',
        }
        
        response = self.client.post(
            reverse('outpatientprescriptions:outpatientprescription_create'),
            valid_data
        )
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Verify prescription was created
        self.assertTrue(
            OutpatientPrescription.objects.filter(
                description='Valid prescription'
            ).exists()
        )