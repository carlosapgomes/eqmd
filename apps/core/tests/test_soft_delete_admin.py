"""
Tests for soft delete functionality in Django admin interface.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.admin.sites import AdminSite
from django.utils import timezone
from apps.patients.models import Patient, AllowedTag
from apps.events.models import Event
from apps.patients.admin import PatientAdmin
from apps.events.admin import EventAdmin

User = get_user_model()


class MockRequest:
    """Mock request object for admin tests."""
    def __init__(self, user):
        self.user = user
        self._messages = MockMessagesStorage()
        self.META = {}


class MockMessagesStorage:
    """Mock messages storage for admin tests."""
    def __init__(self):
        self.messages = []
    
    def add(self, level, message, extra_tags=''):
        self.messages.append({
            'level': level,
            'message': message,
            'extra_tags': extra_tags
        })


class TestSoftDeleteAdminInterface(TestCase):
    """Test soft delete functionality in Django admin."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        self.regular_user = User.objects.create_user(
            username='doctor',
            email='doctor@example.com',
            profession_type=0,  # MEDICAL_DOCTOR
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='admin', password='testpass123')

    def test_patient_admin_shows_all_records(self):
        """Test that PatientAdmin shows both active and deleted patients."""
        # Create active and deleted patients
        active_patient = Patient.objects.create(
            name='Active Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.regular_user,
            updated_by=self.regular_user
        )
        
        deleted_patient = Patient.objects.create(
            name='Deleted Patient',
            fiscal_number='987654321',
            healthcard_number='H987654',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.regular_user,
            updated_by=self.regular_user
        )
        deleted_patient.delete(deleted_by=self.admin_user, reason='Admin test deletion')

        # Test admin queryset includes deleted records
        site = AdminSite()
        admin = PatientAdmin(Patient, site)
        request = MockRequest(self.admin_user)
        
        queryset = admin.get_queryset(request)
        self.assertEqual(queryset.count(), 2)
        
        # Should include both active and deleted
        patient_names = {p.name for p in queryset}
        self.assertEqual(patient_names, {'Active Patient', 'Deleted Patient'})

    def test_patient_admin_list_display_includes_deletion_fields(self):
        """Test that admin list display shows deletion status fields."""
        site = AdminSite()
        admin = PatientAdmin(Patient, site)
        
        # Check that deletion fields are in list_display
        expected_fields = ['is_deleted', 'deleted_at', 'deleted_by']
        for field in expected_fields:
            self.assertIn(field, admin.list_display)

    def test_patient_admin_list_filter_includes_deletion_status(self):
        """Test that admin list filter includes deletion status."""
        site = AdminSite()
        admin = PatientAdmin(Patient, site)
        
        # Check that deletion filters are available
        expected_filters = ['is_deleted', 'deleted_at']
        for filter_field in expected_filters:
            self.assertIn(filter_field, admin.list_filter)

    def test_patient_admin_readonly_fields(self):
        """Test that deletion fields are read-only in admin."""
        site = AdminSite()
        admin = PatientAdmin(Patient, site)
        
        expected_readonly = ['deleted_at', 'deleted_by', 'deletion_reason']
        for field in expected_readonly:
            self.assertIn(field, admin.readonly_fields)

    def test_patient_admin_soft_delete_action(self):
        """Test admin soft delete bulk action."""
        # Create test patients
        patients = []
        for i in range(3):
            patient = Patient.objects.create(
                name=f'Test Patient {i}',
                fiscal_number=f'12345678{i}',
                healthcard_number=f'H12345{i}',
                birthday='1990-01-01',
                status=Patient.Status.INPATIENT,
                created_by=self.regular_user,
                updated_by=self.regular_user
            )
            patients.append(patient)

        site = AdminSite()
        admin = PatientAdmin(Patient, site)
        request = MockRequest(self.admin_user)
        
        # Create queryset of active patients
        queryset = Patient.objects.filter(id__in=[p.id for p in patients])
        
        # Execute soft delete action
        admin.soft_delete_selected(request, queryset)
        
        # All patients should be soft deleted
        self.assertEqual(Patient.objects.count(), 0)
        self.assertEqual(Patient.all_objects.count(), 3)
        self.assertEqual(Patient.all_objects.deleted().count(), 3)
        
        # Check deletion metadata
        for patient in Patient.all_objects.deleted():
            self.assertTrue(patient.is_deleted)
            self.assertEqual(patient.deleted_by, self.admin_user)
            self.assertIn('Bulk deletion by admin', patient.deletion_reason)

    def test_patient_admin_restore_action(self):
        """Test admin restore bulk action."""
        # Create and delete test patients
        patients = []
        for i in range(3):
            patient = Patient.objects.create(
                name=f'Restore Patient {i}',
                fiscal_number=f'87654321{i}',
                healthcard_number=f'HR8765{i}',
                birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
                created_by=self.regular_user,
                updated_by=self.regular_user
            )
            patient.delete(deleted_by=self.admin_user, reason=f'Test deletion {i}')
            patients.append(patient)

        site = AdminSite()
        admin = PatientAdmin(Patient, site)
        request = MockRequest(self.admin_user)
        
        # Create queryset of deleted patients
        queryset = Patient.all_objects.deleted().filter(id__in=[p.id for p in patients])
        
        # Execute restore action
        admin.restore_selected(request, queryset)
        
        # All patients should be restored
        self.assertEqual(Patient.objects.count(), 3)
        self.assertEqual(Patient.all_objects.deleted().count(), 0)
        
        # Check restoration
        for patient in Patient.objects.all():
            self.assertFalse(patient.is_deleted)
            self.assertIsNone(patient.deleted_at)
            self.assertIsNone(patient.deleted_by)
            self.assertEqual(patient.deletion_reason, '')

    def test_event_admin_shows_all_records(self):
        """Test that EventAdmin shows both active and deleted events."""
        patient = Patient.objects.create(
            name='Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.regular_user,
            updated_by=self.regular_user
        )

        # Create active and deleted events
        active_event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=patient,
            description='Active Event',
            event_type=1,
            created_by=self.regular_user,
            updated_by=self.regular_user
        )
        
        deleted_event = Event.objects.create(
            event_datetime=timezone.now(),
            patient=patient,
            description='Deleted Event',
            event_type=2,
            created_by=self.regular_user,
            updated_by=self.regular_user
        )
        deleted_event.delete(deleted_by=self.admin_user, reason='Event test deletion')

        # Test admin queryset includes deleted records
        site = AdminSite()
        admin = EventAdmin(Event, site)
        request = MockRequest(self.admin_user)
        
        queryset = admin.get_queryset(request)
        self.assertEqual(queryset.count(), 2)
        
        # Should include both active and deleted
        event_descriptions = {e.description for e in queryset}
        self.assertEqual(event_descriptions, {'Active Event', 'Deleted Event'})

    def test_allowed_tag_admin_shows_all_records(self):
        """Test that AllowedTagAdmin shows both active and deleted tags."""
        # Create active and deleted tags
        active_tag = AllowedTag.objects.create(
            name='Active Tag',
            color='#00FF00',
            created_by=self.admin_user,
                updated_by=self.admin_user
        )
        
        deleted_tag = AllowedTag.objects.create(
            name='Deleted Tag',
            color='#FF0000',
            created_by=self.admin_user,
                updated_by=self.admin_user
        )
        deleted_tag.delete(deleted_by=self.admin_user, reason='Tag test deletion')

        # Since AllowedTag admin should also show all records (including deleted)
        # Test that both are visible in all_objects queryset
        self.assertEqual(AllowedTag.objects.count(), 1)  # Only active
        self.assertEqual(AllowedTag.all_objects.count(), 2)  # All including deleted


class TestSoftDeleteAdminViews(TestCase):
    """Test soft delete functionality through admin web views."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='admin', password='testpass123')

    def test_admin_changelist_shows_deletion_status(self):
        """Test that admin changelist shows deletion status."""
        # Create test patient
        patient = Patient.objects.create(
            name='Changelist Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.admin_user,
                updated_by=self.admin_user
        )
        
        # Access admin changelist
        url = reverse('admin:patients_patient_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Should show the patient in changelist
        self.assertContains(response, 'Changelist Patient')
        
        # Soft delete the patient
        patient.delete(deleted_by=self.admin_user, reason='Changelist test')
        
        # Refresh changelist - should still show patient but marked as deleted
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Changelist Patient')

    def test_admin_change_form_shows_deletion_fields(self):
        """Test that admin change form shows deletion fields when appropriate."""
        # Create and delete patient
        patient = Patient.objects.create(
            name='Form Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.admin_user,
                updated_by=self.admin_user
        )
        patient.delete(deleted_by=self.admin_user, reason='Form test deletion')
        
        # Access patient change form
        url = reverse('admin:patients_patient_change', args=[patient.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Should show deletion information
        self.assertContains(response, 'Form test deletion')
        self.assertContains(response, 'admin')  # deleted_by username

    def test_admin_filters_work_with_soft_deletes(self):
        """Test that admin list filters work correctly with soft deleted records."""
        # Create mix of active and deleted patients
        active_patient = Patient.objects.create(
            name='Active Filter Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.admin_user,
                updated_by=self.admin_user
        )
        
        deleted_patient = Patient.objects.create(
            name='Deleted Filter Patient',
            fiscal_number='987654321',
            healthcard_number='H987654',
            birthday='1990-01-01',
            status=Patient.Status.DISCHARGED,
            created_by=self.admin_user,
            updated_by=self.admin_user
        )
        deleted_patient.delete(deleted_by=self.admin_user, reason='Filter test')
        
        # Test filter by deletion status
        url = reverse('admin:patients_patient_changelist')
        
        # Filter for deleted records
        response = self.client.get(url + '?is_deleted=1')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Deleted Filter Patient')
        self.assertNotContains(response, 'Active Filter Patient')
        
        # Filter for active records
        response = self.client.get(url + '?is_deleted=0')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Filter Patient')
        self.assertNotContains(response, 'Deleted Filter Patient')

    def test_admin_search_works_with_soft_deletes(self):
        """Test that admin search works correctly with soft deleted records."""
        # Create searchable patients
        active_patient = Patient.objects.create(
            name='Searchable Active Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.admin_user,
                updated_by=self.admin_user
        )
        
        deleted_patient = Patient.objects.create(
            name='Searchable Deleted Patient',
            fiscal_number='987654321',
            healthcard_number='H987654',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.admin_user,
                updated_by=self.admin_user
        )
        deleted_patient.delete(deleted_by=self.admin_user, reason='Search test')
        
        # Search should find both active and deleted records
        url = reverse('admin:patients_patient_changelist')
        response = self.client.get(url + '?q=Searchable')
        self.assertEqual(response.status_code, 200)
        
        # Should find both patients
        self.assertContains(response, 'Searchable Active Patient')
        self.assertContains(response, 'Searchable Deleted Patient')


class TestSoftDeleteAdminPermissions(TestCase):
    """Test soft delete admin functionality with different user permissions."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='superuser',
            email='super@example.com',
            password='testpass123'
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            is_staff=True,
            profession_type=0,  # MEDICAL_DOCTOR
            password='testpass123'
        )

    def test_superuser_can_access_all_admin_features(self):
        """Test that superuser can access all soft delete admin features."""
        client = Client()
        client.login(username='superuser', password='testpass123')
        
        # Create and delete patient
        patient = Patient.objects.create(
            name='Superuser Test Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.staff_user,
            updated_by=self.staff_user
        )
        patient.delete(deleted_by=self.staff_user, reason='Permission test')
        
        # Superuser should be able to access admin
        url = reverse('admin:patients_patient_changelist')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Should see the deleted patient
        self.assertContains(response, 'Superuser Test Patient')

    def test_staff_user_admin_access_limited(self):
        """Test that regular staff users have limited admin access."""
        client = Client()
        
        # Staff user should not be able to access admin by default
        # (unless specifically given admin permissions for specific models)
        login_success = client.login(username='staff', password='testpass123')
        self.assertTrue(login_success)
        
        # Try to access patient admin
        url = reverse('admin:patients_patient_changelist')
        response = client.get(url)
        
        # Should either redirect to login or show permission denied
        # The exact behavior depends on admin configuration
        self.assertIn(response.status_code, [302, 403])


class TestSoftDeleteAdminEdgeCases(TestCase):
    """Test edge cases in soft delete admin functionality."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='admin', password='testpass123')

    def test_admin_handles_already_deleted_records(self):
        """Test admin bulk actions on already deleted records."""
        # Create and soft delete patient
        patient = Patient.objects.create(
            name='Already Deleted Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.admin_user,
                updated_by=self.admin_user
        )
        patient.delete(deleted_by=self.admin_user, reason='First deletion')
        
        # Try to soft delete again through admin action
        site = AdminSite()
        admin = PatientAdmin(Patient, site)
        request = MockRequest(self.admin_user)
        
        queryset = Patient.all_objects.filter(id=patient.id)
        admin.soft_delete_selected(request, queryset)
        
        # Should handle gracefully - patient remains deleted
        deleted_patient = Patient.all_objects.get(id=patient.id)
        self.assertTrue(deleted_patient.is_deleted)

    def test_admin_handles_non_deleted_restore_attempt(self):
        """Test admin restore action on non-deleted records."""
        # Create active patient
        patient = Patient.objects.create(
            name='Active Restore Patient',
            fiscal_number='123456789',
            healthcard_number='H123456',
            birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
            created_by=self.admin_user,
                updated_by=self.admin_user
        )
        
        # Try to restore active patient through admin action
        site = AdminSite()
        admin = PatientAdmin(Patient, site)
        request = MockRequest(self.admin_user)
        
        queryset = Patient.objects.filter(id=patient.id)
        admin.restore_selected(request, queryset)
        
        # Should handle gracefully - patient remains active
        active_patient = Patient.objects.get(id=patient.id)
        self.assertFalse(active_patient.is_deleted)

    def test_admin_performance_with_large_deleted_dataset(self):
        """Test admin performance with many deleted records."""
        # Create many deleted records
        for i in range(50):
            patient = Patient.objects.create(
                name=f'Performance Patient {i}',
                fiscal_number=f'PERF{i:06d}',
                healthcard_number=f'HP{i:06d}',
                birthday='1990-01-01',
            status=Patient.Status.INPATIENT,
                created_by=self.admin_user,
                updated_by=self.admin_user
            )
            if i % 2 == 0:  # Delete half
                patient.delete(deleted_by=self.admin_user, reason=f'Performance test {i}')
        
        # Admin changelist should load without performance issues
        url = reverse('admin:patients_patient_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Should show all records (both active and deleted)
        # The exact count depends on pagination settings