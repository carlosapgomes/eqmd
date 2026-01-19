"""
Failing tests for admin interface updates.
These tests will fail until admin interface is updated for new fields.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.http import HttpRequest
from apps.drugtemplates.models import DrugTemplate
from apps.drugtemplates.admin import DrugTemplateAdmin

User = get_user_model()


class DrugTemplateAdminTest(TestCase):
    """Tests for updated DrugTemplate admin interface."""
    
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.client = Client()
        self.client.login(username='admin', password='adminpass123')
        
        self.site = AdminSite()
        self.admin = DrugTemplateAdmin(DrugTemplate, self.site)

    def test_admin_list_display_includes_new_fields(self):
        """Test that admin list display includes new fields."""
        # This will fail until admin is updated
        
        # Create test template
        system_user = User.objects.create_user(
            username='system',
            email='system@hospital.internal'
        )
        drug_template = DrugTemplate.objects.create(
            name='Test Drug',
            concentration='100 mg',
            pharmaceutical_form='comprimido',
            creator=system_user,
            is_imported=True,
            import_source='Test CSV'
        )
        
        # Test admin changelist page
        response = self.client.get('/admin/drugtemplates/drugtemplate/')
        self.assertEqual(response.status_code, 200)
        
        # Should display new fields in list
        content = response.content.decode()
        self.assertIn('100 mg', content)  # concentration
        self.assertIn('comprimido', content)  # pharmaceutical_form
        self.assertIn('Test CSV', content)  # import_source
        
        # Should show imported status
        self.assertIn('Sim', content)  # is_imported = True displayed as "Sim"

    def test_admin_list_filter_includes_new_fields(self):
        """Test that admin list filters include new fields."""
        # This will fail until admin filters are updated
        
        response = self.client.get('/admin/drugtemplates/drugtemplate/')
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Should have filter for is_imported
        self.assertIn('Por origem', content)
        self.assertIn('Importado', content)
        self.assertIn('Criado por usuário', content)
        
        # Should have filter for pharmaceutical_form
        self.assertIn('Por forma farmacêutica', content)
        
        # Should have filter for import_source
        self.assertIn('Por fonte de importação', content)

    def test_admin_search_fields_include_new_fields(self):
        """Test that admin search includes new fields."""
        # This will fail until admin search fields are updated
        
        # Create test templates
        system_user = User.objects.create_user(
            username='system',
            email='system@hospital.internal'
        )
        drug1 = DrugTemplate.objects.create(
            name='Searchable Drug',
            concentration='250 mg',
            pharmaceutical_form='cápsula',
            creator=system_user,
            is_imported=True
        )
        drug2 = DrugTemplate.objects.create(
            name='Another Drug',
            concentration='500 mg',
            pharmaceutical_form='comprimido',
            creator=system_user,
            is_imported=True
        )
        
        # Search by concentration
        response = self.client.get('/admin/drugtemplates/drugtemplate/?q=250')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Searchable Drug')
        self.assertNotContains(response, 'Another Drug')
        
        # Search by pharmaceutical form
        response = self.client.get('/admin/drugtemplates/drugtemplate/?q=cápsula')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Searchable Drug')
        self.assertNotContains(response, 'Another Drug')

    def test_admin_fieldsets_include_new_fields(self):
        """Test that admin form fieldsets include new fields."""
        # This will fail until admin fieldsets are updated
        
        response = self.client.get('/admin/drugtemplates/drugtemplate/add/')
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Should have fields for new model fields
        self.assertIn('concentration', content)
        self.assertIn('pharmaceutical_form', content)
        self.assertIn('is_imported', content)
        self.assertIn('import_source', content)
        
        # Should organize fields in logical fieldsets
        self.assertIn('Informações do Medicamento', content)
        self.assertIn('Informações de Importação', content)

    def test_admin_readonly_fields_for_imported_drugs(self):
        """Test that imported drugs have readonly fields in admin."""
        # This will fail until admin readonly logic is implemented
        
        system_user = User.objects.create_user(
            username='system',
            email='system@hospital.internal'
        )
        imported_drug = DrugTemplate.objects.create(
            name='Imported Drug',
            concentration='300 mg',
            pharmaceutical_form='solução',
            creator=system_user,
            is_imported=True,
            import_source='CSV Import'
        )
        
        response = self.client.get(
            f'/admin/drugtemplates/drugtemplate/{imported_drug.pk}/change/'
        )
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Core imported fields should be readonly
        # Look for readonly indicators in HTML
        self.assertTrue(
            'readonly' in content or
            'disabled' in content or
            'Somente leitura' in content
        )

    def test_admin_custom_actions_for_source_management(self):
        """Test custom admin actions for source management."""
        # This will fail until custom actions are implemented
        
        response = self.client.get('/admin/drugtemplates/drugtemplate/')
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Should have custom actions for source management
        self.assertIn('Marcar como importado', content)
        self.assertIn('Marcar como criado por usuário', content)

    def test_admin_import_source_display_method(self):
        """Test admin method for displaying import source."""
        # This will fail until admin display method is implemented
        
        # Test display method exists and works
        request = HttpRequest()
        
        # Test with imported drug
        system_user = User.objects.create_user(
            username='system',
            email='system@hospital.internal'
        )
        imported_drug = DrugTemplate.objects.create(
            name='Import Test',
            concentration='100 mg',
            pharmaceutical_form='comprimido',
            creator=system_user,
            is_imported=True,
            import_source='Test Source'
        )
        
        # Should have method to display import status
        self.assertTrue(hasattr(self.admin, 'import_status_display'))
        import_status = self.admin.import_status_display(imported_drug)
        self.assertIn('Importado', import_status)
        self.assertIn('Test Source', import_status)
        
        # Test with user-created drug
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        user_drug = DrugTemplate.objects.create(
            name='User Test',
            concentration='200 mg',
            pharmaceutical_form='cápsula',
            usage_instructions='User instructions',
            creator=user,
            is_imported=False
        )
        
        user_status = self.admin.import_status_display(user_drug)
        self.assertIn('Usuário', user_status)

    def test_admin_pharmaceutical_form_display_method(self):
        """Test admin method for displaying pharmaceutical form."""
        # This will fail until admin display method is implemented
        
        drug_template = DrugTemplate.objects.create(
            name='Form Test',
            concentration='500 mg',
            pharmaceutical_form='comprimido revestido',
            creator=self.admin_user
        )
        
        # Should have method to format pharmaceutical form display
        self.assertTrue(hasattr(self.admin, 'pharmaceutical_form_display'))
        form_display = self.admin.pharmaceutical_form_display(drug_template)
        self.assertEqual(form_display, 'comprimido revestido')

    def test_admin_concentration_display_method(self):
        """Test admin method for displaying concentration."""
        # This will fail until admin display method is implemented
        
        drug_template = DrugTemplate.objects.create(
            name='Concentration Test',
            concentration='25.5 mg/mL',
            pharmaceutical_form='solução',
            creator=self.admin_user
        )
        
        # Should have method to format concentration display
        self.assertTrue(hasattr(self.admin, 'concentration_display'))
        concentration_display = self.admin.concentration_display(drug_template)
        self.assertEqual(concentration_display, '25.5 mg/mL')

    def test_admin_bulk_actions_with_import_protection(self):
        """Test that bulk actions respect import protection."""
        # This will fail until bulk action protection is implemented
        
        # Create mixed templates
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        user_template = DrugTemplate.objects.create(
            name='User Template',
            concentration='100 mg',
            pharmaceutical_form='comprimido',
            usage_instructions='Test',
            creator=user
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
            import_source='Protected'
        )
        
        # Try bulk delete action
        response = self.client.post(
            '/admin/drugtemplates/drugtemplate/',
            {
                'action': 'delete_selected',
                '_selected_action': [user_template.pk, imported_template.pk]
            },
            follow=True
        )
        
        # Should show protection warning or prevent action
        content = response.content.decode()
        self.assertTrue(
            'imported' in content.lower() or
            'importado' in content.lower() or
            'proteção' in content.lower() or
            'protegido' in content.lower()
        )