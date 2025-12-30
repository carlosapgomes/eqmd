# User Lifecycle Management - Cronjob Setup

This guide provides detailed instructions for setting up automated cronjobs for the User Lifecycle Management system in EquipeMed. Proper automation ensures consistent enforcement of lifecycle policies without manual intervention.

## Overview

The lifecycle system requires several automated tasks:

- **Daily expiration checking** - Updates user statuses based on expiration dates
- **Daily notification sending** - Sends expiration warnings via email  
- **Weekly reporting** - Generates reports on inactive users
- **Monthly cleanup** - Comprehensive lifecycle reports for administrators

## Cronjob Configuration

### 1. System Requirements

Before setting up cronjobs, ensure:

- ✅ User lifecycle system is fully configured and tested
- ✅ Management commands work correctly when run manually
- ✅ Email system is configured and functional
- ✅ Log directories exist and are writable
- ✅ Report directories exist and are writable

### 2. Create Report Directories

```bash
# Create directories for automated reports
sudo mkdir -p /var/log/eqmd
sudo chown $USER:$USER /var/log/eqmd
```

### 3. Production Cronjob Configuration

Create the main cronjob configuration file:

```bash
# Create cronjob configuration
sudo nano /etc/cron.d/equipemd-lifecycle
```

Add the following configuration:

```bash
# EquipeMed User Lifecycle Management Cronjobs
# Maintained by: System Administrator
# Documentation: /home/carlos/projects/eqmd/docs/security/user-lifecycle-cronjobs.md

SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=admin@yourorganization.com

# Daily Tasks - Critical Operations

# Daily expiration status checking (6:00 AM)
0 6 * * * eqmd cd /home/carlos/projects/eqmd && /usr/bin/flock -n /tmp/check_expiration.lock docker compose exec -T eqmd python manage.py check_user_expiration >> /var/log/eqmd/expiration_check.log 2>&1

# Daily expiration notifications (8:00 AM) 
0 8 * * * eqmd cd /home/carlos/projects/eqmd && /usr/bin/flock -n /tmp/send_notifications.lock docker compose exec -T eqmd python manage.py send_expiration_notifications >> /var/log/eqmd/notifications.log 2>&1

# Weekly Tasks - Reporting and Analysis

# Weekly inactive user report (Sundays at 7:00 AM)
0 7 * * 0 eqmd cd /home/carlos/projects/eqmd && docker compose exec -T eqmd python manage.py cleanup_inactive_users --format csv > /var/log/eqmd/inactive_users_$(date +\%Y\%m\%d).csv 2>&1

# Weekly comprehensive lifecycle report (Sundays at 7:30 AM)
30 7 * * 0 eqmd cd /home/carlos/projects/eqmd && docker compose exec -T eqmd python manage.py lifecycle_report --output-file /tmp/lifecycle_report_$(date +\%Y\%m\%d).csv >> /var/log/eqmd/reports.log 2>&1

# Monthly Tasks - Maintenance

# Monthly log rotation and cleanup (1st of month at 2:00 AM)
0 2 1 * * eqmd cd /home/carlos/projects/eqmd && /home/carlos/projects/eqmd/scripts/lifecycle_monthly_cleanup.sh >> /var/log/eqmd/maintenance.log 2>&1

# Monitoring Tasks

# Health check every 4 hours (check if commands are working)
0 */4 * * * eqmd cd /home/carlos/projects/eqmd && docker compose exec -T eqmd python manage.py check_user_expiration --dry-run --role resident | tail -1 >> /var/log/eqmd/health_check.log 2>&1 || echo "ERROR: Lifecycle health check failed at $(date)" >> /var/log/eqmd/health_check.log
```

### 4. Development/Staging Configuration

For development or staging environments, use less frequent scheduling:

```bash
# Development cronjob (reduced frequency)
sudo nano /etc/cron.d/equipemd-lifecycle-dev
```

```bash
# EquipeMed User Lifecycle Management - Development Environment
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=dev-team@yourorganization.com

# Daily expiration check (9:00 AM only)
0 9 * * * eqmd cd /home/carlos/projects/eqmd && docker compose exec -T eqmd python manage.py check_user_expiration >> /var/log/eqmd/dev_expiration.log 2>&1

# Test notifications (Mondays only at 10:00 AM)
0 10 * * 1 eqmd cd /home/carlos/projects/eqmd && docker compose exec -T eqmd python manage.py send_expiration_notifications --dry-run >> /var/log/eqmd/dev_notifications.log 2>&1

# Weekly reports (Fridays at 5:00 PM)
0 17 * * 5 eqmd cd /home/carlos/projects/eqmd && docker compose exec -T eqmd python manage.py lifecycle_report --output-file /tmp/dev_report_$(date +\%Y\%m\%d).csv >> /var/log/eqmd/dev_reports.log 2>&1
```

### 5. Create Maintenance Scripts

Create the monthly cleanup script:

```bash
sudo nano /app/scripts/lifecycle_monthly_cleanup.sh
```

```bash
#!/bin/bash
# EquipeMed Lifecycle Monthly Maintenance Script

set -e

# Configuration
LOG_DIR="/var/log/eqmd"
RETENTION_DAYS=90
BACKUP_DIR="/app/backups/lifecycle"

echo "Starting lifecycle monthly maintenance - $(date)"

# Archive old logs (keep 90 days)
find $LOG_DIR -name "*.log" -type f -mtime +$RETENTION_DAYS -exec gzip {} \;
find $LOG_DIR -name "*.log.gz" -type f -mtime +365 -delete

# Generate monthly summary report  
cd /home/carlos/projects/eqmd
docker compose exec -T eqmd python manage.py lifecycle_report --output-file /tmp/monthly_summary_$(date +%Y%m).csv

# Database cleanup - remove old renewal requests (keep 2 years)
docker compose exec -T eqmd python manage.py shell -c "
from apps.core.models import AccountRenewalRequest
from datetime import datetime, timedelta

cutoff_date = datetime.now() - timedelta(days=730)
old_requests = AccountRenewalRequest.objects.filter(
    created_at__lt=cutoff_date,
    status__in=['approved', 'denied']
)
count = old_requests.count()
old_requests.delete()
print(f'Cleaned up {count} old renewal requests')
"

# Check system health
docker compose exec -T eqmd python manage.py check_user_expiration --dry-run > /tmp/health_check.out 2>&1
if [ $? -eq 0 ]; then
    echo "Health check passed - $(date)"
else
    echo "Health check FAILED - $(date)" 
    cat /tmp/health_check.out
fi

echo "Lifecycle monthly maintenance completed - $(date)"
```

Make the script executable:

```bash
sudo chmod +x /app/scripts/lifecycle_monthly_cleanup.sh
sudo chown www-data:www-data /app/scripts/lifecycle_monthly_cleanup.sh
```

## Testing Cronjob Setup

### 1. Syntax Validation

Validate cronjob syntax before activation:

```bash
# Test cron syntax
crontab -T /etc/cron.d/equipemd-lifecycle

# If command not available, use online validator or manual check
```

### 2. Manual Command Testing

Test each command individually as the www-data user:

```bash
# Test as the cronjob user
sudo -u www-data bash -c "cd /app && uv run python manage.py check_user_expiration --dry-run"
sudo -u www-data bash -c "cd /app && uv run python manage.py send_expiration_notifications --dry-run"
sudo -u www-data bash -c "cd /app && uv run python manage.py cleanup_inactive_users --format table"
sudo -u www-data bash -c "cd /app && uv run python manage.py lifecycle_report --output-file /tmp/test_report.csv"
```

### 3. Test Log Rotation

Test log directory permissions and rotation:

```bash
# Create test logs
sudo -u www-data touch /app/logs/lifecycle/test.log
sudo -u www-data echo "Test log entry" > /app/logs/lifecycle/test.log

# Test compression and cleanup
sudo -u www-data find /app/logs/lifecycle -name "test.log" -exec gzip {} \;
ls -la /app/logs/lifecycle/test.log.gz
```

### 4. Email Notification Testing

Test that cron emails are working:

```bash
# Send test email via cron
echo "cd /app && echo 'Test cron email' | mail -s 'Cronjob Test' admin@yourorganization.com" | sudo crontab -u www-data -

# Remove test after verification
sudo crontab -u www-data -r
```

## Monitoring Cronjob Execution

### 1. Log Monitoring

Monitor cronjob execution through logs:

```bash
# Watch real-time lifecycle logs
tail -f /app/logs/lifecycle/*.log

# Check for errors in logs
grep -i error /app/logs/lifecycle/*.log

# Monitor cron execution
sudo tail -f /var/log/cron
```

### 2. Report Verification

Verify that reports are generated correctly:

```bash
# Check recent reports
ls -la /app/reports/lifecycle/ | head -10

# Verify report content
head -5 /app/reports/lifecycle/lifecycle_report_$(date +%Y%m%d).csv
```

### 3. Status Dashboard

Create a simple status dashboard script:

```bash
sudo nano /app/scripts/lifecycle_status.sh
```

```bash
#!/bin/bash
# EquipeMed Lifecycle Status Dashboard

echo "=== EquipeMed Lifecycle System Status ==="
echo "Generated: $(date)"
echo

# Check last execution times
echo "--- Last Execution Times ---"
echo "Expiration Check: $(ls -t /app/logs/lifecycle/expiration_check.log 2>/dev/null | head -1 | xargs stat -c %y 2>/dev/null || echo 'No logs found')"
echo "Notifications: $(ls -t /app/logs/lifecycle/notifications.log 2>/dev/null | head -1 | xargs stat -c %y 2>/dev/null || echo 'No logs found')"
echo "Reports: $(ls -t /app/logs/lifecycle/reports.log 2>/dev/null | head -1 | xargs stat -c %y 2>/dev/null || echo 'No logs found')"
echo

# Check for recent errors
echo "--- Recent Errors ---"
grep -i error /app/logs/lifecycle/*.log 2>/dev/null | tail -5 || echo "No recent errors found"
echo

# Check report generation
echo "--- Recent Reports ---"
ls -t /app/reports/lifecycle/*.csv 2>/dev/null | head -5 | while read file; do
    echo "$(basename $file): $(stat -c %y "$file")"
done
echo

# System status
echo "--- System Status ---"
cd /app && uv run python manage.py check_user_expiration --dry-run --role resident | grep "Found\|users"
echo

echo "=== End Status Report ==="
```

Run status dashboard:

```bash
sudo chmod +x /app/scripts/lifecycle_status.sh
/app/scripts/lifecycle_status.sh
```

## Troubleshooting

### Common Issues

#### Issue: Cronjobs not executing

**Check cron daemon status:**

```bash
sudo systemctl status cron
sudo systemctl restart cron
```

**Check cron logs:**

```bash
sudo tail -f /var/log/cron | grep lifecycle
```

**Verify file permissions:**

```bash
ls -la /etc/cron.d/equipemd-lifecycle
# Should be owned by root with 644 permissions
```

#### Issue: Commands failing in cron but working manually

**Check environment variables:**

```bash
# Add to cronjob for debugging
* * * * * www-data cd /app && env > /tmp/cron_env.log 2>&1
```

**Check PATH issues:**

```bash
# Use full paths in cronjob
0 6 * * * www-data cd /app && /usr/bin/uv run /usr/bin/python manage.py check_user_expiration
```

#### Issue: Email notifications not sending

**Test email in cron environment:**

```bash
# Test email with same environment as cron
sudo -u www-data bash -c "cd /app && uv run python manage.py shell -c \"
from django.core.mail import send_mail
send_mail('Test', 'Cron test', 'noreply@equipemd.com', ['admin@yourorg.com'])
\""
```

#### Issue: Log files growing too large

**Implement log rotation:**

```bash
sudo nano /etc/logrotate.d/equipemd-lifecycle
```

```
/app/logs/lifecycle/*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    create 644 www-data www-data
    copytruncate
}
```

### Emergency Procedures

#### Disable All Cronjobs Temporarily

```bash
# Disable cronjobs (rename file)
sudo mv /etc/cron.d/equipemd-lifecycle /etc/cron.d/equipemd-lifecycle.disabled

# Re-enable when ready
sudo mv /etc/cron.d/equipemd-lifecycle.disabled /etc/cron.d/equipemd-lifecycle
```

#### Manual Emergency Run

If cronjobs fail, run manually:

```bash
# Emergency expiration check
sudo -u www-data bash -c "cd /app && uv run python manage.py check_user_expiration"

# Emergency notification send  
sudo -u www-data bash -c "cd /app && uv run python manage.py send_expiration_notifications"

# Generate emergency report
sudo -u www-data bash -c "cd /app && uv run python manage.py lifecycle_report --output-file /app/reports/emergency_$(date +%Y%m%d_%H%M).csv"
```

## Performance Considerations

### Resource Usage

Monitor resource usage during cronjob execution:

```bash
# Monitor CPU/memory usage during lifecycle commands
top -u www-data | grep python

# Monitor database connections
uv run python manage.py shell -c "
from django.db import connection
print('Database queries:', len(connection.queries))
"
```

### Optimization Tips

1. **Stagger execution times** - Don't run all commands simultaneously
2. **Use flock** - Prevent overlapping executions with file locks
3. **Monitor log sizes** - Implement proper log rotation
4. **Database indexes** - Ensure lifecycle fields are indexed
5. **Batch processing** - Use queryset chunking for large datasets

### Lock File Management

Use file locks to prevent command overlap:

```bash
# Example with timeout
0 6 * * * www-data cd /app && /usr/bin/timeout 3600 /usr/bin/flock -n /tmp/check_expiration.lock uv run python manage.py check_user_expiration
```

## Security Considerations

### File Permissions

Ensure proper permissions on all lifecycle files:

```bash
# Set correct permissions
sudo chown -R www-data:www-data /app/reports/lifecycle
sudo chmod 755 /app/reports/lifecycle
sudo chmod 644 /app/reports/lifecycle/*.csv

sudo chown -R www-data:www-data /app/logs/lifecycle  
sudo chmod 755 /app/logs/lifecycle
sudo chmod 644 /app/logs/lifecycle/*.log

# Restrict cronjob file access
sudo chmod 644 /etc/cron.d/equipemd-lifecycle
sudo chown root:root /etc/cron.d/equipemd-lifecycle
```

### Sensitive Data

Protect sensitive information in logs:

```bash
# Check logs for sensitive data
grep -r -i "password\|secret\|token" /app/logs/lifecycle/
```

### Email Security

Configure secure email notifications:

```python
# In settings.py - use TLS for email
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'noreply@yourorganization.com'
EMAIL_HOST_PASSWORD = 'secure_password_from_env'
```

## Best Practices

1. **Test thoroughly** - Test all cronjobs in staging first
2. **Monitor regularly** - Check logs and reports weekly
3. **Document changes** - Keep this documentation updated
4. **Version control** - Store cronjob configs in version control
5. **Backup strategy** - Backup cronjob configurations and reports
6. **Alert mechanisms** - Set up alerts for cronjob failures
7. **Gradual rollout** - Enable cronjobs one at a time initially

## Related Documentation

- [User Lifecycle Management](user-lifecycle-management.md) - Main system overview
- [Admin Setup Guide](user-lifecycle-admin-setup.md) - Initial configuration
- [Management Commands](user-lifecycle-commands.md) - Command reference

## Support

For cronjob issues:

1. Check cronjob logs: `/app/logs/lifecycle/`
2. Verify cron daemon: `sudo systemctl status cron`
3. Test commands manually as www-data user
4. Review file permissions and ownership
5. Check email configuration if notifications fail
