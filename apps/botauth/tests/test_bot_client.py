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