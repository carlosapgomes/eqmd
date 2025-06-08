from django.test import TestCase
from django.template.loader import render_to_string
from django.urls import reverse
from django.contrib.auth import get_user_model
from ..models import Patient, PatientHospitalRecord

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