"""
Tests for PDF form duplication eligibility service.

Covers:
- Template-level duplication eligibility rules
- Submission-level duplication eligibility rules
- APAC and AIH exclusion
- Permission checks
"""
from django.test import TestCase
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from apps.pdf_forms.tests.factories import (
    PDFFormTemplateFactory,
    PDFFormSubmissionFactory,
    UserFactory,
    PatientFactory,
)
from apps.pdf_forms.models import PDFFormSubmission
from apps.pdf_forms.services.duplication import (
    is_template_duplication_supported,
    can_duplicate_pdf_submission,
    build_duplicate_initial_data,
)
from apps.events.models import Event
from django.test import Client
from django.urls import reverse
from unittest.mock import patch, MagicMock


class TemplateDuplicationEligibilityTests(TestCase):
    """Tests for is_template_duplication_supported."""

    def test_template_duplication_is_disabled_by_default(self):
        """New templates must have duplication disabled by default."""
        template = PDFFormTemplateFactory(
            form_type="HOSPITAL",
            is_active=True,
        )
        self.assertFalse(template.allow_duplication)

    def test_hospital_template_with_opt_in_supports_duplication(self):
        """Active HOSPITAL template with allow_duplication=True supports duplication."""
        template = PDFFormTemplateFactory(
            form_type="HOSPITAL",
            is_active=True,
            allow_duplication=True,
        )
        self.assertTrue(is_template_duplication_supported(template))

    def test_apac_template_with_opt_in_does_not_support_duplication(self):
        """APAC template never supports duplication even if opt-in is enabled."""
        template = PDFFormTemplateFactory(
            form_type="APAC",
            is_active=True,
            allow_duplication=True,
        )
        self.assertFalse(is_template_duplication_supported(template))

    def test_aih_template_with_opt_in_does_not_support_duplication(self):
        """AIH template never supports duplication even if opt-in is enabled."""
        template = PDFFormTemplateFactory(
            form_type="AIH",
            is_active=True,
            allow_duplication=True,
        )
        self.assertFalse(is_template_duplication_supported(template))

    def test_inactive_hospital_template_does_not_support_duplication(self):
        """Inactive HOSPITAL template does not support duplication even with opt-in."""
        template = PDFFormTemplateFactory(
            form_type="HOSPITAL",
            is_active=False,
            allow_duplication=True,
        )
        self.assertFalse(is_template_duplication_supported(template))


class SubmissionDuplicationEligibilityTests(TestCase):
    """Tests for can_duplicate_pdf_submission."""

    def setUp(self):
        """Set up common test data."""
        self.patient = PatientFactory()
        self.user = UserFactory()
        # Give user the events.add_event permission
        content_type = ContentType.objects.get_for_model(Event)
        add_event_perm = Permission.objects.get(
            content_type=content_type,
            codename="add_event",
        )
        self.user.user_permissions.add(add_event_perm)

    def test_submission_duplication_requires_template_support_and_add_event_permission(self):
        """Submission duplication requires template support AND events.add_event permission."""
        template = PDFFormTemplateFactory(
            form_type="HOSPITAL",
            is_active=True,
            allow_duplication=True,
        )
        submission = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=self.user,
        )
        self.assertTrue(
            can_duplicate_pdf_submission(self.user, submission),
        )

    def test_submission_duplication_fails_without_add_event_permission(self):
        """Submission duplication fails when user lacks events.add_event."""
        user_no_perm = UserFactory()
        template = PDFFormTemplateFactory(
            form_type="HOSPITAL",
            is_active=True,
            allow_duplication=True,
        )
        submission = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=user_no_perm,
        )
        self.assertFalse(
            can_duplicate_pdf_submission(user_no_perm, submission),
        )

    def test_submission_duplication_fails_for_apac_template(self):
        """Submission duplication fails for APAC templates."""
        template = PDFFormTemplateFactory(
            form_type="APAC",
            is_active=True,
            allow_duplication=True,
        )
        submission = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=self.user,
        )
        self.assertFalse(
            can_duplicate_pdf_submission(self.user, submission),
        )

    def test_submission_duplication_fails_for_inactive_template(self):
        """Submission duplication fails for inactive templates."""
        template = PDFFormTemplateFactory(
            form_type="HOSPITAL",
            is_active=False,
            allow_duplication=True,
        )
        submission = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=self.user,
        )
        self.assertFalse(
            can_duplicate_pdf_submission(self.user, submission),
        )

    def test_submission_duplication_fails_without_opt_in(self):
        """Submission duplication fails when template opt-in is disabled."""
        template = PDFFormTemplateFactory(
            form_type="HOSPITAL",
            is_active=True,
            allow_duplication=False,
        )
        submission = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=self.user,
        )
        self.assertFalse(
            can_duplicate_pdf_submission(self.user, submission),
        )


class PDFFormSubmissionDuplicateViewTests(TestCase):
    """Tests for the PDFFormSubmissionDuplicate view."""

    def setUp(self):
        """Set up common test data."""
        self.client = Client()
        self.user = UserFactory()
        self.patient = PatientFactory()
        self.template = PDFFormTemplateFactory(
            form_type="HOSPITAL",
            is_active=True,
            allow_duplication=True,
        )
        self.source_data = {
            'patient_name': self.patient.name,
            'clinical_notes': 'Original clinical notes',
            'blood_type': 'O+',
        }
        self.source = PDFFormSubmissionFactory(
            form_template=self.template,
            patient=self.patient,
            created_by=self.user,
            form_data=self.source_data,
        )
        # Give user events.add_event permission
        content_type = ContentType.objects.get_for_model(Event)
        add_event_perm = Permission.objects.get(
            content_type=content_type,
            codename="add_event",
        )
        self.user.user_permissions.add(add_event_perm)
        self.client.force_login(self.user)

    def _duplicate_url(self, submission):
        """Helper to build duplicate URL for a submission."""
        return reverse(
            'pdf_forms:submission_duplicate',
            kwargs={'pk': submission.pk},
        )

    @patch(
        'apps.pdf_forms.services.form_generator.DynamicFormGenerator.generate_form_class'
    )
    def test_duplicate_get_prefills_form_from_source_submission(
        self,
        mock_generate_form,
    ):
        """
        GET request to duplicate view should render a prefilled form
        with values from the source submission form_data.
        """
        mock_form_class = MagicMock()
        mock_form_instance = MagicMock()
        mock_form_instance.fields = {}
        mock_form_instance.initial = {}
        mock_form_class.return_value = mock_form_instance
        mock_generate_form.return_value = mock_form_class

        url = self._duplicate_url(self.source)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form_template'],
            self.template,
        )
        self.assertEqual(response.context['patient'], self.patient)
        self.assertIn('is_duplicate', response.context)
        self.assertTrue(response.context['is_duplicate'])
        self.assertIn('source_submission', response.context)
        self.assertEqual(
            response.context['source_submission'],
            self.source,
        )

    @patch(
        'apps.pdf_forms.services.form_generator.DynamicFormGenerator.generate_form_class'
    )
    def test_duplicate_get_initializes_procedure_display_field(
        self,
        mock_generate_form,
    ):
        """
        When the source has procedure_code and procedure_description,
        the procedure display field should be initialized as
        'CODE - Description'.
        """
        procedure_template = PDFFormTemplateFactory(
            form_type="HOSPITAL",
            is_active=True,
            allow_duplication=True,
            form_fields={
                'procedure_code': {
                    'type': 'text',
                    'required': True,
                    'label': 'Código',
                },
                'procedure_description': {
                    'type': 'text',
                    'required': True,
                    'label': 'Descrição',
                },
            },
        )
        procedure_source = PDFFormSubmissionFactory(
            form_template=procedure_template,
            patient=self.patient,
            created_by=self.user,
            form_data={
                'procedure_code': '12345',
                'procedure_description': 'Appendectomy',
                'patient_name': self.patient.name,
            },
        )

        # Build a proper mock form class with required attributes
        mock_form_class = MagicMock()
        mock_form_class.base_fields = {
            'procedure_code': MagicMock(),
            'procedure_description': MagicMock(),
        }
        mock_form_class._procedure_search_config = {
            'display_field': 'procedure_display',
            'code_field': 'procedure_code',
            'description_field': 'procedure_description',
            'required': True,
            'label': 'Procedimento',
            'help_text': 'Digite o código ou descrição',
        }
        mock_form_class._patient_initial_values = {}

        result = build_duplicate_initial_data(
            mock_form_class,
            procedure_source.form_data,
        )
        self.assertEqual(
            result.get('procedure_display'),
            '12345 - Appendectomy',
        )
        self.assertEqual(result.get('procedure_code'), '12345')
        self.assertEqual(
            result.get('procedure_description'),
            'Appendectomy',
        )

    @patch(
        'apps.pdf_forms.services.form_generator.DynamicFormGenerator.generate_form_class'
    )
    def test_duplicate_post_creates_new_submission_for_same_template_and_patient(
        self,
        mock_generate_form,
    ):
        """POST to duplicate view should create a new submission."""
        mock_form_class = MagicMock()
        mock_form_instance = MagicMock()
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'patient_name': self.patient.name,
            'clinical_notes': 'Updated notes',
        }
        mock_form_class.return_value = mock_form_instance
        mock_generate_form.return_value = mock_form_class

        url = self._duplicate_url(self.source)

        initial_count = PDFFormSubmission.objects.count()

        # Mock sanitize to avoid validation issues
        with patch(
            'apps.pdf_forms.security.PDFFormSecurity.sanitize_form_data',
            return_value=mock_form_instance.cleaned_data,
        ):
            response = self.client.post(url, {'patient_name': 'Test'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            PDFFormSubmission.objects.count(),
            initial_count + 1,
        )

        new_submission = PDFFormSubmission.objects.exclude(
            pk=self.source.pk
        ).first()
        self.assertIsNotNone(new_submission)
        self.assertEqual(
            new_submission.form_template,
            self.template,
        )
        self.assertEqual(new_submission.patient, self.patient)

    @patch(
        'apps.pdf_forms.services.form_generator.DynamicFormGenerator.generate_form_class'
    )
    def test_duplicate_post_does_not_modify_source_submission(
        self,
        mock_generate_form,
    ):
        """
        After a duplicate POST, the source submission form_data must
        remain unchanged.
        """
        mock_form_class = MagicMock()
        mock_form_instance = MagicMock()
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.cleaned_data = {
            'patient_name': 'New Name',
            'clinical_notes': 'New notes',
        }
        mock_form_class.return_value = mock_form_instance
        mock_generate_form.return_value = mock_form_class

        original_source_data = dict(self.source.form_data)

        url = self._duplicate_url(self.source)

        with patch(
            'apps.pdf_forms.security.PDFFormSecurity.sanitize_form_data',
            return_value=mock_form_instance.cleaned_data,
        ):
            self.client.post(url, {'patient_name': 'New Name'})

        self.source.refresh_from_db()
        self.assertEqual(
            self.source.form_data,
            original_source_data,
        )

    def test_duplicate_get_rejects_apac_submission(self):
        """
        GET to duplicate view must reject APAC submissions with 403
        even if allow_duplication is True.
        """
        apac_template = PDFFormTemplateFactory(
            form_type="APAC",
            is_active=True,
            allow_duplication=True,
        )
        apac_submission = PDFFormSubmissionFactory(
            form_template=apac_template,
            patient=self.patient,
            created_by=self.user,
        )

        url = self._duplicate_url(apac_submission)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_duplicate_get_rejects_hospital_submission_without_template_opt_in(
        self,
    ):
        """
        GET to duplicate view must reject hospital submissions whose
        template does not have allow_duplication enabled.
        """
        template_no_optin = PDFFormTemplateFactory(
            form_type="HOSPITAL",
            is_active=True,
            allow_duplication=False,
        )
        ineligible_submission = PDFFormSubmissionFactory(
            form_template=template_no_optin,
            patient=self.patient,
            created_by=self.user,
        )

        url = self._duplicate_url(ineligible_submission)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_duplicate_get_with_real_dynamic_form_prefills_source_values(
        self,
    ):
        """
        Integration test: GET to duplicate view with real
        DynamicFormGenerator (no mock). The form must render with
        initial values from the source submission form_data.
        """
        template = PDFFormTemplateFactory(
            form_type="HOSPITAL",
            is_active=True,
            allow_duplication=True,
            form_fields={
                'patient_name': {
                    'type': 'text',
                    'required': True,
                    'label': 'Patient Name',
                },
                'surgery_date': {
                    'type': 'date',
                    'required': True,
                    'label': 'Surgery Date',
                },
                'clinical_notes': {
                    'type': 'textarea',
                    'required': False,
                    'label': 'Clinical Notes',
                },
            },
        )
        source_form_data = {
            'patient_name': 'John Doe',
            'surgery_date': '2025-06-01',
            'clinical_notes': 'Pre-operative assessment completed',
        }
        source = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=self.user,
            form_data=source_form_data,
        )

        url = self._duplicate_url(source)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form_template'], template)
        self.assertEqual(response.context['patient'], self.patient)
        self.assertTrue(response.context['is_duplicate'])
        self.assertEqual(response.context['source_submission'], source)

        form = response.context['form']
        self.assertIsNotNone(form)
        self.assertIn('patient_name', form.fields)
        self.assertIn('surgery_date', form.fields)
        self.assertIn('clinical_notes', form.fields)

        # Initial values must match source form_data
        self.assertEqual(
            form.initial.get('patient_name'),
            source_form_data['patient_name'],
        )
        self.assertEqual(
            form.initial.get('surgery_date'),
            source_form_data['surgery_date'],
        )
        self.assertEqual(
            form.initial.get('clinical_notes'),
            source_form_data['clinical_notes'],
        )

        # The response HTML should contain the source text values
        self.assertContains(response, 'John Doe')
        self.assertContains(
            response,
            'Pre-operative assessment completed',
        )

    def test_duplicate_get_with_real_procedure_fields_initializes_display(
        self,
    ):
        """
        Integration test: template with procedure_code and
        procedure_description. The synthetic display field must be
        initialized as 'CODE - Description' in the duplicate form.
        """
        template = PDFFormTemplateFactory(
            form_type="HOSPITAL",
            is_active=True,
            allow_duplication=True,
            form_fields={
                'procedure_code': {
                    'type': 'text',
                    'required': True,
                    'label': 'Código',
                },
                'procedure_description': {
                    'type': 'text',
                    'required': True,
                    'label': 'Descrição',
                },
                'patient_name': {
                    'type': 'text',
                    'required': True,
                    'label': 'Patient Name',
                },
            },
        )
        source_form_data = {
            'procedure_code': '0407040161',
            'procedure_description': 'LAPAROTOMIA EXPLORADORA',
            'patient_name': self.patient.name,
        }
        source = PDFFormSubmissionFactory(
            form_template=template,
            patient=self.patient,
            created_by=self.user,
            form_data=source_form_data,
        )

        url = self._duplicate_url(source)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        form = response.context['form']
        self.assertIsNotNone(form)

        # The real DynamicFormGenerator creates procedure_display
        # and _procedure_search_config when it detects the naming
        # convention.
        self.assertIn('procedure_display', form.fields)
        self.assertIn('procedure_code', form.fields)
        self.assertIn('procedure_description', form.fields)

        # Display field must be initialized with the concatenated
        # code and description
        self.assertEqual(
            form.initial.get('procedure_display'),
            '0407040161 - LAPAROTOMIA EXPLORADORA',
        )

        # Hidden fields must also be preserved
        self.assertEqual(
            form.initial.get('procedure_code'),
            '0407040161',
        )
        self.assertEqual(
            form.initial.get('procedure_description'),
            'LAPAROTOMIA EXPLORADORA',
        )

        # The HTML should show the procedure display text
        self.assertContains(
            response,
            '0407040161 - LAPAROTOMIA EXPLORADORA',
        )
