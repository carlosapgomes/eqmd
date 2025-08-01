# Phase 5: Email Alerts Implementation Plan

## Executive Summary

**Objective**: Implement automated email alerts for critical security events to ensure immediate notification of suspicious activities and potential database abuse.

**Timeline**: 1-2 days  
**Priority**: MEDIUM (Proactive notification)  
**Risk Level**: LOW (Non-breaking notification system)

## Problem Statement

Even with comprehensive monitoring (Phase 4), administrators need:

- **Immediate notification** of critical security events
- **24/7 monitoring** without constant dashboard watching
- **Multiple notification channels** for redundancy
- **Escalation procedures** for unacknowledged alerts
- **Batch summaries** to avoid alert fatigue

Based on your database poisoning experience, email alerts provide:
- **Immediate awareness** of malicious activity
- **Off-hours notification** when attacks often occur
- **Multiple recipient support** for incident response teams
- **Audit trail** of notifications sent

## Solution: Comprehensive Email Alert System

Multi-layered email notification system with:
- Real-time critical alerts
- Daily/weekly summary reports
- Escalation procedures
- Alert deduplication
- Rich HTML formatting with actionable links

## Implementation Plan

### Step 1: Email Alert Infrastructure

#### 1.1: Email Alert Models

```python
# apps/core/models/email_alerts.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.core.models.monitoring import SecurityAlert

User = get_user_model()

class EmailAlertRule(models.Model):
    """Define rules for when to send email alerts."""
    
    ALERT_TYPES = [
        ('suspicious_activity', 'Suspicious Activity'),
        ('multiple_locations', 'Multiple Geographic Locations'),
        ('bulk_operations', 'Bulk Operations'),
        ('unusual_hours', 'Unusual Access Hours'),
        ('failed_permissions', 'Failed Permission Attempts'),
        ('rapid_changes', 'Rapid Data Changes'),
        ('deletion_attempts', 'Deletion Attempts'),
        ('all', 'All Alert Types'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    
    # Alert criteria
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    min_severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    
    # Notification settings
    immediate_notification = models.BooleanField(default=True)
    batch_notification = models.BooleanField(default=False)
    
    # Recipients
    recipients = models.ManyToManyField(User, related_name='alert_rules')
    additional_emails = models.TextField(
        blank=True,
        help_text="Additional email addresses (one per line)"
    )
    
    # Rate limiting
    max_alerts_per_hour = models.PositiveIntegerField(default=10)
    cooldown_minutes = models.PositiveIntegerField(default=60)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_email_alert_rule'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"
    
    def get_all_recipients(self):
        """Get all email addresses for this rule."""
        emails = list(self.recipients.values_list('email', flat=True))
        
        if self.additional_emails:
            additional = [email.strip() for email in self.additional_emails.split('\n') if email.strip()]
            emails.extend(additional)
        
        return emails
    
    def should_send_alert(self, alert):
        """Check if this rule should trigger for the given alert."""
        if not self.is_active:
            return False
        
        # Check alert type
        if self.alert_type != 'all' and self.alert_type != alert.alert_type:
            return False
        
        # Check severity
        severity_order = ['low', 'medium', 'high', 'critical']
        min_severity_idx = severity_order.index(self.min_severity)
        alert_severity_idx = severity_order.index(alert.severity)
        
        if alert_severity_idx < min_severity_idx:
            return False
        
        # Check rate limiting
        if self._is_rate_limited():
            return False
        
        return True
    
    def _is_rate_limited(self):
        """Check if this rule is currently rate limited."""
        from apps.core.models.email_alerts import EmailAlertSent
        
        cutoff_time = timezone.now() - timezone.timedelta(hours=1)
        recent_alerts = EmailAlertSent.objects.filter(
            rule=self,
            sent_at__gte=cutoff_time
        ).count()
        
        return recent_alerts >= self.max_alerts_per_hour

class EmailAlertSent(models.Model):
    """Track sent email alerts for rate limiting and auditing."""
    
    rule = models.ForeignKey(EmailAlertRule, on_delete=models.CASCADE)
    alert = models.ForeignKey(SecurityAlert, on_delete=models.CASCADE)
    
    recipients = models.TextField()  # JSON list of email addresses
    subject = models.CharField(max_length=200)
    
    # Sending status
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Email tracking
    email_message_id = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_email_alert_sent'
        indexes = [
            models.Index(fields=['rule', 'sent_at']),
            models.Index(fields=['alert', 'is_sent']),
        ]
    
    def __str__(self):
        return f"Alert to {len(self.get_recipients())} recipients at {self.sent_at}"
    
    def get_recipients(self):
        """Get list of recipient email addresses."""
        import json
        try:
            return json.loads(self.recipients)
        except (json.JSONDecodeError, TypeError):
            return []

class EmailAlertTemplate(models.Model):
    """Email templates for different alert types."""
    
    TEMPLATE_TYPES = [
        ('immediate_alert', 'Immediate Alert'),
        ('daily_summary', 'Daily Summary'),
        ('weekly_summary', 'Weekly Summary'),
        ('escalation', 'Escalation'),
    ]
    
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    
    # Email content
    subject_template = models.CharField(max_length=200)
    html_template = models.TextField()
    text_template = models.TextField()
    
    # Template variables documentation
    available_variables = models.TextField(
        blank=True,
        help_text="Documentation of available template variables"
    )
    
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_email_alert_template'
        unique_together = ['template_type', 'is_default']
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
```

#### 1.2: Email Alert Service

```python
# apps/core/services/email_alerts.py
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
import json
import logging
from typing import List, Dict, Any

from apps.core.models.monitoring import SecurityAlert
from apps.core.models.email_alerts import (
    EmailAlertRule, EmailAlertSent, EmailAlertTemplate
)

logger = logging.getLogger('email_alerts')

class EmailAlertService:
    """Service for sending security alert emails."""
    
    def __init__(self):
        self.from_email = getattr(settings, 'SECURITY_ALERT_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL)
        self.base_url = getattr(settings, 'SITE_BASE_URL', 'http://localhost:8000')
    
    def process_alert(self, alert: SecurityAlert) -> List[EmailAlertSent]:
        """Process a security alert and send appropriate emails."""
        sent_alerts = []
        
        # Find applicable rules
        applicable_rules = EmailAlertRule.objects.filter(
            is_active=True
        ).prefetch_related('recipients')
        
        for rule in applicable_rules:
            if rule.should_send_alert(alert):
                try:
                    sent_alert = self._send_immediate_alert(rule, alert)
                    if sent_alert:
                        sent_alerts.append(sent_alert)
                except Exception as e:
                    logger.error(f"Error sending alert for rule {rule.name}: {e}")
        
        return sent_alerts
    
    def _send_immediate_alert(self, rule: EmailAlertRule, alert: SecurityAlert) -> EmailAlertSent:
        """Send an immediate alert email."""
        
        # Get template
        template = self._get_template('immediate_alert')
        if not template:
            logger.error("No immediate alert template found")
            return None
        
        # Prepare template context
        context = self._build_alert_context(alert)
        
        # Render email content
        subject = Template(template.subject_template).render(Context(context))
        html_content = Template(template.html_template).render(Context(context))
        text_content = Template(template.text_template).render(Context(context))
        
        # Get recipients
        recipients = rule.get_all_recipients()
        if not recipients:
            logger.warning(f"No recipients for rule {rule.name}")
            return None
        
        # Create sent alert record
        sent_alert = EmailAlertSent.objects.create(
            rule=rule,
            alert=alert,
            recipients=json.dumps(recipients),
            subject=subject
        )
        
        try:
            # Send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=recipients
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            # Update sent alert record
            sent_alert.is_sent = True
            sent_alert.sent_at = timezone.now()
            sent_alert.save()
            
            logger.info(f"Sent alert email to {len(recipients)} recipients for alert {alert.id}")
            
        except Exception as e:
            sent_alert.error_message = str(e)
            sent_alert.save()
            logger.error(f"Failed to send alert email: {e}")
            
        return sent_alert
    
    def send_daily_summary(self, date=None) -> List[EmailAlertSent]:
        """Send daily summary emails."""
        if date is None:
            date = timezone.now().date()
        
        # Get alerts from the specified date
        start_time = timezone.datetime.combine(date, timezone.datetime.min.time())
        end_time = start_time + timezone.timedelta(days=1)
        
        alerts = SecurityAlert.objects.filter(
            created_at__gte=start_time,
            created_at__lt=end_time
        ).order_by('-created_at')
        
        if not alerts.exists():
            logger.info(f"No alerts to summarize for {date}")
            return []
        
        # Get template
        template = self._get_template('daily_summary')
        if not template:
            logger.error("No daily summary template found")
            return []
        
        # Build summary context
        context = self._build_summary_context(alerts, 'daily', date)
        
        # Get summary rules (rules with batch_notification=True)
        summary_rules = EmailAlertRule.objects.filter(
            is_active=True,
            batch_notification=True
        ).prefetch_related('recipients')
        
        sent_alerts = []
        
        for rule in summary_rules:
            try:
                sent_alert = self._send_summary_email(rule, template, context, alerts.first())
                if sent_alert:
                    sent_alerts.append(sent_alert)
            except Exception as e:
                logger.error(f"Error sending daily summary for rule {rule.name}: {e}")
        
        return sent_alerts
    
    def send_weekly_summary(self, end_date=None) -> List[EmailAlertSent]:
        """Send weekly summary emails."""
        if end_date is None:
            end_date = timezone.now().date()
        
        start_date = end_date - timezone.timedelta(days=7)
        start_time = timezone.datetime.combine(start_date, timezone.datetime.min.time())
        end_time = timezone.datetime.combine(end_date, timezone.datetime.max.time())
        
        alerts = SecurityAlert.objects.filter(
            created_at__gte=start_time,
            created_at__lte=end_time
        ).order_by('-created_at')
        
        if not alerts.exists():
            logger.info(f"No alerts to summarize for week ending {end_date}")
            return []
        
        template = self._get_template('weekly_summary')
        if not template:
            logger.error("No weekly summary template found")
            return []
        
        context = self._build_summary_context(alerts, 'weekly', end_date)
        
        summary_rules = EmailAlertRule.objects.filter(
            is_active=True,
            batch_notification=True
        ).prefetch_related('recipients')
        
        sent_alerts = []
        
        for rule in summary_rules:
            try:
                sent_alert = self._send_summary_email(rule, template, context, alerts.first())
                if sent_alert:
                    sent_alerts.append(sent_alert)
            except Exception as e:
                logger.error(f"Error sending weekly summary for rule {rule.name}: {e}")
        
        return sent_alerts
    
    def _send_summary_email(self, rule: EmailAlertRule, template: EmailAlertTemplate, 
                           context: Dict[str, Any], reference_alert: SecurityAlert) -> EmailAlertSent:
        """Send a summary email."""
        
        # Render email content
        subject = Template(template.subject_template).render(Context(context))
        html_content = Template(template.html_template).render(Context(context))
        text_content = Template(template.text_template).render(Context(context))
        
        # Get recipients
        recipients = rule.get_all_recipients()
        if not recipients:
            return None
        
        # Create sent alert record (using reference alert)
        sent_alert = EmailAlertSent.objects.create(
            rule=rule,
            alert=reference_alert,
            recipients=json.dumps(recipients),
            subject=subject
        )
        
        try:
            # Send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=recipients
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            # Update sent alert record
            sent_alert.is_sent = True
            sent_alert.sent_at = timezone.now()
            sent_alert.save()
            
            logger.info(f"Sent summary email to {len(recipients)} recipients")
            
        except Exception as e:
            sent_alert.error_message = str(e)
            sent_alert.save()
            logger.error(f"Failed to send summary email: {e}")
            
        return sent_alert
    
    def _get_template(self, template_type: str) -> EmailAlertTemplate:
        """Get email template by type."""
        return EmailAlertTemplate.objects.filter(
            template_type=template_type,
            is_active=True
        ).order_by('-is_default').first()
    
    def _build_alert_context(self, alert: SecurityAlert) -> Dict[str, Any]:
        """Build template context for a single alert."""
        
        dashboard_url = f"{self.base_url}{reverse('core:security_dashboard')}"
        
        return {
            'alert': alert,
            'alert_type_display': alert.get_alert_type_display(),
            'severity_display': alert.get_severity_display(),
            'user_name': alert.user.get_full_name() if alert.user else 'Unknown',
            'user_username': alert.user.username if alert.user else 'Unknown',
            'formatted_datetime': alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'dashboard_url': dashboard_url,
            'alert_url': f"{dashboard_url}#alert-{alert.id}",
            'ip_address': alert.ip_address or 'Unknown',
            'metadata': alert.metadata,
            'site_name': getattr(settings, 'SITE_NAME', 'EquipeMed'),
        }
    
    def _build_summary_context(self, alerts, period: str, date) -> Dict[str, Any]:
        """Build template context for summary emails."""
        
        # Group alerts by type and severity
        alert_stats = {
            'total': alerts.count(),
            'by_type': {},
            'by_severity': {},
            'by_user': {},
        }
        
        for alert in alerts:
            # By type
            alert_type = alert.get_alert_type_display()
            alert_stats['by_type'][alert_type] = alert_stats['by_type'].get(alert_type, 0) + 1
            
            # By severity
            severity = alert.get_severity_display()
            alert_stats['by_severity'][severity] = alert_stats['by_severity'].get(severity, 0) + 1
            
            # By user
            if alert.user:
                username = alert.user.username
                alert_stats['by_user'][username] = alert_stats['by_user'].get(username, 0) + 1
        
        dashboard_url = f"{self.base_url}{reverse('core:security_dashboard')}"
        
        return {
            'period': period,
            'date': date,
            'alert_stats': alert_stats,
            'recent_alerts': alerts[:10],  # Top 10 most recent
            'dashboard_url': dashboard_url,
            'site_name': getattr(settings, 'SITE_NAME', 'EquipeMed'),
        }
```

### Step 2: Default Email Templates

#### 2.1: Immediate Alert Template

```python
# apps/core/fixtures/email_templates.py
DEFAULT_IMMEDIATE_ALERT_TEMPLATE = {
    'name': 'Default Immediate Alert',
    'template_type': 'immediate_alert',
    'subject_template': '🚨 {{ site_name }} Security Alert: {{ alert_type_display }}',
    'html_template': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Security Alert</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }
        .alert-container { max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 8px; }
        .alert-header { background: #dc3545; color: white; padding: 15px; border-radius: 8px 8px 0 0; margin: -20px -20px 20px -20px; }
        .alert-title { margin: 0; font-size: 18px; }
        .alert-severity { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; text-transform: uppercase; }
        .severity-critical { background: #dc3545; color: white; }
        .severity-high { background: #fd7e14; color: white; }
        .severity-medium { background: #ffc107; color: black; }
        .severity-low { background: #28a745; color: white; }
        .alert-details { margin: 20px 0; }
        .detail-row { margin: 10px 0; }
        .detail-label { font-weight: bold; display: inline-block; width: 120px; }
        .btn { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 10px 5px 0 0; }
        .btn:hover { background: #0056b3; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="alert-container">
        <div class="alert-header">
            <h1 class="alert-title">🚨 Security Alert</h1>
        </div>
        
        <div class="alert-details">
            <div class="detail-row">
                <span class="detail-label">Alert Type:</span>
                <span>{{ alert_type_display }}</span>
            </div>
            
            <div class="detail-row">
                <span class="detail-label">Severity:</span>
                <span class="alert-severity severity-{{ alert.severity }}">{{ severity_display }}</span>
            </div>
            
            <div class="detail-row">
                <span class="detail-label">Time:</span>
                <span>{{ formatted_datetime }}</span>
            </div>
            
            {% if user_name %}
            <div class="detail-row">
                <span class="detail-label">User:</span>
                <span>{{ user_name }} ({{ user_username }})</span>
            </div>
            {% endif %}
            
            {% if ip_address != 'Unknown' %}
            <div class="detail-row">
                <span class="detail-label">IP Address:</span>
                <span>{{ ip_address }}</span>
            </div>
            {% endif %}
            
            <div class="detail-row">
                <span class="detail-label">Description:</span>
                <span>{{ alert.description }}</span>
            </div>
        </div>
        
        <div style="margin: 30px 0;">
            <a href="{{ dashboard_url }}" class="btn">View Security Dashboard</a>
            {% if alert_url %}
            <a href="{{ alert_url }}" class="btn">View Alert Details</a>
            {% endif %}
        </div>
        
        <div class="footer">
            <p>This is an automated security alert from {{ site_name }}.</p>
            <p>If you believe this alert was sent in error, please contact your system administrator.</p>
        </div>
    </div>
</body>
</html>
    ''',
    'text_template': '''
SECURITY ALERT - {{ site_name }}

Alert Type: {{ alert_type_display }}
Severity: {{ severity_display }}
Time: {{ formatted_datetime }}
{% if user_name %}User: {{ user_name }} ({{ user_username }}){% endif %}
{% if ip_address != 'Unknown' %}IP Address: {{ ip_address }}{% endif %}

Description:
{{ alert.description }}

To view more details, visit the security dashboard:
{{ dashboard_url }}

This is an automated security alert from {{ site_name }}.
    ''',
    'is_default': True,
    'is_active': True,
    'available_variables': '''
Available template variables:
- alert: The SecurityAlert object
- alert_type_display: Human-readable alert type
- severity_display: Human-readable severity level
- user_name: Full name of the user (if available)
- user_username: Username (if available)
- formatted_datetime: Formatted alert datetime
- dashboard_url: URL to security dashboard
- alert_url: URL to specific alert (if available)
- ip_address: IP address from alert
- metadata: Additional alert metadata
- site_name: Site name from settings
    '''
}

DEFAULT_DAILY_SUMMARY_TEMPLATE = {
    'name': 'Default Daily Summary',
    'template_type': 'daily_summary',
    'subject_template': '📊 {{ site_name }} Security Summary - {{ date }}',
    'html_template': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Daily Security Summary</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }
        .summary-container { max-width: 700px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 8px; }
        .summary-header { background: #17a2b8; color: white; padding: 15px; border-radius: 8px 8px 0 0; margin: -20px -20px 20px -20px; }
        .summary-title { margin: 0; font-size: 18px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: white; padding: 15px; border-radius: 6px; text-align: center; border-left: 4px solid #17a2b8; }
        .stat-number { font-size: 24px; font-weight: bold; color: #17a2b8; }
        .stat-label { font-size: 12px; color: #666; text-transform: uppercase; }
        .alert-list { margin: 20px 0; }
        .alert-item { background: white; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 4px solid #dc3545; }
        .alert-meta { font-size: 12px; color: #666; }
        .btn { display: inline-block; padding: 10px 20px; background: #17a2b8; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="summary-container">
        <div class="summary-header">
            <h1 class="summary-title">📊 Daily Security Summary - {{ date }}</h1>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ alert_stats.total }}</div>
                <div class="stat-label">Total Alerts</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-number">{{ alert_stats.by_severity.Critical|default:0 }}</div>
                <div class="stat-label">Critical</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-number">{{ alert_stats.by_severity.High|default:0 }}</div>
                <div class="stat-label">High Severity</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-number">{{ alert_stats.by_user|length }}</div>
                <div class="stat-label">Users Involved</div>
            </div>
        </div>
        
        {% if recent_alerts %}
        <div class="alert-list">
            <h3>Recent Alerts</h3>
            {% for alert in recent_alerts %}
            <div class="alert-item">
                <strong>{{ alert.get_alert_type_display }}</strong> - {{ alert.title }}
                <div class="alert-meta">
                    {{ alert.created_at|date:"H:i" }} | 
                    Severity: {{ alert.get_severity_display }} |
                    {% if alert.user %}User: {{ alert.user.username }}{% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div style="margin: 30px 0;">
            <a href="{{ dashboard_url }}" class="btn">View Full Security Dashboard</a>
        </div>
        
        <div class="footer">
            <p>This is an automated daily security summary from {{ site_name }}.</p>
        </div>
    </div>
</body>
</html>
    ''',
    'text_template': '''
DAILY SECURITY SUMMARY - {{ site_name }}
Date: {{ date }}

STATISTICS:
- Total Alerts: {{ alert_stats.total }}
- Critical: {{ alert_stats.by_severity.Critical|default:0 }}
- High Severity: {{ alert_stats.by_severity.High|default:0 }}
- Users Involved: {{ alert_stats.by_user|length }}

RECENT ALERTS:
{% for alert in recent_alerts %}
- {{ alert.get_alert_type_display }}: {{ alert.title }}
  Time: {{ alert.created_at|date:"H:i" }} | Severity: {{ alert.get_severity_display }}{% if alert.user %} | User: {{ alert.user.username }}{% endif %}

{% endfor %}

View the full security dashboard: {{ dashboard_url }}

This is an automated daily security summary from {{ site_name }}.
    ''',
    'is_default': True,
    'is_active': True,
}
```

### Step 3: Signal Integration

#### 3.1: Auto-send Email Alerts

```python
# apps/core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models.monitoring import SecurityAlert
from apps.core.services.email_alerts import EmailAlertService
import logging

logger = logging.getLogger('email_alerts')

@receiver(post_save, sender=SecurityAlert)
def send_email_alert(sender, instance, created, **kwargs):
    """Automatically send email alerts when security alerts are created."""
    
    if not created:
        return  # Only send for new alerts
    
    try:
        email_service = EmailAlertService()
        sent_alerts = email_service.process_alert(instance)
        
        logger.info(f"Processed alert {instance.id}, sent {len(sent_alerts)} email notifications")
        
    except Exception as e:
        logger.error(f"Error processing email alert for security alert {instance.id}: {e}")
```

### Step 4: Management Commands

#### 4.1: Send Summary Emails

```python
# apps/core/management/commands/send_summary_emails.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.services.email_alerts import EmailAlertService
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'Send security alert summary emails'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['daily', 'weekly'],
            default='daily',
            help='Type of summary to send'
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Date for summary (YYYY-MM-DD), defaults to today/last week'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending'
        )
    
    def handle(self, *args, **options):
        email_service = EmailAlertService()
        
        if options['date']:
            target_date = timezone.datetime.strptime(options['date'], '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()
            if options['type'] == 'weekly':
                target_date = target_date - timedelta(days=target_date.weekday())  # Start of week
        
        if options['dry_run']:
            self.stdout.write(f"DRY RUN: Would send {options['type']} summary for {target_date}")
            return
        
        if options['type'] == 'daily':
            sent_alerts = email_service.send_daily_summary(target_date)
            self.stdout.write(
                self.style.SUCCESS(f"Sent daily summary emails: {len(sent_alerts)} notifications")
            )
        
        elif options['type'] == 'weekly':
            sent_alerts = email_service.send_weekly_summary(target_date)
            self.stdout.write(
                self.style.SUCCESS(f"Sent weekly summary emails: {len(sent_alerts)} notifications")
            )
```

#### 4.2: Test Email Alerts

```python
# apps/core/management/commands/test_email_alerts.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.models.monitoring import SecurityAlert
from apps.core.services.email_alerts import EmailAlertService

User = get_user_model()

class Command(BaseCommand):
    help = 'Test email alert system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='Email address to send test to'
        )
    
    def handle(self, *args, **options):
        # Create a test alert
        test_user = User.objects.filter(is_superuser=True).first()
        
        test_alert = SecurityAlert.objects.create(
            alert_type='bulk_operations',
            severity='high',
            title='Test Alert - Email System Verification',
            description='This is a test alert to verify the email notification system is working correctly.',
            user=test_user,
            ip_address='192.168.1.100',
            metadata={
                'test': True,
                'operation_count': 25,
                'time_period': '1h'
            }
        )
        
        # Send test email
        email_service = EmailAlertService()
        
        # Temporarily create a test rule
        from apps.core.models.email_alerts import EmailAlertRule
        test_rule = EmailAlertRule(
            name='Test Rule',
            alert_type='all',
            min_severity='low',
            additional_emails=options['email']
        )
        
        # Build context and send
        context = email_service._build_alert_context(test_alert)
        template = email_service._get_template('immediate_alert')
        
        if template:
            from django.core.mail import EmailMultiAlternatives
            from django.template import Template, Context
            
            subject = Template(template.subject_template).render(Context(context))
            html_content = Template(template.html_template).render(Context(context))
            text_content = Template(template.text_template).render(Context(context))
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=email_service.from_email,
                to=[options['email']]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            self.stdout.write(
                self.style.SUCCESS(f"Test email sent to {options['email']}")
            )
        else:
            self.stdout.write(
                self.style.ERROR("No email template found")
            )
        
        # Clean up test alert
        test_alert.delete()
```

### Step 5: Cron Job Configuration

#### 5.1: Automated Email Schedules

```bash
# Add to crontab for automated email summaries

# Send daily summary every morning at 8 AM
0 8 * * * cd /path/to/eqmd && uv run python manage.py send_summary_emails --type=daily

# Send weekly summary every Monday at 9 AM
0 9 * * 1 cd /path/to/eqmd && uv run python manage.py send_summary_emails --type=weekly

# Test email system monthly (first day of month at 10 AM)
0 10 1 * * cd /path/to/eqmd && uv run python manage.py test_email_alerts --email=admin@yourhospital.com
```

### Step 6: Admin Interface

#### 6.1: Email Alert Admin

```python
# apps/core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from apps.core.models.email_alerts import (
    EmailAlertRule, EmailAlertSent, EmailAlertTemplate
)

@admin.register(EmailAlertRule)
class EmailAlertRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'alert_type', 'min_severity', 'is_active',
        'immediate_notification', 'batch_notification', 'recipient_count'
    ]
    list_filter = ['is_active', 'alert_type', 'min_severity', 'immediate_notification']
    search_fields = ['name', 'description']
    filter_horizontal = ['recipients']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'is_active']
        }),
        ('Alert Criteria', {
            'fields': ['alert_type', 'min_severity']
        }),
        ('Notification Settings', {
            'fields': ['immediate_notification', 'batch_notification']
        }),
        ('Recipients', {
            'fields': ['recipients', 'additional_emails']
        }),
        ('Rate Limiting', {
            'fields': ['max_alerts_per_hour', 'cooldown_minutes']
        }),
    ]
    
    def recipient_count(self, obj):
        return len(obj.get_all_recipients())
    recipient_count.short_description = 'Recipients'

@admin.register(EmailAlertSent)
class EmailAlertSentAdmin(admin.ModelAdmin):
    list_display = [
        'alert', 'rule', 'recipient_count', 'is_sent', 
        'sent_at', 'created_at'
    ]
    list_filter = ['is_sent', 'sent_at', 'rule']
    search_fields = ['subject', 'recipients']
    readonly_fields = ['alert', 'rule', 'recipients', 'subject', 'created_at']
    
    def recipient_count(self, obj):
        return len(obj.get_recipients())
    recipient_count.short_description = 'Recipients'

@admin.register(EmailAlertTemplate)
class EmailAlertTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'is_default', 'is_active']
    list_filter = ['template_type', 'is_default', 'is_active']
    search_fields = ['name']
    
    fieldsets = [
        ('Template Information', {
            'fields': ['name', 'template_type', 'is_default', 'is_active']
        }),
        ('Email Content', {
            'fields': ['subject_template', 'html_template', 'text_template']
        }),
        ('Documentation', {
            'fields': ['available_variables'],
            'classes': ['collapse']
        }),
    ]
```

## Implementation Checklist

### Development Phase
- [ ] Create email alert models (EmailAlertRule, EmailAlertSent, EmailAlertTemplate)
- [ ] Implement EmailAlertService with template rendering
- [ ] Create default email templates (immediate, daily, weekly)
- [ ] Add signal handlers for automatic email sending
- [ ] Create management commands for summaries and testing
- [ ] Build admin interfaces for email configuration
- [ ] Write comprehensive tests

### Configuration Phase
- [ ] Configure Django email settings
- [ ] Set up default alert rules
- [ ] Create email templates in database
- [ ] Configure recipient lists
- [ ] Set up rate limiting parameters
- [ ] Configure summary schedules

### Testing Phase
- [ ] Test immediate alert sending
- [ ] Test daily/weekly summaries
- [ ] Test rate limiting functionality
- [ ] Test template rendering
- [ ] Test recipient management
- [ ] Verify email delivery
- [ ] Test escalation procedures

### Deployment Phase
- [ ] Deploy email system to staging
- [ ] Verify email configuration in staging
- [ ] Set up production cron jobs
- [ ] Configure SMTP/email service
- [ ] Train administrators on email management
- [ ] Deploy to production
- [ ] Monitor email delivery rates

## Expected Benefits

### Immediate Notification
- **Real-time alerts** for critical security events
- **24/7 monitoring** without manual oversight
- **Multiple recipients** for redundancy
- **Rich formatting** with actionable links

### Reduced Alert Fatigue
- **Rate limiting** prevents email flooding
- **Batch summaries** for non-critical alerts
- **Severity filtering** ensures important alerts get attention
- **Template customization** for relevant information

### Incident Response
- **Immediate awareness** of security issues
- **Historical tracking** of all notifications sent
- **Escalation support** through multiple recipient rules
- **Audit trail** of alert communications

## Success Metrics

- [ ] Critical alerts sent within 60 seconds of detection
- [ ] Email delivery rate > 95%
- [ ] False positive rate < 10%
- [ ] Admin response time to critical alerts < 15 minutes
- [ ] Zero missed critical security events
- [ ] Summary emails provide useful security insights

This email alert system provides the immediate notification capabilities needed to detect and respond quickly to the type of database abuse you experienced, ensuring administrators are alerted even when not actively monitoring the system.