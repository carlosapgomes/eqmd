# User Lifecycle Management Commands Reference

Complete reference for all management commands in the User Lifecycle Management system.

## Overview

The User Lifecycle Management system provides 6 essential management commands:

1. **`check_user_expiration`** - Daily status checking and updates
2. **`send_expiration_notifications`** - Email notification delivery
3. **`cleanup_inactive_users`** - Inactive user reporting
4. **`extend_user_access`** - Individual user access extension
5. **`bulk_user_operations`** - Bulk operations for multiple users
6. **`lifecycle_report`** - Comprehensive CSV reporting

## Command Details

### 1. check_user_expiration

**Purpose**: Check and update user expiration statuses automatically.

**Usage**:

```bash
docker compose exec eqmd python manage.py check_user_expiration [OPTIONS]
```

**Options**:

- `--dry-run` - Show what would be updated without making changes
- `--role {resident,student,all}` - Check specific user roles only (default: all)

**Examples**:

```bash
# Check all users and update statuses
docker compose exec eqmd python manage.py check_user_expiration

# Preview changes without applying them
docker compose exec eqmd python manage.py check_user_expiration --dry-run

# Check only resident users
docker compose exec eqmd python manage.py check_user_expiration --role resident
```

**Sample Output**:

```
Starting simplified expiration check (dry_run=False)
Found 4 users to check

2 users newly expired:
  - sample_res_ana (Residente) - Expired: 15/01/2025
  - sample_res_carlos (Residente) - Expired: 18/01/2025

1 users expiring soon:
  - sample_est_paula (Estudante) - 25 days left

0 errors occurred
```

**Scheduling**: Run daily at 6:00 AM via cron.

---

### 2. send_expiration_notifications

**Purpose**: Send email notifications to users approaching expiration.

**Usage**:

```bash
docker compose exec eqmd python manage.py send_expiration_notifications [OPTIONS]
```

**Options**:

- `--dry-run` - Show notifications that would be sent without sending them
- `--warning-days DAYS [DAYS ...]` - Days before expiration to send warnings (default: 30 14 7 3 1)

**Examples**:

```bash
# Send notifications with default warning periods
docker compose exec eqmd python manage.py send_expiration_notifications

# Preview notifications without sending
docker compose exec eqmd python manage.py send_expiration_notifications --dry-run

# Custom warning periods (only 30, 7, 1 days)
docker compose exec eqmd python manage.py send_expiration_notifications --warning-days 30 7 1
```

**Sample Output**:

```
Sending expiration notifications (simplified - email only, dry_run=False)
Found 0 users to notify (30 days)
Found 1 users to notify (14 days)
  Email sent to sample_res_ana
Found 0 users to notify (7 days)
Found 2 users to notify (3 days)
  Email sent to sample_res_carlos
  Email sent to sample_est_paula
Found 0 users to notify (1 days)
Sent 3 notifications, 0 errors
```

**Rate Limiting**: Maximum one notification per user per week to prevent spam.

**Scheduling**: Run daily at 8:00 AM via cron.

---

### 3. cleanup_inactive_users

**Purpose**: Generate reports on inactive users (no automatic changes made).

**Usage**:

```bash
docker compose exec eqmd python manage.py cleanup_inactive_users [OPTIONS]
```

**Options**:

- `--inactivity-days DAYS` - Days of inactivity to report on (default: 90)
- `--format {table,csv}` - Output format (default: table)

**Examples**:

```bash
# Generate table report for 90-day inactive users
docker compose exec eqmd python manage.py cleanup_inactive_users

# Generate CSV report for 60-day inactive users
docker compose exec eqmd python manage.py cleanup_inactive_users --inactivity-days 60 --format csv

# Generate report with custom threshold
docker compose exec eqmd python manage.py cleanup_inactive_users --inactivity-days 30 --format table
```

**Sample Output** (table format):

```
Generating inactive user report (simplified - no auto-changes)
Found 3 inactive users

INACTIVE USER REPORT
------------------------------------------------------------
Username             Profession      Last Activity Days 
------------------------------------------------------------
sample_res_ana       Residente       15/12/2024   45   
sample_est_paula     Estudante       10/12/2024   50   
sample_est_pedro     Estudante       05/12/2024   55   

RECOMMENDATION: Review these users for potential status updates
```

**Note**: This command only reports - it never automatically changes user status.

**Scheduling**: Run weekly on Sundays at 7:00 AM via cron.

---

### 4. extend_user_access

**Purpose**: Extend access expiration for individual users.

**Usage**:

```bash
docker compose exec eqmd python manage.py extend_user_access USERNAME [OPTIONS]
```

**Required Arguments**:

- `USERNAME` - Username of user to extend access

**Options**:

- `--days DAYS` - Number of days to extend access (required)
- `--reason REASON` - Reason for access extension (required)
- `--force` - Force extension even if user is expired/departed

**Examples**:

```bash
# Extend user access by 90 days
docker compose exec eqmd python manage.py extend_user_access sample_res_ana \
  --days 90 \
  --reason "Performance review completed, extension approved"

# Force extension for expired user
docker compose exec eqmd python manage.py extend_user_access expired_user \
  --days 60 \
  --reason "Special circumstances" \
  --force
```

**Interactive Process**:

```
Current user status:
  Username: sample_res_ana
  Current expiration: 26/02/2025 00:00
  Current status: Expiring Soon (30 days)

Proposed extension:
  Extension period: 90 days
  New expiration: 27/05/2025 00:00
  Reason: Performance review completed

Confirm extension? (y/N): y
Successfully extended access for sample_res_ana
New expiration: 27/05/2025 00:00
New status: Active
```

**Usage**: Used by administrators for individual user management.

---

### 5. bulk_user_operations

**Purpose**: Perform bulk operations on multiple users.

**Usage**:

```bash
docker compose exec eqmd python manage.py bulk_user_operations {extend,set-expiration} [OPTIONS]
```

#### Subcommand: extend

Bulk extend user access from CSV file.

**Options**:

- `--csv-file FILE` - CSV file with usernames and extension data (required)
- `--dry-run` - Preview changes without applying them

**CSV Format**:

```csv
username,days,reason
sample_res_ana,90,Performance review completed
sample_res_carlos,120,Extended residency program
sample_est_paula,60,Rotation extension
```

**Examples**:

```bash
# Test bulk extension (dry run)
docker compose exec eqmd python manage.py bulk_user_operations extend \
  --csv-file extensions.csv \
  --dry-run

# Apply bulk extensions
docker compose exec eqmd python manage.py bulk_user_operations extend \
  --csv-file extensions.csv
```

#### Subcommand: set-expiration

Set expiration dates for all users of a specific role.

**Options**:

- `--role {resident,student}` - User role to update (required)
- `--months MONTHS` - Months from now to expire (required)
- `--reason REASON` - Reason for expiration update (default: "Bulk expiration update")

**Examples**:

```bash
# Set all residents to expire in 18 months
docker compose exec eqmd python manage.py bulk_user_operations set-expiration \
  --role resident \
  --months 18 \
  --reason "Updated residency program duration"

# Set all students to expire in 6 months
docker compose exec eqmd python manage.py bulk_user_operations set-expiration \
  --role student \
  --months 6
```

**Confirmation Required**:

```
Found 12 residents to update
Set expiration to 27/07/2026 for all residents? (y/N): y
Successfully updated expiration for 12 residents
```

---

### 6. lifecycle_report

**Purpose**: Generate comprehensive user lifecycle reports in CSV format.

**Usage**:

```bash
docker compose exec eqmd python manage.py lifecycle_report [OPTIONS]
```

**Options**:

- `--output-file FILE` - Output CSV file path (default: lifecycle_report_YYYYMMDD.csv)
- `--days-ahead DAYS` - Look ahead days for expiration analysis (default: 90)

**Examples**:

```bash
# Generate report with default filename
docker compose exec eqmd python manage.py lifecycle_report

# Generate report with custom filename
docker compose exec eqmd python manage.py lifecycle_report --output-file monthly_report.csv

# Generate report looking 60 days ahead
docker compose exec eqmd python manage.py lifecycle_report --days-ahead 60 --output-file custom_report.csv
```

**Sample CSV Output**:

```csv
username,full_name,email,profession,account_status,expiration_date,days_until_expiration,last_activity,days_since_activity,supervisor
sample_res_ana,Ana Rodrigues,ana@example.com,Residente,Active,26/02/2025,45,15/12/2024,30,dr.silva
sample_dr_silva,João Silva,silva@example.com,Médico,Active,Never,N/A,20/12/2024,25,None
sample_est_paula,Paula Alves,paula@example.com,Estudante,Expiring Soon,15/02/2025,35,10/12/2024,35,dr.costa
```

**Report Fields**:

- `username` - User's login username
- `full_name` - Full display name
- `email` - Email address
- `profession` - Professional role
- `account_status` - Current lifecycle status
- `expiration_date` - When access expires (or "Never")
- `days_until_expiration` - Days remaining until expiration
- `last_activity` - Last meaningful activity timestamp
- `days_since_activity` - Days since last activity
- `supervisor` - Assigned supervisor username

**Scheduling**: Run weekly on Sundays at 7:30 AM via cron.

## Common Usage Patterns

### Daily Maintenance Workflow

```bash
# 1. Check and update user statuses
docker compose exec eqmd python manage.py check_user_expiration

# 2. Send expiration notifications
docker compose exec eqmd python manage.py send_expiration_notifications

# 3. Check for any issues
tail -f /app/logs/lifecycle/expiration_check.log
tail -f /app/logs/lifecycle/notifications.log
```

### Weekly Reporting Workflow

```bash
# 1. Generate comprehensive lifecycle report
docker compose exec eqmd python manage.py lifecycle_report --output-file weekly_$(date +%Y%m%d).csv

# 2. Identify inactive users
docker compose exec eqmd python manage.py cleanup_inactive_users --format csv > inactive_$(date +%Y%m%d).csv

# 3. Review results
head -10 weekly_$(date +%Y%m%d).csv
head -10 inactive_$(date +%Y%m%d).csv
```

### Individual User Management

```bash
# 1. Check specific user status
docker compose exec eqmd python manage.py lifecycle_report | grep username

# 2. Extend user access if needed
docker compose exec eqmd python manage.py extend_user_access username \
  --days 90 \
  --reason "Approved by supervisor"

# 3. Verify extension
docker compose exec eqmd python manage.py lifecycle_report | grep username
```

### Bulk User Management

```bash
# 1. Create CSV file with extensions
cat > extensions.csv << EOF
username,days,reason
user1,90,Performance approved
user2,120,Extended program
user3,60,Special circumstances
EOF

# 2. Test bulk operation
docker compose exec eqmd python manage.py bulk_user_operations extend \
  --csv-file extensions.csv \
  --dry-run

# 3. Apply changes
docker compose exec eqmd python manage.py bulk_user_operations extend \
  --csv-file extensions.csv

# 4. Clean up
rm extensions.csv
```

## Error Handling

All commands include comprehensive error handling:

### Common Error Messages

**User not found**:

```
CommandError: User "nonexistent_user" does not exist
```

**Invalid role**:

```
CommandError: argument --role: invalid choice: 'invalid' (choose from 'resident', 'student', 'all')
```

**Missing CSV file**:

```
CommandError: File not found: missing_file.csv
```

**Invalid CSV format**:

```
CommandError: CSV must contain columns: username, days, reason
```

**Permission denied**:

```
CommandError: Cannot extend access for departed user. Use --force to override.
```

### Error Recovery

Most commands support recovery mechanisms:

1. **Dry-run mode** - Test commands before applying changes
2. **Force options** - Override restrictions when necessary
3. **Detailed logging** - All operations logged for troubleshooting
4. **Rollback support** - Changes trackable via audit history

## Performance Considerations

### Command Execution Times

Typical execution times for a system with ~100 users:

- `check_user_expiration`: 2-5 seconds
- `send_expiration_notifications`: 5-15 seconds (depends on email count)
- `cleanup_inactive_users`: 1-3 seconds
- `extend_user_access`: 1-2 seconds
- `bulk_user_operations`: 5-30 seconds (depends on operation size)
- `lifecycle_report`: 3-10 seconds

### Optimization Tips

1. **Use role filtering** - Limit `check_user_expiration` to specific roles when possible
2. **Batch email sending** - Default notification batching reduces email server load
3. **CSV preprocessing** - Validate CSV files before bulk operations
4. **Database indexes** - Lifecycle fields are automatically indexed
5. **Log rotation** - Implement log rotation to prevent disk space issues

## Security Considerations

### Audit Logging

All command executions are logged:

```bash
# View command execution logs
tail -f /app/logs/lifecycle/*.log

# Search for specific user actions
grep "sample_res_ana" /app/logs/lifecycle/*.log
```

### Permission Requirements

Commands require appropriate Django permissions:

- **Daily commands** - Can be run by cron user (www-data)
- **Extension commands** - Require staff user permissions
- **Bulk operations** - Require superuser permissions for safety
- **Reports** - Can be run by any staff user

### Sensitive Data Protection

Commands protect sensitive information:

- Passwords never logged or displayed
- Email addresses only in designated log files
- Patient data never included in lifecycle operations
- Audit trails maintain data integrity

## Troubleshooting Guide

### Command Not Found

```bash
# Verify command availability
docker compose exec eqmd python manage.py help | grep lifecycle

# Check Django path
docker compose exec eqmd python manage.py shell -c "import apps.accounts.management.commands.check_user_expiration"
```

### Database Connection Issues

```bash
# Test database connectivity
docker compose exec eqmd python manage.py check --database

# Verify migrations
docker compose exec eqmd python manage.py showmigrations accounts | grep lifecycle
```

### Email Delivery Problems

```bash
# Test email configuration
docker compose exec eqmd python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])
print('Email sent successfully')
"
```

### Permission Errors

```bash
# Check file permissions
ls -la /app/reports/lifecycle/
ls -la /app/logs/lifecycle/

# Fix permissions if needed
sudo chown -R www-data:www-data /app/reports/lifecycle/
sudo chown -R www-data:www-data /app/logs/lifecycle/
```

## Integration with Monitoring

### Health Checks

```bash
# Simple health check command
docker compose exec eqmd python manage.py check_user_expiration --dry-run --role resident | grep "Found"

# Expected output: "Found N users to check"
```

### Metrics Collection

```bash
# Extract metrics from command output
docker compose exec eqmd python manage.py lifecycle_report | wc -l  # Total active users
docker compose exec eqmd python manage.py cleanup_inactive_users | grep "Found" | cut -d' ' -f2  # Inactive count
```

### Log Analysis

```bash
# Success/failure rates
grep -c "Successfully" /app/logs/lifecycle/expiration_check.log
grep -c "ERROR" /app/logs/lifecycle/*.log

# User activity patterns
grep "status updated" /app/logs/lifecycle/expiration_check.log | tail -10
```

This completes the comprehensive command reference for the User Lifecycle Management system.
