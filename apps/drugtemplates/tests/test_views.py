from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.messages import get_messages
from django.http import Http404
# Note: Hospital model removed after single-hospital refactor
from apps.drugtemplates.models import DrugTemplate, PrescriptionTemplate, PrescriptionTemplateItem
from apps.drugtemplates.forms import DrugTemplateForm, PrescriptionTemplateForm

User = get_user_model()


class DrugTemplateListViewTest(TestCase):
    """Test cases for DrugTemplateListView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        
        cls.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )

        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user1,
            updated_by=cls.user1
        )

        # Create public template
        cls.public_template = DrugTemplate.objects.create(
            name='Public Drug',
            presentation='10mg tablet',
            usage_instructions='Take 1 tablet daily',
            creator=cls.user1,
            is_public=True
        )

        # Create private template for user1
        cls.private_template_user1 = DrugTemplate.objects.create(
            name='Private Drug User1',
            presentation='20mg tablet',
            usage_instructions='Take 1 tablet twice daily',
            creator=cls.user1,
            is_public=False
        )

        # Create private template for user2
        cls.private_template_user2 = DrugTemplate.objects.create(
            name='Private Drug User2',
            presentation='30mg tablet',
            usage_instructions='Take 1 tablet three times daily',
            creator=cls.user2,
            is_public=False
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username='user1', password='testpass123')

    def test_view_url_accessible_by_name(self):
        """Test that view is accessible by name."""
        response = self.client.get(reverse('drugtemplates:list'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        response = self.client.get(reverse('drugtemplates:list'))
        self.assertTemplateUsed(response, 'drugtemplates/drugtemplate_list.html')

    def test_view_shows_public_and_user_private_templates(self):
        """Test that view shows public templates and user's private templates."""
        response = self.client.get(reverse('drugtemplates:list'))
        templates = response.context['drug_templates']
        
        # Should see public template and user1's private template
        self.assertIn(self.public_template, templates)
        self.assertIn(self.private_template_user1, templates)
        
        # Should NOT see user2's private template
        self.assertNotIn(self.private_template_user2, templates)

    def test_view_name_search_filter(self):
        """Test name search filter functionality."""
        response = self.client.get(
            reverse('drugtemplates:list'),
            {'name': 'Public'}
        )
        templates = response.context['drug_templates']
        
        self.assertIn(self.public_template, templates)
        self.assertNotIn(self.private_template_user1, templates)

    def test_view_creator_filter(self):
        """Test creator filter functionality."""
        response = self.client.get(
            reverse('drugtemplates:list'),
            {'creator': str(self.user1.id)}
        )
        templates = response.context['drug_templates']
        
        # Should show user1's templates
        self.assertIn(self.public_template, templates)
        self.assertIn(self.private_template_user1, templates)

    def test_view_visibility_filter_public(self):
        """Test visibility filter for public templates only."""
        response = self.client.get(
            reverse('drugtemplates:list'),
            {'visibility': 'public'}
        )
        templates = response.context['drug_templates']
        
        self.assertIn(self.public_template, templates)
        self.assertNotIn(self.private_template_user1, templates)

    def test_view_visibility_filter_private(self):
        """Test visibility filter for private templates only."""
        response = self.client.get(
            reverse('drugtemplates:list'),
            {'visibility': 'private'}
        )
        templates = response.context['drug_templates']
        
        self.assertNotIn(self.public_template, templates)
        self.assertIn(self.private_template_user1, templates)

    def test_view_visibility_filter_mine(self):
        """Test visibility filter for user's own templates."""
        response = self.client.get(
            reverse('drugtemplates:list'),
            {'visibility': 'mine'}
        )
        templates = response.context['drug_templates']
        
        # Should show both public and private templates created by user1
        self.assertIn(self.public_template, templates)
        self.assertIn(self.private_template_user1, templates)

    def test_view_pagination(self):
        """Test pagination functionality."""
        response = self.client.get(reverse('drugtemplates:list'))
        self.assertIn('is_paginated', response.context)
        self.assertIn('page_obj', response.context)

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        response = self.client.get(reverse('drugtemplates:list'))
        self.assertRedirects(response, '/accounts/login/?next=/drugtemplates/')


class DrugTemplateDetailViewTest(TestCase):
    """Test cases for DrugTemplateDetailView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        
        cls.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )

        cls.public_template = DrugTemplate.objects.create(
            name='Public Drug',
            presentation='10mg tablet',
            usage_instructions='Take 1 tablet daily',
            creator=cls.user1,
            is_public=True
        )

        cls.private_template = DrugTemplate.objects.create(
            name='Private Drug',
            presentation='20mg tablet',
            usage_instructions='Take 1 tablet twice daily',
            creator=cls.user1,
            is_public=False
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()

    def test_view_public_template_accessible_to_any_user(self):
        """Test that public templates are accessible to any authenticated user."""
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(
            reverse('drugtemplates:detail', kwargs={'pk': self.public_template.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['drugtemplate'], self.public_template)

    def test_view_private_template_accessible_to_creator(self):
        """Test that private templates are accessible to creator."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(
            reverse('drugtemplates:detail', kwargs={'pk': self.private_template.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['drugtemplate'], self.private_template)

    def test_view_private_template_not_accessible_to_other_users(self):
        """Test that private templates are not accessible to other users."""
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(
            reverse('drugtemplates:detail', kwargs={'pk': self.private_template.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(
            reverse('drugtemplates:detail', kwargs={'pk': self.public_template.pk})
        )
        self.assertTemplateUsed(response, 'drugtemplates/drugtemplate_detail.html')

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        response = self.client.get(
            reverse('drugtemplates:detail', kwargs={'pk': self.public_template.pk})
        )
        self.assertRedirects(response, f'/accounts/login/?next=/drugtemplates/{self.public_template.pk}/')


class DrugTemplateCreateViewTest(TestCase):
    """Test cases for DrugTemplateCreateView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Doctor
        )

        cls.non_doctor_user = User.objects.create_user(
            username='nurseuser',
            email='nurse@example.com',
            password='testpass123',
            profession=3  # Nurse
        )

        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()

    def test_view_accessible_to_doctors(self):
        """Test that view is accessible to doctors."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('drugtemplates:create'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('drugtemplates:create'))
        self.assertTemplateUsed(response, 'drugtemplates/drugtemplate_create_form.html')

    def test_view_uses_correct_form(self):
        """Test that view uses correct form class."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('drugtemplates:create'))
        self.assertIsInstance(response.context['form'], DrugTemplateForm)

    def test_post_creates_drug_template(self):
        """Test that POST request creates new drug template."""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'Test Drug',
            'presentation': '10mg tablets',
            'usage_instructions': 'Take 1 tablet daily with food',
            'is_public': True
        }
        
        response = self.client.post(reverse('drugtemplates:create'), form_data)
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Check that drug template was created
        self.assertTrue(
            DrugTemplate.objects.filter(
                name='Test Drug',
                creator=self.user
            ).exists()
        )

    def test_post_invalid_form_shows_errors(self):
        """Test that POST with invalid data shows form errors."""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': '',  # Missing required field
            'presentation': '10mg tablets',
            'usage_instructions': 'Take 1 tablet daily',
            'is_public': False
        }
        
        response = self.client.post(reverse('drugtemplates:create'), form_data)
        
        # Should stay on form page
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'name', 'This field is required.')

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        response = self.client.get(reverse('drugtemplates:create'))
        self.assertRedirects(response, '/accounts/login/?next=/drugtemplates/create/')


class DrugTemplateUpdateViewTest(TestCase):
    """Test cases for DrugTemplateUpdateView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123',
            profession_type=0  # Doctor
        )
        
        cls.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123',
            profession_type=0  # Doctor
        )

        cls.drug_template = DrugTemplate.objects.create(
            name='Test Drug',
            presentation='10mg tablet',
            usage_instructions='Take 1 tablet daily',
            creator=cls.user1,
            is_public=False
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()

    def test_view_accessible_to_creator(self):
        """Test that view is accessible to template creator."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(
            reverse('drugtemplates:update', kwargs={'pk': self.drug_template.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_view_not_accessible_to_other_users(self):
        """Test that view is not accessible to other users."""
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(
            reverse('drugtemplates:update', kwargs={'pk': self.drug_template.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(
            reverse('drugtemplates:update', kwargs={'pk': self.drug_template.pk})
        )
        self.assertTemplateUsed(response, 'drugtemplates/drugtemplate_update_form.html')

    def test_post_updates_drug_template(self):
        """Test that POST request updates drug template."""
        self.client.login(username='user1', password='testpass123')
        
        form_data = {
            'name': 'Updated Drug Name',
            'presentation': '20mg tablets',
            'usage_instructions': 'Take 2 tablets daily with food',
            'is_public': True
        }
        
        response = self.client.post(
            reverse('drugtemplates:update', kwargs={'pk': self.drug_template.pk}),
            form_data
        )
        
        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)
        
        # Check that drug template was updated
        self.drug_template.refresh_from_db()
        self.assertEqual(self.drug_template.name, 'Updated Drug Name')
        self.assertEqual(self.drug_template.presentation, '20mg tablets')
        self.assertTrue(self.drug_template.is_public)

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        response = self.client.get(
            reverse('drugtemplates:update', kwargs={'pk': self.drug_template.pk})
        )
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/drugtemplates/{self.drug_template.pk}/update/'
        )


class DrugTemplateDeleteViewTest(TestCase):
    """Test cases for DrugTemplateDeleteView."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123',
            profession_type=0  # Doctor
        )
        
        cls.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123',
            profession_type=0  # Doctor
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        
        # Create fresh template for each test
        self.drug_template = DrugTemplate.objects.create(
            name='Test Drug',
            presentation='10mg tablet',
            usage_instructions='Take 1 tablet daily',
            creator=self.user1,
            is_public=False
        )

    def test_view_accessible_to_creator(self):
        """Test that view is accessible to template creator."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(
            reverse('drugtemplates:delete', kwargs={'pk': self.drug_template.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_view_not_accessible_to_other_users(self):
        """Test that view is not accessible to other users."""
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(
            reverse('drugtemplates:delete', kwargs={'pk': self.drug_template.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_view_uses_correct_template(self):
        """Test that view uses correct template."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(
            reverse('drugtemplates:delete', kwargs={'pk': self.drug_template.pk})
        )
        self.assertTemplateUsed(response, 'drugtemplates/drugtemplate_confirm_delete.html')

    def test_post_deletes_drug_template(self):
        """Test that POST request deletes drug template."""
        self.client.login(username='user1', password='testpass123')
        template_id = self.drug_template.id
        
        response = self.client.post(
            reverse('drugtemplates:delete', kwargs={'pk': self.drug_template.pk})
        )
        
        # Should redirect after successful deletion
        self.assertEqual(response.status_code, 302)
        
        # Check that drug template was deleted
        self.assertFalse(DrugTemplate.objects.filter(id=template_id).exists())

    def test_view_requires_login(self):
        """Test that view requires authentication."""
        response = self.client.get(
            reverse('drugtemplates:delete', kwargs={'pk': self.drug_template.pk})
        )
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/drugtemplates/{self.drug_template.pk}/delete/'
        )


class PrescriptionTemplateViewsTest(TestCase):
    """Test cases for PrescriptionTemplate views."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Doctor
        )

        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user,
            updated_by=cls.user
        )

        cls.prescription_template = PrescriptionTemplate.objects.create(
            name='Test Prescription Template',
            creator=cls.user,
            is_public=False
        )

        # Add some items to the template
        PrescriptionTemplateItem.objects.create(
            template=cls.prescription_template,
            drug_name='Drug A',
            presentation='10mg tablet',
            usage_instructions='Take 1 daily',
            quantity='30',
            order=1
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_prescription_template_list_view(self):
        """Test prescription template list view."""
        response = self.client.get(reverse('drugtemplates:prescription_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.prescription_template, response.context['prescription_templates'])

    def test_prescription_template_detail_view(self):
        """Test prescription template detail view."""
        response = self.client.get(
            reverse('drugtemplates:prescription_detail', kwargs={'pk': self.prescription_template.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['prescriptiontemplate'], self.prescription_template)

    def test_prescription_template_create_view(self):
        """Test prescription template create view."""
        response = self.client.get(reverse('drugtemplates:prescription_create'))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], PrescriptionTemplateForm)

    def test_prescription_template_create_post(self):
        """Test creating prescription template via POST."""
        form_data = {
            'name': 'New Prescription Template',
            'is_public': True,
            
            # Formset management data
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '1',
            'items-MAX_NUM_FORMS': '1000',
            
            # Item data
            'items-0-drug_name': 'Test Drug',
            'items-0-presentation': '10mg tablet',
            'items-0-usage_instructions': 'Take 1 daily',
            'items-0-quantity': '30',
            'items-0-order': '1',
        }
        
        response = self.client.post(reverse('drugtemplates:prescription_create'), form_data)
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Check that template was created
        self.assertTrue(
            PrescriptionTemplate.objects.filter(
                name='New Prescription Template',
                creator=self.user
            ).exists()
        )

    def test_prescription_template_update_view(self):
        """Test prescription template update view."""
        response = self.client.get(
            reverse('drugtemplates:prescription_update', kwargs={'pk': self.prescription_template.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_prescription_template_delete_view(self):
        """Test prescription template delete view."""
        response = self.client.get(
            reverse('drugtemplates:prescription_delete', kwargs={'pk': self.prescription_template.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_prescription_template_delete_post(self):
        """Test deleting prescription template via POST."""
        template_id = self.prescription_template.id
        
        response = self.client.post(
            reverse('drugtemplates:prescription_delete', kwargs={'pk': self.prescription_template.pk})
        )
        
        # Should redirect after successful deletion
        self.assertEqual(response.status_code, 302)
        
        # Check that template was deleted
        self.assertFalse(PrescriptionTemplate.objects.filter(id=template_id).exists())


class PermissionTestsMixin:
    """Mixin for testing permission requirements across views."""

    def test_non_doctor_access_denied(self):
        """Test that non-doctors are denied access to create/update/delete views."""
        # This would need to be implemented in each view test class
        # based on the specific permission decorators used
        pass


class ViewIntegrationTest(TestCase):
    """Integration tests for view workflows."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession_type=0  # Doctor
        )

        cls.hospital = Hospital.objects.create(
            name='Test Hospital',
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_complete_drug_template_crud_workflow(self):
        """Test complete CRUD workflow for drug templates."""
        # Create
        create_data = {
            'name': 'Workflow Test Drug',
            'presentation': '10mg tablets',
            'usage_instructions': 'Take 1 tablet daily with food',
            'is_public': False
        }
        
        response = self.client.post(reverse('drugtemplates:create'), create_data)
        self.assertEqual(response.status_code, 302)
        
        # Get the created template
        template = DrugTemplate.objects.get(name='Workflow Test Drug')
        
        # Read (Detail view)
        response = self.client.get(
            reverse('drugtemplates:detail', kwargs={'pk': template.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['drugtemplate'], template)
        
        # Update
        update_data = {
            'name': 'Updated Workflow Test Drug',
            'presentation': '20mg tablets',
            'usage_instructions': 'Take 2 tablets daily with food',
            'is_public': True
        }
        
        response = self.client.post(
            reverse('drugtemplates:update', kwargs={'pk': template.pk}),
            update_data
        )
        self.assertEqual(response.status_code, 302)
        
        # Verify update
        template.refresh_from_db()
        self.assertEqual(template.name, 'Updated Workflow Test Drug')
        self.assertTrue(template.is_public)
        
        # Delete
        response = self.client.post(
            reverse('drugtemplates:delete', kwargs={'pk': template.pk})
        )
        self.assertEqual(response.status_code, 302)
        
        # Verify deletion
        self.assertFalse(DrugTemplate.objects.filter(id=template.id).exists())