"""
Tests for report template CRUD views.
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.mixins import PermissionDenied

from apps.accounts.models import EqmdCustomUser
from apps.reports.models import ReportTemplate
from apps.reports.services.permissions import can_manage_report_templates


class TemplateViewTests(TestCase):
    """Tests for template list, create, and update views."""

    def setUp(self):
        """Set up test users and templates."""
        self.admin_user = EqmdCustomUser.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            password_change_required=False,
            terms_accepted=True,
        )
        self.doctor = EqmdCustomUser.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.MEDICAL_DOCTOR,
            password_change_required=False,
            terms_accepted=True,
        )
        self.resident = EqmdCustomUser.objects.create_user(
            username='resident',
            email='resident@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.RESIDENT,
            password_change_required=False,
            terms_accepted=True,
        )
        self.nurse = EqmdCustomUser.objects.create_user(
            username='nurse',
            email='nurse@test.com',
            password='testpass123',
            profession_type=EqmdCustomUser.NURSE,
            password_change_required=False,
            terms_accepted=True,
        )

        # Create templates
        self.public_template = ReportTemplate.objects.create(
            name='Public Template',
            markdown_body='Dear {{patient_name}}, Record: {{patient_record_number}}',
            is_public=True,
            created_by=self.admin_user,
            updated_by=self.admin_user
        )
        self.private_template_admin = ReportTemplate.objects.create(
            name='Private Admin Template',
            markdown_body='Admin only: {{patient_name}}, {{patient_record_number}}',
            is_public=False,
            created_by=self.admin_user,
            updated_by=self.admin_user
        )
        self.private_template_doctor = ReportTemplate.objects.create(
            name='Private Doctor Template',
            markdown_body='Doctor only: {{patient_name}}, {{patient_record_number}}',
            is_public=False,
            created_by=self.doctor,
            updated_by=self.doctor
        )

    def test_template_list_requires_permission(self):
        """Template list view requires authentication."""
        response = self.client.get(reverse('reports:template_list'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_template_list_shows_public_and_own(self):
        """Template list shows public templates and user's own private templates."""
        # Login as admin
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('reports:template_list'))
        self.assertEqual(response.status_code, 200)

        # Check context contains correct templates
        templates = list(response.context['object_list'])
        self.assertEqual(len(templates), 2)  # public + own private
        template_names = {t.name for t in templates}
        self.assertIn('Public Template', template_names)
        self.assertIn('Private Admin Template', template_names)
        self.assertNotIn('Private Doctor Template', template_names)

        # Login as doctor
        self.client.logout()
        self.client.login(username='doctor', password='testpass123')
        response = self.client.get(reverse('reports:template_list'))
        self.assertEqual(response.status_code, 200)

        templates = list(response.context['object_list'])
        self.assertEqual(len(templates), 2)  # public + own private
        template_names = {t.name for t in templates}
        self.assertIn('Public Template', template_names)
        self.assertIn('Private Doctor Template', template_names)
        self.assertNotIn('Private Admin Template', template_names)

    def test_template_create_sets_creator_fields(self):
        """Template creation sets created_by and updated_by fields."""
        self.client.login(username='doctor', password='testpass123')

        response = self.client.post(
            reverse('reports:template_create'),
            {
                'name': 'New Template',
                'markdown_body': 'Test: {{patient_name}}, {{patient_record_number}}',
                'is_active': True,
                'is_public': False,
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('reports:template_list')))

        # Verify template was created
        template = ReportTemplate.objects.get(name='New Template')
        self.assertEqual(template.created_by, self.doctor)
        self.assertEqual(template.updated_by, self.doctor)
        self.assertEqual(template.markdown_body, 'Test: {{patient_name}}, {{patient_record_number}}')
        self.assertFalse(template.is_public)

    def test_template_create_forbidden_for_non_manager(self):
        """Template creation is forbidden for users who cannot manage templates."""
        self.client.login(username='nurse', password='testpass123')

        response = self.client.post(
            reverse('reports:template_create'),
            {
                'name': 'Nurse Template',
                'markdown_body': 'Test: {{patient_name}}, {{patient_record_number}}',
                'is_active': True,
                'is_public': False,
            }
        )

        # Nurse cannot manage templates, should get 403
        self.assertEqual(response.status_code, 403)

        # Verify template was not created
        self.assertFalse(ReportTemplate.objects.filter(name='Nurse Template').exists())

    def test_template_update_allowed_for_creator(self):
        """Template update is allowed for the creator."""
        self.client.login(username='doctor', password='testpass123')

        response = self.client.post(
            reverse('reports:template_update', kwargs={'pk': self.private_template_doctor.pk}),
            {
                'name': 'Updated Private Doctor Template',
                'markdown_body': 'Updated: {{patient_name}}',
                'is_active': True,
                'is_public': True,
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('reports:template_list')))

        # Verify template was updated
        self.private_template_doctor.refresh_from_db()
        self.assertEqual(self.private_template_doctor.name, 'Updated Private Doctor Template')
        self.assertTrue(self.private_template_doctor.is_public)

    def test_template_update_allowed_for_admin(self):
        """Template update is allowed for admin users (staff)."""
        self.client.login(username='admin', password='testpass123')

        response = self.client.post(
            reverse('reports:template_update', kwargs={'pk': self.private_template_doctor.pk}),
            {
                'name': 'Admin Updated Doctor Template',
                'markdown_body': 'Admin changed: {{patient_name}}',
                'is_active': True,
                'is_public': False,
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('reports:template_list')))

        # Verify template was updated
        self.private_template_doctor.refresh_from_db()
        self.assertEqual(self.private_template_doctor.name, 'Admin Updated Doctor Template')

    def test_template_update_forbidden_for_non_creator(self):
        """Template update is forbidden for non-creator non-admin users."""
        # Doctor tries to update admin's template
        self.client.login(username='doctor', password='testpass123')

        response = self.client.post(
            reverse('reports:template_update', kwargs={'pk': self.private_template_admin.pk}),
            {
                'name': 'Hacked Template',
                'markdown_body': 'Hacked: {{patient_name}}',
                'is_active': True,
                'is_public': True,
            }
        )

        # Non-creator non-admin cannot update, should get 403
        self.assertEqual(response.status_code, 403)

        # Verify template was not updated
        self.private_template_admin.refresh_from_db()
        self.assertEqual(self.private_template_admin.name, 'Private Admin Template')
        self.assertFalse(self.private_template_admin.is_public)

    def test_template_create_get_form(self):
        """Template create form page loads successfully for authorized users."""
        self.client.login(username='doctor', password='testpass123')
        response = self.client.get(reverse('reports:template_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="markdown_body"')

    def test_template_update_get_form(self):
        """Template update form page loads successfully for authorized users."""
        self.client.login(username='doctor', password='testpass123')
        response = self.client.get(reverse('reports:template_update', kwargs={'pk': self.private_template_doctor.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Private Doctor Template')
        self.assertContains(response, 'Doctor only: {{patient_name}}')

    def test_template_create_invalid_placeholders(self):
        """Template creation with invalid placeholders shows validation error."""
        self.client.login(username='doctor', password='testpass123')

        response = self.client.post(
            reverse('reports:template_create'),
            {
                'name': 'Invalid Template',
                'markdown_body': 'Invalid: {{invalid_placeholder}}',
                'is_active': True,
                'is_public': False,
            }
        )

        # Should stay on form page with errors
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'markdown_body',
            'Unknown placeholders: invalid_placeholder'
        )

    def test_template_create_missing_required_placeholders(self):
        """Template creation missing required placeholders shows validation error."""
        self.client.login(username='doctor', password='testpass123')

        # Missing patient_name
        response = self.client.post(
            reverse('reports:template_create'),
            {
                'name': 'Incomplete Template',
                'markdown_body': 'Only record: {{patient_record_number}}',
                'is_active': True,
                'is_public': False,
            }
        )

        # Should stay on form page with errors
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'markdown_body',
            'Missing required placeholders: patient_name'
        )
