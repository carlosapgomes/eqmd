"""
Permission tests for DailyNote app.

Tests comprehensive permission system integration including:
- Different user roles (doctor, nurse, student, etc.)
- Hospital context requirements
- Time-based edit/delete restrictions
- Unauthorized access attempts
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import Mock, patch

from apps.dailynotes.models import DailyNote
from apps.patients.models import Patient
# Note: Hospital model removed after single-hospital refactor
# Patient status constants (using integer values from Patient.Status)
OUTPATIENT = 1
INPATIENT = 2

User = get_user_model()


class SimpleDailyNotePermissionTest(TestCase):
    """Simple test to verify basic permission functionality."""

    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.profession_type = 0  # MEDICAL_DOCTOR
        self.user.save()

        # Create a hospital
        self.hospital = Hospital.objects.create(
            name="Test Hospital",
            address="Test Address"
        )

        # Create a patient
        self.patient = Patient.objects.create(
            name="Test Patient",
            birthday=timezone.now().date() - timedelta(days=365*30),
            status=OUTPATIENT,
            current_hospital=self.hospital,
            created_by=self.user,
            updated_by=self.user
        )

        # Create a daily note
        self.dailynote = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Test daily note",
            content="Test content",
            created_by=self.user,
            updated_by=self.user
        )

        self.client = Client()

    def test_basic_form_creation(self):
        """Test that the form can be created with a user."""
        from apps.dailynotes.forms import DailyNoteForm

        # Test form creation with user
        form = DailyNoteForm(user=self.user)
        self.assertIsNotNone(form)
        self.assertIn('patient', form.fields)

    @patch('apps.core.permissions.utils.can_access_patient')
    def test_form_patient_validation(self, mock_can_access):
        """Test that form validates patient access permission."""
        from apps.dailynotes.forms import DailyNoteForm

        # Mock permission check to return False
        mock_can_access.return_value = False

        form_data = {
            'patient': self.patient.id,
            'event_datetime': timezone.now(),
            'description': 'Test description',
            'content': 'Test content with enough characters'
        }

        form = DailyNoteForm(data=form_data, user=self.user)
        is_valid = form.is_valid()

        # Should be invalid due to permission check
        self.assertFalse(is_valid)
        if not is_valid:
            self.assertIn('patient', form.errors)

    def test_dailynote_creation(self):
        """Test that daily note can be created successfully."""
        self.assertEqual(DailyNote.objects.count(), 1)
        self.assertEqual(self.dailynote.patient, self.patient)
        self.assertEqual(self.dailynote.created_by, self.user)

    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    def test_form_filters_patients_by_hospital_context(self, mock_can_access, mock_has_context):
        """Test that form filters patients based on hospital context."""
        from apps.dailynotes.forms import DailyNoteForm

        # Mock permission and hospital context checks to return True
        mock_can_access.return_value = True
        mock_has_context.return_value = True

        # Set hospital context
        self.user.current_hospital = self.hospital
        self.user.has_hospital_context = True

        form = DailyNoteForm(user=self.user)

        # Should include patients from the user's hospital
        patient_ids = list(form.fields['patient'].queryset.values_list('id', flat=True))
        self.assertIn(self.patient.id, patient_ids)

    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    def test_form_no_hospital_context_shows_no_patients(self, mock_can_access, mock_has_context):
        """Test that form shows no patients when user has no hospital context."""
        from apps.dailynotes.forms import DailyNoteForm

        # Mock permission check to return True, hospital context to return False
        mock_can_access.return_value = True
        mock_has_context.return_value = False

        # No hospital context
        self.user.current_hospital = None
        self.user.has_hospital_context = False

        form = DailyNoteForm(user=self.user)

        # Should show no patients
        self.assertEqual(form.fields['patient'].queryset.count(), 0)


class DailyNoteViewPermissionIntegrationTest(TestCase):
    """Integration tests for view permissions."""

    def setUp(self):
        """Set up test data."""
        # Create a test user with permissions
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.profession_type = 0  # MEDICAL_DOCTOR
        self.user.save()

        # Add required permissions
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            codename__in=['view_event', 'add_event', 'change_event', 'delete_event']
        )
        self.user.user_permissions.set(permissions)

        # Create a hospital
        self.hospital = Hospital.objects.create(
            name="Test Hospital",
            address="Test Address"
        )

        # Create a patient
        self.patient = Patient.objects.create(
            name="Test Patient",
            birthday=timezone.now().date() - timedelta(days=365*30),
            status=OUTPATIENT,
            current_hospital=self.hospital,
            created_by=self.user,
            updated_by=self.user
        )

        # Create a daily note
        self.dailynote = DailyNote.objects.create(
            patient=self.patient,
            event_datetime=timezone.now(),
            description="Test daily note",
            content="Test content",
            created_by=self.user,
            updated_by=self.user
        )

        self.client = Client()

    @patch('apps.hospitals.middleware.HospitalContextMiddleware._add_hospital_context')
    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    def test_list_view_with_permissions(self, mock_can_access, mock_has_context, mock_add_context):
        """Test that list view works with proper permissions."""
        mock_has_context.return_value = True
        mock_can_access.return_value = True
        
        # Mock the middleware to set hospital context
        def mock_middleware(request):
            request.user.current_hospital = self.hospital
            request.user.has_hospital_context = True
        
        mock_add_context.side_effect = mock_middleware

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dailynotes:dailynote_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test daily note')

    @patch('apps.hospitals.middleware.HospitalContextMiddleware._add_hospital_context')
    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    def test_detail_view_with_permissions(self, mock_can_access, mock_has_context, mock_add_context):
        """Test that detail view works with proper permissions."""
        mock_has_context.return_value = True
        mock_can_access.return_value = True

        # Mock the middleware to set hospital context
        def mock_middleware(request):
            request.user.current_hospital = self.hospital
            request.user.has_hospital_context = True
        
        mock_add_context.side_effect = mock_middleware
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('dailynotes:dailynote_detail', kwargs={'pk': self.dailynote.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test daily note')

        # Check that permission context is added
        self.assertIn('can_edit_dailynote', response.context)
        self.assertIn('can_delete_dailynote', response.context)

    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    @patch('apps.core.permissions.utils.can_edit_event')
    def test_template_edit_button_visibility(self, mock_can_edit, mock_can_access, mock_has_context):
        """Test that edit button is only visible when user can edit."""
        mock_has_context.return_value = True
        mock_can_access.return_value = True

        # Set hospital context on user
        self.user.current_hospital = self.hospital
        self.user.has_hospital_context = True

        self.client.login(username='testuser', password='testpass123')

        # Test with edit permission
        mock_can_edit.return_value = True
        response = self.client.get(
            reverse('dailynotes:dailynote_detail', kwargs={'pk': self.dailynote.pk})
        )
        self.assertContains(response, 'Editar')

        # Test without edit permission
        mock_can_edit.return_value = False
        response = self.client.get(
            reverse('dailynotes:dailynote_detail', kwargs={'pk': self.dailynote.pk})
        )
        self.assertNotContains(response, 'href="/dailynotes/{}/update/"'.format(self.dailynote.pk))

    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    @patch('apps.core.permissions.utils.can_delete_event')
    def test_template_delete_button_visibility(self, mock_can_delete, mock_can_access, mock_has_context):
        """Test that delete button is only visible when user can delete."""
        mock_has_context.return_value = True
        mock_can_access.return_value = True

        # Set hospital context on user
        self.user.current_hospital = self.hospital
        self.user.has_hospital_context = True

        self.client.login(username='testuser', password='testpass123')

        # Test with delete permission
        mock_can_delete.return_value = True
        response = self.client.get(
            reverse('dailynotes:dailynote_detail', kwargs={'pk': self.dailynote.pk})
        )
        self.assertContains(response, 'Excluir')

        # Test without delete permission
        mock_can_delete.return_value = False
        response = self.client.get(
            reverse('dailynotes:dailynote_detail', kwargs={'pk': self.dailynote.pk})
        )
        self.assertNotContains(response, 'href="/dailynotes/{}/delete/"'.format(self.dailynote.pk))


class DailyNoteSecurityTest(TestCase):
    """Security tests for DailyNote permissions."""

    def setUp(self):
        """Set up test data."""
        # Create users from different hospitals
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user1.profession_type = 0  # MEDICAL_DOCTOR
        self.user1.save()

        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.user2.profession_type = 0  # MEDICAL_DOCTOR
        self.user2.save()

        # Add required permissions
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            codename__in=['view_event', 'add_event', 'change_event', 'delete_event']
        )
        self.user1.user_permissions.set(permissions)
        self.user2.user_permissions.set(permissions)

        # Create hospitals
        self.hospital1 = Hospital.objects.create(
            name="Hospital 1",
            address="Address 1"
        )
        self.hospital2 = Hospital.objects.create(
            name="Hospital 2",
            address="Address 2"
        )

        # Create patients in different hospitals
        self.patient1 = Patient.objects.create(
            name="Patient 1",
            birthday=timezone.now().date() - timedelta(days=365*30),
            status=OUTPATIENT,
            current_hospital=self.hospital1,
            created_by=self.user1,
            updated_by=self.user1
        )

        self.patient2 = Patient.objects.create(
            name="Patient 2",
            birthday=timezone.now().date() - timedelta(days=365*25),
            status=OUTPATIENT,
            current_hospital=self.hospital2,
            created_by=self.user2,
            updated_by=self.user2
        )

        # Create daily notes
        self.dailynote1 = DailyNote.objects.create(
            patient=self.patient1,
            event_datetime=timezone.now(),
            description="Daily note 1",
            content="Content 1",
            created_by=self.user1,
            updated_by=self.user1
        )

        self.dailynote2 = DailyNote.objects.create(
            patient=self.patient2,
            event_datetime=timezone.now(),
            description="Daily note 2",
            content="Content 2",
            created_by=self.user2,
            updated_by=self.user2
        )

        self.client = Client()

    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    def test_cross_hospital_access_denied(self, mock_can_access, mock_has_context):
        """Test that users cannot access daily notes from other hospitals."""
        mock_has_context.return_value = True

        # Mock permission to deny access to patient from different hospital
        def mock_permission_check(user, patient):
            return patient.current_hospital == getattr(user, 'current_hospital', None)

        mock_can_access.side_effect = mock_permission_check

        # Set user1's hospital context
        self.user1.current_hospital = self.hospital1
        self.user1.has_hospital_context = True

        self.client.login(username='user1', password='testpass123')

        # Should be able to access own hospital's daily note
        response = self.client.get(
            reverse('dailynotes:dailynote_detail', kwargs={'pk': self.dailynote1.pk})
        )
        self.assertEqual(response.status_code, 200)

        # Should NOT be able to access other hospital's daily note
        response = self.client.get(
            reverse('dailynotes:dailynote_detail', kwargs={'pk': self.dailynote2.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access daily notes."""
        # Don't login
        response = self.client.get(reverse('dailynotes:dailynote_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

        response = self.client.get(
            reverse('dailynotes:dailynote_detail', kwargs={'pk': self.dailynote1.pk})
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login


class DailyNotePermissionTestCase(TestCase):
    """Base test case with common setup for permission tests."""
    
    def setUp(self):
        """Set up test data."""
        # Create hospitals
        self.hospital1 = Hospital.objects.create(
            name="Hospital 1",
            address="Address 1"
        )
        self.hospital2 = Hospital.objects.create(
            name="Hospital 2", 
            address="Address 2"
        )
        
        # Create users with different roles (using integer values)
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123'
        )
        self.doctor.profession_type = 0  # MEDICAL_DOCTOR
        self.doctor.save()

        self.nurse = User.objects.create_user(
            username='nurse',
            email='nurse@test.com',
            password='testpass123'
        )
        self.nurse.profession_type = 2  # NURSE
        self.nurse.save()

        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123'
        )
        self.student.profession_type = 4  # STUDENT
        self.student.save()
        
        # Create patients
        self.patient1 = Patient.objects.create(
            name="Patient 1",
            birthday=timezone.now().date() - timedelta(days=365*30),
            status=INPATIENT,
            current_hospital=self.hospital1,
            created_by=self.doctor,
            updated_by=self.doctor
        )

        self.patient2 = Patient.objects.create(
            name="Patient 2",
            birthday=timezone.now().date() - timedelta(days=365*25),
            status=OUTPATIENT,
            current_hospital=self.hospital2,
            created_by=self.nurse,
            updated_by=self.nurse
        )
        
        # Create daily notes
        self.dailynote1 = DailyNote.objects.create(
            patient=self.patient1,
            event_datetime=timezone.now(),
            description="Test daily note 1",
            content="Test content 1",
            created_by=self.doctor,
            updated_by=self.doctor
        )

        self.dailynote2 = DailyNote.objects.create(
            patient=self.patient2,
            event_datetime=timezone.now() - timedelta(hours=25),  # Old note
            description="Test daily note 2",
            content="Test content 2",
            created_by=self.nurse,
            updated_by=self.nurse
        )
        
        self.client = Client()


class DailyNoteViewPermissionTests(DailyNotePermissionTestCase):
    """Test permission enforcement in views."""
    
    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    def test_list_view_requires_hospital_context(self, mock_can_access, mock_has_context):
        """Test that list view requires hospital context."""
        mock_has_context.return_value = False
        mock_can_access.return_value = True
        
        self.client.login(username='doctor', password='testpass123')
        response = self.client.get(reverse('dailynotes:dailynote_list'))
        
        self.assertEqual(response.status_code, 403)
    
    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    def test_list_view_filters_by_hospital_context(self, mock_can_access, mock_has_context):
        """Test that list view filters daily notes by hospital context."""
        mock_has_context.return_value = True
        mock_can_access.return_value = True
        
        # Mock hospital context
        self.doctor.current_hospital = self.hospital1
        self.doctor.has_hospital_context = True
        
        self.client.login(username='doctor', password='testpass123')
        
        with patch.object(self.client.session, 'get', return_value=str(self.hospital1.id)):
            response = self.client.get(reverse('dailynotes:dailynote_list'))
        
        self.assertEqual(response.status_code, 200)
        # Should only show daily notes from hospital1
        dailynotes = response.context['dailynote_list']
        self.assertEqual(len(dailynotes), 1)
        self.assertEqual(dailynotes[0].patient.current_hospital, self.hospital1)
    
    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    def test_detail_view_patient_access_required(self, mock_can_access, mock_has_context):
        """Test that detail view requires patient access."""
        mock_has_context.return_value = True
        mock_can_access.return_value = False
        
        self.client.login(username='doctor', password='testpass123')
        response = self.client.get(
            reverse('dailynotes:dailynote_detail', kwargs={'pk': self.dailynote1.pk})
        )
        
        self.assertEqual(response.status_code, 403)
    
    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    @patch('apps.core.permissions.utils.can_edit_event')
    def test_update_view_edit_permission_required(self, mock_can_edit, mock_can_access, mock_has_context):
        """Test that update view requires edit permission."""
        mock_has_context.return_value = True
        mock_can_access.return_value = True
        mock_can_edit.return_value = False
        
        self.client.login(username='doctor', password='testpass123')
        response = self.client.get(
            reverse('dailynotes:dailynote_update', kwargs={'pk': self.dailynote1.pk})
        )
        
        self.assertEqual(response.status_code, 403)
    
    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    @patch('apps.core.permissions.utils.can_delete_event')
    def test_delete_view_delete_permission_required(self, mock_can_delete, mock_can_access, mock_has_context):
        """Test that delete view requires delete permission."""
        mock_has_context.return_value = True
        mock_can_access.return_value = True
        mock_can_delete.return_value = False
        
        self.client.login(username='doctor', password='testpass123')
        response = self.client.get(
            reverse('dailynotes:dailynote_delete', kwargs={'pk': self.dailynote1.pk})
        )
        
        self.assertEqual(response.status_code, 403)


class DailyNoteFormPermissionTests(DailyNotePermissionTestCase):
    """Test permission enforcement in forms."""
    
    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    def test_form_filters_patients_by_permission(self, mock_can_access, mock_has_context):
        """Test that form filters patients based on user permissions."""
        # Mock hospital context to return True
        mock_has_context.return_value = True
        
        # Mock permission check to return True only for patient1
        def mock_permission_check(user, patient):
            return patient == self.patient1
        
        mock_can_access.side_effect = mock_permission_check
        
        # Mock hospital context
        self.doctor.current_hospital = self.hospital1
        self.doctor.has_hospital_context = True
        
        from apps.dailynotes.forms import DailyNoteForm
        form = DailyNoteForm(user=self.doctor)
        
        # Should only include patient1 in queryset (patient2 is in different hospital)
        patient_ids = list(form.fields['patient'].queryset.values_list('id', flat=True))
        self.assertIn(self.patient1.id, patient_ids)
        self.assertNotIn(self.patient2.id, patient_ids)
    
    @patch('apps.core.permissions.utils.can_access_patient')
    def test_form_validation_checks_patient_permission(self, mock_can_access):
        """Test that form validation checks patient access permission."""
        mock_can_access.return_value = False
        
        from apps.dailynotes.forms import DailyNoteForm
        form_data = {
            'patient': self.patient1.id,
            'event_datetime': timezone.now(),
            'description': 'Test description',
            'content': 'Test content with enough characters'
        }
        
        form = DailyNoteForm(data=form_data, user=self.doctor)
        self.assertFalse(form.is_valid())
        self.assertIn('patient', form.errors)


class DailyNoteTimeBasedPermissionTests(DailyNotePermissionTestCase):
    """Test time-based permission restrictions."""
    
    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    def test_edit_permission_time_limit(self, mock_can_access, mock_has_context):
        """Test that edit permission respects time limit."""
        mock_has_context.return_value = True
        mock_can_access.return_value = True
        
        # Create an old daily note (more than 24 hours old)
        old_dailynote = DailyNote.objects.create(
            patient=self.patient1,
            event_datetime=timezone.now() - timedelta(hours=25),
            description="Old daily note",
            content="Old content",
            created_by=self.doctor,
            updated_by=self.doctor
        )
        old_dailynote.created_at = timezone.now() - timedelta(hours=25)
        old_dailynote.save()
        
        self.client.login(username='doctor', password='testpass123')
        response = self.client.get(
            reverse('dailynotes:dailynote_update', kwargs={'pk': old_dailynote.pk})
        )
        
        # Should be forbidden due to time limit
        self.assertEqual(response.status_code, 403)
    
    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    def test_delete_permission_time_limit(self, mock_can_access, mock_has_context):
        """Test that delete permission respects time limit."""
        mock_has_context.return_value = True
        mock_can_access.return_value = True
        
        # Create an old daily note (more than 24 hours old)
        old_dailynote = DailyNote.objects.create(
            patient=self.patient1,
            event_datetime=timezone.now() - timedelta(hours=25),
            description="Old daily note",
            content="Old content",
            created_by=self.doctor,
            updated_by=self.doctor
        )
        old_dailynote.created_at = timezone.now() - timedelta(hours=25)
        old_dailynote.save()
        
        self.client.login(username='doctor', password='testpass123')
        response = self.client.get(
            reverse('dailynotes:dailynote_delete', kwargs={'pk': old_dailynote.pk})
        )
        
        # Should be forbidden due to time limit
        self.assertEqual(response.status_code, 403)


class DailyNoteRoleBasedPermissionTests(DailyNotePermissionTestCase):
    """Test role-based permission restrictions."""
    
    @patch('apps.core.permissions.utils.has_hospital_context')
    @patch('apps.core.permissions.utils.can_access_patient')
    def test_student_outpatient_only_access(self, mock_can_access, mock_has_context):
        """Test that students can only access outpatients."""
        mock_has_context.return_value = True
        
        # Mock permission to allow access only to outpatients for students
        def mock_permission_check(user, patient):
            if user.profession_type == 4:  # STUDENT
                return patient.status == OUTPATIENT
            return True
        
        mock_can_access.side_effect = mock_permission_check
        
        self.client.login(username='student', password='testpass123')
        
        # Should not be able to access inpatient daily note
        response = self.client.get(
            reverse('dailynotes:dailynote_detail', kwargs={'pk': self.dailynote1.pk})
        )
        self.assertEqual(response.status_code, 403)
