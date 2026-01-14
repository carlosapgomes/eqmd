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