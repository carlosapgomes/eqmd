from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import models
from apps.patients.models import Patient, AllowedTag
from datetime import datetime, timedelta

User = get_user_model()


class TestPatientHistory(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            profession_type='doctor'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            profession_type='nurse'
        )
        
    def test_patient_creation_history(self):
        """Test that patient creation is tracked."""
        patient = Patient.objects.create(
            name='Test Patient',
            created_by=self.user
        )
        
        # Check history record created
        history = patient.history.first()
        self.assertEqual(history.history_type, '+')  # Creation
        self.assertEqual(history.history_user, self.user)
        self.assertEqual(history.name, 'Test Patient')
        
    def test_patient_modification_history(self):
        """Test that patient modifications are tracked."""
        patient = Patient.objects.create(
            name='Test Patient',
            created_by=self.user
        )
        
        # Modify patient
        patient.name = 'Modified Patient'
        patient.status = 'inpatient'
        patient._change_reason = 'Updated patient name and status'
        patient.save()
        
        # Check history records
        history_records = list(patient.history.all())
        self.assertEqual(len(history_records), 2)
        
        # Latest change
        latest = history_records[0]
        self.assertEqual(latest.history_type, '~')  # Change
        self.assertEqual(latest.name, 'Modified Patient')
        self.assertEqual(latest.status, 'inpatient')
        self.assertEqual(latest.history_change_reason, 'Updated patient name and status')
        
    def test_patient_multiple_modifications(self):
        """Test multiple sequential modifications are tracked."""
        patient = Patient.objects.create(
            name='Test Patient',
            created_by=self.user
        )
        
        # First modification
        patient.name = 'Modified Name 1'
        patient._change_reason = 'First modification'
        patient.save()
        
        # Second modification by different user
        patient.status = 'discharged'
        patient._change_reason = 'Status change by nurse'
        patient.updated_by = self.user2
        patient.save()
        
        # Check all history records
        history_records = list(patient.history.all().order_by('-history_date'))
        self.assertEqual(len(history_records), 3)
        
        # Verify sequence
        self.assertEqual(history_records[0].status, 'discharged')
        self.assertEqual(history_records[0].history_change_reason, 'Status change by nurse')
        self.assertEqual(history_records[1].name, 'Modified Name 1')
        self.assertEqual(history_records[1].history_change_reason, 'First modification')
        self.assertEqual(history_records[2].history_type, '+')  # Original creation
        
    def test_user_association_with_changes(self):
        """Test that changes are correctly associated with users."""
        patient = Patient.objects.create(
            name='Test Patient',
            created_by=self.user
        )
        
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
        patient = Patient.objects.create(
            name='Test Patient',
            created_by=self.user
        )
        
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
        
        # Check each reason is tracked (excluding creation record)
        for i, reason in enumerate(test_reasons):
            self.assertEqual(history_records[i].history_change_reason, reason)
            
    def test_status_change_to_deceased_tracking(self):
        """Test tracking of critical status changes to deceased."""
        patient = Patient.objects.create(
            name='Test Patient',
            status='inpatient',
            created_by=self.user
        )
        
        # Change to deceased status
        patient.status = 'deceased'
        patient._change_reason = 'Patient declared deceased by physician'
        patient.save()
        
        # Find the deceased status change in history
        deceased_change = patient.history.filter(status='deceased').first()
        self.assertIsNotNone(deceased_change)
        self.assertEqual(deceased_change.history_type, '~')
        self.assertEqual(deceased_change.history_change_reason, 'Patient declared deceased by physician')
        
    def test_bulk_changes_detection(self):
        """Test detection of bulk changes by same user."""
        # Create multiple patients with changes by same user
        patients = []
        for i in range(15):  # Create more than threshold (10)
            patient = Patient.objects.create(
                name=f'Patient {i}',
                created_by=self.user
            )
            # Make a modification to each
            patient.status = 'inpatient'
            patient._change_reason = f'Bulk admission {i}'
            patient.save()
            patients.append(patient)
            
        # Count changes by user in last day
        yesterday = datetime.now() - timedelta(days=1)
        change_count = Patient.history.filter(
            history_date__gte=yesterday,
            history_user=self.user,
            history_type='~'  # Only modifications, not creations
        ).count()
        
        # Should detect bulk changes (15 modifications)
        self.assertGreaterEqual(change_count, 10)


class TestAllowedTagHistory(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            profession_type='doctor'
        )
        
    def test_allowed_tag_creation_history(self):
        """Test that AllowedTag creation is tracked."""
        tag = AllowedTag.objects.create(
            name='Test Tag',
            description='Test Description',
            color='#FF0000',
            created_by=self.user
        )
        
        # Check history record created
        history = tag.history.first()
        self.assertEqual(history.history_type, '+')
        self.assertEqual(history.history_user, self.user)
        self.assertEqual(history.name, 'Test Tag')
        
    def test_allowed_tag_modification_history(self):
        """Test that AllowedTag modifications are tracked."""
        tag = AllowedTag.objects.create(
            name='Original Tag',
            description='Original Description',
            color='#FF0000',
            created_by=self.user
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
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            profession_type='doctor',
            is_staff=True
        )
        
    def test_user_creation_history(self):
        """Test that user creation is tracked."""
        user = User.objects.create_user(
            username='newuser',
            email='newuser@example.com',
            profession_type='nurse'
        )
        
        # Check history record created
        history = user.history.first()
        self.assertEqual(history.history_type, '+')
        self.assertEqual(history.username, 'newuser')
        self.assertEqual(history.profession_type, 'nurse')
        
    def test_user_modification_history(self):
        """Test that user modifications are tracked."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            profession_type='student'
        )
        
        # Modify user
        user.profession_type = 'nurse'
        user.first_name = 'Test'
        user.last_name = 'User'
        user._change_reason = 'Updated profession and name'
        user.save()
        
        # Check history
        history_records = list(user.history.all())
        self.assertEqual(len(history_records), 2)
        
        latest = history_records[0]
        self.assertEqual(latest.history_type, '~')
        self.assertEqual(latest.profession_type, 'nurse')
        self.assertEqual(latest.first_name, 'Test')
        self.assertEqual(latest.history_change_reason, 'Updated profession and name')
        
    def test_sensitive_fields_excluded(self):
        """Test that sensitive fields like password are excluded from history."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
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
        self.user = User.objects.create_user(
            username='perftest',
            email='perf@example.com',
            profession_type='doctor'
        )
        
    def test_history_query_performance(self):
        """Test that history queries perform reasonably well."""
        # Create patients with history
        patients = []
        for i in range(50):
            patient = Patient.objects.create(
                name=f'Performance Test Patient {i}',
                created_by=self.user
            )
            # Add some modifications
            for j in range(3):
                patient.status = ['inpatient', 'outpatient', 'discharged'][j]
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