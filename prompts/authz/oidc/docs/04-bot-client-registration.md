# Phase 04 – Bot Client Registration

## Goal

Model bots as OIDC Clients using django-oidc-provider. Each bot is a confidential OAuth2 client that can authenticate using client credentials, but CANNOT obtain tokens for users directly - they must use the delegated token endpoint.

## Prerequisites

- Phase 03 completed (Matrix identity binding)
- All existing tests passing

## Context

Bots are NOT Django users. They are OAuth2 clients that can:
1. Authenticate themselves using client_id + client_secret
2. Request delegated tokens on behalf of users (via custom endpoint)

They CANNOT:
1. Log in as users
2. Obtain tokens via standard OAuth flows (authorization_code, implicit)
3. Access user data without delegation

## Tasks

### Task 4.1: Create Bot Client Model Extension

We'll extend the django-oidc-provider Client model with EQMD-specific fields.

Create `apps/botauth/models.py` (extend existing):

```python
# Add to existing models.py

from oidc_provider.models import Client


class BotClientProfile(models.Model):
    """
    Extension of OIDC Client with EQMD-specific bot configuration.
    
    This model adds:
    - Allowed scopes for this bot
    - Rate limiting configuration
    - Activity tracking
    - Administrative controls
    """
    
    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name='bot_profile',
        verbose_name='OIDC Client'
    )
    
    # Human-readable identification
    display_name = models.CharField(
        max_length=100,
        help_text='Human-readable name for this bot'
    )
    description = models.TextField(
        blank=True,
        help_text='Description of what this bot does'
    )
    
    # Scope restrictions
    allowed_scopes = models.JSONField(
        default=list,
        help_text='List of scopes this bot is allowed to request'
    )
    
    # Rate limiting
    max_delegations_per_hour = models.PositiveIntegerField(
        default=100,
        help_text='Maximum delegated tokens this bot can request per hour'
    )
    max_api_calls_per_minute = models.PositiveIntegerField(
        default=60,
        help_text='Maximum API calls per minute with delegated tokens'
    )
    
    # Administrative controls
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this bot is currently active'
    )
    suspended_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When this bot was suspended'
    )
    suspension_reason = models.TextField(
        blank=True,
        help_text='Reason for suspension'
    )
    
    # Activity tracking
    last_delegation_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Last time this bot requested a delegated token'
    )
    total_delegations = models.PositiveIntegerField(
        default=0,
        help_text='Total number of delegated tokens issued'
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_bots'
    )
    
    class Meta:
        verbose_name = 'Bot Client Profile'
        verbose_name_plural = 'Bot Client Profiles'
    
    def __str__(self):
        status = '🟢' if self.is_active else '🔴'
        return f"{status} {self.display_name} ({self.client.client_id[:8]}...)"
    
    def can_request_scope(self, scope):
        """Check if this bot is allowed to request a specific scope."""
        return scope in self.allowed_scopes
    
    def can_request_scopes(self, scopes):
        """Check if this bot is allowed to request all given scopes."""
        return all(self.can_request_scope(s) for s in scopes)
    
    def is_rate_limited(self):
        """Check if this bot has exceeded rate limits."""
        from django.core.cache import cache
        
        key = f"bot_delegation_count:{self.client.client_id}"
        count = cache.get(key, 0)
        return count >= self.max_delegations_per_hour
    
    def record_delegation(self):
        """Record a delegation request for rate limiting."""
        from django.core.cache import cache
        from django.utils import timezone
        
        # Update rate limit counter
        key = f"bot_delegation_count:{self.client.client_id}"
        count = cache.get(key, 0)
        cache.set(key, count + 1, 3600)  # 1 hour TTL
        
        # Update activity tracking
        self.last_delegation_at = timezone.now()
        self.total_delegations += 1
        self.save(update_fields=['last_delegation_at', 'total_delegations', 'updated_at'])
    
    def suspend(self, reason=''):
        """Suspend this bot."""
        from django.utils import timezone
        self.is_active = False
        self.suspended_at = timezone.now()
        self.suspension_reason = reason
        self.save()
    
    def reactivate(self):
        """Reactivate this bot."""
        self.is_active = True
        self.suspended_at = None
        self.suspension_reason = ''
        self.save()
    
    @classmethod
    def get_by_client_id(cls, client_id):
        """Get bot profile by client_id."""
        try:
            return cls.objects.select_related('client').get(
                client__client_id=client_id
            )
        except cls.DoesNotExist:
            return None


class BotClientAuditLog(models.Model):
    """
    Audit log for bot client operations.
    """
    
    class EventType(models.TextChoices):
        BOT_CREATED = 'created', 'Bot Created'
        BOT_UPDATED = 'updated', 'Bot Updated'
        BOT_SUSPENDED = 'suspended', 'Bot Suspended'
        BOT_REACTIVATED = 'reactivated', 'Bot Reactivated'
        SCOPES_CHANGED = 'scopes_changed', 'Scopes Changed'
        SECRET_ROTATED = 'secret_rotated', 'Secret Rotated'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    bot_profile = models.ForeignKey(
        BotClientProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    
    # Denormalized for when bot is deleted
    client_id = models.CharField(max_length=255)
    bot_name = models.CharField(max_length=100)
    
    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices
    )
    
    event_details = models.JSONField(default=dict)
    
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Bot Client Audit Log'
        verbose_name_plural = 'Bot Client Audit Logs'
        ordering = ['-created_at']
```

### Task 4.2: Create Bot Registration Service

Create `apps/botauth/bot_service.py`:

```python
"""
Service for managing bot clients.
"""

import secrets
import logging
from django.db import transaction
from oidc_provider.models import Client, ResponseType

from .models import BotClientProfile, BotClientAuditLog

logger = logging.getLogger('security.bot_management')


# Default scopes that can be assigned to bots
ALLOWED_BOT_SCOPES = [
    'patient:read',
    'exam:read',
    'dailynote:draft',
    'dischargereport:draft',
    'prescription:draft',
    'summary:generate',
]

# Scopes that must NEVER be assigned to bots
FORBIDDEN_BOT_SCOPES = [
    'patient:write',
    'note:finalize',
    'prescription:sign',
    'discharge:finalize',
    'user:read',
    'user:write',
    'admin:read',
    'admin:write',
]


class BotClientService:
    """Service for managing bot OIDC clients."""
    
    @classmethod
    @transaction.atomic
    def create_bot(cls, display_name, description='', allowed_scopes=None,
                   created_by=None):
        """
        Create a new bot client.
        
        Returns (bot_profile, client_secret) - secret is only shown once!
        """
        if allowed_scopes is None:
            allowed_scopes = []
        
        # Validate scopes
        for scope in allowed_scopes:
            if scope not in ALLOWED_BOT_SCOPES:
                raise ValueError(f"Invalid or forbidden scope: {scope}")
            if scope in FORBIDDEN_BOT_SCOPES:
                raise ValueError(f"Forbidden scope: {scope}")
        
        # Generate client credentials
        client_id = f"bot_{secrets.token_urlsafe(16)}"
        client_secret = secrets.token_urlsafe(32)
        
        # Create OIDC Client
        client = Client.objects.create(
            name=display_name,
            client_id=client_id,
            client_secret=client_secret,
            client_type='confidential',
            # No redirect URIs - bots don't use authorization flows
            redirect_uris='',
            # No response types for standard flows
            jwt_alg='HS256',
            require_consent=False,
            reuse_consent=False,
        )
        
        # Create bot profile
        bot_profile = BotClientProfile.objects.create(
            client=client,
            display_name=display_name,
            description=description,
            allowed_scopes=allowed_scopes,
            created_by=created_by
        )
        
        # Audit log
        cls._log_event(
            bot_profile=bot_profile,
            event_type=BotClientAuditLog.EventType.BOT_CREATED,
            performed_by=created_by,
            details={'allowed_scopes': allowed_scopes}
        )
        
        logger.info(f"Bot created: {display_name} ({client_id})")
        
        # Return profile and secret (secret only shown once!)
        return bot_profile, client_secret
    
    @classmethod
    @transaction.atomic
    def update_scopes(cls, bot_profile, new_scopes, performed_by=None):
        """Update the allowed scopes for a bot."""
        # Validate scopes
        for scope in new_scopes:
            if scope not in ALLOWED_BOT_SCOPES:
                raise ValueError(f"Invalid or forbidden scope: {scope}")
        
        old_scopes = bot_profile.allowed_scopes
        bot_profile.allowed_scopes = new_scopes
        bot_profile.save(update_fields=['allowed_scopes', 'updated_at'])
        
        # Audit log
        cls._log_event(
            bot_profile=bot_profile,
            event_type=BotClientAuditLog.EventType.SCOPES_CHANGED,
            performed_by=performed_by,
            details={'old_scopes': old_scopes, 'new_scopes': new_scopes}
        )
        
        logger.info(f"Bot scopes updated: {bot_profile.display_name}")
    
    @classmethod
    @transaction.atomic
    def rotate_secret(cls, bot_profile, performed_by=None):
        """
        Rotate the client secret for a bot.
        
        Returns the new secret (only shown once!).
        """
        new_secret = secrets.token_urlsafe(32)
        bot_profile.client.client_secret = new_secret
        bot_profile.client.save(update_fields=['client_secret'])
        
        # Audit log
        cls._log_event(
            bot_profile=bot_profile,
            event_type=BotClientAuditLog.EventType.SECRET_ROTATED,
            performed_by=performed_by
        )
        
        logger.info(f"Bot secret rotated: {bot_profile.display_name}")
        
        return new_secret
    
    @classmethod
    @transaction.atomic
    def suspend_bot(cls, bot_profile, reason='', performed_by=None):
        """Suspend a bot."""
        bot_profile.suspend(reason)
        
        # Audit log
        cls._log_event(
            bot_profile=bot_profile,
            event_type=BotClientAuditLog.EventType.BOT_SUSPENDED,
            performed_by=performed_by,
            details={'reason': reason}
        )
        
        logger.warning(f"Bot suspended: {bot_profile.display_name} - {reason}")
    
    @classmethod
    @transaction.atomic
    def reactivate_bot(cls, bot_profile, performed_by=None):
        """Reactivate a suspended bot."""
        bot_profile.reactivate()
        
        # Audit log
        cls._log_event(
            bot_profile=bot_profile,
            event_type=BotClientAuditLog.EventType.BOT_REACTIVATED,
            performed_by=performed_by
        )
        
        logger.info(f"Bot reactivated: {bot_profile.display_name}")
    
    @classmethod
    def validate_client_credentials(cls, client_id, client_secret):
        """
        Validate bot client credentials.
        
        Returns BotClientProfile if valid, None otherwise.
        """
        try:
            client = Client.objects.get(client_id=client_id)
            if client.client_secret != client_secret:
                return None
            
            bot_profile = BotClientProfile.objects.get(client=client)
            if not bot_profile.is_active:
                return None
            
            return bot_profile
        except (Client.DoesNotExist, BotClientProfile.DoesNotExist):
            return None
    
    @classmethod
    def _log_event(cls, bot_profile, event_type, performed_by=None, details=None):
        """Create an audit log entry."""
        BotClientAuditLog.objects.create(
            bot_profile=bot_profile,
            client_id=bot_profile.client.client_id,
            bot_name=bot_profile.display_name,
            event_type=event_type,
            event_details=details or {},
            performed_by=performed_by
        )
```

### Task 4.3: Create Admin Interface for Bots

Extend `apps/botauth/admin.py`:

```python
# Add to existing admin.py

from oidc_provider.models import Client
from .models import BotClientProfile, BotClientAuditLog
from .bot_service import BotClientService, ALLOWED_BOT_SCOPES


class BotClientProfileInline(admin.StackedInline):
    """Inline for BotClientProfile on Client admin."""
    model = BotClientProfile
    can_delete = False
    verbose_name_plural = 'Bot Profile'
    
    readonly_fields = ['created_at', 'updated_at', 'last_delegation_at', 
                       'total_delegations', 'suspended_at']


@admin.register(BotClientProfile)
class BotClientProfileAdmin(admin.ModelAdmin):
    list_display = [
        'display_name', 'client_id_short', 'is_active', 
        'scope_count', 'total_delegations', 'last_delegation_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['display_name', 'client__client_id', 'description']
    readonly_fields = [
        'client', 'created_at', 'updated_at', 'created_by',
        'last_delegation_at', 'total_delegations', 'suspended_at'
    ]
    
    fieldsets = [
        ('Bot Identity', {
            'fields': ['client', 'display_name', 'description']
        }),
        ('Scopes', {
            'fields': ['allowed_scopes'],
            'description': f'Allowed scopes: {", ".join(ALLOWED_BOT_SCOPES)}'
        }),
        ('Rate Limiting', {
            'fields': ['max_delegations_per_hour', 'max_api_calls_per_minute']
        }),
        ('Status', {
            'fields': ['is_active', 'suspended_at', 'suspension_reason']
        }),
        ('Activity', {
            'fields': ['last_delegation_at', 'total_delegations'],
            'classes': ['collapse']
        }),
        ('Audit', {
            'fields': ['created_at', 'updated_at', 'created_by'],
            'classes': ['collapse']
        }),
    ]
    
    actions = ['suspend_bots', 'reactivate_bots']
    
    def client_id_short(self, obj):
        return obj.client.client_id[:12] + '...'
    client_id_short.short_description = 'Client ID'
    
    def scope_count(self, obj):
        return len(obj.allowed_scopes)
    scope_count.short_description = 'Scopes'
    
    def suspend_bots(self, request, queryset):
        for bot in queryset:
            BotClientService.suspend_bot(
                bot, 
                reason='Admin bulk suspension',
                performed_by=request.user
            )
        self.message_user(request, f'{queryset.count()} bot(s) suspended.')
    suspend_bots.short_description = 'Suspend selected bots'
    
    def reactivate_bots(self, request, queryset):
        for bot in queryset:
            BotClientService.reactivate_bot(bot, performed_by=request.user)
        self.message_user(request, f'{queryset.count()} bot(s) reactivated.')
    reactivate_bots.short_description = 'Reactivate selected bots'


@admin.register(BotClientAuditLog)
class BotClientAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'event_type', 'bot_name', 'performed_by', 'created_at'
    ]
    list_filter = ['event_type', 'created_at']
    search_fields = ['bot_name', 'client_id']
    readonly_fields = [
        'id', 'bot_profile', 'client_id', 'bot_name', 'event_type',
        'event_details', 'performed_by', 'created_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
```

### Task 4.4: Create Management Command for Bot Registration

Create `apps/botauth/management/__init__.py` and `apps/botauth/management/commands/__init__.py` (empty).

Create `apps/botauth/management/commands/create_bot.py`:

```python
"""
Management command to create a new bot client.
"""

from django.core.management.base import BaseCommand, CommandError
from apps.botauth.bot_service import BotClientService, ALLOWED_BOT_SCOPES


class Command(BaseCommand):
    help = 'Create a new bot client for OIDC delegation'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'name',
            help='Display name for the bot'
        )
        parser.add_argument(
            '--description',
            default='',
            help='Description of the bot'
        )
        parser.add_argument(
            '--scopes',
            nargs='+',
            default=[],
            help=f'Allowed scopes (choose from: {", ".join(ALLOWED_BOT_SCOPES)})'
        )
    
    def handle(self, *args, **options):
        name = options['name']
        description = options['description']
        scopes = options['scopes']
        
        # Validate scopes
        for scope in scopes:
            if scope not in ALLOWED_BOT_SCOPES:
                raise CommandError(
                    f"Invalid scope: {scope}\n"
                    f"Allowed scopes: {', '.join(ALLOWED_BOT_SCOPES)}"
                )
        
        try:
            bot_profile, client_secret = BotClientService.create_bot(
                display_name=name,
                description=description,
                allowed_scopes=scopes
            )
            
            self.stdout.write(self.style.SUCCESS(f'\nBot created successfully!\n'))
            self.stdout.write(f'Name: {bot_profile.display_name}')
            self.stdout.write(f'Client ID: {bot_profile.client.client_id}')
            self.stdout.write(
                self.style.WARNING(f'Client Secret: {client_secret}')
            )
            self.stdout.write(f'Allowed Scopes: {", ".join(scopes) or "(none)"}')
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  Save the client secret now! It cannot be retrieved later.'
                )
            )
            
        except ValueError as e:
            raise CommandError(str(e))
```

Create `apps/botauth/management/commands/list_bots.py`:

```python
"""
Management command to list all bot clients.
"""

from django.core.management.base import BaseCommand
from apps.botauth.models import BotClientProfile


class Command(BaseCommand):
    help = 'List all registered bot clients'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Show only active bots'
        )
    
    def handle(self, *args, **options):
        queryset = BotClientProfile.objects.select_related('client').all()
        
        if options['active_only']:
            queryset = queryset.filter(is_active=True)
        
        if not queryset.exists():
            self.stdout.write('No bots registered.')
            return
        
        self.stdout.write(f'\n{"Name":<30} {"Client ID":<25} {"Status":<10} {"Scopes":<30}')
        self.stdout.write('-' * 95)
        
        for bot in queryset:
            status = '🟢 Active' if bot.is_active else '🔴 Suspended'
            scopes = ', '.join(bot.allowed_scopes[:3])
            if len(bot.allowed_scopes) > 3:
                scopes += f' (+{len(bot.allowed_scopes) - 3})'
            
            self.stdout.write(
                f'{bot.display_name:<30} '
                f'{bot.client.client_id[:20]:<25} '
                f'{status:<10} '
                f'{scopes:<30}'
            )
        
        self.stdout.write(f'\nTotal: {queryset.count()} bot(s)')
```

### Task 4.5: Create Tests for Bot Management

Create `apps/botauth/tests/test_bot_client.py`:

```python
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from oidc_provider.models import Client

from apps.botauth.models import BotClientProfile, BotClientAuditLog
from apps.botauth.bot_service import (
    BotClientService, ALLOWED_BOT_SCOPES, FORBIDDEN_BOT_SCOPES
)

User = get_user_model()


class BotClientServiceTest(TestCase):
    """Tests for BotClientService."""
    
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@hospital.com',
            password='adminpass'
        )
    
    def test_create_bot(self):
        """Test creating a bot client."""
        bot, secret = BotClientService.create_bot(
            display_name='Test Bot',
            description='A test bot',
            allowed_scopes=['patient:read', 'dailynote:draft'],
            created_by=self.admin_user
        )
        
        self.assertIsNotNone(bot)
        self.assertIsNotNone(secret)
        self.assertTrue(bot.client.client_id.startswith('bot_'))
        self.assertEqual(bot.allowed_scopes, ['patient:read', 'dailynote:draft'])
        self.assertTrue(bot.is_active)
        
        # Verify audit log
        log = BotClientAuditLog.objects.filter(
            bot_profile=bot,
            event_type='created'
        ).first()
        self.assertIsNotNone(log)
    
    def test_create_bot_forbidden_scope(self):
        """Test that forbidden scopes are rejected."""
        with self.assertRaises(ValueError) as ctx:
            BotClientService.create_bot(
                display_name='Bad Bot',
                allowed_scopes=['note:finalize']  # Forbidden!
            )
        self.assertIn('forbidden', str(ctx.exception).lower())
    
    def test_validate_credentials(self):
        """Test credential validation."""
        bot, secret = BotClientService.create_bot(
            display_name='Auth Bot',
            allowed_scopes=['patient:read']
        )
        
        # Valid credentials
        result = BotClientService.validate_client_credentials(
            bot.client.client_id,
            secret
        )
        self.assertEqual(result, bot)
        
        # Invalid secret
        result = BotClientService.validate_client_credentials(
            bot.client.client_id,
            'wrong_secret'
        )
        self.assertIsNone(result)
        
        # Invalid client_id
        result = BotClientService.validate_client_credentials(
            'invalid_client',
            secret
        )
        self.assertIsNone(result)
    
    def test_suspend_reactivate(self):
        """Test suspending and reactivating a bot."""
        bot, secret = BotClientService.create_bot(
            display_name='Suspend Bot',
            allowed_scopes=['patient:read']
        )
        
        # Suspend
        BotClientService.suspend_bot(bot, reason='Testing', performed_by=self.admin_user)
        bot.refresh_from_db()
        self.assertFalse(bot.is_active)
        self.assertIsNotNone(bot.suspended_at)
        
        # Suspended bot fails validation
        result = BotClientService.validate_client_credentials(
            bot.client.client_id,
            secret
        )
        self.assertIsNone(result)
        
        # Reactivate
        BotClientService.reactivate_bot(bot, performed_by=self.admin_user)
        bot.refresh_from_db()
        self.assertTrue(bot.is_active)
        
        # Check audit logs
        logs = BotClientAuditLog.objects.filter(bot_profile=bot).order_by('created_at')
        event_types = [log.event_type for log in logs]
        self.assertIn('suspended', event_types)
        self.assertIn('reactivated', event_types)
    
    def test_rotate_secret(self):
        """Test rotating bot secret."""
        bot, old_secret = BotClientService.create_bot(
            display_name='Rotate Bot',
            allowed_scopes=['patient:read']
        )
        
        new_secret = BotClientService.rotate_secret(bot, performed_by=self.admin_user)
        
        self.assertNotEqual(old_secret, new_secret)
        
        # Old secret should fail
        result = BotClientService.validate_client_credentials(
            bot.client.client_id,
            old_secret
        )
        self.assertIsNone(result)
        
        # New secret should work
        result = BotClientService.validate_client_credentials(
            bot.client.client_id,
            new_secret
        )
        self.assertEqual(result, bot)
    
    def test_scope_validation(self):
        """Test scope validation on bot."""
        bot, _ = BotClientService.create_bot(
            display_name='Scope Bot',
            allowed_scopes=['patient:read', 'dailynote:draft']
        )
        
        self.assertTrue(bot.can_request_scope('patient:read'))
        self.assertTrue(bot.can_request_scope('dailynote:draft'))
        self.assertFalse(bot.can_request_scope('prescription:draft'))
        
        self.assertTrue(bot.can_request_scopes(['patient:read', 'dailynote:draft']))
        self.assertFalse(bot.can_request_scopes(['patient:read', 'prescription:draft']))
```

### Task 4.6: Run Migrations

```bash
uv run python manage.py makemigrations botauth
uv run python manage.py migrate botauth
```

## Files to Create

1. `apps/botauth/bot_service.py` - BotClientService
2. `apps/botauth/management/__init__.py`
3. `apps/botauth/management/commands/__init__.py`
4. `apps/botauth/management/commands/create_bot.py`
5. `apps/botauth/management/commands/list_bots.py`
6. `apps/botauth/tests/test_bot_client.py`

## Files to Modify

1. `apps/botauth/models.py` - Add BotClientProfile, BotClientAuditLog
2. `apps/botauth/admin.py` - Add bot admin interfaces

## Acceptance Criteria

- [ ] BotClientProfile model extends OIDC Client with EQMD-specific fields
- [ ] BotClientAuditLog tracks all bot management operations
- [ ] BotClientService can create, suspend, reactivate bots
- [ ] Credential validation works correctly
- [ ] Scope validation enforces allowed/forbidden lists
- [ ] Rate limiting fields exist (enforcement in Phase 06)
- [ ] Admin interface allows managing bots
- [ ] Management commands work (`create_bot`, `list_bots`)
- [ ] All tests pass

## Verification Commands

```bash
# Run migrations
uv run python manage.py migrate botauth

# Create a test bot
uv run python manage.py create_bot "Matrix Draft Bot" \
    --description "Bot for creating draft documents via Matrix" \
    --scopes patient:read dailynote:draft dischargereport:draft

# List bots
uv run python manage.py list_bots

# Run tests
uv run pytest apps/botauth/tests/test_bot_client.py -v

# Verify in admin
uv run python manage.py runserver
# Navigate to /admin/ and check BotClientProfile section
```

## Security Notes

- Bot client secrets are generated securely and shown only once
- Forbidden scopes cannot be assigned to bots under any circumstance
- All bot management operations are audited
- Suspended bots cannot authenticate
- Rate limiting fields are prepared (enforcement in Phase 06)
