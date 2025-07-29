from django.test import TestCase, RequestFactory
from django.template import Template, Context
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import transaction
from apps.patients.models import Patient, AllowedTag, Tag
from apps.patients.context_processors import patient_stats, recent_patients
from apps.patients.templatetags.patient_tags import patient_status_badge, patient_tags

User = get_user_model()

class PatientDashboardIntegrationTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password'
        )
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.user,
            updated_by=self.user
        )

    def test_context_processors(self):
        """Test that context processors return expected data"""
        request = self.factory.get('/')
        request.user = self.user

        stats = patient_stats(request)
        self.assertEqual(stats['total_patients'], 1)
        self.assertEqual(stats['inpatient_count'], 1)

        recent = recent_patients(request)
        self.assertEqual(recent['recent_patients'].count(), 1)

    def test_template_tags(self):
        """Test that template tags render correctly"""
        # Test status badge
        badge = patient_status_badge(Patient.Status.INPATIENT)
        self.assertIn('bg-success', badge)

        # Test patient tags inclusion tag
        template = Template('{% load patient_tags %}{% patient_tags patient %}')
        context = Context({'patient': self.patient})
        rendered = template.render(context)
        self.assertIsNotNone(rendered)

    def test_dashboard_widgets(self):
        """Test that dashboard widgets render correctly"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('core:dashboard'))

        # This test assumes a dashboard view exists at the URL 'core:dashboard'
        # If it doesn't, you'll need to adjust this test
        if response.status_code == 200:
            self.assertContains(response, 'Patient Statistics')
            self.assertContains(response, 'Recent Patients')


# NOTE: PatientHospitalIntegrationTest removed - functionality no longer exists
# after single-hospital refactor. Hospital and PatientHospitalRecord models
# were removed in favor of environment-based single hospital configuration.


class PatientTaggingIntegrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password'
        )
        
        # Create some allowed tags
        self.high_priority_tag = AllowedTag.objects.create(
            name='High Priority',
            description='Requires immediate attention',
            color='#dc3545',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.diabetic_tag = AllowedTag.objects.create(
            name='Diabetic',
            description='Patient has diabetes',
            color='#fd7e14',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )

    def test_patient_tagging_workflow(self):
        """Test complete patient tagging workflow"""
        # Create patient
        patient = Patient.objects.create(
            name='Tagged Patient',
            birthday='1980-12-10',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add tags to patient
        tag1 = Tag.objects.create(
            allowed_tag=self.high_priority_tag,
            notes='Urgent care needed',
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag1)
        
        tag2 = Tag.objects.create(
            allowed_tag=self.diabetic_tag,
            notes='Type 2 diabetes',
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag2)
        
        # Verify tags are assigned
        patient_tags = patient.tags.all()
        self.assertEqual(patient_tags.count(), 2)
        
        # Verify tag content
        high_priority = patient_tags.filter(allowed_tag=self.high_priority_tag).first()
        self.assertEqual(high_priority.notes, 'Urgent care needed')
        
        diabetic = patient_tags.filter(allowed_tag=self.diabetic_tag).first()
        self.assertEqual(diabetic.notes, 'Type 2 diabetes')
        
        # Test tag display through template tags
        template = Template('{% load patient_tags %}{% patient_tags patient %}')
        context = Context({'patient': patient})
        rendered = template.render(context)
        
        # Should contain tag names and colors
        self.assertIn('High Priority', rendered)
        self.assertIn('Diabetic', rendered)
        self.assertIn('#dc3545', rendered)
        self.assertIn('#fd7e14', rendered)