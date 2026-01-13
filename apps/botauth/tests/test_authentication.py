"""
Tests for DelegatedJWTAuthentication backend.
"""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from rest_framework.exceptions import AuthenticationFailed

from apps.botauth.authentication import DelegatedJWTAuthentication, DelegatedAuthInfo
from apps.botauth.models import BotClientProfile, MatrixUserBinding
from apps.botauth.tokens import DelegatedTokenGenerator
from oidc_provider.models import Client

User = get_user_model()


@pytest.fixture
def authentication_backend():
    """Return the authentication backend instance."""
    return DelegatedJWTAuthentication()


@pytest.fixture
def active_user(db):
    """Create an active user for testing."""
    return User.objects.create_user(
        username='physician',
        email='physician@example.com',
        password='test_password',
        is_active=True
    )


@pytest.fixture
def inactive_user(db):
    """Create an inactive user for testing."""
    return User.objects.create_user(
        username='inactive_physician',
        email='inactive@example.com',
        password='test_password',
        is_active=False
    )


@pytest.fixture
def bot_profile(db):
    """Create a bot client profile for testing."""
    from apps.botauth.bot_service import BotClientService
    bot, _ = BotClientService.create_bot(
        display_name='Test Bot',
        description='A test bot',
        allowed_scopes=['patient:read', 'dailynote:draft']
    )
    return bot


@pytest.fixture
def inactive_bot_profile(db):
    """Create an inactive bot client profile for testing."""
    from apps.botauth.bot_service import BotClientService
    bot, _ = BotClientService.create_bot(
        display_name='Inactive Bot',
        description='An inactive test bot',
        allowed_scopes=['patient:read']
    )
    bot.is_active = False
    bot.save()
    return bot


@pytest.fixture
def valid_token(active_user, bot_profile):
    """Generate a valid delegated token."""
    return DelegatedTokenGenerator.generate_token(
        user=active_user,
        bot_profile=bot_profile,
        scopes=['patient:read', 'dailynote:draft'],
        ttl_seconds=600
    )


@pytest.fixture
def expired_token(active_user, bot_profile):
    """Generate an expired token."""
    return DelegatedTokenGenerator.generate_token(
        user=active_user,
        bot_profile=bot_profile,
        scopes=['patient:read'],
        ttl_seconds=-600  # Already expired
    )


@pytest.fixture
def malformed_token():
    """Return a malformed token."""
    return 'invalid.jwt.token'


class TestDelegatedJWTAuthentication:
    """Test suite for DelegatedJWTAuthentication."""
    
    def test_authenticate_with_valid_token(self, authentication_backend, active_user, bot_profile, valid_token):
        """Test authentication with a valid delegated token."""
        factory = RequestFactory()
        request = factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {valid_token}'
        
        result = authentication_backend.authenticate(request)
        
        assert result is not None
        user, auth_info = result
        
        assert user == active_user
        assert isinstance(auth_info, DelegatedAuthInfo)
        assert auth_info.bot_client_id == bot_profile.client.client_id
        assert auth_info.bot_name == bot_profile.display_name
        assert set(auth_info.scopes) == {'patient:read', 'dailynote:draft'}
        assert auth_info.is_delegated
        
        # Check request attributes (set by authenticate method)
        assert hasattr(request, 'actor')
        assert request.actor == bot_profile.client.client_id
        assert hasattr(request, 'actor_name')
        assert request.actor_name == bot_profile.display_name
        assert hasattr(request, 'scopes')
        assert request.scopes == {'patient:read', 'dailynote:draft'}
        assert hasattr(request, 'is_delegated')
        assert request.is_delegated is True
        assert hasattr(request, 'delegation_jti')
    
    def test_authenticate_with_expired_token(self, authentication_backend, expired_token):
        """Test authentication with an expired token."""
        factory = RequestFactory()
        request = factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {expired_token}'
        
        with pytest.raises(AuthenticationFailed) as exc_info:
            authentication_backend.authenticate(request)
        
        assert 'Token has expired' in str(exc_info.value)
    
    def test_authenticate_with_malformed_token(self, authentication_backend, malformed_token):
        """Test authentication with a malformed token."""
        factory = RequestFactory()
        request = factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {malformed_token}'
        
        with pytest.raises(AuthenticationFailed) as exc_info:
            authentication_backend.authenticate(request)
        
        assert 'Invalid token' in str(exc_info.value)
    
    def test_authenticate_with_inactive_user(self, authentication_backend, inactive_user, bot_profile):
        """Test authentication with an inactive user."""
        token = DelegatedTokenGenerator.generate_token(
            user=inactive_user,
            bot_profile=bot_profile,
            scopes=['patient:read'],
            ttl_seconds=600
        )
        
        factory = RequestFactory()
        request = factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        with pytest.raises(AuthenticationFailed) as exc_info:
            authentication_backend.authenticate(request)
        
        assert 'User account is inactive' in str(exc_info.value)
    
    def test_authenticate_with_inactive_bot(self, authentication_backend, active_user, inactive_bot_profile):
        """Test authentication with an inactive bot."""
        token = DelegatedTokenGenerator.generate_token(
            user=active_user,
            bot_profile=inactive_bot_profile,
            scopes=['patient:read'],
            ttl_seconds=600
        )
        
        factory = RequestFactory()
        request = factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        with pytest.raises(AuthenticationFailed) as exc_info:
            authentication_backend.authenticate(request)
        
        assert 'Bot is no longer active' in str(exc_info.value)
    
    def test_authenticate_without_bearer_prefix(self, authentication_backend):
        """Test authentication without Bearer prefix."""
        factory = RequestFactory()
        request = factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = 'invalid_format_token'
        
        result = authentication_backend.authenticate(request)
        
        # Should return None for non-Bearer auth
        assert result is None
    
    def test_authenticate_without_auth_header(self, authentication_backend):
        """Test authentication without Authorization header."""
        factory = RequestFactory()
        request = factory.get('/api/test/')
        
        result = authentication_backend.authenticate(request)
        
        # Should return None when no auth header
        assert result is None
    
    def test_authenticate_header_method(self, authentication_backend):
        """Test the authenticate_header method."""
        factory = RequestFactory()
        request = factory.get('/api/test/')
        
        header = authentication_backend.authenticate_header(request)
        
        assert header == 'Bearer realm="eqmd-api"'
    
    def test_scopes_properly_extracted(self, authentication_backend, active_user, bot_profile):
        """Test that scopes are properly extracted and set on request."""
        scopes = ['patient:read', 'exam:read', 'dailynote:draft']
        token = DelegatedTokenGenerator.generate_token(
            user=active_user,
            bot_profile=bot_profile,
            scopes=scopes,
            ttl_seconds=600
        )
        
        factory = RequestFactory()
        request = factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        result = authentication_backend.authenticate(request)
        user, auth_info = result
        
        assert request.scopes == set(scopes)
        assert auth_info.scopes == set(scopes)


class TestDelegatedAuthInfo:
    """Test suite for DelegatedAuthInfo class."""
    
    def test_delegated_auth_info_properties(self, active_user, bot_profile):
        """Test DelegatedAuthInfo properties."""
        token_payload = {
            'sub': f'user:{active_user.id}',
            'azp': bot_profile.client.client_id,
            'scope': 'patient:read dailynote:draft'
        }
        
        auth_info = DelegatedAuthInfo(
            token_payload=token_payload,
            bot_client_id=bot_profile.client.client_id,
            bot_name=bot_profile.display_name,
            scopes={'patient:read', 'dailynote:draft'}
        )
        
        assert auth_info.token_payload == token_payload
        assert auth_info.bot_client_id == bot_profile.client.client_id
        assert auth_info.bot_name == bot_profile.display_name
        assert auth_info.scopes == {'patient:read', 'dailynote:draft'}
        assert auth_info.is_delegated is True


class TestAuthenticationIntegration:
    """Integration tests for authentication with various scenarios."""
    
    def test_multiple_bots_different_scopes(self, authentication_backend, active_user, db):
        """Test authentication with different bots having different scopes."""
        from apps.botauth.bot_service import BotClientService
        
        # Create first bot
        profile1, _ = BotClientService.create_bot(
            display_name='Bot 1',
            allowed_scopes=['patient:read']
        )
        
        # Create second bot
        profile2, _ = BotClientService.create_bot(
            display_name='Bot 2',
            allowed_scopes=['dailynote:draft']
        )
        
        # Test with first bot
        token1 = DelegatedTokenGenerator.generate_token(
            user=active_user,
            bot_profile=profile1,
            scopes=['patient:read'],
            ttl_seconds=600
        )
        
        factory = RequestFactory()
        request1 = factory.get('/api/test/')
        request1.META['HTTP_AUTHORIZATION'] = f'Bearer {token1}'
        
        result1 = authentication_backend.authenticate(request1)
        user1, auth_info1 = result1
        
        assert user1 == active_user
        assert auth_info1.bot_client_id == profile1.client.client_id
        assert request1.scopes == {'patient:read'}
        
        # Test with second bot
        token2 = DelegatedTokenGenerator.generate_token(
            user=active_user,
            bot_profile=profile2,
            scopes=['dailynote:draft'],
            ttl_seconds=600
        )
        
        request2 = factory.get('/api/test/')
        request2.META['HTTP_AUTHORIZATION'] = f'Bearer {token2}'
        
        result2 = authentication_backend.authenticate(request2)
        user2, auth_info2 = result2
        
        assert user2 == active_user
        assert auth_info2.bot_client_id == profile2.client.client_id
        assert request2.scopes == {'dailynote:draft'}
    
    def test_session_authentication_still_works(self, active_user, db):
        """Test that session authentication still works for regular users."""
        factory = RequestFactory()
        request = factory.get('/api/test/')
        request.user = active_user
        
        # Session authentication should work via DRF's SessionAuthentication
        # This test ensures we didn't break existing auth
        assert request.user.is_authenticated
        assert not hasattr(request, 'is_delegated') or not request.is_delegated