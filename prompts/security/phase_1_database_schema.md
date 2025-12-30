# Phase 1: Database Schema Foundation

## Overview

**Timeline: 1-2 weeks**
**Priority: High**

Implement core database fields and structures to support comprehensive user lifecycle management. This foundation phase enables all subsequent features while maintaining compatibility with existing audit history systems.

## Database Model Extensions

### Primary User Model Changes

#### New Fields for EqmdCustomUser

```python
# apps/accounts/models.py - EqmdCustomUser class additions

class EqmdCustomUser(AbstractUser):
    # ... existing fields ...

    # === User Lifecycle Management Fields ===

    # Expiration Management
    access_expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When user access automatically expires (NULL = no expiration)"
    )
    expiration_reason = models.CharField(
        max_length=100,
        choices=[
            ('end_of_internship', 'End of Internship/Residency'),
            ('end_of_rotation', 'End of Clinical Rotation'),
            ('employment_end', 'Employment Termination'),
            ('leave_of_absence', 'Leave of Absence'),
            ('disciplinary', 'Disciplinary Action'),
            ('administrative', 'Administrative Decision'),
            ('inactivity', 'Account Inactivity'),
        ],
        blank=True,
        help_text="Reason for access expiration"
    )

    # Activity Tracking
    last_meaningful_activity = models.DateTimeField(
        null=True, blank=True,
        help_text="Last time user performed meaningful action (not just login)"
    )
    activity_score = models.PositiveIntegerField(
        default=0,
        help_text="Activity score based on recent meaningful actions"
    )

    # Account Lifecycle Status
    account_status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('expiring_soon', 'Expiring Soon (30 days)'),
            ('expired', 'Access Expired'),
            ('inactive', 'Inactive (no recent activity)'),
            ('suspended', 'Administratively Suspended'),
            ('departed', 'No longer with institution'),
            ('renewal_required', 'Renewal Required'),
        ],
        default='active',
        db_index=True,
        help_text="Current account lifecycle status"
    )

    # Access Review and Renewal
    last_access_review = models.DateTimeField(
        null=True, blank=True,
        help_text="When access was last reviewed by administrator"
    )
    reviewed_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_users',
        help_text="Administrator who last reviewed this user's access"
    )
    next_review_due = models.DateField(
        null=True, blank=True,
        help_text="When next access review is due"
    )

    # Notification Tracking
    expiration_warning_sent = models.DateTimeField(
        null=True, blank=True,
        help_text="When expiration warning was last sent"
    )
    renewal_reminder_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of renewal reminders sent"
    )

    # Role-Specific Extensions
    internship_start_date = models.DateField(
        null=True, blank=True,
        help_text="Start date for internship/residency (for automatic expiration calculation)"
    )
    expected_duration_months = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Expected duration in months (for residents/students)"
    )

    # Supervisor/Department Tracking
    supervisor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='supervised_users',
        help_text="Direct supervisor for renewal approvals"
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        help_text="Department/ward assignment for access reviews"
    )
```

#### Model Methods and Properties

```python
class EqmdCustomUser(AbstractUser):
    # ... fields above ...

    @property
    def days_until_expiration(self):
        """Calculate days until access expires"""
        if not self.access_expires_at:
            return None
        delta = self.access_expires_at.date() - timezone.now().date()
        return delta.days

    @property
    def is_expiring_soon(self):
        """Check if user expires within 30 days"""
        days = self.days_until_expiration
        return days is not None and 0 <= days <= 30

    @property
    def is_expired(self):
        """Check if user access has expired"""
        if not self.access_expires_at:
            return False
        return timezone.now() >= self.access_expires_at

    @property
    def days_since_last_activity(self):
        """Calculate days since last meaningful activity"""
        if not self.last_meaningful_activity:
            return None
        delta = timezone.now().date() - self.last_meaningful_activity.date()
        return delta.days

    @property
    def is_inactive(self):
        """Check if user has been inactive for 90+ days"""
        days = self.days_since_last_activity
        return days is not None and days >= 90

    def calculate_role_based_expiration(self):
        """Calculate expiration date based on professional role"""
        if not self.internship_start_date or not self.expected_duration_months:
            return None

        from dateutil.relativedelta import relativedelta
        return self.internship_start_date + relativedelta(months=self.expected_duration_months)

    def update_activity_score(self, action_type='general'):
        """Update activity score based on user actions"""
        score_weights = {
            'patient_access': 3,
            'note_creation': 5,
            'form_completion': 4,
            'media_upload': 2,
            'general': 1,
        }

        self.activity_score += score_weights.get(action_type, 1)
        self.last_meaningful_activity = timezone.now()

        # Decay activity score over time (weekly decay)
        if self.last_meaningful_activity:
            weeks_since = (timezone.now() - self.last_meaningful_activity).days // 7
            self.activity_score = max(0, self.activity_score - (weeks_since * 5))

    def extend_access(self, days, reason, extended_by_user):
        """Extend user access by specified days"""
        if not self.access_expires_at:
            self.access_expires_at = timezone.now() + timedelta(days=days)
        else:
            self.access_expires_at += timedelta(days=days)

        self.last_access_review = timezone.now()
        self.reviewed_by = extended_by_user
        self._change_reason = f"Access extended by {days} days. Reason: {reason}"

        # Reset notification counters
        self.expiration_warning_sent = None
        self.renewal_reminder_count = 0

        # Update status if needed
        if self.account_status in ['expired', 'expiring_soon']:
            self.account_status = 'active'
```

## Database Migration Strategy

### Migration 1: Core Lifecycle Fields

```python
# apps/accounts/migrations/0004_add_lifecycle_management.py

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_add_terms_acceptance'),
    ]

    operations = [
        # Core expiration fields
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='access_expires_at',
            field=models.DateTimeField(blank=True, null=True,
                help_text="When user access automatically expires (NULL = no expiration)"),
        ),
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='expiration_reason',
            field=models.CharField(blank=True, max_length=100,
                choices=[...]),  # Full choices list
        ),

        # Activity tracking
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='last_meaningful_activity',
            field=models.DateTimeField(blank=True, null=True,
                help_text="Last time user performed meaningful action"),
        ),
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='activity_score',
            field=models.PositiveIntegerField(default=0,
                help_text="Activity score based on recent meaningful actions"),
        ),

        # Account status
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='account_status',
            field=models.CharField(default='active', max_length=20,
                choices=[...]),  # Full choices list
        ),

        # Add database index for performance
        migrations.RunSQL([
            "CREATE INDEX accounts_user_status_idx ON accounts_eqmdcustomuser(account_status);",
            "CREATE INDEX accounts_user_expires_idx ON accounts_eqmdcustomuser(access_expires_at);",
        ]),
    ]
```

### Migration 2: Review and Supervision Fields

```python
# apps/accounts/migrations/0005_add_review_fields.py

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_add_lifecycle_management'),
    ]

    operations = [
        # Access review tracking
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='last_access_review',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='reviewed_by',
            field=models.ForeignKey(blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reviewed_users', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='next_review_due',
            field=models.DateField(blank=True, null=True),
        ),

        # Supervisor relationship
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='supervisor',
            field=models.ForeignKey(blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='supervised_users', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='department',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
```

### Migration 3: Role-Specific and Notification Fields

```python
# apps/accounts/migrations/0006_add_role_notification_fields.py

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_add_review_fields'),
    ]

    operations = [
        # Role-specific fields
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='internship_start_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='expected_duration_months',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),

        # Notification tracking
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='expiration_warning_sent',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='renewal_reminder_count',
            field=models.PositiveIntegerField(default=0),
        ),

        # Historical model updates (for simple-history)
        migrations.AddField(
            model_name='historicaleqmdcustomuser',
            name='access_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        # ... additional historical fields as needed
    ]
```

## Data Population Strategy

### Default Values for Existing Users

```python
# Data migration to set initial values
# apps/accounts/migrations/0007_populate_lifecycle_defaults.py

from django.db import migrations

def populate_default_lifecycle_data(apps, schema_editor):
    """Set initial lifecycle data for existing users"""
    EqmdCustomUser = apps.get_model('accounts', 'EqmdCustomUser')

    # Set all existing users as active with no expiration
    EqmdCustomUser.objects.update(
        account_status='active',
        activity_score=10,  # Give existing users some initial activity
        last_meaningful_activity=timezone.now() - timedelta(days=30),
    )

    # Set role-specific defaults
    residents = EqmdCustomUser.objects.filter(profession_type=1)  # RESIDENT
    students = EqmdCustomUser.objects.filter(profession_type=4)   # STUDENT

    # Residents: Default 1-year expiration
    for resident in residents:
        if not resident.access_expires_at:
            resident.access_expires_at = timezone.now() + timedelta(days=365)
            resident.expiration_reason = 'end_of_internship'
            resident.save()

    # Students: Default 6-month expiration
    for student in students:
        if not student.access_expires_at:
            student.access_expires_at = timezone.now() + timedelta(days=180)
            student.expiration_reason = 'end_of_rotation'
            student.save()

def reverse_populate_lifecycle_data(apps, schema_editor):
    """Reverse migration - clear lifecycle data"""
    EqmdCustomUser = apps.get_model('accounts', 'EqmdCustomUser')
    EqmdCustomUser.objects.update(
        access_expires_at=None,
        expiration_reason='',
        account_status='active',
    )

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0006_add_role_notification_fields'),
    ]

    operations = [
        migrations.RunPython(
            populate_default_lifecycle_data,
            reverse_populate_lifecycle_data,
        ),
    ]
```

## Configuration and Constants

### Role-Based Configuration

```python
# apps/accounts/lifecycle_config.py

from datetime import timedelta

# Default expiration periods by role
ROLE_EXPIRATION_DEFAULTS = {
    0: None,                     # MEDICAL_DOCTOR - no auto expiration
    1: timedelta(days=730),      # RESIDENT - 1 year
    2: None,                     # NURSE - no auto expiration
    3: timedelta(days=730),      # PHYSIOTERAPIST - 2 years
    4: timedelta(days=180),      # STUDENT - 6 months
}

# Activity scoring weights
ACTIVITY_WEIGHTS = {
    'login': 1,
    'patient_view': 2,
    'patient_edit': 3,
    'note_create': 5,
    'note_edit': 3,
    'form_complete': 4,
    'media_upload': 2,
    'media_view': 1,
    'search': 1,
    'admin_action': 2,
}

# Notification thresholds
NOTIFICATION_THRESHOLDS = {
    'expiration_warning_days': [30, 14, 7, 3, 1],  # Days before expiration
    'inactivity_warning_days': [60, 75, 85],        # Days of inactivity
    'review_reminder_days': [30, 14, 7],            # Days before review due
}

# Status transition rules
STATUS_TRANSITIONS = {
    'active': ['expiring_soon', 'inactive', 'suspended', 'renewal_required'],
    'expiring_soon': ['active', 'expired', 'renewal_required'],
    'expired': ['active', 'departed'],
    'inactive': ['active', 'suspended', 'departed'],
    'suspended': ['active', 'departed'],
    'departed': [],  # Terminal status
    'renewal_required': ['active', 'suspended', 'expired'],
}
```

## Testing Requirements

### Unit Tests

```python
# apps/accounts/tests/test_lifecycle_models.py

class UserLifecycleModelTests(TestCase):
    def setUp(self):
        self.user = EqmdCustomUserFactory(
            profession_type=1,  # RESIDENT
            internship_start_date=timezone.now().date(),
            expected_duration_months=12
        )

    def test_expiration_calculation(self):
        """Test role-based expiration calculation"""
        expiration = self.user.calculate_role_based_expiration()
        expected = self.user.internship_start_date + relativedelta(months=12)
        self.assertEqual(expiration, expected)

    def test_activity_score_update(self):
        """Test activity score updates"""
        initial_score = self.user.activity_score
        self.user.update_activity_score('patient_access')
        self.assertGreater(self.user.activity_score, initial_score)
        self.assertIsNotNone(self.user.last_meaningful_activity)

    def test_expiration_properties(self):
        """Test expiration status properties"""
        # Set expiration to 15 days from now
        self.user.access_expires_at = timezone.now() + timedelta(days=15)

        self.assertTrue(self.user.is_expiring_soon)
        self.assertFalse(self.user.is_expired)
        self.assertEqual(self.user.days_until_expiration, 15)

    def test_access_extension(self):
        """Test access extension functionality"""
        original_expiration = timezone.now() + timedelta(days=30)
        self.user.access_expires_at = original_expiration

        admin_user = EqmdCustomUserFactory(is_staff=True)
        self.user.extend_access(60, "Performance review completed", admin_user)

        expected_expiration = original_expiration + timedelta(days=60)
        self.assertEqual(self.user.access_expires_at.date(), expected_expiration.date())
        self.assertEqual(self.user.reviewed_by, admin_user)
```

### Integration Tests

```python
# apps/accounts/tests/test_lifecycle_integration.py

class LifecycleIntegrationTests(TestCase):
    def test_migration_data_integrity(self):
        """Test that migrations preserve existing user data"""
        # Test will be implemented to verify migration safety
        pass

    def test_simple_history_integration(self):
        """Test lifecycle changes are tracked in history"""
        user = EqmdCustomUserFactory()
        user.account_status = 'expired'
        user._change_reason = 'Access expired due to inactivity'
        user.save()

        history = user.history.first()
        self.assertEqual(history.account_status, 'expired')
        self.assertEqual(history.history_change_reason, 'Access expired due to inactivity')
```

## Security Considerations

### Data Protection

- **Sensitive Data**: Supervisor relationships and review reasons require proper access controls
- **Audit Trail**: All lifecycle changes must be tracked in history tables
- **Privacy**: Activity tracking should not expose specific patient interactions

### Performance Optimization

- **Database Indexes**: Added on frequently queried fields (status, expiration date)
- **Query Efficiency**: Properties use efficient date calculations
- **Batch Operations**: Designed for bulk status updates without performance impact

## Documentation Requirements

### Admin Documentation

- **Field Descriptions**: Clear help text for all new fields
- **Workflow Guides**: Step-by-step procedures for common lifecycle tasks
- **Troubleshooting**: Common issues and resolution procedures

### Developer Documentation

- **API Reference**: Model methods and properties documentation
- **Integration Guide**: How to update activity scores from other apps
- **Migration Guide**: Safe procedures for schema changes

## Rollback Plan

### Migration Rollback

```bash
# If issues occur, rollback migrations in reverse order
uv run python manage.py migrate accounts 0003_add_terms_acceptance

# Manual data cleanup if needed
uv run python manage.py shell -c "
from apps.accounts.models import EqmdCustomUser
EqmdCustomUser.objects.update(account_status='active')
"
```

### Feature Flags

- Consider implementing feature flags to gradually enable lifecycle features
- Allow disabling automated expiration during initial rollout
- Provide admin toggle for activity tracking

## Success Metrics

### Technical Metrics

- ✅ **Migration Success**: All existing users migrated without data loss
- ✅ **Performance Impact**: No significant slowdown in authentication flow
- ✅ **Data Integrity**: All fields properly validated and constrained

### Functional Metrics

- ✅ **Role Coverage**: All professional roles have appropriate expiration rules
- ✅ **Activity Tracking**: Meaningful activities properly scored and recorded
- ✅ **Status Accuracy**: Account statuses reflect actual user lifecycle state

---

**Next Phase**: [Phase 2: Middleware and Core Logic](phase_2_middleware_core_logic.md)
