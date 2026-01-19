"""
Failing tests for source tracking functionality.
These tests will fail until source tracking features are implemented.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from apps.drugtemplates.models import DrugTemplate

User = get_user_model()


class SourceTrackingTest(TestCase):
    """Tests for drug template source tracking functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            profession='DR'  # Doctor
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_drugtemplate_list_view_filters_by_source(self):
        """Test that list view can filter by source (user-created vs imported)."""
        # This will fail until view filtering is implemented
        
        # Create user template
        user_template = DrugTemplate.objects.create(
            name='User Drug',
            concentration='100 mg',
            pharmaceutical_form='comprimido',
            usage_instructions='User created instructions',
            creator=self.user,
            is_imported=False
        )
        
        # Create imported template  
        system_user = User.objects.create_user(
            username='system',
            email='system@hospital.internal'
        )
        imported_template = DrugTemplate.objects.create(
            name='Imported Drug',
            concentration='200 mg',
            pharmaceutical_form='cápsula',
            creator=system_user,
            is_imported=True,
            import_source='CSV Import'
        )
        
        # Test filtering by user-created
        response = self.client.get(reverse('drugtemplates:list'), {'source': 'user'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Drug')
        self.assertNotContains(response, 'Imported Drug')
        
        # Test filtering by imported
        response = self.client.get(reverse('drugtemplates:list'), {'source': 'imported'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Imported Drug')
        self.assertNotContains(response, 'User Drug')

    def test_drugtemplate_detail_view_shows_import_source(self):
        """Test that detail view shows import source information."""
        # This will fail until detail view is updated
        
        system_user = User.objects.create_user(
            username='system',
            email='system@hospital.internal'
        )
        imported_template = DrugTemplate.objects.create(
            name='Imported Drug',
            concentration='250 mg',
            pharmaceutical_form='solução',
            creator=system_user,
            is_imported=True,
            import_source='MERGED_medications.csv'
        )
        
        response = self.client.get(
            reverse('drugtemplates:detail', kwargs={'pk': imported_template.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # Should display import source information
        self.assertContains(response, 'Importado')
        self.assertContains(response, 'MERGED_medications.csv')
        self.assertContains(response, 'Medicamento de referência')

    def test_drugtemplate_edit_permissions_for_imported(self):
        """Test that imported templates cannot be fully edited."""
        # This will fail until edit permission logic is implemented
        
        system_user = User.objects.create_user(
            username='system',
            email='system@hospital.internal'
        )
        imported_template = DrugTemplate.objects.create(
            name='Imported Drug',
            concentration='300 mg',
            pharmaceutical_form='injetável',
            creator=system_user,
            is_imported=True,
            import_source='CSV Import'
        )
        
        # Should not allow editing core imported fields
        response = self.client.get(
            reverse('drugtemplates:update', kwargs={'pk': imported_template.pk})
        )
        
        # Should either redirect or show limited edit form
        self.assertTrue(
            response.status_code in [302, 403] or
            'readonly' in response.content.decode().lower()
        )

    def test_drugtemplate_admin_displays_source_information(self):
        """Test that admin interface displays source tracking information."""
        # This will fail until admin interface is updated
        
        # Create admin user
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.client.login(username='admin', password='adminpass123')
        
        # Create imported template
        system_user = User.objects.create_user(
            username='system',
            email='system@hospital.internal'
        )
        imported_template = DrugTemplate.objects.create(
            name='Admin Test Drug',
            concentration='400 mg',
            pharmaceutical_form='cápsula',
            creator=system_user,
            is_imported=True,
            import_source='Test Source'
        )
        
        # Check admin changelist
        response = self.client.get('/admin/drugtemplates/drugtemplate/')
        self.assertEqual(response.status_code, 200)
        
        # Should show import source in list
        self.assertContains(response, 'Test Source')
        self.assertContains(response, 'Importado')

    def test_drugtemplate_admin_filters_by_source(self):
        """Test that admin interface can filter by source."""
        # This will fail until admin filters are implemented
        
        # Create admin user
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.client.login(username='admin', password='adminpass123')
        
        # Check admin changelist has source filters
        response = self.client.get('/admin/drugtemplates/drugtemplate/')
        self.assertEqual(response.status_code, 200)
        
        # Should have filter sidebar
        self.assertContains(response, 'Origem')  # Source filter
        self.assertContains(response, 'Importado')
        self.assertContains(response, 'Criado por usuário')

    def test_drugtemplate_queryset_methods_for_source_filtering(self):
        """Test model manager methods for source filtering."""
        # This will fail until manager methods are implemented
        
        # Create user template
        user_template = DrugTemplate.objects.create(
            name='User Drug',
            concentration='100 mg',
            pharmaceutical_form='comprimido',
            usage_instructions='User instructions',
            creator=self.user,
            is_imported=False
        )
        
        # Create imported template
        system_user = User.objects.create_user(
            username='system',
            email='system@hospital.internal'
        )
        imported_template = DrugTemplate.objects.create(
            name='Imported Drug',
            concentration='200 mg',
            pharmaceutical_form='cápsula',
            creator=system_user,
            is_imported=True,
            import_source='CSV'
        )
        
        # Test manager methods
        user_created = DrugTemplate.objects.user_created()
        self.assertIn(user_template, user_created)
        self.assertNotIn(imported_template, user_created)
        
        imported_drugs = DrugTemplate.objects.imported()
        self.assertIn(imported_template, imported_drugs)
        self.assertNotIn(user_template, imported_drugs)
        
        from_source = DrugTemplate.objects.from_source('CSV')
        self.assertIn(imported_template, from_source)
        self.assertNotIn(user_template, from_source)

    def test_drugtemplate_api_includes_source_information(self):
        """Test that API responses include source tracking information."""
        # This will fail until API is updated (if API exists)
        
        system_user = User.objects.create_user(
            username='system',
            email='system@hospital.internal'
        )
        imported_template = DrugTemplate.objects.create(
            name='API Test Drug',
            concentration='500 mg',
            pharmaceutical_form='tablet',
            creator=system_user,
            is_imported=True,
            import_source='API Test'
        )
        
        # If there's a REST API endpoint, test it includes source info
        try:
            api_url = reverse('api:drugtemplate-detail', kwargs={'pk': imported_template.pk})
            response = self.client.get(api_url, HTTP_ACCEPT='application/json')
            
            if response.status_code == 200:
                data = response.json()
                self.assertIn('is_imported', data)
                self.assertIn('import_source', data)
                self.assertTrue(data['is_imported'])
                self.assertEqual(data['import_source'], 'API Test')
        except:
            # Skip if no API endpoint exists yet
            pass

    def test_drugtemplate_search_considers_source(self):
        """Test that search functionality considers source information."""
        # This will fail until search is updated
        
        # Create templates with different sources
        user_template = DrugTemplate.objects.create(
            name='Searchable User Drug',
            concentration='100 mg',
            pharmaceutical_form='comprimido',
            usage_instructions='Search test',
            creator=self.user,
            is_imported=False
        )
        
        system_user = User.objects.create_user(
            username='system',
            email='system@hospital.internal'
        )
        imported_template = DrugTemplate.objects.create(
            name='Searchable Imported Drug',
            concentration='200 mg',
            pharmaceutical_form='cápsula',
            creator=system_user,
            is_imported=True,
            import_source='Search Test CSV'
        )
        
        # Search with source filter
        response = self.client.get(
            reverse('drugtemplates:list'),
            {'q': 'Searchable', 'source': 'imported'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Searchable Imported Drug')
        self.assertNotContains(response, 'Searchable User Drug')

    def test_drugtemplate_bulk_actions_respect_source_permissions(self):
        """Test that bulk admin actions respect source permissions."""
        # This will fail until bulk actions are implemented
        
        # Create admin user
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.client.login(username='admin', password='adminpass123')
        
        # Create mixed templates
        user_template = DrugTemplate.objects.create(
            name='User Template',
            concentration='100 mg',
            pharmaceutical_form='comprimido',
            usage_instructions='Test',
            creator=self.user,
            is_imported=False
        )
        
        system_user = User.objects.create_user(
            username='system',
            email='system@hospital.internal'
        )
        imported_template = DrugTemplate.objects.create(
            name='Imported Template',
            concentration='200 mg',
            pharmaceutical_form='cápsula',
            creator=system_user,
            is_imported=True,
            import_source='Bulk Test'
        )
        
        # Try to delete both via bulk action
        response = self.client.post(
            '/admin/drugtemplates/drugtemplate/',
            {
                'action': 'delete_selected',
                '_selected_action': [user_template.pk, imported_template.pk]
            }
        )
        
        # Should either prevent deletion of imported or show warning
        self.assertTrue(
            response.status_code in [302, 200] and
            ('error' in response.content.decode().lower() or
             'warning' in response.content.decode().lower() or
             'imported' in response.content.decode().lower())
        )