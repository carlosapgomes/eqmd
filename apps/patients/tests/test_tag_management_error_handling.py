import json
import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.exceptions import PermissionDenied
from apps.patients.models import Patient, AllowedTag, Tag
from apps.core.permissions.utils import can_manage_patient_tags
from apps.events.models import Event, TagAddedEvent, TagRemovedEvent, TagBulkRemoveEvent

User = get_user_model()

class TagManagementErrorHandlingTests(TestCase):
    """Test error handling for invalid tag operations"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user with permission
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@example.com',
            password='testpass123'
        )
        
        # Add permission to user
        from django.contrib.auth.models import Permission
        change_patient_perm = Permission.objects.get(codename='change_patient')
        self.doctor.user_permissions.add(change_patient_perm)
        
        # Create patient
        self.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1990-01-01',
            gender='M',
            status=Patient.Status.INPATIENT,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Create allowed tag
        self.tag = AllowedTag.objects.create(
            name='Test Tag',
            color='blue',
            is_active=True,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Login
        self.client.login(username='doctor', password='testpass123')

    def test_add_tag_to_nonexistent_patient(self):
        """Test adding tag to non-existent patient returns 404"""
        fake_uuid = uuid.uuid4()
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': fake_uuid})
        
        response = self.client.post(url, {
            'tag_id': str(self.tag.id)
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 404)

    def test_remove_tag_from_nonexistent_patient(self):
        """Test removing tag from non-existent patient returns 404"""
        fake_uuid = uuid.uuid4()
        url = reverse('apps.patients:patient_tag_remove', kwargs={
            'patient_id': fake_uuid,
            'tag_id': self.tag.pk
        })
        
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 404)
        # HTML response for 404, not JSON
        self.assertEqual(response.status_code, 404)

    def test_add_nonexistent_tag(self):
        """Test adding non-existent tag returns 400"""
        fake_tag_id = uuid.uuid4()
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            'tag_id': str(fake_tag_id)
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        # HTML response for 404, not JSON
        self.assertEqual(response.status_code, 404)

    def test_remove_nonexistent_tag(self):
        """Test removing non-existent tag returns 400"""
        fake_tag_id = uuid.uuid4()
        url = reverse('apps.patients:patient_tag_remove', kwargs={
            'patient_id': self.patient.id,
            'tag_id': fake_tag_id
        })
        
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        # HTML response for 404, not JSON
        self.assertEqual(response.status_code, 404)

    def test_remove_tag_not_assigned_to_patient(self):
        """Test removing tag that's not assigned to patient returns 400"""
        # Tag exists but not assigned to patient
        url = reverse('apps.patients:patient_tag_remove', kwargs={
            'patient_id': self.patient.id,
            'tag_id': self.tag.pk
        })
        
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('not assigned', data['error'])

    def test_add_inactive_tag(self):
        """Test adding inactive tag returns 400"""
        # Deactivate tag
        self.tag.is_active = False
        self.tag.save()
        
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            'tag_id': str(self.tag.id)
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('inactive', data['error'])

    def test_add_duplicate_tag(self):
        """Test adding duplicate tag returns 400"""
        # First add the tag
        Tag.objects.create(
            patient=self.patient,
            allowed_tag=self.tag,
            created_by=self.doctor,
            updated_by=self.doctor
        )
        
        # Try to add the same tag again
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            'tag_id': str(self.tag.id)
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('already assigned', data['error'])

    def test_bulk_remove_no_tags(self):
        """Test bulk remove when patient has no tags"""
        url = reverse('apps.patients:patient_tag_remove_all', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('no tags', data['error'])

    def test_add_tag_without_ajax(self):
        """Test non-AJAX request returns 400"""
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            'tag_id': str(self.tag.id)
        })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('AJAX', data['error'])

    def test_remove_tag_without_ajax(self):
        """Test non-AJAX request returns 400"""
        url = reverse('apps.patients:patient_tag_remove', kwargs={
            'patient_id': self.patient.id,
            'tag_id': self.tag.pk
        })
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('AJAX', data['error'])

    def test_invalid_uuid_format(self):
        """Test invalid UUID format returns 400"""
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            'tag_id': 'invalid-uuid'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('invalid UUID', data['error'])

    def test_missing_tag_id_parameter(self):
        """Test missing tag_id parameter returns 400"""
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            # Missing tag_id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('tag_id', data['error'])

    def test_api_invalid_patient_id(self):
        """Test API endpoint with invalid patient ID"""
        fake_uuid = uuid.uuid4()
        url = reverse('apps.patients:patient_tags_api', kwargs={'patient_id': fake_uuid})
        
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 404)
        # HTML response for 404, not JSON
        self.assertEqual(response.status_code, 404)

    def test_permission_denied_error_format(self):
        """Test permission denied errors are properly formatted"""
        # Create user without permission
        no_permission_user = User.objects.create_user(
            username='noperm',
            email='noperm@example.com',
            password='testpass123'
        )
        self.client.login(username='noperm', password='testpass123')
        
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            'tag_id': str(self.tag.id)
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('permission', data['error'])

    def test_database_error_handling(self):
        """Test database errors are handled gracefully"""
        # Mock a database error
        original_save = Tag.objects.create
        def mock_save(*args, **kwargs):
            raise Exception("Database connection error")
        
        Tag.objects.create = mock_save
        
        try:
            url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
            
            response = self.client.post(url, {
                'tag_id': str(self.tag.id)
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.content)
            self.assertIn('error', data)
            self.assertIn('server error', data['error'])
        finally:
            # Restore original method
            Tag.objects.create = original_save

    def test_event_creation_failure(self):
        """Test handling when event creation fails"""
        # Mock event creation to fail
        original_create = Event.objects.create
        def mock_create(*args, **kwargs):
            raise Exception("Event creation failed")
        
        Event.objects.create = mock_create
        
        try:
            url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
            
            response = self.client.post(url, {
                'tag_id': str(self.tag.id)
            }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            
            # Should still succeed but log the error
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertIn('tags', data)
            
            # Verify tag was added despite event creation failure
            self.assertTrue(
                Tag.objects.filter(
                    patient=self.patient,
                    allowed_tag=self.tag
                ).exists()
            )
        finally:
            # Restore original method
            Event.objects.create = original_create