from django.test import TestCase
from django.template.loader import render_to_string
from django.urls import reverse
from django.contrib.auth import get_user_model
from ..models import Patient

User = get_user_model()


class TemplateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_template_existence(self):
        """Test that all required templates exist"""
        templates = [
            'patients/patient_base.html',
            'patients/patient_list.html',
            'patients/patient_detail.html',
            'patients/patient_form.html',
            'patients/hospital_record_form.html',
            'patients/patient_confirm_delete.html',
            'patients/hospital_record_confirm_delete.html',
        ]

        for template in templates:
            try:
                context = {'request': None}
                if 'detail' in template:
                    context['patient'] = self.patient
                elif 'form' in template and 'record' not in template:
                    # Skip form templates as they need forms
                    continue
                elif 'form' in template:
                    # Skip hospital record form templates as they need forms
                    continue
                elif 'record' in template and 'confirm_delete' in template:
                    # Create a mock hospital record for delete template
                    context['object'] = type('MockRecord', (), {
                        'patient': self.patient,
                        'hospital': type('MockHospital', (), {'name': 'Test Hospital'})()
                    })()
                elif 'confirm_delete' in template:
                    context['object'] = self.patient
                render_to_string(template, context)
            except Exception as e:
                self.fail(f"Template {template} failed to render: {e}")

    def test_template_inheritance(self):
        """Test that templates properly extend base templates"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('patients:patient_list'))
        self.assertTemplateUsed(response, 'patients/patient_base.html')
        self.assertTemplateUsed(response, 'patients/patient_list.html')

    def test_template_context_variables(self):
        """Test that templates receive expected context variables"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('patients:patient_detail', kwargs={'pk': self.patient.pk}))
        self.assertEqual(response.context['patient'], self.patient)

    def test_patient_detail_gender_display(self):
        """Test that patient detail template displays gender correctly"""
        self.client.force_login(self.user)
        
        # Test each gender choice
        gender_tests = [
            (Patient.GenderChoices.MALE, 'Masculino'),
            (Patient.GenderChoices.FEMALE, 'Feminino'),
            (Patient.GenderChoices.OTHER, 'Outro'),
            (Patient.GenderChoices.NOT_INFORMED, 'Não Informado'),
        ]
        
        for gender_value, expected_label in gender_tests:
            self.patient.gender = gender_value
            self.patient.save()
            
            response = self.client.get(
                reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, expected_label)

    def test_patient_form_gender_field_rendering(self):
        """Test that patient form template renders gender field correctly"""
        self.client.force_login(self.user)
        
        # Test create form
        response = self.client.get(reverse('patients:patient_create'))
        self.assertEqual(response.status_code, 200)
        
        # Should contain gender field options
        self.assertContains(response, 'Masculino')
        self.assertContains(response, 'Feminino') 
        self.assertContains(response, 'Outro')
        self.assertContains(response, 'Não Informado')
        
        # Test update form
        response = self.client.get(
            reverse('patients:patient_update', kwargs={'pk': self.patient.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # Should contain gender field options
        self.assertContains(response, 'Masculino')
        self.assertContains(response, 'Feminino')
        self.assertContains(response, 'Outro')
        self.assertContains(response, 'Não Informado')

    def test_patient_list_template_with_gender(self):
        """Test that patient list template works with patients having different genders"""
        self.client.force_login(self.user)
        
        # Create patients with different genders
        Patient.objects.create(
            name='Male Patient',
            birthday='1990-01-01',
            gender=Patient.GenderChoices.MALE,
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        Patient.objects.create(
            name='Female Patient',
            birthday='1990-01-01',
            gender=Patient.GenderChoices.FEMALE,
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        response = self.client.get(reverse('patients:patient_list'))
        self.assertEqual(response.status_code, 200)
        
        # Should display all patients regardless of gender
        self.assertContains(response, 'Male Patient')
        self.assertContains(response, 'Female Patient')
        self.assertContains(response, 'Test Patient')  # Default patient from setUpTestData

    def test_gender_field_accessibility(self):
        """Test that gender field has proper accessibility attributes"""
        self.client.force_login(self.user)
        
        response = self.client.get(reverse('patients:patient_create'))
        self.assertEqual(response.status_code, 200)
        
        # Check for proper labeling of gender field
        # The exact HTML structure will depend on form widget implementation
        # but should contain proper label association
        content = response.content.decode()
        self.assertIn('gender', content.lower())
        
        # Test that form is accessible
        self.assertContains(response, 'name="gender"')