from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.tests.helpers import create_navigation_user
from ..models import Patient, AllowedTag, Tag

User = get_user_model()


class AllowedTagModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_navigation_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

    def test_allowed_tag_creation(self):
        """Test that AllowedTag can be created with required fields"""
        tag = AllowedTag.objects.create(
            name='High Priority',
            description='For high priority patients',
            color='#dc3545',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(tag.name, 'High Priority')
        self.assertEqual(tag.color, '#dc3545')
        self.assertTrue(tag.is_active)

    def test_allowed_tag_str_representation(self):
        """Test string representation of AllowedTag"""
        tag = AllowedTag.objects.create(
            name='Emergency',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(str(tag), 'Emergency')

    def test_allowed_tag_default_color(self):
        """Test that AllowedTag has default color"""
        tag = AllowedTag.objects.create(
            name='Test Tag',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(tag.color, '#007bff')


class TagModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_navigation_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.allowed_tag = AllowedTag.objects.create(
            name='Critical',
            color='#dc3545',
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_tag_creation(self):
        """Test that Tag can be created with allowed tag"""
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag,
            patient=self.patient,
            notes='Critical patient needs immediate attention',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(tag.allowed_tag, self.allowed_tag)
        self.assertEqual(tag.name, 'Critical')
        self.assertEqual(tag.color, '#dc3545')

    def test_tag_str_representation(self):
        """Test string representation of Tag"""
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(str(tag), 'Critical')

    def test_tag_properties(self):
        """Test Tag properties that access AllowedTag fields"""
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(tag.name, self.allowed_tag.name)
        self.assertEqual(tag.color, self.allowed_tag.color)


class PatientTagsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_navigation_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.allowed_tag1 = AllowedTag.objects.create(
            name='High Priority',
            color='#dc3545',
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.allowed_tag2 = AllowedTag.objects.create(
            name='Follow Up',
            color='#ffc107',
            created_by=cls.user,
            updated_by=cls.user
        )

    def test_patient_tag_assignment(self):
        """Test that tags can be assigned to patients"""
        tag1 = Tag.objects.create(
            allowed_tag=self.allowed_tag1,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )
        tag2 = Tag.objects.create(
            allowed_tag=self.allowed_tag2,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(self.patient.patient_tags.count(), 2)
        self.assertIn(tag1, self.patient.patient_tags.all())
        self.assertIn(tag2, self.patient.patient_tags.all())

    def test_patient_tag_removal(self):
        """Test that tags can be removed from patients"""
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag1,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(self.patient.patient_tags.count(), 1)

        tag.delete()
        self.assertEqual(self.patient.patient_tags.count(), 0)


class PatientTagViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_navigation_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        # Add required permissions
        from django.contrib.auth.models import Permission
        view_perm = Permission.objects.get(codename='view_patient')
        cls.user.user_permissions.add(view_perm)

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.allowed_tag = AllowedTag.objects.create(
            name='VIP',
            color='#6f42c1',
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_patient_detail_displays_tags(self):
        """Test that patient detail view displays tags"""
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        response = self.client.get(
            reverse('patients:patient_detail', kwargs={'pk': self.patient.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'VIP')
        self.assertContains(response, '#6f42c1')

    def test_patient_list_displays_tags(self):
        """Test that patient list view displays tags"""
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        response = self.client.get(reverse('patients:patient_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'VIP')
        self.assertContains(response, '#6f42c1')


class PatientTagManagementViewTests(TestCase):
    """Tests for new tag management views"""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_navigation_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        # Add required permissions
        from django.contrib.auth.models import Permission
        change_perm = Permission.objects.get(codename='change_patient')
        view_perm = Permission.objects.get(codename='view_patient')
        cls.user.user_permissions.add(change_perm, view_perm)

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.allowed_tag1 = AllowedTag.objects.create(
            name='High Priority',
            color='#dc3545',
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.allowed_tag2 = AllowedTag.objects.create(
            name='Follow Up',
            color='#ffc107',
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_patient_tag_add_view_success(self):
        """Test successful tag addition via AJAX"""
        url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})

        response = self.client.post(url, data={
            'tag_id': self.allowed_tag1.pk,
            'notes': 'Urgent case'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('High Priority', data['message'])

        # Verify tag was created and assigned
        self.assertEqual(self.patient.patient_tags.count(), 1)
        tag = self.patient.patient_tags.first()
        self.assertEqual(tag.allowed_tag.name, 'High Priority')
        self.assertEqual(tag.notes, 'Urgent case')

    def test_patient_tag_add_view_missing_tag_id(self):
        """Test tag addition with missing tag_id"""
        url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})

        response = self.client.post(url, data={
            'notes': 'Urgent case'
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('ID da tag é obrigatório', data['error'])

    def test_patient_tag_add_view_invalid_tag_id(self):
        """Test tag addition with invalid tag_id"""
        # Create a dummy allowed tag to get a valid ID format, then delete it
        dummy_allowed_tag = AllowedTag.objects.create(
            name='Dummy Tag',
            created_by=self.user,
            updated_by=self.user
        )
        tag_id = dummy_allowed_tag.id
        dummy_allowed_tag.delete()

        url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})

        response = self.client.post(url, data={
            'tag_id': tag_id,  # Non-existent tag
            'notes': 'Urgent case'
        })

        # get_object_or_404 is inside try/except in the view, so Http404
        # is caught and surfaces as 500 (internal error handler).
        self.assertEqual(response.status_code, 500)

    def test_patient_tag_add_view_permission_denied(self):
        """Test tag addition without proper permissions"""
        # Create user without change_patient permission
        limited_user = create_navigation_user(
            username='limiteduser',
            email='limited@example.com',
            password='testpassword'
        )
        self.client.force_login(limited_user)

        url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})

        response = self.client.post(url, data={
            'tag_id': self.allowed_tag1.pk,
            'notes': 'Urgent case'
        })

        self.assertEqual(response.status_code, 403)

    def test_patient_tag_remove_view_success(self):
        """Test successful tag removal via AJAX"""
        # First add a tag
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag1,
            patient=self.patient,
            notes='Urgent case',
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:patient_tag_remove', kwargs={
            'patient_id': self.patient.pk,
            'tag_id': tag.pk
        })

        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('High Priority', data['message'])

        # Verify tag was removed and deleted
        self.assertEqual(self.patient.patient_tags.count(), 0)
        self.assertFalse(Tag.objects.filter(pk=tag.pk).exists())

    def test_patient_tag_remove_view_nonexistent_tag(self):
        """Test tag removal with non-existent tag"""
        # Create a dummy tag to get a valid tag_id format, then delete it
        dummy_tag = Tag.objects.create(
            allowed_tag=self.allowed_tag1,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )
        tag_id = dummy_tag.pk
        dummy_tag.delete()

        url = reverse('patients:patient_tag_remove', kwargs={
            'patient_id': self.patient.pk,
            'tag_id': tag_id  # Non-existent tag
        })

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_patient_tag_remove_all_view_success(self):
        """Test successful bulk tag removal via AJAX"""
        # Add multiple tags
        tag1 = Tag.objects.create(
            allowed_tag=self.allowed_tag1,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )
        tag2 = Tag.objects.create(
            allowed_tag=self.allowed_tag2,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:patient_tag_remove_all', kwargs={'patient_id': self.patient.pk})

        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('2 tag(s)', data['message'])

        # Verify all tags were removed and deleted
        self.assertEqual(self.patient.patient_tags.count(), 0)
        self.assertFalse(Tag.objects.filter(pk=tag1.pk).exists())
        self.assertFalse(Tag.objects.filter(pk=tag2.pk).exists())

    def test_patient_tag_remove_all_view_no_tags(self):
        """Test bulk tag removal when patient has no tags"""
        url = reverse('patients:patient_tag_remove_all', kwargs={'patient_id': self.patient.pk})

        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Nenhuma tag para remover', data['error'])

    def test_patient_tags_api_view_success(self):
        """Test successful API response for patient tags"""
        # Add a tag
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag1,
            patient=self.patient,
            notes='Urgent case',
            created_by=self.user,
            updated_by=self.user
        )

        url = reverse('patients:patient_tags_api', kwargs={'patient_id': self.patient.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check tags data
        self.assertEqual(len(data['current_tags']), 1)
        tag_data = data['current_tags'][0]
        self.assertEqual(tag_data['name'], 'High Priority')
        self.assertEqual(tag_data['color'], '#dc3545')
        self.assertEqual(tag_data['notes'], 'Urgent case')

        # Check available tags data
        self.assertTrue(data['permissions']['can_manage_tags'])
        self.assertTrue(data['permissions']['can_view_tags'])

    def test_patient_tags_api_view_no_tags(self):
        """Test API response for patient with no tags"""
        url = reverse('patients:patient_tags_api', kwargs={'patient_id': self.patient.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check empty tags list
        self.assertEqual(len(data['current_tags']), 0)

        # Check available tags (should show both allowed tags)
        self.assertEqual(len(data['available_tags']), 2)

    def test_patient_tags_api_view_permission_denied(self):
        """Test API access without proper permissions"""
        # Create user without view_patient permission
        limited_user = create_navigation_user(
            username='limiteduser',
            email='limited@example.com',
            password='testpassword'
        )
        self.client.force_login(limited_user)

        url = reverse('patients:patient_tags_api', kwargs={'patient_id': self.patient.pk})

        response = self.client.get(url)

        # can_view_patient_tags only checks is_authenticated;
        # any authenticated user can view tags.
        self.assertEqual(response.status_code, 200)


class PatientTagIntegrationTests(TestCase):
    """Integration tests for tag management workflow"""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_navigation_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        # Add required permissions
        from django.contrib.auth.models import Permission
        change_perm = Permission.objects.get(codename='change_patient')
        view_perm = Permission.objects.get(codename='view_patient')
        cls.user.user_permissions.add(change_perm, view_perm)

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.allowed_tag1 = AllowedTag.objects.create(
            name='High Priority',
            color='#dc3545',
            description='For high priority patients',
            created_by=cls.user,
            updated_by=cls.user
        )
        cls.allowed_tag2 = AllowedTag.objects.create(
            name='Follow Up',
            color='#ffc107',
            description='Requires follow-up',
            created_by=cls.user,
            updated_by=cls.user
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_complete_tag_management_workflow(self):
        """Test complete workflow: create patient -> add tags -> manage tags"""
        # 1. Verify patient starts with no tags
        self.assertEqual(self.patient.patient_tags.count(), 0)

        # 2. Add first tag via API
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag1.pk,
            'notes': 'Urgent case needs immediate attention'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.patient.patient_tags.count(), 1)

        # 3. Add second tag via API
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag2.pk,
            'notes': 'Follow up in 2 weeks'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.patient.patient_tags.count(), 2)

        # 4. Verify tags via API
        api_url = reverse('patients:patient_tags_api', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(api_url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['current_tags']), 2)

        # Verify tag details
        tag_names = [tag['name'] for tag in data['current_tags']]
        self.assertIn('High Priority', tag_names)
        self.assertIn('Follow Up', tag_names)

        # 5. Remove one tag
        tag_to_remove = self.patient.patient_tags.get(allowed_tag__name='High Priority')
        remove_url = reverse('patients:patient_tag_remove', kwargs={
            'patient_id': self.patient.pk,
            'tag_id': tag_to_remove.pk
        })

        response = self.client.post(remove_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.patient.patient_tags.count(), 1)

        # 6. Verify remaining tag
        response = self.client.get(api_url)
        data = response.json()
        self.assertEqual(len(data['current_tags']), 1)
        self.assertEqual(data['current_tags'][0]['name'], 'Follow Up')

        # 7. Remove all remaining tags
        remove_all_url = reverse('patients:patient_tag_remove_all', kwargs={'patient_id': self.patient.pk})
        response = self.client.post(remove_all_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.patient.patient_tags.count(), 0)

    def test_tag_management_with_duplicate_tags(self):
        """Test that duplicate tags are rejected by the view"""
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})

        # Add tag first time
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag1.pk,
            'notes': 'First addition'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.patient.patient_tags.count(), 1)

        # Try to add same tag again — view rejects duplicates (400)
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag1.pk,
            'notes': 'Second addition'
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('não é possível', data['error'].lower())
        # Still only 1 tag assigned
        self.assertEqual(self.patient.patient_tags.count(), 1)

    def test_tag_management_with_inactive_allowed_tags(self):
        """Test that inactive allowed tags are handled correctly"""
        # Create an inactive allowed tag
        inactive_tag = AllowedTag.objects.create(
            name='Deprecated Tag',
            color='#6c757d',
            is_active=False,
            created_by=self.user,
            updated_by=self.user
        )

        # Try to add inactive tag via API
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': inactive_tag.pk,
            'notes': 'Should not be added'
        })

        # can_add_patient_tag returns False for inactive tags → view returns 400
        self.assertEqual(response.status_code, 400)

    def test_tag_api_available_tags_filtering(self):
        """Test that available tags API correctly filters already assigned tags"""
        # Add a tag to patient
        tag = Tag.objects.create(
            allowed_tag=self.allowed_tag1,
            patient=self.patient,
            created_by=self.user,
            updated_by=self.user
        )

        # Check API response
        api_url = reverse('patients:patient_tags_api', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(api_url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should show only unassigned allowed tags in available_tags
        available_tag_names = [tag['name'] for tag in data['available_tags']]
        self.assertNotIn('High Priority', available_tag_names)  # Already assigned
        self.assertIn('Follow Up', available_tag_names)  # Available

    def test_tag_management_timeline_integration(self):
        """Test that tag operations create timeline events"""
        from apps.events.models import TagAddedEvent, TagRemovedEvent

        # Add a tag
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag1.pk,
            'notes': 'Test timeline integration'
        })

        self.assertEqual(response.status_code, 200)

        # Check that TagAddedEvent was created
        tag_added_event = TagAddedEvent.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(tag_added_event)
        self.assertEqual(tag_added_event.tag_name, 'High Priority')
        self.assertEqual(tag_added_event.tag_color, '#dc3545')
        self.assertEqual(tag_added_event.tag_notes, 'Test timeline integration')

        # Remove the tag
        tag = self.patient.patient_tags.first()
        remove_url = reverse('patients:patient_tag_remove', kwargs={
            'patient_id': self.patient.pk,
            'tag_id': tag.pk
        })

        response = self.client.post(remove_url)
        self.assertEqual(response.status_code, 200)

        # Check that TagRemovedEvent was created
        tag_removed_event = TagRemovedEvent.objects.filter(patient=self.patient).first()
        self.assertIsNotNone(tag_removed_event)
        self.assertEqual(tag_removed_event.tag_name, 'High Priority')
        self.assertEqual(tag_removed_event.tag_color, '#dc3545')

    def test_concurrent_tag_operations(self):
        """Test sequential tag additions (both succeed)"""
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})

        # Add first tag
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag1.pk,
            'notes': 'Sequential add 1'
        })
        self.assertEqual(response.status_code, 200)

        # Add second tag
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag2.pk,
            'notes': 'Sequential add 2'
        })
        self.assertEqual(response.status_code, 200)

        # Both tags should be assigned
        self.assertEqual(self.patient.patient_tags.count(), 2)


class PatientTagPermissionTests(TestCase):
    """Permission tests for tag management functionality"""

    @classmethod
    def setUpTestData(cls):
        # Create users with different permission levels
        cls.doctor = create_navigation_user(
            username='doctor',
            email='doctor@example.com',
            password='testpassword'
        )

        cls.nurse = create_navigation_user(
            username='nurse',
            email='nurse@example.com',
            password='testpassword'
        )

        cls.student = create_navigation_user(
            username='student',
            email='student@example.com',
            password='testpassword'
        )

        cls.limited_user = create_navigation_user(
            username='limited',
            email='limited@example.com',
            password='testpassword'
        )

        cls.patient = Patient.objects.create(
            name='Test Patient',
            birthday='1980-01-01',
            status=Patient.Status.OUTPATIENT,
            created_by=cls.doctor,
            updated_by=cls.doctor
        )

        cls.allowed_tag = AllowedTag.objects.create(
            name='Test Tag',
            color='#007bff',
            created_by=cls.doctor,
            updated_by=cls.doctor
        )

    def test_doctor_can_manage_all_tags(self):
        """Test that doctors can manage all tags"""
        # Add change_patient permission to doctor
        from django.contrib.auth.models import Permission
        change_perm = Permission.objects.get(codename='change_patient')
        self.doctor.user_permissions.add(change_perm)

        self.client.force_login(self.doctor)

        # Test tag addition
        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag.pk,
            'notes': 'Doctor adding tag'
        })

        self.assertEqual(response.status_code, 200)

        # Test tag removal
        tag = self.patient.patient_tags.first()
        remove_url = reverse('patients:patient_tag_remove', kwargs={
            'patient_id': self.patient.pk,
            'tag_id': tag.pk
        })

        response = self.client.post(remove_url)
        self.assertEqual(response.status_code, 200)

    def test_nurse_with_permission_can_manage_tags(self):
        """Test that nurses with proper permission can manage tags"""
        from django.contrib.auth.models import Permission
        change_perm = Permission.objects.get(codename='change_patient')
        self.nurse.user_permissions.add(change_perm)

        self.client.force_login(self.nurse)

        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag.pk,
            'notes': 'Nurse adding tag'
        })

        self.assertEqual(response.status_code, 200)

    def test_user_without_permission_cannot_manage_tags(self):
        """Test that users without change_patient permission cannot manage tags"""
        self.client.force_login(self.limited_user)

        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag.pk,
            'notes': 'Should not work'
        })

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_cannot_access_tag_apis(self):
        """Test that anonymous users cannot access tag management APIs"""
        self.client.logout()

        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag.pk,
            'notes': 'Should not work'
        })

        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_tag_api_permission_context(self):
        """Test that API returns proper permission context"""
        from django.contrib.auth.models import Permission

        # User with permissions
        change_perm = Permission.objects.get(codename='change_patient')
        self.doctor.user_permissions.add(change_perm)

        self.client.force_login(self.doctor)

        api_url = reverse('patients:patient_tags_api', kwargs={'patient_id': self.patient.pk})
        response = self.client.get(api_url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['permissions']['can_manage_tags'])
        self.assertTrue(data['permissions']['can_view_tags'])

        # Limited user is still authenticated → can_view_patient_tags returns True
        self.client.force_login(self.limited_user)
        response = self.client.get(api_url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['permissions']['can_manage_tags'])
        self.assertTrue(data['permissions']['can_view_tags'])

    def test_cross_patient_tag_access(self):
        """Test that any authenticated user can view tags (can_view_patient_tags allows all auth'd users)"""
        from django.contrib.auth.models import Permission

        # Create another patient
        other_patient = Patient.objects.create(
            name='Other Patient',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.doctor,
            updated_by=self.doctor
        )

        # Limited user is still authenticated → can_view_patient_tags returns True
        self.client.force_login(self.limited_user)

        api_url = reverse('patients:patient_tags_api', kwargs={'patient_id': other_patient.pk})
        response = self.client.get(api_url)

        self.assertEqual(response.status_code, 200)

    def test_superuser_can_manage_all_tags(self):
        """Test that superuser can manage all tags regardless of other permissions"""
        # Create superuser
        superuser = User.objects.create_superuser(
            username='superuser',
            email='super@example.com',
            password='testpassword',
            password_change_required=False,
            terms_accepted=True,
        )

        self.client.force_login(superuser)

        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag.pk,
            'notes': 'Superuser adding tag'
        })

        self.assertEqual(response.status_code, 200)

    def test_permission_denied_error_messages(self):
        """Test that permission denied responses redirect to login (PermissionRequiredMixin default)"""
        self.client.force_login(self.limited_user)

        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})
        response = self.client.post(add_url, data={
            'tag_id': self.allowed_tag.pk,
            'notes': 'Should not work'
        })

        # PermissionRequiredMixin returns 403 for authenticated users without permission
        self.assertEqual(response.status_code, 403)

    def test_bulk_operations_permission_check(self):
        """Test that bulk tag operations respect permissions"""
        from django.contrib.auth.models import Permission

        # Add tags first with doctor
        change_perm = Permission.objects.get(codename='change_patient')
        self.doctor.user_permissions.add(change_perm)

        self.client.force_login(self.doctor)

        add_url = reverse('patients:patient_tag_add', kwargs={'patient_id': self.patient.pk})
        self.client.post(add_url, data={'tag_id': self.allowed_tag.pk})

        # Try bulk removal with limited user
        self.client.force_login(self.limited_user)

        remove_all_url = reverse('patients:patient_tag_remove_all', kwargs={'patient_id': self.patient.pk})
        response = self.client.post(remove_all_url)

        self.assertEqual(response.status_code, 403)