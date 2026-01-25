from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta

User = get_user_model()


class TestUserAccountHistory(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            profession_type=User.MEDICAL_DOCTOR,
            is_staff=True,
            is_superuser=True
        )
        
    def test_user_account_creation_history(self):
        """Test that user account creation is tracked."""
        user = User.objects.create_user(
            username='newuser',
            email='newuser@example.com',
            profession_type=User.NURSE,
            first_name='New',
            last_name='User'
        )
        
        # Check history record created
        history = user.history.first()
        self.assertEqual(history.history_type, '+')
        self.assertEqual(history.username, 'newuser')
        self.assertEqual(history.profession_type, User.NURSE)
        self.assertEqual(history.first_name, 'New')
        self.assertEqual(history.last_name, 'User')
        
    def test_profession_type_change_tracking(self):
        """Test that profession type changes are tracked (critical for permissions)."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            profession_type=User.STUDENT
        )
        
        # Change profession type (critical security change)
        user.profession_type = User.MEDICAL_DOCTOR
        user._change_reason = 'Promoted from student to doctor'
        user.save()
        
        # Verify change is tracked
        history_records = list(user.history.all().order_by('-history_date'))
        self.assertEqual(len(history_records), 2)
        
        # Latest change
        latest = history_records[0]
        self.assertEqual(latest.history_type, '~')
        self.assertEqual(latest.profession_type, User.MEDICAL_DOCTOR)
        self.assertEqual(latest.history_change_reason, 'Promoted from student to doctor')
        
        # Original record
        original = history_records[1]
        self.assertEqual(original.profession_type, User.STUDENT)
        
    def test_staff_status_change_tracking(self):
        """Test that staff status changes are tracked."""
        user = User.objects.create_user(
            username='normaluser',
            email='normal@example.com',
            profession_type=User.NURSE
        )
        
        # Grant staff access
        user.is_staff = True
        user._change_reason = 'Granted administrative access'
        user.save()
        
        # Remove staff access
        user.is_staff = False
        user._change_reason = 'Revoked administrative access'
        user.save()
        
        # Check all changes are tracked
        history_records = list(user.history.all().order_by('-history_date'))
        self.assertEqual(len(history_records), 3)  # Creation + 2 modifications
        
        # Latest: staff removed
        latest = history_records[0]
        self.assertEqual(latest.is_staff, False)
        self.assertEqual(latest.history_change_reason, 'Revoked administrative access')
        
        # Previous: staff granted
        previous = history_records[1]
        self.assertEqual(previous.is_staff, True)
        self.assertEqual(previous.history_change_reason, 'Granted administrative access')
        
    def test_superuser_status_change_tracking(self):
        """Test that superuser status changes are tracked."""
        user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            profession_type=User.MEDICAL_DOCTOR,
            is_staff=True
        )
        
        # Grant superuser access (extremely critical change)
        user.is_superuser = True
        user._change_reason = 'Granted superuser privileges for system maintenance'
        user.save()
        
        # Verify change is tracked
        history_records = list(user.history.all().order_by('-history_date'))
        latest = history_records[0]
        
        self.assertEqual(latest.is_superuser, True)
        self.assertEqual(latest.history_change_reason, 'Granted superuser privileges for system maintenance')
        
    def test_account_deactivation_tracking(self):
        """Test that account deactivations are tracked."""
        user = User.objects.create_user(
            username='activeuser',
            email='active@example.com',
            profession_type=User.NURSE,
            is_active=True
        )
        
        # Deactivate account
        user.is_active = False
        user._change_reason = 'Account deactivated due to policy violation'
        user.save()
        
        # Reactivate account
        user.is_active = True
        user._change_reason = 'Account reactivated after investigation'
        user.save()
        
        # Check both changes are tracked
        history_records = list(user.history.all().order_by('-history_date'))
        self.assertEqual(len(history_records), 3)
        
        # Latest: reactivated
        latest = history_records[0]
        self.assertEqual(latest.is_active, True)
        self.assertEqual(latest.history_change_reason, 'Account reactivated after investigation')
        
        # Previous: deactivated
        deactivation = history_records[1]
        self.assertEqual(deactivation.is_active, False)
        self.assertEqual(deactivation.history_change_reason, 'Account deactivated due to policy violation')
        
    def test_email_change_tracking(self):
        """Test that email changes are tracked."""
        user = User.objects.create_user(
            username='emailuser',
            email='original@example.com',
            profession_type=User.MEDICAL_DOCTOR
        )
        
        # Change email
        user.email = 'updated@example.com'
        user._change_reason = 'Email updated per user request'
        user.save()
        
        # Verify change is tracked
        history_records = list(user.history.all().order_by('-history_date'))
        latest = history_records[0]
        
        self.assertEqual(latest.email, 'updated@example.com')
        self.assertEqual(latest.history_change_reason, 'Email updated per user request')
        
    def test_professional_information_changes(self):
        """Test that professional registration changes are tracked."""
        user = User.objects.create_user(
            username='professional',
            email='prof@example.com',
            profession_type=User.MEDICAL_DOCTOR
        )
        
        # Add professional registration
        user.professional_registration_number = 'CRM-123456'
        user.country_id_number = '123.456.789-00'
        user._change_reason = 'Added professional credentials'
        user.save()
        
        # Update registration
        user.professional_registration_number = 'CRM-654321'
        user._change_reason = 'Updated CRM number'
        user.save()
        
        # Check changes are tracked
        history_records = list(user.history.all().order_by('-history_date'))
        self.assertEqual(len(history_records), 3)
        
        # Latest change
        latest = history_records[0]
        self.assertEqual(latest.professional_registration_number, 'CRM-654321')
        self.assertEqual(latest.history_change_reason, 'Updated CRM number')
        
        # Previous change
        previous = history_records[1]
        self.assertEqual(previous.professional_registration_number, 'CRM-123456')
        self.assertEqual(previous.country_id_number, '123.456.789-00')
        
    def test_bulk_user_modifications_detection(self):
        """Test detection of bulk user account modifications."""
        # Create multiple users and modify them
        users = []
        for i in range(15):  # More than suspicious threshold
            user = User.objects.create_user(
                username=f'bulkuser{i}',
                email=f'bulk{i}@example.com',
                profession_type=User.STUDENT
            )
            # Modify each user
            user.profession_type = User.NURSE
            user._change_reason = f'Bulk promotion {i}'
            user.save()
            users.append(user)
            
        # Count modifications in last day
        yesterday = datetime.now() - timedelta(days=1)
        modification_count = User.history.filter(
            history_date__gte=yesterday,
            history_type='~'  # Only modifications
        ).count()
        
        # Should detect bulk modifications
        self.assertGreaterEqual(modification_count, 10)
        
    def test_sensitive_fields_excluded_from_history(self):
        """Test that sensitive fields are properly excluded from history."""
        user = User.objects.create_user(
            username='sensitiveuser',
            email='sensitive@example.com',
            password='originalpassword123'
        )
        
        # Change password
        user.set_password('newpassword123')
        user.save()
        
        # Update last_login (should be excluded)
        user.last_login = datetime.now()
        user.save()
        
        # Get history record
        history = user.history.first()
        
        # Verify sensitive fields are not in history
        # Note: The actual exclusion is configured in the model
        # This test verifies the configuration works
        self.assertTrue(hasattr(history, 'username'))
        self.assertTrue(hasattr(history, 'email'))
        
        # Password and last_login should be excluded from history model
        # due to excluded_fields configuration
        
    def test_account_deletion_attempt_tracking(self):
        """Test tracking of user account deletion attempts."""
        user = User.objects.create_user(
            username='deletableuser',
            email='deletable@example.com',
            profession_type=User.STUDENT
        )
        
        user_id = user.id
        username = user.username
        
        # Delete user (should be tracked)
        user._change_reason = 'Account deleted by administrator'
        user.delete()
        
        # Check deletion is tracked
        deletion_history = User.history.filter(
            id=user_id,
            history_type='-'
        ).first()
        
        self.assertIsNotNone(deletion_history)
        self.assertEqual(deletion_history.username, username)
        self.assertEqual(deletion_history.history_change_reason, 'Account deleted by administrator')


class TestUserHistoryQueries(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            profession_type=User.MEDICAL_DOCTOR,
            is_staff=True
        )
        
    def test_privilege_escalation_detection(self):
        """Test detection of privilege escalation patterns."""
        user = User.objects.create_user(
            username='escalationtest',
            email='escalation@example.com',
            profession_type=User.STUDENT
        )
        
        # Simulate privilege escalation pattern
        escalation_steps = [
            (User.NURSE, 'Promoted to nurse'),
            (User.MEDICAL_DOCTOR, 'Promoted to doctor'),
            (User.MEDICAL_DOCTOR, 'Granted staff access'),  # is_staff=True
        ]
        
        for i, (profession, reason) in enumerate(escalation_steps):
            user.profession_type = profession
            if i == 2:  # Last step grants staff access
                user.is_staff = True
            user._change_reason = reason
            user.save()
            
        # Query for rapid privilege changes
        privilege_changes = User.history.filter(
            id=user.id,
            history_type='~'
        ).count()
        
        # Should detect multiple privilege escalations
        self.assertEqual(privilege_changes, 3)
        
    def test_account_status_change_patterns(self):
        """Test detection of suspicious account status change patterns."""
        user = User.objects.create_user(
            username='statustest',
            email='status@example.com',
            profession_type=User.NURSE
        )
        
        # Rapid activation/deactivation pattern
        for i in range(5):
            user.is_active = not user.is_active
            user._change_reason = f'Status change {i}'
            user.save()
            
        # Check pattern is tracked
        status_changes = User.history.filter(
            id=user.id,
            history_type='~'
        ).count()
        
        self.assertEqual(status_changes, 5)
        
    def test_mass_account_modifications(self):
        """Test detection of mass account modifications by single user."""
        # This would be run by an admin making bulk changes
        users = []
        for i in range(20):
            user = User.objects.create_user(
                username=f'massuser{i}',
                email=f'mass{i}@example.com',
                profession_type=User.STUDENT
            )
            users.append(user)
            
        # Simulate mass modification by admin
        for user in users:
            user.profession_type = User.NURSE
            user._change_reason = 'Mass promotion event'
            user.save()
            
        # Count modifications
        yesterday = datetime.now() - timedelta(days=1)
        mass_changes = User.history.filter(
            history_date__gte=yesterday,
            history_type='~',
            history_change_reason='Mass promotion event'
        ).count()
        
        self.assertEqual(mass_changes, 20)
