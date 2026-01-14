"""
Tests for kill switch functionality.
"""

from io import StringIO
from django.core.management.base import CommandError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from unittest.mock import patch, MagicMock

from apps.botauth.models import BotDelegationConfig, BotClientProfile, MatrixUserBinding
from apps.botauth.killswitch import KillSwitchService
from apps.botauth.audit import AuditEventType, BotAuditLog
from oidc_provider.models import Client

User = get_user_model()


class BotDelegationConfigModelTests(TestCase):
    """Tests for the BotDelegationConfig model."""
    
    def test_singleton_behavior(self):
        """Test that only one config instance can exist."""
        config1 = BotDelegationConfig.get_config()
        config2 = BotDelegationConfig.get_config()
        
        self.assertEqual(config1.pk, config2.pk)
        self.assertEqual(config1.pk, 1)
    
    def test_default_enabled_state(self):
        """Test that delegation is enabled by default."""
        config = BotDelegationConfig.get_config()
        self.assertTrue(config.delegation_enabled)
        self.assertFalse(config.maintenance_mode)
    
    def test_is_delegation_enabled(self):
        """Test the class method for checking delegation status."""
        config = BotDelegationConfig.get_config()
        
        # Default state
        self.assertTrue(BotDelegationConfig.is_delegation_enabled())
        
        # Disabled
        config.delegation_enabled = False
        config.save()
        self.assertFalse(BotDelegationConfig.is_delegation_enabled())
        
        # Maintenance mode
        config.delegation_enabled = True
        config.maintenance_mode = True
        config.save()
        self.assertFalse(BotDelegationConfig.is_delegation_enabled())
    
    def test_str_representation(self):
        """Test the string representation of config."""
        config = BotDelegationConfig.get_config()
        
        # Enabled
        config.delegation_enabled = True
        config.maintenance_mode = False
        config.save()
        self.assertIn('🟢 Enabled', str(config))
        
        # Disabled
        config.delegation_enabled = False
        config.maintenance_mode = False
        config.save()
        self.assertIn('🔴 Disabled', str(config))
        
        # Maintenance
        config.delegation_enabled = True
        config.maintenance_mode = True
        config.save()
        self.assertIn('🟡 Maintenance', str(config))


class KillSwitchServiceTests(TestCase):
    """Tests for the KillSwitchService."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testdoctor',
            email='doctor@example.com',
            password='testpass123',
            profession_type=0,  # Medical Doctor
            is_active=True,
            account_status='active'
        )
        cache.clear()  # Clear cache before each test
    
    def test_is_delegation_enabled_cache(self):
        """Test that is_delegation_enabled uses cache."""
        config = BotDelegationConfig.get_config()
        
        # First call should hit database
        enabled1 = KillSwitchService.is_delegation_enabled()
        self.assertTrue(enabled1)
        
        # Change config
        config.delegation_enabled = False
        config.save()
        
        # Cache should still return old value
        enabled2 = KillSwitchService.is_delegation_enabled()
        self.assertTrue(enabled2)
        
        # Clear cache and check again
        cache.delete('bot_delegation_enabled')
        enabled3 = KillSwitchService.is_delegation_enabled()
        self.assertFalse(enabled3)
    
    def test_get_status(self):
        """Test getting full delegation status."""
        config = BotDelegationConfig.get_config()
        
        status = KillSwitchService.get_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('enabled', status)
        self.assertIn('maintenance_mode', status)
        self.assertIn('maintenance_message', status)
        self.assertIn('disabled_at', status)
        self.assertIn('disabled_reason', status)
        
        self.assertTrue(status['enabled'])
        self.assertFalse(status['maintenance_mode'])
    
    def test_disable_delegation(self):
        """Test disabling delegation."""
        config = BotDelegationConfig.get_config()
        self.assertTrue(config.delegation_enabled)
        
        KillSwitchService.disable_delegation(
            self.user, 
            reason='Test disable'
        )
        
        config.refresh_from_db()
        self.assertFalse(config.delegation_enabled)
        self.assertIsNotNone(config.disabled_at)
        self.assertEqual(config.disabled_by, self.user)
        self.assertEqual(config.disabled_reason, 'Test disable')
        
        # Check audit log
        audit_log = BotAuditLog.objects.filter(
            event_type=AuditEventType.KILLSWITCH_ACTIVATED
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.user_id, self.user.id)
    
    def test_enable_delegation(self):
        """Test enabling delegation."""
        config = BotDelegationConfig.get_config()
        config.delegation_enabled = False
        config.save()
        
        KillSwitchService.enable_delegation(self.user)
        
        config.refresh_from_db()
        self.assertTrue(config.delegation_enabled)
        self.assertFalse(config.maintenance_mode)
        self.assertIsNone(config.disabled_at)
        self.assertIsNone(config.disabled_by)
        self.assertEqual(config.disabled_reason, '')
        
        # Check audit log
        audit_log = BotAuditLog.objects.filter(
            event_type=AuditEventType.KILLSWITCH_DEACTIVATED
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.user_id, self.user.id)
    
    def test_enable_maintenance(self):
        """Test enabling maintenance mode."""
        KillSwitchService.enable_maintenance('System maintenance')
        
        config = BotDelegationConfig.get_config()
        self.assertTrue(config.maintenance_mode)
        self.assertEqual(config.maintenance_message, 'System maintenance')
    
    def test_disable_maintenance(self):
        """Test disabling maintenance mode."""
        config = BotDelegationConfig.get_config()
        config.maintenance_mode = True
        config.maintenance_message = 'Maintenance'
        config.save()
        
        KillSwitchService.disable_maintenance()
        
        config.refresh_from_db()
        self.assertFalse(config.maintenance_mode)


class KillSwitchAPITests(APITestCase):
    """Tests for kill switch integration with API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create user
        self.user = User.objects.create_user(
            username='testdoctor',
            email='doctor@example.com',
            password='testpass123',
            profession_type=0,  # Medical Doctor
            is_active=True,
            account_status='active'
        )
        
        # Create Matrix binding
        self.matrix_binding = MatrixUserBinding.objects.create(
            user=self.user,
            matrix_id='@doctor:example.com',
            verified=True
        )
        
        # Create OIDC client
        self.oidc_client = Client.objects.create(
            client_id='test_bot',
            client_secret='test_secret',
            _redirect_uris='',
            _scope='openid'
        )
        
        # Create bot profile
        self.bot_profile = BotClientProfile.objects.create(
            client=self.oidc_client,
            display_name='Test Bot',
            allowed_scopes=['patient:read', 'dailynote:draft']
        )
        
        cache.clear()
    
    def test_delegation_blocked_when_disabled(self):
        """Test that delegation is blocked when kill switch is active."""
        # Disable delegation
        KillSwitchService.disable_delegation(
            self.user,
            reason='Test'
        )
        
        # Try to request token
        response = self.client.post(
            '/auth/api/delegated-token/',
            {
                'client_id': 'test_bot',
                'client_secret': 'test_secret',
                'matrix_id': '@doctor:example.com',
                'scopes': ['patient:read']
            }
        )
        
        self.assertEqual(response.status_code, 503)
        self.assertIn('Bot delegation is currently disabled', response.json()['error'])
    
    def test_delegation_blocked_in_maintenance_mode(self):
        """Test that delegation is blocked during maintenance."""
        # Enable maintenance mode
        KillSwitchService.enable_maintenance('Scheduled maintenance')
        
        # Try to request token
        response = self.client.post(
            '/auth/api/delegated-token/',
            {
                'client_id': 'test_bot',
                'client_secret': 'test_secret',
                'matrix_id': '@doctor:example.com',
                'scopes': ['patient:read']
            }
        )
        
        self.assertEqual(response.status_code, 503)
        self.assertIn('Scheduled maintenance', response.json()['error'])
    
    def test_delegation_works_when_enabled(self):
        """Test that delegation works normally when enabled."""
        # Ensure delegation is enabled
        KillSwitchService.enable_delegation(self.user)
        
        # Request token
        response = self.client.post(
            '/auth/api/delegated-token/',
            {
                'client_id': 'test_bot',
                'client_secret': 'test_secret',
                'matrix_id': '@doctor:example.com',
                'scopes': ['patient:read']
            }
        )
        
        # Should not get 503 error (may fail for other reasons, but not kill switch)
        self.assertNotEqual(response.status_code, 503)


class ManagementCommandTests(TestCase):
    """Tests for the kill switch management command."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123',
            username='admin'
        )
        cache.clear()
    
    def test_status_command(self):
        """Test the status command."""
        out = StringIO()
        call_command(
            'delegation_killswitch',
            'status',
            stdout=out
        )
        
        output = out.getvalue()
        self.assertIn('Bot Delegation Status', output)
        self.assertIn('Enabled:', output)
    
    def test_disable_command(self):
        """Test the disable command."""
        out = StringIO()
        call_command(
            'delegation_killswitch',
            'disable',
            '--reason', 'Test disable',
            stdout=out
        )
        
        config = BotDelegationConfig.get_config()
        self.assertFalse(config.delegation_enabled)
        
        output = out.getvalue()
        self.assertIn('Bot delegation DISABLED', output)
    
    def test_enable_command(self):
        """Test the enable command."""
        # First disable
        config = BotDelegationConfig.get_config()
        config.delegation_enabled = False
        config.save()
        
        # Then enable
        out = StringIO()
        call_command(
            'delegation_killswitch',
            'enable',
            stdout=out
        )
        
        config.refresh_from_db()
        self.assertTrue(config.delegation_enabled)
        
        output = out.getvalue()
        self.assertIn('Bot delegation enabled', output)
    
    def test_maintenance_on_command(self):
        """Test enabling maintenance mode."""
        out = StringIO()
        call_command(
            'delegation_killswitch',
            'maintenance-on',
            '--message', 'Test maintenance',
            stdout=out
        )
        
        config = BotDelegationConfig.get_config()
        self.assertTrue(config.maintenance_mode)
        self.assertEqual(config.maintenance_message, 'Test maintenance')
    
    def test_maintenance_off_command(self):
        """Test disabling maintenance mode."""
        config = BotDelegationConfig.get_config()
        config.maintenance_mode = True
        config.save()
        
        out = StringIO()
        call_command(
            'delegation_killswitch',
            'maintenance-off',
            stdout=out
        )
        
        config.refresh_from_db()
        self.assertFalse(config.maintenance_mode)
    
    def test_command_requires_superuser(self):
        """Test that commands fail gracefully if no superuser exists."""
        # Delete all superusers
        User.objects.filter(is_superuser=True).delete()
        
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                'delegation_killswitch',
                'disable',
                stdout=out
            )