# Phase 12 – Kill Switches & Revocation

## Goal

Implement emergency controls to disable bot delegation system-wide or per-user, ensuring immediate loss of access when needed.

## Prerequisites

- Phase 11 completed (Audit Logging)
- All existing tests passing

## Tasks

### Task 12.1: Create Global Kill Switch Model

Add to `apps/botauth/models.py`:

```python
class BotDelegationConfig(models.Model):
    """
    Singleton model for global bot delegation configuration.
    """
    
    # Global kill switch
    delegation_enabled = models.BooleanField(
        default=True,
        help_text="Master switch to enable/disable all bot delegation"
    )
    
    disabled_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When delegation was disabled"
    )
    disabled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='disabled_delegation'
    )
    disabled_reason = models.TextField(
        blank=True,
        help_text="Reason for disabling delegation"
    )
    
    # Rate limiting overrides
    global_rate_limit = models.PositiveIntegerField(
        default=1000,
        help_text="Maximum delegations per hour across all bots"
    )
    
    # Maintenance mode
    maintenance_mode = models.BooleanField(
        default=False,
        help_text="If True, delegation returns maintenance message"
    )
    maintenance_message = models.TextField(
        blank=True,
        default="Bot delegation is temporarily unavailable for maintenance."
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Bot Delegation Configuration'
        verbose_name_plural = 'Bot Delegation Configuration'
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        pass  # Prevent deletion
    
    @classmethod
    def get_config(cls):
        """Get or create the singleton config."""
        config, _ = cls.objects.get_or_create(pk=1)
        return config
    
    @classmethod
    def is_delegation_enabled(cls):
        """Quick check if delegation is enabled."""
        config = cls.get_config()
        return config.delegation_enabled and not config.maintenance_mode
```

### Task 12.2: Create Kill Switch Service

Create `apps/botauth/killswitch.py`:

```python
"""
Kill switch service for emergency bot delegation control.
"""

import logging
from django.utils import timezone
from django.core.cache import cache

from .models import BotDelegationConfig
from .audit import AuditLogger, AuditEventType

logger = logging.getLogger('security.killswitch')

CACHE_KEY = 'bot_delegation_enabled'
CACHE_TTL = 30  # 30 seconds - balance between performance and responsiveness


class KillSwitchService:
    """Service for managing bot delegation kill switch."""
    
    @classmethod
    def is_delegation_enabled(cls):
        """
        Check if delegation is enabled.
        Uses cache for performance.
        """
        cached = cache.get(CACHE_KEY)
        if cached is not None:
            return cached
        
        enabled = BotDelegationConfig.is_delegation_enabled()
        cache.set(CACHE_KEY, enabled, CACHE_TTL)
        return enabled
    
    @classmethod
    def get_status(cls):
        """Get full delegation status."""
        config = BotDelegationConfig.get_config()
        return {
            'enabled': config.delegation_enabled,
            'maintenance_mode': config.maintenance_mode,
            'maintenance_message': config.maintenance_message,
            'disabled_at': config.disabled_at,
            'disabled_reason': config.disabled_reason,
        }
    
    @classmethod
    def disable_delegation(cls, user, reason=''):
        """
        Disable all bot delegation (emergency kill switch).
        """
        config = BotDelegationConfig.get_config()
        config.delegation_enabled = False
        config.disabled_at = timezone.now()
        config.disabled_by = user
        config.disabled_reason = reason
        config.save()
        
        # Clear cache immediately
        cache.delete(CACHE_KEY)
        
        # Audit log
        AuditLogger.log(
            event_type=AuditEventType.KILLSWITCH_ACTIVATED,
            user=user,
            details={'reason': reason}
        )
        
        logger.critical(
            f"BOT DELEGATION DISABLED by {user.email}: {reason}"
        )
    
    @classmethod
    def enable_delegation(cls, user):
        """
        Re-enable bot delegation.
        """
        config = BotDelegationConfig.get_config()
        was_disabled = not config.delegation_enabled
        
        config.delegation_enabled = True
        config.maintenance_mode = False
        config.disabled_at = None
        config.disabled_by = None
        config.disabled_reason = ''
        config.save()
        
        # Clear cache
        cache.delete(CACHE_KEY)
        
        if was_disabled:
            # Audit log
            AuditLogger.log(
                event_type=AuditEventType.KILLSWITCH_DEACTIVATED,
                user=user
            )
            
            logger.warning(
                f"Bot delegation RE-ENABLED by {user.email}"
            )
    
    @classmethod
    def enable_maintenance(cls, message=''):
        """
        Enable maintenance mode (soft disable with message).
        """
        config = BotDelegationConfig.get_config()
        config.maintenance_mode = True
        if message:
            config.maintenance_message = message
        config.save()
        
        cache.delete(CACHE_KEY)
        
        logger.info(f"Bot delegation maintenance mode enabled: {message}")
    
    @classmethod
    def disable_maintenance(cls):
        """
        Disable maintenance mode.
        """
        config = BotDelegationConfig.get_config()
        config.maintenance_mode = False
        config.save()
        
        cache.delete(CACHE_KEY)
        
        logger.info("Bot delegation maintenance mode disabled")
```

### Task 12.3: Update Delegation Endpoint to Check Kill Switch

Update `apps/botauth/api_views.py` (DelegatedTokenView):

```python
from .killswitch import KillSwitchService

class DelegatedTokenView(APIView):
    def post(self, request):
        # Check kill switch FIRST
        if not KillSwitchService.is_delegation_enabled():
            status_info = KillSwitchService.get_status()
            
            if status_info['maintenance_mode']:
                return Response(
                    {'error': status_info['maintenance_message']},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            return Response(
                {'error': 'Bot delegation is currently disabled'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # ... rest of the endpoint ...
```

### Task 12.4: Create Admin Interface for Kill Switch

Add to `apps/botauth/admin.py`:

```python
from .models import BotDelegationConfig
from .killswitch import KillSwitchService

@admin.register(BotDelegationConfig)
class BotDelegationConfigAdmin(admin.ModelAdmin):
    list_display = ['delegation_enabled', 'maintenance_mode', 'updated_at']
    readonly_fields = ['disabled_at', 'disabled_by', 'updated_at']
    
    fieldsets = [
        ('Kill Switch', {
            'fields': ['delegation_enabled', 'disabled_at', 'disabled_by', 'disabled_reason'],
            'description': 'Emergency control to disable all bot delegation'
        }),
        ('Maintenance', {
            'fields': ['maintenance_mode', 'maintenance_message']
        }),
        ('Rate Limiting', {
            'fields': ['global_rate_limit']
        }),
    ]
    
    actions = ['emergency_disable', 'enable_delegation']
    
    def emergency_disable(self, request, queryset):
        KillSwitchService.disable_delegation(
            request.user, 
            reason='Admin emergency disable'
        )
        self.message_user(request, 'Bot delegation DISABLED')
    emergency_disable.short_description = '🚨 EMERGENCY: Disable all bot delegation'
    
    def enable_delegation(self, request, queryset):
        KillSwitchService.enable_delegation(request.user)
        self.message_user(request, 'Bot delegation enabled')
    enable_delegation.short_description = '✅ Enable bot delegation'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
```

### Task 12.5: Create Management Commands

Create `apps/botauth/management/commands/delegation_killswitch.py`:

```python
"""
Management command for bot delegation kill switch.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.botauth.killswitch import KillSwitchService

User = get_user_model()


class Command(BaseCommand):
    help = 'Control bot delegation kill switch'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['status', 'disable', 'enable', 'maintenance-on', 'maintenance-off'],
            help='Action to perform'
        )
        parser.add_argument(
            '--reason',
            default='',
            help='Reason for disable action'
        )
        parser.add_argument(
            '--message',
            default='',
            help='Maintenance message'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'status':
            status = KillSwitchService.get_status()
            self.stdout.write(f"\nBot Delegation Status:")
            self.stdout.write(f"  Enabled: {status['enabled']}")
            self.stdout.write(f"  Maintenance: {status['maintenance_mode']}")
            if not status['enabled']:
                self.stdout.write(f"  Disabled at: {status['disabled_at']}")
                self.stdout.write(f"  Reason: {status['disabled_reason']}")
        
        elif action == 'disable':
            # Use system user for CLI operations
            system_user = User.objects.filter(is_superuser=True).first()
            KillSwitchService.disable_delegation(
                system_user,
                reason=options['reason'] or 'CLI disable'
            )
            self.stdout.write(
                self.style.ERROR('🚨 Bot delegation DISABLED')
            )
        
        elif action == 'enable':
            system_user = User.objects.filter(is_superuser=True).first()
            KillSwitchService.enable_delegation(system_user)
            self.stdout.write(
                self.style.SUCCESS('✅ Bot delegation enabled')
            )
        
        elif action == 'maintenance-on':
            KillSwitchService.enable_maintenance(options['message'])
            self.stdout.write('Maintenance mode enabled')
        
        elif action == 'maintenance-off':
            KillSwitchService.disable_maintenance()
            self.stdout.write('Maintenance mode disabled')
```

### Task 12.6: Run Migration

```bash
uv run python manage.py makemigrations botauth
uv run python manage.py migrate botauth
```

## Acceptance Criteria

- [x] Global kill switch disables all delegation
- [x] Kill switch check happens before any delegation
- [x] Maintenance mode returns friendly message
- [x] Cache ensures kill switch check is fast
- [x] Admin can toggle kill switch
- [x] CLI command works for emergency response
- [x] All actions are audit logged
- [x] All tests pass

## Emergency Procedures

### To Immediately Disable All Bot Delegation:

**Option 1: CLI (fastest)**
```bash
cd /path/to/eqmd
uv run python manage.py delegation_killswitch disable --reason "Security incident"
```

**Option 2: Admin Interface**
1. Go to /admin/botauth/botdelegationconfig/
2. Click "Emergency: Disable all bot delegation"

**Option 3: Database (last resort)**
```sql
UPDATE botauth_botdelegationconfig SET delegation_enabled = FALSE;
```

### To Re-enable:
```bash
uv run python manage.py delegation_killswitch enable
```

## Notes

- Kill switch affects NEW token requests only
- Existing tokens remain valid until expiration (max 10 min)
- Consider this acceptable given token short lifetime
- If immediate revocation needed, change DELEGATED_TOKEN_SECRET
