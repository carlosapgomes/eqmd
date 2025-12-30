# Phase 1: Simplified Database Schema

## Overview

**Timeline: 1 week**
**Priority: High**

Implement **essential** database fields for user lifecycle management. This simplified schema focuses on core expiration and basic activity tracking while maintaining compatibility with existing audit history systems.

## Database Model Extensions (Simplified)

### Essential Fields for EqmdCustomUser

```python
# apps/accounts/models.py - EqmdCustomUser class additions

class EqmdCustomUser(AbstractUser):
    # ... existing fields ...

    # === Essential User Lifecycle Fields ===

    # Core Expiration Management
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
            ('administrative', 'Administrative Decision'),
            ('inactivity', 'Account Inactivity'),
        ],
        blank=True,
        help_text="Reason for access expiration"
    )

    # Simple Activity Tracking (timestamp only, no complex scoring)
    last_meaningful_activity = models.DateTimeField(
        null=True, blank=True,
        help_text="Last time user performed meaningful action (not just login)"
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

    # Role-Specific Fields for Auto-Expiration
    internship_start_date = models.DateField(
        null=True, blank=True,
        help_text="Start date for internship/residency (for automatic expiration calculation)"
    )
    expected_duration_months = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Expected duration in months (for residents/students)"
    )

    # Supervisor for Approval Workflows
    supervisor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='supervised_users',
        help_text="Direct supervisor for renewal approvals"
    )

    # Basic Notification Tracking
    expiration_warning_sent = models.DateTimeField(
        null=True, blank=True,
        help_text="When expiration warning was last sent"
    )
```

### Essential Model Methods (Simplified)

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

    def update_activity_timestamp(self):
        """Update last meaningful activity timestamp (simplified - no scoring)"""
        self.last_meaningful_activity = timezone.now()

    def extend_access(self, days, reason, extended_by_user):
        """Extend user access by specified days"""
        if not self.access_expires_at:
            self.access_expires_at = timezone.now() + timedelta(days=days)
        else:
            self.access_expires_at += timedelta(days=days)

        self._change_reason = f"Access extended by {days} days. Reason: {reason}"

        # Reset notification tracking
        self.expiration_warning_sent = None

        # Update status if needed
        if self.account_status in ['expired', 'expiring_soon']:
            self.account_status = 'active'
```

## Simplified Database Migrations

### Migration 1: Core Essential Fields

```python
# apps/accounts/migrations/0004_add_essential_lifecycle_fields.py

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_add_terms_acceptance'),
    ]

    operations = [
        # Essential expiration fields
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
                choices=[
                    ('end_of_internship', 'End of Internship/Residency'),
                    ('end_of_rotation', 'End of Clinical Rotation'),
                    ('employment_end', 'Employment Termination'),
                    ('leave_of_absence', 'Leave of Absence'),
                    ('administrative', 'Administrative Decision'),
                    ('inactivity', 'Account Inactivity'),
                ]),
        ),

        # Simple activity tracking (timestamp only)
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='last_meaningful_activity',
            field=models.DateTimeField(blank=True, null=True,
                help_text="Last time user performed meaningful action"),
        ),

        # Account status
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='account_status',
            field=models.CharField(default='active', max_length=20,
                choices=[
                    ('active', 'Active'),
                    ('expiring_soon', 'Expiring Soon (30 days)'),
                    ('expired', 'Access Expired'),
                    ('inactive', 'Inactive (no recent activity)'),
                    ('suspended', 'Administratively Suspended'),
                    ('departed', 'No longer with institution'),
                    ('renewal_required', 'Renewal Required'),
                ]),
        ),

        # Role-specific fields
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='internship_start_date',
            field=models.DateField(blank=True, null=True,
                help_text="Start date for internship/residency"),
        ),
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='expected_duration_months',
            field=models.PositiveIntegerField(blank=True, null=True,
                help_text="Expected duration in months"),
        ),

        # Supervisor relationship
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='supervisor',
            field=models.ForeignKey(blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='supervised_users', to=settings.AUTH_USER_MODEL),
        ),

        # Basic notification tracking
        migrations.AddField(
            model_name='eqmdcustomuser',
            name='expiration_warning_sent',
            field=models.DateTimeField(blank=True, null=True,
                help_text="When expiration warning was last sent"),
        ),

        # Performance indexes
        migrations.RunSQL([
            "CREATE INDEX accounts_user_status_idx ON accounts_eqmdcustomuser(account_status);",
            "CREATE INDEX accounts_user_expires_idx ON accounts_eqmdcustomuser(access_expires_at);",
        ]),
    ]
```

### Migration 2: Data Population

```python
# apps/accounts/migrations/0005_populate_essential_lifecycle_data.py

from django.db import migrations
from django.utils import timezone
from datetime import timedelta

def populate_essential_lifecycle_data(apps, schema_editor):
    """Set initial lifecycle data for existing users"""
    EqmdCustomUser = apps.get_model('accounts', 'EqmdCustomUser')

    # Set all existing users as active with basic activity
    EqmdCustomUser.objects.update(
        account_status='active',
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
        ('accounts', '0004_add_essential_lifecycle_fields'),
    ]

    operations = [
        migrations.RunPython(
            populate_essential_lifecycle_data,
            reverse_populate_lifecycle_data,
        ),
    ]
```

## Simplified Configuration

### Role-Based Configuration (Essential Only)

```python
# apps/accounts/lifecycle_config.py

from datetime import timedelta

# Simplified default expiration periods by role
ROLE_EXPIRATION_DEFAULTS = {
    0: None,                     # MEDICAL_DOCTOR - no auto expiration
    1: timedelta(days=365),      # RESIDENT - 1 year
    2: None,                     # NURSE - no auto expiration
    3: None,                     # PHYSIOTERAPIST - no auto expiration
    4: timedelta(days=180),      # STUDENT - 6 months
}

# Simple notification thresholds
NOTIFICATION_THRESHOLDS = {
    'expiration_warning_days': [30, 14, 7, 3, 1],  # Days before expiration
    'inactivity_threshold_days': 90,                # Days before marking inactive
}

# Simplified status transitions
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

## Renewal Request Model (Simplified)

```python
# apps/core/models.py - Add basic renewal request tracking

class AccountRenewalRequest(models.Model):
    """Track user account renewal requests (simplified)"""

    user = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.CASCADE,
        related_name='renewal_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # User-provided information
    current_position = models.CharField(max_length=200)
    supervisor_name = models.CharField(max_length=200)
    supervisor_email = models.EmailField()
    renewal_reason = models.TextField()
    expected_duration_months = models.PositiveIntegerField()

    # Simple request status
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Administrative response (simplified)
    reviewed_by = models.ForeignKey(
        'accounts.EqmdCustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_renewal_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Renewal request for {self.user.username} - {self.status}"

    def approve(self, reviewed_by_user, duration_months, admin_notes=''):
        """Approve renewal request and extend user access"""
        from django.utils import timezone
        from datetime import timedelta

        self.status = 'approved'
        self.reviewed_by = reviewed_by_user
        self.reviewed_at = timezone.now()
        self.admin_notes = admin_notes

        # Calculate new expiration date
        current_expiration = self.user.access_expires_at or timezone.now()
        extension = timedelta(days=duration_months * 30)  # Approximate months
        new_expiration = current_expiration + extension

        # Update user account
        self.user.access_expires_at = new_expiration
        self.user.account_status = 'active'
        self.user._change_reason = f'Access renewed via request #{self.id}'

        # Save changes
        self.save()
        self.user.save()

    def deny(self, reviewed_by_user, admin_notes):
        """Deny renewal request"""
        self.status = 'denied'
        self.reviewed_by = reviewed_by_user
        self.reviewed_at = timezone.now()
        self.admin_notes = admin_notes
        self.save()
```

## Testing Requirements (Simplified)

### Essential Unit Tests

```python
# apps/accounts/tests/test_simplified_lifecycle.py

class SimplifiedLifecycleTests(TestCase):
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

    def test_activity_timestamp_update(self):
        """Test simple activity timestamp updates"""
        self.assertIsNone(self.user.last_meaningful_activity)
        self.user.update_activity_timestamp()
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
```

## Security Considerations (Simplified)

### Data Protection

- **Audit Trail**: All lifecycle changes tracked in existing history tables
- **Privacy**: Activity tracking uses simple timestamps (no detailed patient interaction data)
- **Access Controls**: Supervisor relationships require proper admin access

### Performance Optimization

- **Database Indexes**: Added on frequently queried fields (status, expiration date)
- **Simple Queries**: Properties use efficient date calculations
- **Minimal Overhead**: No complex scoring algorithms or frequent updates

## Rollback Plan

### Migration Rollback

```bash
# If issues occur, rollback migration
uv run python manage.py migrate accounts 0003_add_terms_acceptance

# Manual cleanup if needed
uv run python manage.py shell -c "
from apps.accounts.models import EqmdCustomUser
EqmdCustomUser.objects.update(account_status='active')
"
```

## What Was Simplified

### ❌ Removed from Original Plan

- **Access Review Fields**: `last_access_review`, `reviewed_by`, `next_review_due` (can be added later)
- **Complex Activity Scoring**: `activity_score` field and scoring algorithms
- **Advanced Notification Tracking**: `renewal_reminder_count` and complex notification state
- **Department Field**: Can be added later if needed
- **Complex Status Calculation**: Simplified to basic time-based checks

### ✅ Kept (Essential)

- Core expiration fields for automated blocking
- Simple activity timestamp for basic inactivity detection
- Role-specific fields for automatic expiration calculation
- Supervisor relationship for approval workflows
- Basic renewal request system

## Success Metrics (Simplified)

### Technical Metrics

- ✅ **Migration Success**: All existing users migrated without data loss
- ✅ **Performance Impact**: Minimal impact on authentication flow
- ✅ **Essential Function**: Core expiration blocking works correctly

### Functional Metrics

- ✅ **Role Coverage**: Residents and students have appropriate expiration rules
- ✅ **Activity Tracking**: Basic activity timestamps recorded
- ✅ **Status Management**: Core account statuses function correctly

---

**Next Phase**: [Phase 2: Simplified Middleware and Core Logic](phase_2_middleware_core_logic_simplified.md)
