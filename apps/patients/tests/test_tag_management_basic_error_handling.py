import json
import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from apps.patients.models import Patient, AllowedTag, Tag

User = get_user_model()

class TagManagementBasicErrorHandlingTests(TestCase):
    """Test basic error handling for invalid tag operations"""

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
            'tag_id': str(self.tag.pk)
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 404)

    def test_add_nonexistent_tag(self):
        """Test adding non-existent tag returns 400"""
        fake_tag_id = uuid.uuid4()
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            'tag_id': str(fake_tag_id)
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_add_inactive_tag(self):
        """Test adding inactive tag returns 400"""
        # Deactivate tag
        self.tag.is_active = False
        self.tag.save()
        
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            'tag_id': str(self.tag.pk)
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_add_duplicate_tag(self):
        """Test adding duplicate tag returns 400"""
        # First add the tag
        self.patient.tags.add(self.tag)
        
        # Try to add the same tag again
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            'tag_id': str(self.tag.pk)
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_add_tag_without_ajax(self):
        """Test non-AJAX request returns 400"""
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            'tag_id': str(self.tag.pk)
        })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_missing_tag_id_parameter(self):
        """Test missing tag_id parameter returns 400"""
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            # Missing tag_id
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_invalid_uuid_format(self):
        """Test invalid UUID format returns 400"""
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            'tag_id': 'invalid-uuid'
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_successful_tag_add(self):
        """Test successful tag add returns 200"""
        url = reverse('apps.patients:patient_tag_add', kwargs={'patient_id': self.patient.id})
        
        response = self.client.post(url, {
            'tag_id': str(self.tag.pk)
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('tags', data)
        
        # Verify tag was actually added
        self.assertTrue(
            self.patient.tags.filter(
                allowed_tag=self.tag
            ).exists()
        )

    def test_remove_existing_tag(self):
        """Test successful tag removal returns 200"""
        # First add the tag
        self.patient.tags.add(self.tag)
        
        # Get the tag instance
        tag_instance = self.patient.tags.get(allowed_tag=self.tag)
        
        url = reverse('apps.patients:patient_tag_remove', kwargs={
            'patient_id': self.patient.id,
            'tag_id': tag_instance.id
        })
        
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('tags', data)
        
        # Verify tag was actually removed
        self.assertFalse(
            self.patient.tags.filter(
                allowed_tag=self.tag
            ).exists()
        )

    def test_api_endpoint_returns_tags(self):
        """Test API endpoint returns current patient tags"""
        # Add a tag first
        self.patient.tags.add(self.tag)
        
        url = reverse('apps.patients:patient_tags_api', kwargs={'patient_id': self.patient.id})
        
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('tags', data)
        self.assertEqual(len(data['tags']), 1)
        self.assertEqual(data['tags'][0]['name'], self.tag.name)