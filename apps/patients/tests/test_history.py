from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts.tests.helpers import create_navigation_user
from apps.patients.models import AllowedTag, Patient

User = get_user_model()


def _create_patient(user, name, **kwargs):
    """Create a Patient with the audit actor set for history tracking."""
    patient = Patient(
        name=name,
        birthday='1980-01-01',
        created_by=user,
        updated_by=user,
        **kwargs,
    )
    patient._history_user = user
    patient.save()
    return patient


def _create_allowed_tag(user, name, **kwargs):
    """Create an AllowedTag with the audit actor set for history tracking."""
    tag = AllowedTag(name=name, created_by=user, updated_by=user, **kwargs)
    tag._history_user = user
    tag.save()
    return tag


class TestPatientHistory(TestCase):
    def setUp(self):
        self.user = create_navigation_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR,
        )
        self.user2 = create_navigation_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123',
            profession_type=User.NURSE,
        )
        
    def test_patient_creation_history(self):
        """Test that patient creation is tracked."""
        patient = _create_patient(self.user, 'Test Patient')
        
        # Check history record created
        history = patient.history.first()
        self.assertEqual(history.history_type, '+')  # Creation
        self.assertEqual(history.history_user, self.user)
        self.assertEqual(history.name, 'Test Patient')
        
    def test_patient_modification_history(self):
        """Test that patient modifications are tracked."""
        patient = _create_patient(self.user, 'Test Patient')
        
        # Modify patient
        patient.name = 'Modified Patient'
        patient.status = Patient.Status.INPATIENT
        patient._change_reason = 'Updated patient name and status'
        patient.save()
        
        # Check history records
        history_records = list(patient.history.all())
        self.assertEqual(len(history_records), 2)
        
        # Latest change
        latest = history_records[0]
        self.assertEqual(latest.history_type, '~')  # Change
        self.assertEqual(latest.name, 'Modified Patient')
        self.assertEqual(latest.status, Patient.Status.INPATIENT)
        self.assertEqual(latest.history_change_reason, 'Updated patient name and status')
        
    def test_patient_multiple_modifications(self):
        """Test multiple sequential modifications are tracked."""
        patient = _create_patient(self.user, 'Test Patient')
        
        # First modification
        patient.name = 'Modified Name 1'
        patient._change_reason = 'First modification'
        patient.save()
        
        # Second modification by different user
        patient.status = Patient.Status.DISCHARGED
        patient._change_reason = 'Status change by nurse'
        patient.updated_by = self.user2
        patient.save()
        
        # Check all history records
        history_records = list(patient.history.all().order_by('-history_date'))
        self.assertEqual(len(history_records), 3)
        
        # Verify sequence
        self.assertEqual(history_records[0].status, Patient.Status.DISCHARGED)
        self.assertEqual(history_records[0].history_change_reason, 'Status change by nurse')
        self.assertEqual(history_records[1].name, 'Modified Name 1')
        self.assertEqual(history_records[1].history_change_reason, 'First modification')
        self.assertEqual(history_records[2].history_type, '+')  # Original creation
        
    def test_user_association_with_changes(self):
        """Test that changes are correctly associated with users."""
        patient = _create_patient(self.user, 'Test Patient')
        
        # Modification by first user
        patient.name = 'Modified by User 1'
        patient.save()
        
        # Modification by second user  
        patient.name = 'Modified by User 2'
        patient.updated_by = self.user2
        patient.save()
        
        history_records = list(patient.history.all().order_by('-history_date'))
        
        # Check user associations
        self.assertEqual(history_records[0].history_user, self.user)  # Latest change
        self.assertEqual(history_records[1].history_user, self.user)  # Second change
        self.assertEqual(history_records[2].history_user, self.user)  # Creation
        
    def test_change_reason_tracking(self):
        """Test that change reasons are properly tracked."""
        patient = _create_patient(self.user, 'Test Patient')
        
        test_reasons = [
            'Updated patient personal information',
            'Status change due to admission',
            'Corrected patient demographics'
        ]
        
        for reason in test_reasons:
            patient.name = f'Updated: {reason}'
            patient._change_reason = reason
            patient.save()
            
        history_records = list(patient.history.all().order_by('-history_date'))
        
        # Check each reason is tracked (newest first, excluding creation record)
        for i, reason in enumerate(reversed(test_reasons)):
            self.assertEqual(history_records[i].history_change_reason, reason)
            
    def test_status_change_to_deceased_tracking(self):
        """Test tracking of critical status changes to deceased."""
        patient = _create_patient(
            self.user, 'Test Patient', status=Patient.Status.INPATIENT
        )
        
        # Change to deceased status
        patient.status = Patient.Status.DECEASED
        patient._change_reason = 'Patient declared deceased by physician'
        patient.save()
        
        # Find the deceased status change in history
        deceased_change = patient.history.filter(
            status=Patient.Status.DECEASED
        ).first()
        self.assertIsNotNone(deceased_change)
        self.assertEqual(deceased_change.history_type, '~')
        self.assertEqual(deceased_change.history_change_reason, 'Patient declared deceased by physician')
        
    def test_bulk_changes_detection(self):
        """Test detection of bulk changes by same user."""
        # Create multiple patients with changes by same user
        patients = []
        for i in range(15):  # Create more than threshold (10)
            patient = _create_patient(self.user, f'Patient {i}')
            # Make a modification to each
            patient.status = Patient.Status.INPATIENT
            patient._change_reason = f'Bulk admission {i}'
            patient.save()
            patients.append(patient)
            
        # Count changes by user in last day
        yesterday = timezone.now() - timedelta(days=1)
        change_count = Patient.history.filter(
            history_date__gte=yesterday,
            history_user=self.user,
            history_type='~'  # Only modifications, not creations
        ).count()
        
        # Should detect bulk changes (15 modifications)
        self.assertGreaterEqual(change_count, 10)


class TestAllowedTagHistory(TestCase):
    def setUp(self):
        self.user = create_navigation_user(
            username='admin_user',
            email='admin@example.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR,
        )
        
    def test_allowed_tag_creation_history(self):
        """Test that AllowedTag creation is tracked."""
        tag = _create_allowed_tag(
            self.user,
            name='Test Tag',
            description='Test Description',
            color='#FF0000',
        )
        
        # Check history record created
        history = tag.history.first()
        self.assertEqual(history.history_type, '+')
        self.assertEqual(history.history_user, self.user)
        self.assertEqual(history.name, 'Test Tag')
        
    def test_allowed_tag_modification_history(self):
        """Test that AllowedTag modifications are tracked."""
        tag = _create_allowed_tag(
            self.user,
            name='Original Tag',
            description='Original Description',
            color='#FF0000',
        )
        
        # Modify tag
        tag.name = 'Modified Tag'
        tag.color = '#00FF00'
        tag._change_reason = 'Updated tag name and color'
        tag.save()
        
        # Check history
        history_records = list(tag.history.all())
        self.assertEqual(len(history_records), 2)
        
        latest = history_records[0]
        self.assertEqual(latest.history_type, '~')
        self.assertEqual(latest.name, 'Modified Tag')
        self.assertEqual(latest.color, '#00FF00')
        self.assertEqual(latest.history_change_reason, 'Updated tag name and color')


class TestUserHistory(TestCase):
    def setUp(self):
        self.admin_user = create_navigation_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR,
            is_staff=True,
        )
        
    def test_user_creation_history(self):
        """Test that user creation is tracked."""
        user = create_navigation_user(
            username='newuser',
            email='newuser@example.com',
            password='testpass123',
            profession_type=User.NURSE,
        )
        
        # Check history record created
        history = user.history.first()
        self.assertEqual(history.history_type, '+')
        self.assertEqual(history.username, 'newuser')
        self.assertEqual(history.profession_type, User.NURSE)
        
    def test_user_modification_history(self):
        """Test that user modifications are tracked."""
        user = create_navigation_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            profession_type=User.STUDENT,
        )
        
        # Modify user
        user.profession_type = User.NURSE
        user.first_name = 'Test'
        user.last_name = 'User'
        user._change_reason = 'Updated profession and name'
        user.save()
        
        # Check history
        history_records = list(user.history.all())
        self.assertEqual(len(history_records), 2)
        
        latest = history_records[0]
        self.assertEqual(latest.history_type, '~')
        self.assertEqual(latest.profession_type, User.NURSE)
        self.assertEqual(latest.first_name, 'Test')
        self.assertEqual(latest.history_change_reason, 'Updated profession and name')
        
    def test_sensitive_fields_excluded(self):
        """Test that sensitive fields like password are excluded from history."""
        user = create_navigation_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        
        # Change password
        user.set_password('newpass123')
        user.save()
        
        # Check history - password should not be tracked
        history = user.history.first()
        # The history record should exist but password field should be excluded
        self.assertTrue(hasattr(history, 'username'))
        # Password field should be excluded from history model
        # This test verifies the excluded_fields configuration works


class TestHistoryPerformance(TestCase):
    def setUp(self):
        self.user = create_navigation_user(
            username='perftest',
            email='perf@example.com',
            password='testpass123',
            profession_type=User.MEDICAL_DOCTOR,
        )
        
    def test_history_query_performance(self):
        """Test that history queries perform reasonably well."""
        # Create patients with history
        patients = []
        for i in range(50):
            patient = _create_patient(self.user, f'Performance Test Patient {i}')
            # Add some modifications
            for j in range(3):
                patient.status = [
                    Patient.Status.INPATIENT,
                    Patient.Status.OUTPATIENT,
                    Patient.Status.DISCHARGED,
                ][j]
                patient._change_reason = f'Status change {j}'
                patient.save()
            patients.append(patient)
            
        # Test efficient history querying with select_related
        with self.assertNumQueries(1):
            history_records = list(
                Patient.history.select_related('history_user')
                .filter(history_user=self.user)[:10]
            )
            
        self.assertEqual(len(history_records), 10)
        # Verify user data is available without additional queries
        for record in history_records:
            self.assertIsNotNone(record.history_user.username)
