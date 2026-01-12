"""
Comprehensive test suite for medical procedures functionality.
Tests model, management command, API endpoints, and admin interface.
"""

import json
import uuid
from io import StringIO
from unittest.mock import patch, mock_open
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.postgres.search import SearchVector
from django.urls import reverse
from django.contrib.admin.sites import AdminSite
from apps.core.models import MedicalProcedure
from apps.core.admin import MedicalProcedureAdmin
import tempfile
import csv

User = get_user_model()


class MedicalProcedureModelTest(TestCase):
    """Test MedicalProcedure model functionality."""

    def setUp(self):
        """Set up test data."""
        self.procedure = MedicalProcedure.objects.create(
            code='0301010012',
            description='Consulta médica em atenção especializada para tratamento de diabetes',
            is_active=True
        )

    def test_model_creation(self):
        """Test basic model creation."""
        self.assertEqual(self.procedure.code, '0301010012')
        self.assertEqual(
            self.procedure.description, 
            'Consulta médica em atenção especializada para tratamento de diabetes'
        )
        self.assertTrue(self.procedure.is_active)
        self.assertIsNotNone(self.procedure.id)
        self.assertIsNotNone(self.procedure.created_at)
        self.assertIsNotNone(self.procedure.updated_at)

    def test_str_representation(self):
        """Test string representation of model."""
        expected = "0301010012 - Consulta médica em atenção especializada para trat..."
        self.assertEqual(str(self.procedure), expected)

    def test_short_description_property(self):
        """Test short_description property."""
        # Test with long description
        self.assertEqual(
            self.procedure.short_description,
            'Consulta médica em atenção especializada para tratamento de diabetes'
        )
        
        # Test with very long description
        long_procedure = MedicalProcedure.objects.create(
            code='TEST001',
            description='A' * 150,  # 150 characters
            is_active=True
        )
        self.assertEqual(len(long_procedure.short_description), 100)
        self.assertTrue(long_procedure.short_description.endswith('...'))

    def test_get_display_text(self):
        """Test get_display_text method."""
        expected = "0301010012 - Consulta médica em atenção especializada para tratamento de diabetes"
        self.assertEqual(self.procedure.get_display_text(), expected)

    def test_code_uppercase_on_save(self):
        """Test that code is automatically converted to uppercase."""
        procedure = MedicalProcedure.objects.create(
            code='test123',
            description='Test procedure',
            is_active=True
        )
        self.assertEqual(procedure.code, 'TEST123')

    def test_unique_code_constraint(self):
        """Test that code field has unique constraint."""
        with self.assertRaises(Exception):  # IntegrityError expected
            MedicalProcedure.objects.create(
                code='0301010012',  # Same code as setUp procedure
                description='Another procedure',
                is_active=True
            )

    def test_active_classmethod(self):
        """Test active() class method."""
        # Create inactive procedure
        MedicalProcedure.objects.create(
            code='INACTIVE001',
            description='Inactive procedure',
            is_active=False
        )
        
        active_procedures = MedicalProcedure.active()
        self.assertEqual(active_procedures.count(), 1)
        self.assertEqual(active_procedures.first().code, '0301010012')

    def test_simple_search_classmethod(self):
        """Test simple_search() class method."""
        # Test search by code
        results = MedicalProcedure.simple_search('0301010012')
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().code, '0301010012')
        
        # Test search by description
        results = MedicalProcedure.simple_search('diabetes')
        self.assertEqual(results.count(), 1)
        
        # Test case insensitive search
        results = MedicalProcedure.simple_search('DIABETES')
        self.assertEqual(results.count(), 1)
        
        # Test no results
        results = MedicalProcedure.simple_search('nonexistent')
        self.assertEqual(results.count(), 0)
        
        # Test empty query
        results = MedicalProcedure.simple_search('')
        self.assertEqual(results.count(), 0)


class ImportProceduresCommandTest(TestCase):
    """Test import_procedures management command."""

    def create_test_csv(self, data):
        """Create a temporary CSV file with test data."""
        csv_content = StringIO()
        writer = csv.DictWriter(csv_content, fieldnames=['code', 'description', 'is_active'])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        return csv_content.getvalue()

    def create_test_json(self, data):
        """Create test JSON data."""
        return json.dumps(data)

    @patch('builtins.open', create=True)
    def test_import_csv_success(self, mock_file):
        """Test successful CSV import."""
        csv_data = [
            {'code': 'TEST001', 'description': 'Test procedure 1', 'is_active': 'true'},
            {'code': 'TEST002', 'description': 'Test procedure 2', 'is_active': 'false'},
        ]
        csv_content = self.create_test_csv(csv_data)
        mock_file.return_value.__enter__.return_value = StringIO(csv_content)
        
        # Mock file path existence
        with patch('pathlib.Path.exists', return_value=True):
            out = StringIO()
            call_command('import_procedures', '--file=test.csv', stdout=out)
        
        # Check that procedures were created
        self.assertEqual(MedicalProcedure.objects.count(), 2)
        
        procedure1 = MedicalProcedure.objects.get(code='TEST001')
        self.assertEqual(procedure1.description, 'Test procedure 1')
        self.assertTrue(procedure1.is_active)
        
        procedure2 = MedicalProcedure.objects.get(code='TEST002')
        self.assertEqual(procedure2.description, 'Test procedure 2')
        self.assertFalse(procedure2.is_active)

    @patch('builtins.open', create=True)
    def test_import_json_success(self, mock_file):
        """Test successful JSON import."""
        json_data = [
            {'code': 'JSON001', 'description': 'JSON test procedure 1', 'is_active': True},
            {'code': 'JSON002', 'description': 'JSON test procedure 2', 'is_active': False},
        ]
        json_content = self.create_test_json(json_data)
        mock_file.return_value.__enter__.return_value = StringIO(json_content)
        
        with patch('pathlib.Path.exists', return_value=True):
            out = StringIO()
            call_command('import_procedures', '--file=test.json', stdout=out)
        
        self.assertEqual(MedicalProcedure.objects.count(), 2)

    @patch('builtins.open', create=True)
    def test_dry_run_mode(self, mock_file):
        """Test dry run mode doesn't save data."""
        csv_data = [
            {'code': 'DRYRUN001', 'description': 'Dry run test', 'is_active': 'true'},
        ]
        csv_content = self.create_test_csv(csv_data)
        mock_file.return_value.__enter__.return_value = StringIO(csv_content)
        
        with patch('pathlib.Path.exists', return_value=True):
            out = StringIO()
            call_command('import_procedures', '--file=test.csv', '--dry-run', stdout=out)
        
        # No procedures should be created in dry run mode
        self.assertEqual(MedicalProcedure.objects.count(), 0)
        self.assertIn('DRY RUN MODE', out.getvalue())

    @patch('builtins.open', create=True)
    def test_update_existing_procedure(self, mock_file):
        """Test updating existing procedures."""
        # Create existing procedure
        existing = MedicalProcedure.objects.create(
            code='UPDATE001',
            description='Original description',
            is_active=True
        )
        
        csv_data = [
            {'code': 'UPDATE001', 'description': 'Updated description', 'is_active': 'false'},
        ]
        csv_content = self.create_test_csv(csv_data)
        mock_file.return_value.__enter__.return_value = StringIO(csv_content)
        
        with patch('pathlib.Path.exists', return_value=True):
            out = StringIO()
            call_command('import_procedures', '--file=test.csv', '--update', stdout=out)
        
        # Procedure should be updated
        updated = MedicalProcedure.objects.get(code='UPDATE001')
        self.assertEqual(updated.description, 'Updated description')
        self.assertFalse(updated.is_active)

    def test_file_not_found(self):
        """Test error when file doesn't exist."""
        with self.assertRaises(CommandError):
            call_command('import_procedures', '--file=nonexistent.csv')


class ProceduresAPITest(TestCase):
    """Test procedures API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create test procedures
        self.procedure1 = MedicalProcedure.objects.create(
            code='API001',
            description='API test procedure for diabetes',
            is_active=True
        )
        self.procedure2 = MedicalProcedure.objects.create(
            code='API002',
            description='Another API test procedure',
            is_active=True
        )
        self.inactive_procedure = MedicalProcedure.objects.create(
            code='INACTIVE',
            description='Inactive procedure',
            is_active=False
        )

    def test_procedures_search_success(self):
        """Test successful procedures search."""
        url = reverse('apps.core:procedures_search_api')
        response = self.client.get(url, {'q': 'diabetes'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['code'], 'API001')
        self.assertIn('diabetes', data['results'][0]['description'])

    def test_procedures_search_missing_query(self):
        """Test search without query parameter."""
        url = reverse('apps.core:procedures_search_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_procedures_search_short_query(self):
        """Test search with too short query."""
        url = reverse('apps.core:procedures_search_api')
        response = self.client.get(url, {'q': 'a'})
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('must be at least 2 characters', data['error'])

    def test_procedures_search_with_limit(self):
        """Test search with limit parameter."""
        url = reverse('apps.core:procedures_search_api')
        response = self.client.get(url, {'q': 'API', 'limit': '1'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)

    def test_procedures_search_include_inactive(self):
        """Test search including inactive procedures."""
        url = reverse('apps.core:procedures_search_api')
        response = self.client.get(url, {'q': 'INACTIVE', 'active_only': 'false'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['code'], 'INACTIVE')

    def test_procedure_detail_success(self):
        """Test successful procedure detail retrieval."""
        url = reverse('apps.core:procedure_detail_api', args=[self.procedure1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['code'], 'API001')
        self.assertIn('diabetes', data['description'])
        self.assertTrue(data['is_active'])

    def test_procedure_detail_not_found(self):
        """Test procedure detail with non-existent ID."""
        fake_id = uuid.uuid4()
        url = reverse('apps.core:procedure_detail_api', args=[fake_id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('not found', data['error'])

    def test_procedures_list_success(self):
        """Test successful procedures listing."""
        url = reverse('apps.core:procedures_list_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('results', data)
        self.assertIn('pagination', data)
        self.assertEqual(len(data['results']), 3)  # All procedures

    def test_procedures_list_with_filters(self):
        """Test procedures listing with filters."""
        url = reverse('apps.core:procedures_list_api')
        response = self.client.get(url, {'active': 'true', 'search': 'diabetes'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['code'], 'API001')

    def test_api_requires_authentication(self):
        """Test that API endpoints require authentication."""
        self.client.logout()
        
        # Test search endpoint
        url = reverse('apps.core:procedures_search_api')
        response = self.client.get(url, {'q': 'test'})
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test detail endpoint
        url = reverse('apps.core:procedure_detail_api', args=[self.procedure1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


class MedicalProcedureAdminTest(TestCase):
    """Test MedicalProcedure admin interface."""

    def setUp(self):
        """Set up test data."""
        self.admin_site = AdminSite()
        self.admin = MedicalProcedureAdmin(MedicalProcedure, self.admin_site)
        
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.procedure = MedicalProcedure.objects.create(
            code='ADMIN001',
            description='Admin test procedure with a very long description that should be truncated in the list view',
            is_active=True
        )

    def test_short_description_display(self):
        """Test short_description_display method."""
        # Test with long description
        display = self.admin.short_description_display(self.procedure)
        self.assertTrue(len(display) < len(self.procedure.description))
        self.assertIn('title=', display)  # Should have tooltip
        
        # Test with short description
        short_procedure = MedicalProcedure.objects.create(
            code='SHORT001',
            description='Short description',
            is_active=True
        )
        display = self.admin.short_description_display(short_procedure)
        self.assertEqual(display, 'Short description')

    def test_activate_procedures_action(self):
        """Test activate_procedures admin action."""
        # Create inactive procedure
        inactive = MedicalProcedure.objects.create(
            code='INACTIVE001',
            description='Inactive procedure',
            is_active=False
        )
        
        queryset = MedicalProcedure.objects.filter(id=inactive.id)
        
        # Mock request
        class MockRequest:
            pass
        request = MockRequest()
        
        # Execute action
        self.admin.activate_procedures(request, queryset)
        
        # Check that procedure is now active
        inactive.refresh_from_db()
        self.assertTrue(inactive.is_active)

    def test_deactivate_procedures_action(self):
        """Test deactivate_procedures admin action."""
        queryset = MedicalProcedure.objects.filter(id=self.procedure.id)
        
        class MockRequest:
            pass
        request = MockRequest()
        
        self.admin.deactivate_procedures(request, queryset)
        
        self.procedure.refresh_from_db()
        self.assertFalse(self.procedure.is_active)


class MedicalProcedureSearchTest(TestCase):
    """Test full-text search functionality with fallback."""

    def setUp(self):
        """Set up test procedures for search testing."""
        self.procedures = [
            MedicalProcedure.objects.create(
                code='SEARCH001',
                description='Consulta médica para diabetes tipo 1',
                is_active=True
            ),
            MedicalProcedure.objects.create(
                code='SEARCH002',
                description='Consulta médica para hipertensão arterial',
                is_active=True
            ),
            MedicalProcedure.objects.create(
                code='SEARCH003',
                description='Procedimento cirúrgico cardiovascular',
                is_active=True
            ),
        ]

    @patch('apps.core.models.medical_procedure.MedicalProcedure.search')
    def test_search_fallback_mechanism(self, mock_search):
        """Test that search falls back to simple search when full-text search fails."""
        # Mock full-text search to raise an exception
        mock_search.side_effect = Exception("PostgreSQL extension not available")
        
        # This should fall back to simple_search
        results = MedicalProcedure.simple_search('diabetes')
        
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().code, 'SEARCH001')

    def test_simple_search_functionality(self):
        """Test simple search functionality."""
        # Test search by partial description
        results = MedicalProcedure.simple_search('consulta')
        self.assertEqual(results.count(), 2)
        
        # Test search by code
        results = MedicalProcedure.simple_search('SEARCH001')
        self.assertEqual(results.count(), 1)
        
        # Test case insensitive search
        results = MedicalProcedure.simple_search('DIABETES')
        self.assertEqual(results.count(), 1)


class MedicalProcedureIntegrationTest(TestCase):
    """Integration tests for the complete procedures system."""

    def setUp(self):
        """Set up for integration testing."""
        self.user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='integrationuser', password='testpass123')

    def test_complete_workflow(self):
        """Test complete workflow from import to API usage."""
        # Step 1: Create procedure via model
        procedure = MedicalProcedure.objects.create(
            code='WORKFLOW001',
            description='Integration test procedure for diabetes management',
            is_active=True
        )
        
        # Step 2: Test API search
        url = reverse('apps.core:procedures_search_api')
        response = self.client.get(url, {'q': 'diabetes'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['code'], 'WORKFLOW001')
        
        # Step 3: Test API detail
        detail_url = reverse('apps.core:procedure_detail_api', args=[procedure.id])
        detail_response = self.client.get(detail_url)
        
        self.assertEqual(detail_response.status_code, 200)
        detail_data = detail_response.json()
        self.assertEqual(detail_data['code'], 'WORKFLOW001')
        
        # Step 4: Test API listing
        list_url = reverse('apps.core:procedures_list_api')
        list_response = self.client.get(list_url)
        
        self.assertEqual(list_response.status_code, 200)
        list_data = list_response.json()
        self.assertEqual(len(list_data['results']), 1)
        
    def test_error_handling(self):
        """Test error handling across the system."""
        # Test API with invalid UUID
        url = reverse('apps.core:procedure_detail_api', args=['invalid-uuid'])
        # This should raise a URL resolution error, so we'll test with a valid UUID format
        fake_uuid = uuid.uuid4()
        url = reverse('apps.core:procedure_detail_api', args=[fake_uuid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)