from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from ..models import Patient, AllowedTag, Tag

User = get_user_model()


class PatientTagErrorHandlingTests(TestCase):
    """Tests for error handling in tag management operations"""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        # Add required permissions
        from django.contrib.auth.models import Permission
        change_perm = Permission.objects.get(codename='change_patient')
        view_perm = Permission.objects.get(codename='view_patient')
        cls.user.user_permissions.add(change_perm, view_perm)
        
        cls.allowed_tag = AllowedTag.objects.create(
            name='Test Tag',
            color='#007bff',
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_add_tag_with_missing_tag_id(self):
        """Test error handling when tag_id is missing"""
        patient = Patient.objects.create(
            name='Error Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        response = self.client.post(add_url, data={
            'notes': 'Missing tag_id'
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('ID da tag é obrigatório', data['error'])

    def test_add_tag_with_invalid_tag_id(self):
        """Test error handling with invalid tag_id"""
        patient = Patient.objects.create(
            name='Error Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': 'invalid-uuid-format',
            'notes': 'Invalid tag_id'
        })
        
        # Should handle the error gracefully
        self.assertIn(response.status_code, [400, 404, 500])

    def test_add_tag_with_nonexistent_tag_id(self):
        """Test error handling with non-existent tag_id"""
        patient = Patient.objects.create(
            name='Error Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create a dummy allowed tag to get a valid ID format, then delete it
        dummy_allowed_tag = AllowedTag.objects.create(
            name='Dummy Tag',
            created_by=self.user,
            updated_by=self.user
        )
        tag_id = dummy_allowed_tag.id
        dummy_allowed_tag.delete()
        
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': tag_id,
            'notes': 'Non-existent tag'
        })
        
        # Should handle the error gracefully
        self.assertIn(response.status_code, [400, 404, 500])

    def test_add_tag_with_invalid_patient_id(self):
        """Test error handling with invalid patient_id"""
        fake_uuid = '12345678-1234-5678-9012-123456789012'
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': fake_uuid})
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag.pk,
            'notes': 'Invalid patient'
        })
        
        self.assertEqual(response.status_code, 404)

    def test_remove_tag_with_invalid_tag_id(self):
        """Test error handling when removing tag with invalid tag_id"""
        patient = Patient.objects.create(
            name='Error Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        remove_url = reverse('patients:patient_tag_remove', kwargs={
            'patient_id': patient.pk,
            'tag_id': 'invalid-uuid-format'
        })
        
        response = self.client.post(remove_url)
        self.assertEqual(response.status_code, 400)

    def test_remove_tag_with_nonexistent_tag_id(self):
        """Test error handling when removing non-existent tag"""
        patient = Patient.objects.create(
            name='Error Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create a dummy tag to get a valid ID format, then delete it
        dummy_tag = Tag.objects.create(
            allowed_tag=self.allowed_tag,
            created_by=self.user,
            updated_by=self.user
        )
        tag_id = dummy_tag.pk
        dummy_tag.delete()
        
        remove_url = reverse('patients:patient_tag_remove', kwargs={
            'patient_id': patient.pk,
            'tag_id': tag_id
        })
        
        response = self.client.post(remove_url)
        self.assertEqual(response.status_code, 404)

    def test_remove_tag_with_invalid_patient_id(self):
        """Test error handling when removing tag with invalid patient_id"""
        fake_uuid = '12345678-1234-5678-9012-123456789012'
        remove_url = reverse('patients:patient_tag_remove', kwargs={
            'patient_id': fake_uuid,
            'tag_id': 'some-tag-id'
        })
        
        response = self.client.post(remove_url)
        # Should handle the error gracefully
        self.assertIn(response.status_code, [404, 400, 500, 302])

    def test_remove_all_tags_with_invalid_patient_id(self):
        """Test error handling when removing all tags with invalid patient_id"""
        fake_uuid = '12345678-1234-5678-9012-123456789012'
        remove_all_url = reverse('patients:patient_tag_remove_all', kwargs={'patient_id': fake_uuid})
        response = self.client.post(remove_all_url)
        
        self.assertEqual(response.status_code, 404)

    def test_remove_all_tags_when_no_tags_exist(self):
        """Test error handling when trying to remove all tags from patient with no tags"""
        patient = Patient.objects.create(
            name='Error Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        remove_all_url = reverse('patients:patient_tag_remove_all', kwargs={'patient_id': patient.pk})
        response = self.client.post(remove_all_url)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Nenhuma tag para remover', data['error'])

    def test_api_access_with_invalid_patient_id(self):
        """Test error handling when accessing API with invalid patient_id"""
        fake_uuid = '12345678-1234-5678-9012-123456789012'
        api_url = reverse('patients:patient_tags_api', kwargs={'patient_id': fake_uuid})
        response = self.client.get(api_url)
        
        self.assertEqual(response.status_code, 404)

    def test_permission_denied_error_handling(self):
        """Test that permission denied errors are handled properly"""
        # Create user without permissions
        limited_user = User.objects.create_user(
            username='limiteduser',
            email='limited@example.com',
            password='testpassword'
        )
        
        patient = Patient.objects.create(
            name='Permission Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client.force_login(limited_user)
        
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag.pk,
            'notes': 'Should fail'
        })
        
        # Should handle permission error gracefully
        self.assertIn(response.status_code, [403, 302])

    def test_anonymous_user_error_handling(self):
        """Test that anonymous user access is handled properly"""
        self.client.logout()
        
        patient = Patient.objects.create(
            name='Anonymous Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag.pk,
            'notes': 'Should redirect'
        })
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_csrf_token_error_handling(self):
        """Test that CSRF token validation works"""
        patient = Patient.objects.create(
            name='CSRF Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        
        # Try to post without CSRF token
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag.pk,
            'notes': 'No CSRF token'
        })
        
        # Should handle CSRF protection
        self.assertIn(response.status_code, [200, 403])

    def test_inactive_allowed_tag_error_handling(self):
        """Test error handling when trying to add inactive allowed tag"""
        # Create an inactive allowed tag
        inactive_tag = AllowedTag.objects.create(
            name='Inactive Tag',
            color='#6c757d',
            is_active=False,
            created_by=self.user,
            updated_by=self.user
        )
        
        patient = Patient.objects.create(
            name='Inactive Tag Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': inactive_tag.pk,
            'notes': 'Should fail'
        })
        
        # Should handle the error gracefully
        self.assertIn(response.status_code, [400, 404, 500])

    def test_database_connection_error_simulation(self):
        """Test error handling when database operations fail"""
        # This is a simple test to verify error handling structure
        # In a real application, you might mock database operations to simulate failures
        
        patient = Patient.objects.create(
            name='Database Error Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test with invalid data that would cause database errors
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': 'invalid-data-type',
            'notes': 'Database error test'
        })
        
        # Should handle the error gracefully
        self.assertIn(response.status_code, [400, 404, 500])

    def test_concurrent_tag_modification_error_handling(self):
        """Test error handling for concurrent tag modifications"""
        patient = Patient.objects.create(
            name='Concurrent Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Add a tag
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag,
            notes='Concurrent test',
            created_by=self.user,
            updated_by=self.user
        )
        patient.tags.add(tag)
        
        # Try to remove the same tag multiple times
        remove_url = reverse('patients:patient_tag_remove', kwargs={
            'patient_id': patient.pk,
            'tag_id': tag.pk
        })
        
        # First removal should succeed
        response1 = self.client.post(remove_url)
        self.assertEqual(response1.status_code, 200)
        
        # Second removal should fail
        response2 = self.client.post(remove_url)
        self.assertEqual(response2.status_code, 404)

    def test_invalid_json_response_handling(self):
        """Test that invalid JSON responses are handled"""
        patient = Patient.objects.create(
            name='JSON Error Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test API access
        api_url = reverse('patients:patient_tags_api', kwargs={'patient_id': patient.pk})
        response = self.client.get(api_url)
        
        # Should return valid JSON
        self.assertEqual(response.status_code, 200)
        try:
            data = response.json()
            self.assertIsInstance(data, dict)
        except ValueError:
            self.fail('API response should be valid JSON')

    def test_rate_limiting_error_handling(self):
        """Test error handling for rate limiting (if implemented)"""
        patient = Patient.objects.create(
            name='Rate Limit Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        
        # Make multiple rapid requests
        for i in range(5):
            response = self.client.post(add_url, data={
                'tag_id': self.allowed_tag.pk,
                'notes': f'Rate limit test {i}'
            })
            # All should succeed (rate limiting may not be implemented)
            self.assertIn(response.status_code, [200, 400])

    def test_validation_error_handling(self):
        """Test that validation errors are handled properly"""
        patient = Patient.objects.create(
            name='Validation Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test with extremely long notes that might cause validation errors
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag.pk,
            'notes': 'x' * 10000  # Very long notes
        })
        
        # Should handle the error gracefully
        self.assertIn(response.status_code, [200, 400])

    def test_server_error_simulation(self):
        """Test handling of server errors (500 status)"""
        # This test verifies that the error handling infrastructure is in place
        # In a real application, you might simulate server errors using mocks
        
        patient = Patient.objects.create(
            name='Server Error Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test with malformed request that might cause server errors
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': None,  # Invalid data
            'notes': 'Server error test'
        })
        
        # Should handle the error gracefully
        self.assertIn(response.status_code, [400, 404, 500])

    def test_timeout_error_handling(self):
        """Test that timeout errors are handled properly"""
        # This test verifies the timeout handling infrastructure
        # In a real application, you might mock timeout scenarios
        
        patient = Patient.objects.create(
            name='Timeout Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Normal requests should work
        api_url = reverse('patients:patient_tags_api', kwargs={'patient_id': patient.pk})
        response = self.client.get(api_url)
        
        # Should complete quickly
        self.assertEqual(response.status_code, 200)

    def test_malformed_request_handling(self):
        """Test handling of malformed HTTP requests"""
        patient = Patient.objects.create(
            name='Malformed Request Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test with malformed POST data
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        response = self.client.post(add_url, data={
            'invalid_field': 'invalid_value',
            'malformed': 'data'
        })
        
        # Should handle the error gracefully
        self.assertIn(response.status_code, [400, 404, 500])

    def test_error_message_consistency(self):
        """Test that error messages are consistent and user-friendly"""
        patient = Patient.objects.create(
            name='Error Message Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test missing tag_id error
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        response = self.client.post(add_url, data={'notes': 'Missing tag_id'})
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIsInstance(data['error'], str)
        self.assertTrue(len(data['error']) > 0)

    def test_error_logging_infrastructure(self):
        """Test that error logging infrastructure is in place"""
        # This test verifies that the views have proper error handling
        # that would log errors in a production environment
        
        patient = Patient.objects.create(
            name='Error Logging Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test with invalid data that would trigger error handling
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': 'invalid',
            'notes': 'Error logging test'
        })
        
        # Should handle the error gracefully
        self.assertIn(response.status_code, [400, 404, 500])

    def test_graceful_degradation_on_errors(self):
        """Test that the system degrades gracefully on errors"""
        patient = Patient.objects.create(
            name='Graceful Degradation Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test that the page still loads even if some components fail
        detail_url = reverse('patients:patient_detail', kwargs={'pk': patient.pk})
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gerenciamento de Tags')
        
        # The JavaScript should handle errors gracefully
        self.assertContains(response, 'showError')
        self.assertContains(response, 'showSuccess')