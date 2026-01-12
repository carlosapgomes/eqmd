# Phase 11 – Audit Logging

## Goal

Implement comprehensive audit logging for all delegation-related actions, ensuring full traceability for legal and clinical compliance.

## Prerequisites

- Phase 10 completed (Document Promotion)
- All existing tests passing

## Tasks

### Task 11.1: Create Centralized Audit Logger

Create `apps/botauth/audit.py`:

```python
"""
Centralized audit logging for bot delegation system.
"""

import logging
import json
from django.utils import timezone
from django.db import models
from django.conf import settings

logger = logging.getLogger('security.audit')


class AuditEventType:
    """Audit event type constants."""
    
    # Delegation events
    DELEGATION_REQUESTED = 'delegation.requested'
    DELEGATION_GRANTED = 'delegation.granted'
    DELEGATION_DENIED = 'delegation.denied'
    
    # Token events
    TOKEN_ISSUED = 'token.issued'
    TOKEN_EXPIRED = 'token.expired'
    TOKEN_USED = 'token.used'
    
    # Bot action events
    BOT_READ_PATIENT = 'bot.read.patient'
    BOT_CREATE_DRAFT = 'bot.create.draft'
    BOT_GENERATE_SUMMARY = 'bot.generate.summary'
    
    # Draft lifecycle events
    DRAFT_CREATED = 'draft.created'
    DRAFT_PROMOTED = 'draft.promoted'
    DRAFT_REJECTED = 'draft.rejected'
    DRAFT_EXPIRED = 'draft.expired'
    
    # Matrix binding events
    BINDING_CREATED = 'binding.created'
    BINDING_VERIFIED = 'binding.verified'
    BINDING_REVOKED = 'binding.revoked'
    
    # Bot management events
    BOT_CREATED = 'bot.created'
    BOT_SUSPENDED = 'bot.suspended'
    BOT_REACTIVATED = 'bot.reactivated'
    
    # Kill switch events
    KILLSWITCH_ACTIVATED = 'killswitch.activated'
    KILLSWITCH_DEACTIVATED = 'killswitch.deactivated'


class BotAuditLog(models.Model):
    """
    Immutable audit log for all bot delegation events.
    
    This model provides a complete audit trail for compliance with
    medical record-keeping requirements.
    """
    
    id = models.BigAutoField(primary_key=True)
    
    # Event identification
    event_type = models.CharField(max_length=50, db_index=True)
    event_id = models.UUIDField(default=None, null=True)  # For correlation
    
    # Timestamp
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Actor identification
    user_id = models.IntegerField(null=True, db_index=True)
    user_email = models.EmailField(blank=True)
    bot_client_id = models.CharField(max_length=100, blank=True, db_index=True)
    bot_name = models.CharField(max_length=100, blank=True)
    
    # Target identification
    patient_id = models.UUIDField(null=True, db_index=True)
    event_object_id = models.UUIDField(null=True)  # Draft/event being acted on
    
    # Request context
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    token_jti = models.CharField(max_length=36, blank=True)
    scopes = models.JSONField(default=list)
    
    # Event details
    details = models.JSONField(default=dict)
    
    # Result
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Bot Audit Log'
        verbose_name_plural = 'Bot Audit Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', '-timestamp']),
            models.Index(fields=['user_id', '-timestamp']),
            models.Index(fields=['bot_client_id', '-timestamp']),
            models.Index(fields=['patient_id', '-timestamp']),
        ]
        # Make table append-only at database level if supported
        managed = True
    
    def __str__(self):
        return f"{self.event_type} @ {self.timestamp}"
    
    def save(self, *args, **kwargs):
        # Prevent updates to existing records
        if self.pk:
            raise ValueError("Audit logs are immutable")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        raise ValueError("Audit logs cannot be deleted")


class AuditLogger:
    """
    Utility class for creating audit log entries.
    """
    
    @classmethod
    def log(cls, event_type, request=None, user=None, bot=None, patient=None,
            event_object=None, details=None, success=True, error=None):
        """
        Create an audit log entry.
        
        Args:
            event_type: AuditEventType constant
            request: HTTP request (optional, for context)
            user: User involved (optional)
            bot: BotClientProfile (optional)
            patient: Patient involved (optional)
            event_object: Event/Draft involved (optional)
            details: Additional details dict (optional)
            success: Whether the action succeeded
            error: Error message if failed
        """
        entry = BotAuditLog(
            event_type=event_type,
            success=success,
            error_message=error or '',
            details=details or {}
        )
        
        # Extract request context
        if request:
            entry.ip_address = cls._get_client_ip(request)
            entry.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            
            if hasattr(request, 'delegation_jti'):
                entry.token_jti = request.delegation_jti
            if hasattr(request, 'scopes'):
                entry.scopes = list(request.scopes)
        
        # User context
        if user:
            entry.user_id = user.id
            entry.user_email = user.email
        elif request and hasattr(request, 'user') and request.user.is_authenticated:
            entry.user_id = request.user.id
            entry.user_email = request.user.email
        
        # Bot context
        if bot:
            entry.bot_client_id = bot.client.client_id
            entry.bot_name = bot.display_name
        elif request and hasattr(request, 'actor'):
            entry.bot_client_id = request.actor
            entry.bot_name = getattr(request, 'actor_name', '')
        
        # Target context
        if patient:
            entry.patient_id = patient.id if hasattr(patient, 'id') else patient
        
        if event_object:
            entry.event_object_id = event_object.id if hasattr(event_object, 'id') else event_object
        
        entry.save()
        
        # Also log to standard logger
        log_msg = (
            f"AUDIT: {event_type} | "
            f"user={entry.user_email or 'none'} | "
            f"bot={entry.bot_name or 'none'} | "
            f"success={success}"
        )
        if success:
            logger.info(log_msg)
        else:
            logger.warning(f"{log_msg} | error={error}")
        
        return entry
    
    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
```

### Task 11.2: Add Audit Logging to All Services

Update `apps/botauth/api_views.py` (DelegatedTokenView):

```python
from .audit import AuditLogger, AuditEventType

# In DelegatedTokenView.post(), add after successful token generation:
AuditLogger.log(
    event_type=AuditEventType.TOKEN_ISSUED,
    request=request,
    user=user,
    bot=bot_profile,
    details={
        'scopes': requested_scopes,
        'expires_in': expires_in
    }
)

# Add for denials:
AuditLogger.log(
    event_type=AuditEventType.DELEGATION_DENIED,
    request=request,
    user=user,
    details={'reason': error_message},
    success=False,
    error=error_message
)
```

Update `apps/botauth/promotion_service.py`:

```python
from .audit import AuditLogger, AuditEventType

# In promote_draft():
AuditLogger.log(
    event_type=AuditEventType.DRAFT_PROMOTED,
    user=approving_user,
    patient=draft.patient,
    event_object=draft,
    details={
        'original_author': original_created_by.email,
        'bot': draft.draft_created_by_bot
    }
)

# In reject_draft():
AuditLogger.log(
    event_type=AuditEventType.DRAFT_REJECTED,
    user=rejecting_user,
    event_object=draft,
    details={'reason': reason}
)
```

### Task 11.3: Create Audit Log Admin

Add to `apps/botauth/admin.py`:

```python
from .audit import BotAuditLog

@admin.register(BotAuditLog)
class BotAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'event_type', 'user_email', 'bot_name', 
        'success', 'ip_address'
    ]
    list_filter = ['event_type', 'success', 'timestamp']
    search_fields = ['user_email', 'bot_name', 'bot_client_id', 'ip_address']
    readonly_fields = [
        'id', 'event_type', 'event_id', 'timestamp',
        'user_id', 'user_email', 'bot_client_id', 'bot_name',
        'patient_id', 'event_object_id',
        'ip_address', 'user_agent', 'token_jti', 'scopes',
        'details', 'success', 'error_message'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
```

### Task 11.4: Create Audit Report Command

Create `apps/botauth/management/commands/audit_report.py`:

```python
"""
Generate audit reports for bot delegation activity.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.botauth.audit import BotAuditLog


class Command(BaseCommand):
    help = 'Generate audit report for bot delegation'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=7,
            help='Number of days to include in report'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        since = timezone.now() - timedelta(days=days)
        
        logs = BotAuditLog.objects.filter(timestamp__gte=since)
        
        self.stdout.write(f"\n=== Bot Delegation Audit Report ===")
        self.stdout.write(f"Period: Last {days} days")
        self.stdout.write(f"Total events: {logs.count()}\n")
        
        # Event type breakdown
        self.stdout.write("Events by type:")
        for event_type in logs.values('event_type').distinct():
            count = logs.filter(event_type=event_type['event_type']).count()
            self.stdout.write(f"  {event_type['event_type']}: {count}")
        
        # Failed events
        failed = logs.filter(success=False)
        self.stdout.write(f"\nFailed events: {failed.count()}")
        
        # Top users
        self.stdout.write("\nTop delegating users:")
        from django.db.models import Count
        top_users = logs.values('user_email').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        for u in top_users:
            self.stdout.write(f"  {u['user_email']}: {u['count']}")
        
        # Top bots
        self.stdout.write("\nTop bots:")
        top_bots = logs.values('bot_name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        for b in top_bots:
            self.stdout.write(f"  {b['bot_name']}: {b['count']}")
```

### Task 11.5: Run Migration

```bash
uv run python manage.py makemigrations botauth
uv run python manage.py migrate botauth
```

## Acceptance Criteria

- [ ] BotAuditLog model stores all delegation events
- [ ] Audit logs are immutable (no updates or deletes)
- [ ] All services log their actions
- [ ] Admin interface shows audit logs (read-only)
- [ ] Audit report command works
- [ ] Logs include all context (user, bot, patient, IP)
- [ ] All tests pass

## Compliance Notes

- Audit logs must be retained per hospital policy (typically 7+ years)
- Consider archiving old logs to separate storage
- Logs should be backed up separately from main database
- Consider log integrity verification (checksums)
