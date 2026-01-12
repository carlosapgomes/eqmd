import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.botauth.scopes import (
    get_scope, get_allowed_bot_scopes, get_forbidden_bot_scopes,
    is_scope_allowed_for_bots, is_draft_scope, validate_scopes,
    validate_delegation_scopes, parse_scope, ScopeAction
)
from apps.botauth.permissions import (
    HasScope, HasAnyScope, IsDelegatedRequest, IsHumanRequest, DenyBotAccess
)
from apps.botauth.bot_service import BotClientService

User = get_user_model()


class ScopeRegistryTest(TestCase):
    """Tests for scope registry functions."""
    
    def test_get_scope(self):
        """Test getting scope definition."""
        scope = get_scope('patient:read')
        self.assertEqual(scope.name, 'patient:read')
        self.assertEqual(scope.action, ScopeAction.READ)
        self.assertTrue(scope.allowed_for_bots)
    
    def test_get_scope_unknown(self):
        """Test getting unknown scope raises error."""
        with self.assertRaises(ValueError):
            get_scope('unknown:scope')
    
    def test_allowed_bot_scopes(self):
        """Test getting allowed bot scopes."""
        allowed = get_allowed_bot_scopes()
        self.assertIn('patient:read', allowed)
        self.assertIn('dailynote:draft', allowed)
        self.assertNotIn('patient:write', allowed)
        self.assertNotIn('note:finalize', allowed)
    
    def test_forbidden_bot_scopes(self):
        """Test getting forbidden bot scopes."""
        forbidden = get_forbidden_bot_scopes()
        self.assertIn('patient:write', forbidden)
        self.assertIn('note:finalize', forbidden)
        self.assertNotIn('patient:read', forbidden)
    
    def test_is_draft_scope(self):
        """Test identifying draft scopes."""
        self.assertTrue(is_draft_scope('dailynote:draft'))
        self.assertTrue(is_draft_scope('dischargereport:draft'))
        self.assertFalse(is_draft_scope('patient:read'))
        self.assertFalse(is_draft_scope('unknown:scope'))
    
    def test_parse_scope(self):
        """Test parsing scopes."""
        resource, action = parse_scope('patient:read')
        self.assertEqual(resource, 'patient')
        self.assertEqual(action, 'read')
        
        with self.assertRaises(ValueError):
            parse_scope('invalid_scope')
    
    def test_validate_scopes(self):
        """Test scope validation."""
        # Valid scopes
        valid, errors = validate_scopes(['patient:read', 'dailynote:draft'])
        self.assertTrue(valid)
        self.assertEqual(errors, [])
        
        # Unknown scope
        valid, errors = validate_scopes(['unknown:scope'])
        self.assertFalse(valid)
        self.assertIn('Unknown scope', errors[0])
        
        # Forbidden scope
        valid, errors = validate_scopes(['patient:write'], for_bot=True)
        self.assertFalse(valid)
        self.assertIn('not allowed for bots', errors[0])


class ScopePermissionTest(TestCase):
    """Tests for scope-based permissions."""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='testdoc',
            email='doc@hospital.com',
            password='testpass',
            profession_type=0  # Medical Doctor
        )
        
        # Create a test view
        class TestView(APIView):
            permission_classes = [HasScope]
            required_scopes = ['patient:read']
            
            def get(self, request):
                return Response({'status': 'ok'})
        
        self.view = TestView.as_view()
    
    def test_has_scope_with_valid_scope(self):
        """Test HasScope allows request with valid scope."""
        request = self.factory.get('/test/')
        request.user = self.user
        request.scopes = {'patient:read', 'dailynote:draft'}
        
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_has_scope_without_scope(self):
        """Test HasScope denies request without scope."""
        request = self.factory.get('/test/')
        request.user = self.user
        request.scopes = {'dailynote:draft'}  # Missing patient:read
        request.actor = 'some_bot'  # Mark as delegated request
        
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_has_scope_human_user_allowed(self):
        """Test HasScope allows human users without scopes."""
        request = self.factory.get('/test/')
        request.user = self.user
        # No scopes, no actor = human user
        
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_deny_bot_access(self):
        """Test DenyBotAccess permission."""
        class ProtectedView(APIView):
            permission_classes = [DenyBotAccess]
            
            def get(self, request):
                return Response({'status': 'ok'})
        
        view = ProtectedView.as_view()
        
        # Human request - allowed
        request = self.factory.get('/test/')
        request.user = self.user
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Bot request - denied
        request = self.factory.get('/test/')
        request.user = self.user
        request.actor = 'some_bot'
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class DelegationScopeValidationTest(TestCase):
    """Tests for delegation scope validation."""
    
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@hospital.com',
            password='testpass',
            profession_type=0  # Medical Doctor
        )
        self.nurse = User.objects.create_user(
            username='nurse',
            email='nurse@hospital.com',
            password='testpass',
            profession_type=2  # Nurse
        )
        
        self.bot, _ = BotClientService.create_bot(
            display_name='Test Bot',
            allowed_scopes=['patient:read', 'dailynote:draft']
        )
    
    def test_doctor_can_delegate_draft_scope(self):
        """Test that doctors can delegate draft scopes."""
        valid, errors = validate_delegation_scopes(
            ['patient:read', 'dailynote:draft'],
            self.doctor,
            self.bot
        )
        self.assertTrue(valid)
        self.assertEqual(errors, [])
    
    def test_nurse_cannot_delegate_draft_scope(self):
        """Test that nurses cannot delegate draft scopes."""
        valid, errors = validate_delegation_scopes(
            ['dailynote:draft'],
            self.nurse,
            self.bot
        )
        self.assertFalse(valid)
        self.assertIn('Only doctors can delegate', errors[0])
    
    def test_bot_scope_limit(self):
        """Test that bot cannot request scopes it doesn't have."""
        valid, errors = validate_delegation_scopes(
            ['prescription:draft'],  # Bot doesn't have this scope
            self.doctor,
            self.bot
        )
        self.assertFalse(valid)
        self.assertIn('Bot not authorized', errors[0])


class ScopeConvenienceSetsTest(TestCase):
    """Tests for predefined scope sets."""
    
    def test_dailynote_bot_scopes(self):
        """Test daily note bot scope set."""
        from apps.botauth.scopes import DAILYNOTE_BOT_SCOPES
        
        self.assertIn('patient:read', DAILYNOTE_BOT_SCOPES)
        self.assertIn('dailynote:draft', DAILYNOTE_BOT_SCOPES)
        self.assertIn('summary:generate', DAILYNOTE_BOT_SCOPES)
    
    def test_discharge_bot_scopes(self):
        """Test discharge bot scope set."""
        from apps.botauth.scopes import DISCHARGE_BOT_SCOPES
        
        self.assertIn('patient:read', DISCHARGE_BOT_SCOPES)
        self.assertIn('dischargereport:draft', DISCHARGE_BOT_SCOPES)
    
    def test_prescription_bot_scopes(self):
        """Test prescription bot scope set."""
        from apps.botauth.scopes import PRESCRIPTION_BOT_SCOPES
        
        self.assertIn('patient:read', PRESCRIPTION_BOT_SCOPES)
        self.assertIn('prescription:draft', PRESCRIPTION_BOT_SCOPES)
    
    def test_readonly_bot_scopes(self):
        """Test read-only bot scope set."""
        from apps.botauth.scopes import READONLY_BOT_SCOPES
        
        self.assertIn('patient:read', READONLY_BOT_SCOPES)
        self.assertNotIn('dailynote:draft', READONLY_BOT_SCOPES)


class ScopeActionEnumTest(TestCase):
    """Tests for ScopeAction enum."""
    
    def test_scope_action_values(self):
        """Test ScopeAction enum values."""
        self.assertEqual(ScopeAction.READ.value, 'read')
        self.assertEqual(ScopeAction.DRAFT.value, 'draft')
        self.assertEqual(ScopeAction.GENERATE.value, 'generate')
        self.assertEqual(ScopeAction.WRITE.value, 'write')
        self.assertEqual(ScopeAction.FINALIZE.value, 'finalize')
        self.assertEqual(ScopeAction.SIGN.value, 'sign')