"""
Service for managing bot clients.
"""

import secrets
import logging
from django.db import transaction
from oidc_provider.models import Client, ResponseType

from .models import BotClientProfile, BotClientAuditLog

logger = logging.getLogger('security.bot_management')


# Import scope utilities from the centralized scope registry
from .scopes import get_allowed_bot_scopes, get_forbidden_bot_scopes

# Use these functions instead of hardcoded lists
ALLOWED_BOT_SCOPES = get_allowed_bot_scopes()
FORBIDDEN_BOT_SCOPES = get_forbidden_bot_scopes()


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