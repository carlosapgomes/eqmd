"""
Test suite for ICD-10 (CID) codes functionality.
Tests model, management command, API endpoints, and admin interface.
"""

import json
import uuid
from io import StringIO
from unittest.mock import patch
import csv
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from django.contrib.admin.sites import AdminSite
from apps.core.admin import MedicalProcedureAdmin
from apps.core.models import Icd10Code

User = get_user_model()


class Icd10CodeModelTest(TestCase):
    """Test Icd10Code model functionality."""

    def setUp(self):
        self.code = Icd10Code.objects.create(
            code='A00',
            description='Colera',
            is_active=True
        )

    def test_model_creation(self):
        self.assertEqual(self.code.code, 'A00')
        self.assertEqual(self.code.description, 'Colera')
        self.assertTrue(self.code.is_active)
        self.assertIsNotNone(self.code.id)
        self.assertIsNotNone(self.code.created_at)
        self.assertIsNotNone(self.code.updated_at)

    def test_str_representation(self):
        expected = "A00 - Colera"
        self.assertEqual(str(self.code), expected)

    def test_short_description_property(self):
        long_code = Icd10Code.objects.create(
            code='TEST001',
            description='A' * 150,
            is_active=True
        )
        self.assertEqual(len(long_code.short_description), 100)
        self.assertTrue(long_code.short_description.endswith('...'))

    def test_get_display_text(self):
        expected = "A00 - Colera"
        self.assertEqual(self.code.get_display_text(), expected)

    def test_code_uppercase_on_save(self):
        code = Icd10Code.objects.create(
            code='a01',
            description='Test code',
            is_active=True
        )
        self.assertEqual(code.code, 'A01')

    def test_unique_code_constraint(self):
        with self.assertRaises(Exception):
            Icd10Code.objects.create(
                code='A00',
                description='Duplicate code',
                is_active=True
            )

    def test_active_classmethod(self):
        Icd10Code.objects.create(
            code='INACTIVE001',
            description='Inactive code',
            is_active=False
        )

        active_codes = Icd10Code.active()
        self.assertEqual(active_codes.count(), 1)
        self.assertEqual(active_codes.first().code, 'A00')

    def test_simple_search_classmethod(self):
        results = Icd10Code.simple_search('A00')
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().code, 'A00')

        results = Icd10Code.simple_search('Colera')
        self.assertEqual(results.count(), 1)

        results = Icd10Code.simple_search('colera')
        self.assertEqual(results.count(), 1)

        results = Icd10Code.simple_search('nonexistent')
        self.assertEqual(results.count(), 0)

        results = Icd10Code.simple_search('')
        self.assertEqual(results.count(), 0)


class ImportIcd10CodesCommandTest(TestCase):
    """Test import_icd10_codes management command."""

    def create_test_csv(self, data):
        csv_content = StringIO()
        writer = csv.DictWriter(csv_content, fieldnames=['codigo', 'descricao', 'is_active'])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        return csv_content.getvalue()

    def create_test_json(self, data):
        return json.dumps(data)

    @patch('builtins.open', create=True)
    def test_import_csv_success(self, mock_file):
        csv_data = [
            {'codigo': 'A00', 'descricao': 'Colera', 'is_active': 'true'},
            {'codigo': 'A01', 'descricao': 'Febre tifoide', 'is_active': 'false'},
        ]
        csv_content = self.create_test_csv(csv_data)
        mock_file.return_value.__enter__.return_value = StringIO(csv_content)

        with patch('pathlib.Path.exists', return_value=True):
            out = StringIO()
            call_command('import_icd10_codes', '--file=test.csv', stdout=out)

        self.assertEqual(Icd10Code.objects.count(), 2)
        code1 = Icd10Code.objects.get(code='A00')
        self.assertTrue(code1.is_active)
        code2 = Icd10Code.objects.get(code='A01')
        self.assertFalse(code2.is_active)

    @patch('builtins.open', create=True)
    def test_import_json_success(self, mock_file):
        json_data = [
            {'code': 'B00', 'description': 'Herpes', 'is_active': True},
            {'code': 'B01', 'description': 'Varicela', 'is_active': False},
        ]
        json_content = self.create_test_json(json_data)
        mock_file.return_value.__enter__.return_value = StringIO(json_content)

        with patch('pathlib.Path.exists', return_value=True):
            out = StringIO()
            call_command('import_icd10_codes', '--file=test.json', stdout=out)

        self.assertEqual(Icd10Code.objects.count(), 2)

    @patch('builtins.open', create=True)
    def test_dry_run_mode(self, mock_file):
        csv_data = [
            {'codigo': 'C00', 'descricao': 'Dry run', 'is_active': 'true'},
        ]
        csv_content = self.create_test_csv(csv_data)
        mock_file.return_value.__enter__.return_value = StringIO(csv_content)

        with patch('pathlib.Path.exists', return_value=True):
            out = StringIO()
            call_command('import_icd10_codes', '--file=test.csv', '--dry-run', stdout=out)

        self.assertEqual(Icd10Code.objects.count(), 0)
        self.assertIn('DRY RUN MODE', out.getvalue())

    @patch('builtins.open', create=True)
    def test_update_existing_code(self, mock_file):
        Icd10Code.objects.create(
            code='D00',
            description='Original description',
            is_active=True
        )

        csv_data = [
            {'codigo': 'D00', 'descricao': 'Updated description', 'is_active': 'false'},
        ]
        csv_content = self.create_test_csv(csv_data)
        mock_file.return_value.__enter__.return_value = StringIO(csv_content)

        with patch('pathlib.Path.exists', return_value=True):
            out = StringIO()
            call_command('import_icd10_codes', '--file=test.csv', '--update', stdout=out)

        updated = Icd10Code.objects.get(code='D00')
        self.assertEqual(updated.description, 'Updated description')
        self.assertFalse(updated.is_active)

    def test_file_not_found(self):
        with self.assertRaises(CommandError):
            call_command('import_icd10_codes', '--file=nonexistent.csv')


class Icd10CodesAPITest(TestCase):
    """Test ICD-10 API endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.password_change_required = False
        self.user.terms_accepted = True
        self.user.account_status = 'active'
        self.user.save(update_fields=['password_change_required', 'terms_accepted', 'account_status'])
        self.client.force_login(self.user)

        self.code1 = Icd10Code.objects.create(
            code='E00',
            description='Iodo deficiente',
            is_active=True
        )
        self.code2 = Icd10Code.objects.create(
            code='E01',
            description='Outra doenca',
            is_active=True
        )
        self.inactive_code = Icd10Code.objects.create(
            code='E02',
            description='Inactive code',
            is_active=False
        )

    def test_icd10_search_success(self):
        url = reverse('apps.core:icd10_search_api')
        response = self.client.get(url, {'q': 'Iodo'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['code'], 'E00')

    def test_icd10_search_missing_query(self):
        url = reverse('apps.core:icd10_search_api')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_icd10_search_short_query(self):
        url = reverse('apps.core:icd10_search_api')
        response = self.client.get(url, {'q': 'a'})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('at least 2 characters', data['error'])

    def test_icd10_search_with_limit(self):
        url = reverse('apps.core:icd10_search_api')
        response = self.client.get(url, {'q': 'E0', 'limit': '1'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)

    def test_icd10_search_include_inactive(self):
        url = reverse('apps.core:icd10_search_api')
        response = self.client.get(url, {'q': 'E02', 'active_only': 'false'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['code'], 'E02')

    def test_icd10_detail_success(self):
        url = reverse('apps.core:icd10_detail_api', args=[self.code1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['code'], 'E00')

    def test_icd10_detail_not_found(self):
        fake_id = uuid.uuid4()
        url = reverse('apps.core:icd10_detail_api', args=[fake_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('not found', data['error'])

    def test_icd10_list_success(self):
        url = reverse('apps.core:icd10_list_api')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 3)

    def test_icd10_list_with_filters(self):
        url = reverse('apps.core:icd10_list_api')
        response = self.client.get(url, {'active': 'true', 'search': 'Iodo'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['code'], 'E00')

    def test_api_requires_authentication(self):
        self.client.logout()

        url = reverse('apps.core:icd10_search_api')
        response = self.client.get(url, {'q': 'test'})
        self.assertEqual(response.status_code, 302)

        url = reverse('apps.core:icd10_detail_api', args=[self.code1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


class Icd10AdminTest(TestCase):
    """Test ICD-10 admin interface."""

    def setUp(self):
        self.admin_site = AdminSite()
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.code = Icd10Code.objects.create(
            code='F00',
            description='A' * 120,
            is_active=True
        )

    def test_short_description_display(self):
        from apps.core.admin import Icd10CodeAdmin

        admin = Icd10CodeAdmin(Icd10Code, self.admin_site)
        display = admin.short_description_display(self.code)
        self.assertIn('title=', display)
        self.assertIn('...', display)
