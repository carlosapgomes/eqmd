import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from oidc_provider.models import Client


class MatrixUserBinding(models.Model):
    """
    Links a Matrix user ID to an EQMD user account.
    
    This binding allows the Matrix bot to identify which EQMD physician
    is issuing commands and request delegated tokens on their behalf.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matrix_binding',
        verbose_name='EQMD User'
    )
    
    matrix_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Matrix User ID',
        help_text='Full Matrix ID (e.g., @username:server.com)'
    )
    
    # Verification tracking
    verified = models.BooleanField(
        default=False,
        help_text='Whether the binding has been verified by the user'
    )
    verified_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When the binding was verified'
    )
    
    # Verification token (for email/web verification flow)
    verification_token = models.CharField(
        max_length=64,
        blank=True,
        help_text='Token for verification process'
    )
    verification_token_expires = models.DateTimeField(
        null=True, blank=True,
        help_text='When the verification token expires'
    )
    
    # Delegation control
    delegation_enabled = models.BooleanField(
        default=True,
        help_text='Whether this binding can be used for bot delegation'
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Matrix User Binding'
        verbose_name_plural = 'Matrix User Bindings'
        indexes = [
            models.Index(fields=['matrix_id']),
            models.Index(fields=['verified', 'delegation_enabled']),
        ]
    
    def __str__(self):
        status = '✓' if self.verified else '?'
        return f"{self.user.email} ↔ {self.matrix_id} [{status}]"
    
    def is_valid_for_delegation(self):
        """Check if this binding can be used for bot delegation."""
        if not self.verified:
            return False
        if not self.delegation_enabled:
            return False
        if not self.user.is_active:
            return False
        if self.user.account_status not in ('active', 'expiring_soon'):
            return False
        return True
    
    def generate_verification_token(self):
        """Generate a new verification token."""
        import secrets
        self.verification_token = secrets.token_urlsafe(32)
        self.verification_token_expires = timezone.now() + timezone.timedelta(hours=24)
        self.save(update_fields=['verification_token', 'verification_token_expires'])
        return self.verification_token
    
    def verify(self):
        """Mark this binding as verified."""
        self.verified = True
        self.verified_at = timezone.now()
        self.verification_token = ''
        self.verification_token_expires = None
        self.save()
    
    @classmethod
    def get_user_for_matrix_id(cls, matrix_id):
        """
        Get the EQMD user for a given Matrix ID.
        Returns None if no valid binding exists.
        """
        try:
            binding = cls.objects.select_related('user').get(
                matrix_id=matrix_id,
                verified=True,
                delegation_enabled=True
            )
            if binding.is_valid_for_delegation():
                return binding.user
            return None
        except cls.DoesNotExist:
            return None


class MatrixBindingAuditLog(models.Model):
    """
    Audit log for Matrix binding operations.
    Immutable record of all binding-related events.
    """
    
    class EventType(models.TextChoices):
        BINDING_CREATED = 'created', 'Binding Created'
        BINDING_VERIFIED = 'verified', 'Binding Verified'
        BINDING_REVOKED = 'revoked', 'Binding Revoked'
        DELEGATION_ENABLED = 'delegation_enabled', 'Delegation Enabled'
        DELEGATION_DISABLED = 'delegation_disabled', 'Delegation Disabled'
        VERIFICATION_FAILED = 'verification_failed', 'Verification Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    binding = models.ForeignKey(
        MatrixUserBinding,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    
    # Denormalized for when binding is deleted
    matrix_id = models.CharField(max_length=255)
    user_email = models.EmailField()
    
    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices
    )
    
    event_details = models.JSONField(
        default=dict,
        help_text='Additional event details'
    )
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Matrix Binding Audit Log'
        verbose_name_plural = 'Matrix Binding Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['matrix_id', '-created_at']),
            models.Index(fields=['user_email', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.matrix_id} @ {self.created_at}"


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


class DelegationAuditLog(models.Model):
    """
    Audit log for delegation token issuance.
    Records every delegated token issued for compliance and debugging.
    """
    
    class Status(models.TextChoices):
        ISSUED = 'issued', 'Token Issued'
        DENIED_INACTIVE_USER = 'denied_inactive', 'Denied: User Inactive'
        DENIED_INVALID_SCOPES = 'denied_scopes', 'Denied: Invalid Scopes'
        DENIED_BOT_SUSPENDED = 'denied_bot', 'Denied: Bot Suspended'
        DENIED_RATE_LIMITED = 'denied_rate', 'Denied: Rate Limited'
        DENIED_NO_BINDING = 'denied_binding', 'Denied: No Matrix Binding'
        DENIED_DELEGATION_DISABLED = 'denied_disabled', 'Denied: Delegation Disabled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Request info
    bot_client_id = models.CharField(max_length=255)
    bot_name = models.CharField(max_length=100)
    matrix_id = models.CharField(max_length=255)
    requested_scopes = models.JSONField(default=list)
    
    # User info (may be null if binding not found)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='delegation_audit_logs'
    )
    user_email = models.EmailField(blank=True)
    
    # Result
    status = models.CharField(max_length=30, choices=Status.choices)
    granted_scopes = models.JSONField(default=list)
    token_jti = models.CharField(max_length=36, blank=True)  # JWT ID if issued
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Error details
    error_message = models.TextField(blank=True)
    
    # Request metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Delegation Audit Log'
        verbose_name_plural = 'Delegation Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['bot_client_id', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.status} - {self.bot_name} for {self.user_email} @ {self.created_at}"


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
