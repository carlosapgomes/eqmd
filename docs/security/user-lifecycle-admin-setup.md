# User Lifecycle Management - Admin Setup Guide

This guide provides detailed instructions for administrators to set up, configure, and use the User Lifecycle Management system in EquipeMed.

## Prerequisites

Before setting up user lifecycle management, ensure:

- ✅ Phase 1 database migrations have been applied
- ✅ Phase 2 middleware is configured and active
- ✅ Phase 3 management commands are available
- ✅ Email system is configured for notifications
- ✅ Django admin access is available

## Initial Setup

### 1. Apply Database Migrations

Run the lifecycle management migrations:

```bash
# Apply the essential lifecycle fields migration
docker compose exec eqmd python manage.py migrate accounts

# Verify migration status
docker compose exec eqmd python manage.py showmigrations accounts
```

Expected output should show lifecycle migrations as applied:

```
accounts
 [X] 0001_initial
 [X] 0002_add_profession_fields
 [X] 0003_add_terms_acceptance
 [X] 0004_add_essential_lifecycle_fields
 [X] 0005_populate_essential_lifecycle_data
```

### 2. Verify Middleware Configuration

Ensure the lifecycle middleware is active in settings:

```python
# config/settings.py
MIDDLEWARE = [
    # ... other middleware ...
    "apps.core.middleware.UserLifecycleMiddleware",
    # ... remaining middleware ...
]
```

Test middleware functionality:

```bash
# Check that middleware loads without errors
docker compose exec eqmd python manage.py check --deploy
```

### 3. Configure Email Settings

Verify email configuration for notifications:

```bash
# Test email configuration
docker compose exec eqmd python manage.py shell -c "
from django.core.mail import send_mail
from django.conf import settings
print('Email backend:', settings.EMAIL_BACKEND)
print('Default from email:', settings.DEFAULT_FROM_EMAIL)
"
```

### 4. Verify Management Commands

Test that all lifecycle commands are available:

```bash
# List lifecycle management commands
docker compose exec eqmd python manage.py help | grep -E "(check_user|send_expiration|cleanup|extend|bulk|lifecycle)"
```

Expected commands:

- `check_user_expiration`
- `send_expiration_notifications`
- `cleanup_inactive_users`
- `extend_user_access`
- `bulk_user_operations`
- `lifecycle_report`

## User Configuration

### 1. Set Expiration Dates for Existing Users

Configure expiration dates for residents and students:

#### Option A: Via Django Admin

1. Go to Django Admin → Users
2. Select residents (profession_type = "Residente")
3. Use bulk edit to set:
   - `access_expires_at`: Appropriate expiration date
   - `expiration_reason`: "end_of_internship"
   - `account_status`: "active"

#### Option B: Via Management Command

```bash
# Set all residents to expire in 12 months
docker compose exec eqmd python manage.py bulk_user_operations set-expiration \
  --role resident \
  --months 12 \
  --reason "Standard residency duration"

# Set all students to expire in 6 months
docker compose exec eqmd python manage.py bulk_user_operations set-expiration \
  --role student \
  --months 6 \
  --reason "Standard rotation duration"
```

### 2. Configure Supervisor Relationships

Set up supervisor relationships for approval workflows:

#### Via Django Admin

1. Go to Django Admin → Users
2. Edit each resident/student user
3. Set the `supervisor` field to their direct supervisor
4. Save changes

#### Via Management Script

```python
# Example script to set supervisors
docker compose exec eqmd python manage.py shell -c "
from apps.accounts.models import EqmdCustomUser

# Set Dr. Silva as supervisor for all residents
supervisor = EqmdCustomUser.objects.get(username='dr.silva')
residents = EqmdCustomUser.objects.filter(profession_type=1)
residents.update(supervisor=supervisor)

print(f'Set supervisor for {residents.count()} residents')
"
```

### 3. Initialize Activity Tracking

Update activity timestamps for all users:

```bash
# Set initial activity for all users (30 days ago)
uv run python manage.py shell -c "
from apps.accounts.models import EqmdCustomUser
from django.utils import timezone
from datetime import timedelta

users = EqmdCustomUser.objects.filter(is_active=True)
activity_date = timezone.now() - timedelta(days=30)

for user in users:
    user.last_meaningful_activity = activity_date
    user.save(update_fields=['last_meaningful_activity'])

print(f'Updated activity for {users.count()} users')
"
```

## Daily Operations

### 1. Manual Expiration Check

Run expiration checking manually to see what would happen:

```bash
# Dry run to see what users would be updated
uv run python manage.py check_user_expiration --dry-run

# Actually update user statuses
uv run python manage.py check_user_expiration

# Check specific role only
uv run python manage.py check_user_expiration --role resident
```

Example output:

```
Starting simplified expiration check (dry_run=False)
Found 4 users to check

2 users expiring soon:
  - sample_res_ana (Residente) - 25 days left
  - sample_res_carlos (Residente) - 28 days left

0 users newly expired:

1 users status updated:
  - sample_est_paula: active -> expiring_soon
```

### 2. Send Expiration Notifications

Test and send expiration notifications:

```bash
# Dry run to see who would receive notifications
uv run python manage.py send_expiration_notifications --dry-run

# Send actual notifications
uv run python manage.py send_expiration_notifications

# Custom warning days
uv run python manage.py send_expiration_notifications --warning-days 30 7 1
```

### 3. Generate Reports

Create reports on user lifecycle status:

```bash
# Generate comprehensive lifecycle report
uv run python manage.py lifecycle_report --output-file lifecycle_$(date +%Y%m%d).csv

# Find inactive users (90+ days no activity)
uv run python manage.py cleanup_inactive_users --inactivity-days 90

# Output inactive users as CSV
uv run python manage.py cleanup_inactive_users --format csv > inactive_users.csv
```

## User Management Tasks

### 1. Extend Individual User Access

Extend access for a specific user:

```bash
# Extend user access by 90 days
uv run python manage.py extend_user_access username_here \
  --days 90 \
  --reason "Performance review completed, extension approved"

# Force extension even for departed users
uv run python manage.py extend_user_access expired_user \
  --days 60 \
  --reason "Special circumstances" \
  --force
```

Example session:

```
Current user status:
  Username: sample_res_ana
  Current expiration: 26/02/2026 00:00
  Current status: Expiring Soon (30 days)

Proposed extension:
  Extension period: 90 days
  New expiration: 27/05/2026 00:00
  Reason: Performance review completed

Confirm extension? (y/N): y
Successfully extended access for sample_res_ana
```

### 2. Bulk User Operations

#### Bulk Access Extension

Create a CSV file with extension data:

```csv
username,days,reason
sample_res_ana,90,Performance review completed
sample_res_carlos,120,Extended residency program
sample_est_paula,60,Rotation extension
```

Apply bulk extensions:

```bash
# Test with dry run first
uv run python manage.py bulk_user_operations extend \
  --csv-file extensions.csv \
  --dry-run

# Apply actual changes
uv run python manage.py bulk_user_operations extend \
  --csv-file extensions.csv
```

#### Bulk Expiration Setting

```bash
# Set expiration for all residents to 18 months from now
uv run python manage.py bulk_user_operations set-expiration \
  --role resident \
  --months 18 \
  --reason "Updated residency program duration"
```

### 3. Handle Renewal Requests

Monitor and process renewal requests via Django Admin:

#### View Renewal Requests

1. Go to Django Admin → Core → Account Renewal Requests
2. View pending requests sorted by creation date
3. Click on a request to review details

#### Approve Renewal Request

```python
# Via Django Admin or shell
uv run python manage.py shell -c "
from apps.core.models import AccountRenewalRequest
from apps.accounts.models import EqmdCustomUser

# Get the renewal request
request = AccountRenewalRequest.objects.get(id=1)
admin_user = EqmdCustomUser.objects.get(username='admin')

# Approve for 12 months
request.approve(
    reviewed_by_user=admin_user,
    duration_months=12,
    admin_notes='Approved - continuing residency program'
)

print(f'Approved renewal for {request.user.username}')
"
```

#### Deny Renewal Request

```python
uv run python manage.py shell -c "
from apps.core.models import AccountRenewalRequest

request = AccountRenewalRequest.objects.get(id=2)
admin_user = EqmdCustomUser.objects.get(username='admin')

request.deny(
    reviewed_by_user=admin_user,
    admin_notes='Insufficient justification provided'
)

print(f'Denied renewal for {request.user.username}')
"
```

## Monitoring and Maintenance

### 1. Check System Health

Monitor lifecycle system health:

```bash
# Check for users with inconsistent status
uv run python manage.py shell -c "
from apps.accounts.models import EqmdCustomUser
from django.utils import timezone

# Find expired users still marked as active
expired_active = EqmdCustomUser.objects.filter(
    access_expires_at__lt=timezone.now(),
    account_status='active'
)
print(f'Expired but active users: {expired_active.count()}')

# Find users without expiration but marked expiring
no_exp_expiring = EqmdCustomUser.objects.filter(
    access_expires_at__isnull=True,
    account_status='expiring_soon'
)
print(f'No expiration but expiring users: {no_exp_expiring.count()}')
"
```

### 2. Review Activity Tracking

Check activity tracking status:

```bash
# Users with no recorded activity
uv run python manage.py shell -c "
from apps.accounts.models import EqmdCustomUser

no_activity = EqmdCustomUser.objects.filter(
    is_active=True,
    last_meaningful_activity__isnull=True
)
print(f'Users with no activity recorded: {no_activity.count()}')

# List users by last activity
for user in EqmdCustomUser.objects.filter(is_active=True)[:10]:
    activity = user.last_meaningful_activity
    if activity:
        print(f'{user.username}: {activity.strftime(\"%Y-%m-%d\")}')
    else:
        print(f'{user.username}: No activity recorded')
"
```

### 3. Email Notification Status

Check email notification delivery:

```bash
# Users who haven't received recent notifications
uv run python manage.py shell -c "
from apps.accounts.models import EqmdCustomUser
from django.utils import timezone
from datetime import timedelta

expiring_users = EqmdCustomUser.objects.filter(
    account_status='expiring_soon',
    expiration_warning_sent__isnull=True
)
print(f'Expiring users without notifications: {expiring_users.count()}')

# Users with old notification timestamps
old_notifications = EqmdCustomUser.objects.filter(
    account_status='expiring_soon',
    expiration_warning_sent__lt=timezone.now() - timedelta(days=14)
)
print(f'Users needing new notifications: {old_notifications.count()}')
"
```

## Troubleshooting

### Common Issues

#### Issue: Commands not found

```bash
# Verify Django can find the commands
uv run python manage.py help | grep lifecycle
```

**Solution**: Ensure migrations are applied and Django can import the commands module.

#### Issue: Email notifications not sending

```bash
# Test email configuration
uv run python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])
"
```

**Solution**: Check email backend configuration and SMTP settings.

#### Issue: Users not being blocked despite expired status

```bash
# Check middleware configuration
uv run python manage.py shell -c "
from django.conf import settings
middleware = settings.MIDDLEWARE
if 'apps.core.middleware.UserLifecycleMiddleware' in middleware:
    print('Middleware configured correctly')
else:
    print('Middleware missing or misconfigured')
"
```

#### Issue: Activity tracking not updating

Check that middleware is processing requests:

```bash
# Monitor logs for middleware activity
tail -f /var/log/django/security.log | grep user_lifecycle
```

### Reset User Status

If needed, reset user lifecycle status:

```bash
# Reset all users to active status (emergency)
uv run python manage.py shell -c "
from apps.accounts.models import EqmdCustomUser

EqmdCustomUser.objects.filter(
    account_status__in=['expired', 'suspended', 'departed']
).update(account_status='active')

print('Reset all problematic user statuses to active')
"
```

### Disable Lifecycle System Temporarily

If needed, temporarily disable lifecycle enforcement:

```python
# Comment out middleware in settings.py
MIDDLEWARE = [
    # ... other middleware ...
    # "apps.core.middleware.UserLifecycleMiddleware",  # Temporarily disabled
    # ... remaining middleware ...
]
```

Then restart the Django application.

## Performance Optimization

### Database Indexes

Verify lifecycle indexes exist:

```sql
-- Check indexes on lifecycle fields
SHOW INDEX FROM accounts_eqmdcustomuser WHERE Key_name LIKE '%status%' OR Key_name LIKE '%expires%';
```

### Monitoring Queries

Monitor lifecycle-related database queries:

```bash
# Enable query logging temporarily to monitor performance
uv run python manage.py shell -c "
import logging
logging.basicConfig()
logging.getLogger('django.db.backends').setLevel(logging.DEBUG)

# Run a lifecycle check and monitor queries
from django.core.management import call_command
call_command('check_user_expiration', '--dry-run')
"
```

## Security Considerations

### Audit Logging

Monitor lifecycle audit events:

```bash
# View recent lifecycle-related changes
uv run python manage.py shell -c "
from simple_history.models import HistoricalRecords
from apps.accounts.models import EqmdCustomUser

# Get recent status changes
recent_changes = EqmdCustomUser.history.filter(
    history_change_reason__icontains='lifecycle'
).order_by('-history_date')[:10]

for change in recent_changes:
    print(f'{change.username}: {change.account_status} at {change.history_date}')
"
```

### Access Controls

Verify admin permissions:

```bash
# Check that only authorized users can access lifecycle admin
uv run python manage.py shell -c "
from apps.accounts.models import EqmdCustomUser

admins = EqmdCustomUser.objects.filter(is_staff=True, is_active=True)
print(f'Active admin users: {admins.count()}')

for admin in admins:
    print(f'Admin: {admin.username} ({admin.email})')
"
```

## Next Steps

After completing the initial setup:

1. **Set up automated cronjobs** - See [Cronjob Setup Guide](user-lifecycle-cronjobs.md)
2. **Configure monitoring** - Set up log monitoring for lifecycle events
3. **Train administrators** - Ensure admins understand renewal request workflows
4. **Document procedures** - Create internal procedures for common scenarios
5. **Plan rollback strategy** - Prepare rollback procedures in case of issues

## Support

For additional help:

- Review management command help: `uv run python manage.py COMMAND_NAME --help`
- Check application logs: `/var/log/django/`
- Monitor audit history via Django Admin
- Consult main [User Lifecycle Documentation](user-lifecycle-management.md)
