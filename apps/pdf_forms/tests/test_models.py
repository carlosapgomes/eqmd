from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.patients.models import Patient
from apps.pdf_forms.models import PDFFormTemplate, PDFFormSubmission
from apps.events.models import Event
from apps.pdf_forms.tests.factories import PDFFormTemplateFactory, PDFFormSubmissionFactory, UserFactory, PatientFactory

User = get_user_model()


class PDFFormTemplateTests(TestCase):
    
    def setUp(self):
        self.user = UserFactory()

    def test_create_pdf_form_template(self):
        """Test creating a PDF form template."""
        template = PDFFormTemplateFactory(created_by=self.user)
        self.assertTrue(template.is_active)
        self.assertEqual(template.created_by, self.user)
        self.assertTrue(template.hospital_specific)
        self.assertIsInstance(template.form_fields, dict)

    def test_pdf_form_template_str_representation(self):
        """Test string representation of PDF form template."""
        template = PDFFormTemplateFactory(name="Test Form", created_by=self.user)
        self.assertEqual(str(template), "Test Form")

    def test_pdf_form_template_ordering(self):
        """Test templates are ordered by name."""
        template_b = PDFFormTemplateFactory(name="B Form", created_by=self.user)
        template_a = PDFFormTemplateFactory(name="A Form", created_by=self.user)
        
        templates = PDFFormTemplate.objects.all()
        self.assertEqual(templates[0], template_a)
        self.assertEqual(templates[1], template_b)

    def test_pdf_form_template_form_fields_default(self):
        """Test that form_fields defaults to empty dict."""
        template = PDFFormTemplateFactory(
            name="Test Template",
            created_by=self.user,
            form_fields={}
        )
        self.assertEqual(template.form_fields, {})

    def test_pdf_form_template_json_field_validation(self):
        """Test that form_fields accepts valid JSON."""
        valid_config = {
            'patient_name': {
                'type': 'text',
                'required': True,
                'label': 'Patient Name',
                'x': 5.0,
                'y': 10.0,
                'width': 8.0,
                'height': 0.7
            }
        }
        
        template = PDFFormTemplateFactory(
            form_fields=valid_config,
            created_by=self.user
        )
        self.assertEqual(template.form_fields, valid_config)


class PDFFormSubmissionTests(TestCase):
    
    def setUp(self):
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user)
        self.template = PDFFormTemplateFactory(created_by=self.user)

    def test_create_pdf_form_submission(self):
        """Test creating a PDF form submission."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        
        self.assertEqual(submission.form_template, self.template)
        self.assertEqual(submission.patient, self.patient)
        self.assertEqual(submission.created_by, self.user)
        self.assertEqual(submission.event_type, Event.PDF_FORM_EVENT)

    def test_pdf_form_submission_str_representation(self):
        """Test string representation of PDF form submission."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        expected_str = f"{self.template.name} - {self.patient.name}"
        self.assertEqual(str(submission), expected_str)

    def test_pdf_form_submission_get_absolute_url(self):
        """Test get_absolute_url method."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        expected_url = f"/pdf-forms/submission/{submission.pk}/"
        self.assertEqual(submission.get_absolute_url(), expected_url)

    def test_pdf_form_submission_form_data_storage(self):
        """Test that form data is properly stored as JSON."""
        form_data = {
            'patient_name': 'John Doe',
            'date_of_birth': '1990-01-01',
            'clinical_notes': 'Test notes'
        }
        
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            form_data=form_data
        )
        
        self.assertEqual(submission.form_data, form_data)

    def test_pdf_form_submission_inherits_event_fields(self):
        """Test that PDFFormSubmission inherits Event model fields."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user
        )
        
        # Test Event model inherited fields
        self.assertIsNotNone(submission.id)  # UUID field
        self.assertIsNotNone(submission.event_datetime)
        self.assertIsNotNone(submission.description)
        self.assertIsNotNone(submission.created_at)
        self.assertIsNotNone(submission.updated_at)

    def test_pdf_form_submission_file_metadata(self):
        """Test file metadata fields."""
        submission = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            original_filename="test_form.pdf",
            file_size=2048
        )
        
        self.assertEqual(submission.original_filename, "test_form.pdf")
        self.assertEqual(submission.file_size, 2048)


class PDFFormModelIntegrationTests(TestCase):
    """Test integration between PDF form models and other app models."""
    
    def setUp(self):
        self.user = UserFactory()
        self.patient = PatientFactory(created_by=self.user)

    def test_template_patient_relationship(self):
        """Test that templates can be used with multiple patients."""
        template = PDFFormTemplateFactory(created_by=self.user)
        patient2 = PatientFactory(created_by=self.user)
        
        submission1 = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=self.user
        )
        
        submission2 = PDFFormSubmissionFactory(
            form_template=template,
            patient=patient2,
            created_by=self.user
        )
        
        # Same template used for different patients
        self.assertEqual(submission1.form_template, template)
        self.assertEqual(submission2.form_template, template)
        self.assertNotEqual(submission1.patient, submission2.patient)

    def test_patient_multiple_submissions(self):
        """Test that a patient can have multiple PDF form submissions."""
        template1 = PDFFormTemplateFactory(name="Form 1", created_by=self.user)
        template2 = PDFFormTemplateFactory(name="Form 2", created_by=self.user)
        
        submission1 = PDFFormSubmissionFactory(
            form_template=template1,
            patient=self.patient,
            created_by=self.user
        )
        
        submission2 = PDFFormSubmissionFactory(
            form_template=template2,
            patient=self.patient,
            created_by=self.user
        )
        
        # Same patient, different forms
        self.assertEqual(submission1.patient, self.patient)
        self.assertEqual(submission2.patient, self.patient)
        self.assertNotEqual(submission1.form_template, submission2.form_template)

    def test_user_permissions_integration(self):
        """Test integration with user permissions."""
        template = PDFFormTemplateFactory(created_by=self.user)
        submission = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=self.user
        )
        
        # Test that created_by is properly set
        self.assertEqual(template.created_by, self.user)
        self.assertEqual(submission.created_by, self.user)
        
        # Test that patient creator and submission creator can be different
        other_user = UserFactory()
        submission2 = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=other_user
        )
        
        self.assertNotEqual(submission2.created_by, self.patient.created_by)

    def test_template_deactivation_effect(self):
        """Test that deactivating a template doesn't affect existing submissions."""
        template = PDFFormTemplateFactory(created_by=self.user, is_active=True)
        submission = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=self.user
        )
        
        # Deactivate template
        template.is_active = False
        template.save()
        
        # Submission should still exist and reference the template
        submission.refresh_from_db()
        self.assertEqual(submission.form_template, template)
        self.assertFalse(submission.form_template.is_active)