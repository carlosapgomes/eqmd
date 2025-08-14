# LGPD Compliance Monitoring - Scheduled Configuration Guide

This document contains the cron job configuration for automated LGPD compliance monitoring.

## Recommended Cron Jobs

Add the following entries to your system's crontab (`crontab -e`):

```bash
# LGPD Compliance Monitoring Schedule
# -------------------------------------

# Daily compliance metrics calculation (runs at 8:00 AM)
0 8 * * * cd /home/carlos/projects/eqmd && uv run python manage.py run_compliance_monitoring --metrics-only >> /var/log/compliance_monitoring_daily.log 2>&1

# Weekly comprehensive compliance monitoring (runs every Monday at 9:00 AM)
0 9 * * 1 cd /home/carlos/projects/eqmd && uv run python manage.py run_compliance_monitoring >> /var/log/compliance_monitoring_weekly.log 2>&1

# Monthly audit creation (runs on the 1st of each month at 10:00 AM)
0 10 1 * * cd /home/carlos/projects/eqmd && python manage.py manage_audit --create --audit-type routine >> /var/log/audit_creation_monthly.log 2>&1

# Training compliance check (runs every Friday at 11:00 AM)
0 11 * * 5 cd /home/carlos/projects/eqmd && uv run python manage.py run_compliance_monitoring --training-only >> /var/log/training_compliance_weekly.log 2>&1

# Annual compliance review (runs on January 1st at 2:00 PM)
0 14 1 1 * cd /home/carlos/projects/eqmd && python manage.py manage_audit --create --audit-type annual_review >> /var/log/annual_audit_creation.log 2>&1

# Monthly policy expiration check (runs on last day of month at 11:00 PM)
0 23 L * * cd /home/carlos/projects/eqmd && uv run python manage.py run_breach_detection >> /var/log/policy_check_monthly.log 2>&1
```

## Log File Setup

Create the log files and set up log rotation:

```bash
# Create log directory
sudo mkdir -p /var/log/eqmd_compliance
sudo chown $(whoami):$(whoami) /var/log/eqmd_compliance

# Create log files
touch /var/log/eqmd_compliance/compliance_monitoring_daily.log
touch /var/log/eqmd_compliance/compliance_monitoring_weekly.log
touch /var/log/eqmd_compliance/audit_creation_monthly.log
touch /var/log/eqmd_compliance/training_compliance_weekly.log
touch /var/log/eqmd_compliance/annual_audit_creation.log
touch /var/log/eqmd_compliance/policy_check_monthly.log

# Set up log rotation
sudo tee /etc/logrotate.d/eqmd-compliance > /dev/null <<EOL
/var/log/eqmd_compliance/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 640 $(whoami) $(whoami)
    postrotate
        # Send notification if there were errors in the logs
        if grep -i "error\|exception\|failed" /var/log/eqmd_compliance/*.log.1 > /dev/null; then
            echo "LGPD Compliance monitoring errors detected in rotated logs" | mail -s "LGPD Monitoring Alerts" dpo@yourhospital.com.br
        fi
    endscript
}
EOL
```

## Alternative: Using Systemd Timers

If you prefer systemd timers over cron jobs, create the following service files:

### Service Files

Create `/etc/systemd/system/compliance-monitoring.service`:
```ini
[Unit]
Description=LGPD Compliance Monitoring
After=network.target

[Service]
Type=oneshot
User=$(whoami)
WorkingDirectory=/home/carlos/projects/eqmd
ExecStart=/home/carlos/projects/eqmd/.venv/bin/python manage.py run_compliance_monitoring
StandardOutput=file:/var/log/eqmd_compliance/compliance_monitoring.log
StandardError=file:/var/log/eqmd_compliance/compliance_monitoring.log
```

Create `/etc/systemd/system/compliance-metrics.service`:
```ini
[Unit]
Description=LGPD Compliance Metrics
After=network.target

[Service]
Type=oneshot
User=$(whoami)
WorkingDirectory=/home/carlos/projects/eqmd
ExecStart=/home/carlos/projects/eqmd/.venv/bin/python manage.py run_compliance_monitoring --metrics-only
StandardOutput=file:/var/log/eqmd_compliance/compliance_metrics.log
StandardError=file:/var/log/eqmd_compliance/compliance_metrics.log
```

### Timer Files

Create `/etc/systemd/system/compliance-daily.timer`:
```ini
[Unit]
Description=Daily LGPD Compliance Monitoring
Requires=compliance-metrics.service

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Create `/etc/systemd/system/compliance-weekly.timer`:
```ini
[Unit]
Description=Weekly LGPD Compliance Monitoring
Requires=compliance-monitoring.service

[Timer]
OnCalendar=Mon *-*-* 09:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### Enable Timers

```bash
sudo systemctl daemon-reload
sudo systemctl enable compliance-daily.timer
sudo systemctl enable compliance-weekly.timer
sudo systemctl start compliance-daily.timer
sudo systemctl start compliance-weekly.timer
```

## Monitoring and Alerting Setup

### Email Alerts Configuration

Add the following settings to your Django settings:

```python
# EMAIL SETTINGS FOR COMPLIANCE ALERTS
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.yourhospital.com.br'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'noreply@yourhospital.com.br'
EMAIL_HOST_PASSWORD = 'your-password'

# COMPLIANCE EMAIL SETTINGS
COMPLIANCE_ADMIN_EMAILS = ['dpo@yourhospital.com.br', 'it@yourhospital.com.br']
COMPLIANCE_ALERT_THRESHOLD = 75  # Alert when compliance falls below 75%
```

### Health Check Endpoint

Create a simple health check endpoint in your URLs:

```python
# urls.py
from django.http import JsonResponse

def compliance_health_check(request):
    """Simple health check for compliance monitoring"""
    from apps.compliance.models import ComplianceIssue
    
    # Check for critical issues
    critical_issues = ComplianceIssue.objects.filter(
        severity='critical',
        status__in=['open', 'in_progress']
    ).count()
    
    status = 'HEALTHY' if critical_issues == 0 else 'DEGRADED'
    
    return JsonResponse({
        'status': status,
        'timestamp': timezone.now().isoformat(),
        'critical_issues': critical_issues,
        'last_monitored': timezone.now().isoformat()
    })
```

## Emergency Procedures

### Manual Compliance Check

If monitoring fails or critical issues are detected:

```bash
# Run immediate comprehensive monitoring
uv run python manage.py run_compliance_monitoring

# Check for overdue patient requests
uv run python manage.py test_patient_rights --check-overdue

# Run breach detection
uv run python manage.py run_breach_detection --emergency

# Create immediate audit if needed
uv run python manage.py manage_audit --create --audit-type incident_triggered
```

### Restore Procedures

1. **Database Backup**: Ensure daily backups are running
2. **Configuration Snapshot**: Keep backups of compliance settings
3. ** emergency Contacts**: Have DPO and IT emergency contacts available

## Maintenance Schedule

### Daily Monitoring
- Calculate compliance metrics
- Check for overdue items
- Training compliance alerts
- Generate issues for problems

### Weekly Monitoring  
- Full comprehensive check
- Audit planning
- Staff training gaps analysis
- حادثة response readiness

### Monthly Tasks
- Create routine audits
- Review compliance trends  
- Policy effectiveness analysis
- Training completion reports

### Annual Review
- Comprehensive audit
- Policy updates
- Legal compliance review
- System optimization

## Security Considerations

1. **Log Security**: Ensure log files are properly secured and rotated
2. **Access Control**: Limit access to compliance monitoring tools
3. **Data Encryption**: Monitor logs may contain sensitive data
4. **Audit Trails**: Keep audit trails of who accesses monitoring data

## Troubleshooting

### Common Issues

1. **Missing Dependencies**: Ensure all Python packages are installed
2. **Database Connection**: Check database connectivity during off-peak hours  
3. **Email Delivery**: Verify email configuration and server availability
4. **Permissions**: Ensure the service user has proper database and file permissions

### Monitoring Validation

To validate that monitoring is working:

```bash
# Check last run status  
tail -20 /var/log/eqmd_compliance/compliance_monitoring_daily.log

# Verify cron job status
crontab -l | grep compliance

# Check systemd timer status
systemctl list-timers --all | grep compliance
```

---

**Note**: Always test monitoring schedules in a staging environment before implementing in production. Monitor logs closely during the first week of operation.