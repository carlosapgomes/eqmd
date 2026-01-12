# Phase 06 – Delegated Token Endpoint

## Goal

Implement the core delegation mechanism: an endpoint where authenticated bots can request short-lived tokens to act on behalf of physicians.

## Prerequisites

- Phase 05 completed (Scope system)
- All existing tests passing

## Context

This is the CRITICAL phase. The delegated token endpoint:
1. Authenticates the bot (client credentials)
2. Identifies the physician (via Matrix ID binding)
3. Validates the physician's status and permissions
4. Validates requested scopes
5. Issues a short-lived JWT

## Tasks

### Task 6.1: Create Token Generation Utilities

Create `apps/botauth/tokens.py`:

```python
"""
JWT token generation and validation for delegated bot authentication.
"""

import jwt
import uuid
from datetime import datetime, timedelta, timezone
from django.conf import settings


class DelegatedTokenGenerator:
    """Generate and validate delegated JWT tokens."""
    
    @classmethod
    def generate_token(cls, user, bot_profile, scopes, ttl_seconds=None):
        """
        Generate a delegated JWT token.
        
        Args:
            user: The physician delegating access
            bot_profile: The bot requesting delegation
            scopes: List of scopes granted
            ttl_seconds: Token lifetime (default from settings)
        
        Returns:
            str: The JWT token
        """
        if ttl_seconds is None:
            ttl_seconds = settings.DELEGATED_TOKEN_LIFETIME_SECONDS
        
        # Cap TTL at maximum allowed
        ttl_seconds = min(ttl_seconds, settings.DELEGATED_TOKEN_LIFETIME_SECONDS)
        
        now = datetime.now(timezone.utc)
        
        payload = {
            # Standard claims
            'iss': settings.DELEGATED_TOKEN_ISSUER,
            'sub': f"user:{user.id}",
            'aud': settings.DELEGATED_TOKEN_AUDIENCE,
            'exp': now + timedelta(seconds=ttl_seconds),
            'iat': now,
            'jti': str(uuid.uuid4()),
            
            # Custom claims
            'azp': bot_profile.client.client_id,  # Authorized party (bot)
            'scope': ' '.join(scopes),
            
            # User info (for audit/logging)
            'user_email': user.email,
            'user_profession': user.profession_type,
            
            # Bot info
            'bot_name': bot_profile.display_name,
        }
        
        token = jwt.encode(
            payload,
            settings.DELEGATED_TOKEN_SECRET,
            algorithm=settings.DELEGATED_TOKEN_ALGORITHM
        )
        
        return token
    
    @classmethod
    def decode_token(cls, token):
        """
        Decode and validate a delegated JWT token.
        
        Returns:
            dict: The token payload
        
        Raises:
            jwt.InvalidTokenError: If token is invalid
        """
        payload = jwt.decode(
            token,
            settings.DELEGATED_TOKEN_SECRET,
            algorithms=[settings.DELEGATED_TOKEN_ALGORITHM],
            audience=settings.DELEGATED_TOKEN_AUDIENCE,
            issuer=settings.DELEGATED_TOKEN_ISSUER
        )
        
        return payload
    
    @classmethod
    def extract_user_id(cls, payload):
        """Extract user ID from token payload."""
        sub = payload.get('sub', '')
        if sub.startswith('user:'):
            return sub[5:]  # Remove 'user:' prefix
        return None
    
    @classmethod
    def extract_scopes(cls, payload):
        """Extract scopes from token payload as a set."""
        scope_str = payload.get('scope', '')
        if not scope_str:
            return set()
        return set(scope_str.split())
```

### Task 6.2: Create Delegation Audit Model

Add to `apps/botauth/models.py`:

```python
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
```

### Task 6.3: Create Delegated Token Endpoint

Create `apps/botauth/api_views.py`:

```python
"""
API views for bot authentication and delegation.
"""

import logging
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .models import MatrixUserBinding, BotClientProfile, DelegationAuditLog
from .bot_service import BotClientService
from .scopes import validate_delegation_scopes
from .tokens import DelegatedTokenGenerator

logger = logging.getLogger('security.delegation')


class DelegatedTokenView(APIView):
    """
    Endpoint for bots to request delegated tokens.
    
    POST /auth/api/delegated-token/
    
    Request body:
    {
        "client_id": "bot_xxx",
        "client_secret": "xxx",
        "matrix_id": "@doctor:server.com",
        "scopes": ["patient:read", "dailynote:draft"]
    }
    
    Response (success):
    {
        "access_token": "eyJ...",
        "token_type": "Bearer",
        "expires_in": 600,
        "scope": "patient:read dailynote:draft"
    }
    """
    
    permission_classes = [AllowAny]  # Bot authenticates via client credentials
    
    def post(self, request):
        # Extract request data
        client_id = request.data.get('client_id')
        client_secret = request.data.get('client_secret')
        matrix_id = request.data.get('matrix_id')
        requested_scopes = request.data.get('scopes', [])
        
        # Get client IP for logging
        ip_address = self._get_client_ip(request)
        
        # Validate required fields
        if not all([client_id, client_secret, matrix_id]):
            return Response(
                {'error': 'Missing required fields: client_id, client_secret, matrix_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not isinstance(requested_scopes, list) or not requested_scopes:
            return Response(
                {'error': 'scopes must be a non-empty list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Authenticate bot
        bot_profile = BotClientService.validate_client_credentials(
            client_id, client_secret
        )
        
        if not bot_profile:
            self._log_denial(
                client_id=client_id,
                matrix_id=matrix_id,
                scopes=requested_scopes,
                status=DelegationAuditLog.Status.DENIED_BOT_SUSPENDED,
                error='Invalid client credentials or bot suspended',
                ip_address=ip_address
            )
            return Response(
                {'error': 'Invalid client credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check rate limiting
        if bot_profile.is_rate_limited():
            self._log_denial(
                client_id=client_id,
                bot_name=bot_profile.display_name,
                matrix_id=matrix_id,
                scopes=requested_scopes,
                status=DelegationAuditLog.Status.DENIED_RATE_LIMITED,
                error='Rate limit exceeded',
                ip_address=ip_address
            )
            return Response(
                {'error': 'Rate limit exceeded. Try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Look up physician by Matrix ID
        user = MatrixUserBinding.get_user_for_matrix_id(matrix_id)
        
        if not user:
            self._log_denial(
                client_id=client_id,
                bot_name=bot_profile.display_name,
                matrix_id=matrix_id,
                scopes=requested_scopes,
                status=DelegationAuditLog.Status.DENIED_NO_BINDING,
                error='No valid Matrix binding found',
                ip_address=ip_address
            )
            return Response(
                {'error': 'No valid user binding for this Matrix ID'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check user can delegate (active, not expired, can create documents)
        denial_reason = self._check_user_can_delegate(user)
        if denial_reason:
            self._log_denial(
                client_id=client_id,
                bot_name=bot_profile.display_name,
                matrix_id=matrix_id,
                user=user,
                scopes=requested_scopes,
                status=DelegationAuditLog.Status.DENIED_INACTIVE_USER,
                error=denial_reason,
                ip_address=ip_address
            )
            return Response(
                {'error': denial_reason},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate scopes
        valid, errors = validate_delegation_scopes(
            requested_scopes, user, bot_profile
        )
        
        if not valid:
            self._log_denial(
                client_id=client_id,
                bot_name=bot_profile.display_name,
                matrix_id=matrix_id,
                user=user,
                scopes=requested_scopes,
                status=DelegationAuditLog.Status.DENIED_INVALID_SCOPES,
                error='; '.join(errors),
                ip_address=ip_address
            )
            return Response(
                {'error': 'Invalid scopes', 'details': errors},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate token
        token = DelegatedTokenGenerator.generate_token(
            user=user,
            bot_profile=bot_profile,
            scopes=requested_scopes
        )
        
        # Decode to get expiration for response
        payload = DelegatedTokenGenerator.decode_token(token)
        expires_at = timezone.datetime.fromtimestamp(
            payload['exp'], tz=timezone.utc
        )
        expires_in = int((expires_at - timezone.now()).total_seconds())
        
        # Record delegation
        bot_profile.record_delegation()
        
        # Audit log
        DelegationAuditLog.objects.create(
            bot_client_id=client_id,
            bot_name=bot_profile.display_name,
            matrix_id=matrix_id,
            requested_scopes=requested_scopes,
            user=user,
            user_email=user.email,
            status=DelegationAuditLog.Status.ISSUED,
            granted_scopes=requested_scopes,
            token_jti=payload['jti'],
            token_expires_at=expires_at,
            ip_address=ip_address
        )
        
        logger.info(
            f"Delegated token issued: bot={bot_profile.display_name}, "
            f"user={user.email}, scopes={requested_scopes}"
        )
        
        return Response({
            'access_token': token,
            'token_type': 'Bearer',
            'expires_in': expires_in,
            'scope': ' '.join(requested_scopes)
        })
    
    def _check_user_can_delegate(self, user):
        """
        Check if user can delegate to bots.
        Returns None if OK, or error message string.
        """
        if not user.is_active:
            return 'User account is inactive'
        
        if user.account_status not in ('active', 'expiring_soon'):
            return f'User account status is {user.account_status}'
        
        if hasattr(user, 'is_expired') and user.is_expired:
            return 'User access has expired'
        
        # Check if user can create documents (doctors/residents)
        from apps.core.permissions import is_doctor
        # Note: Non-doctors can still delegate read-only scopes
        # This is checked per-scope in validate_delegation_scopes
        
        return None
    
    def _log_denial(self, client_id, matrix_id, scopes, status, error,
                    ip_address, bot_name='', user=None):
        """Log a denied delegation request."""
        DelegationAuditLog.objects.create(
            bot_client_id=client_id,
            bot_name=bot_name,
            matrix_id=matrix_id,
            requested_scopes=scopes,
            user=user,
            user_email=user.email if user else '',
            status=status,
            granted_scopes=[],
            error_message=error,
            ip_address=ip_address
        )
        
        logger.warning(
            f"Delegation denied: client={client_id}, matrix={matrix_id}, "
            f"reason={error}"
        )
    
    def _get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
```

### Task 6.4: Add URL Routes

Update `apps/botauth/urls.py`:

```python
from django.urls import path
from . import views
from .api_views import DelegatedTokenView

app_name = 'botauth'

urlpatterns = [
    # Human-facing views
    path('matrix/bind/', views.MatrixBindingCreateView.as_view(), name='binding_create'),
    path('matrix/status/', views.MatrixBindingStatusView.as_view(), name='binding_status'),
    path('matrix/verify/<str:token>/', views.MatrixBindingVerifyView.as_view(), name='binding_verify'),
    path('matrix/revoke/<uuid:pk>/', views.MatrixBindingDeleteView.as_view(), name='binding_delete'),
    
    # Bot API endpoints
    path('api/delegated-token/', DelegatedTokenView.as_view(), name='delegated_token'),
]
```

### Task 6.5: Create Tests

Create `apps/botauth/tests/test_delegation.py`:

```python
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.botauth.models import MatrixUserBinding, DelegationAuditLog
from apps.botauth.bot_service import BotClientService
from apps.botauth.services import MatrixBindingService
from apps.botauth.tokens import DelegatedTokenGenerator

User = get_user_model()


class DelegatedTokenEndpointTest(TestCase):
    """Tests for the delegated token endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create doctor
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@hospital.com',
            password='testpass',
            profession_type=0,  # Medical Doctor
            is_active=True,
            account_status='active'
        )
        
        # Create Matrix binding
        binding, _ = MatrixBindingService.create_binding(
            user=self.doctor,
            matrix_id='@doctor:matrix.hospital.br'
        )
        MatrixBindingService.verify_binding(binding)
        
        # Create bot
        self.bot, self.bot_secret = BotClientService.create_bot(
            display_name='Test Bot',
            allowed_scopes=['patient:read', 'dailynote:draft']
        )
    
    def test_successful_delegation(self):
        """Test successful token delegation."""
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': self.bot_secret,
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': ['patient:read']
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.data)
        self.assertEqual(response.data['token_type'], 'Bearer')
        self.assertIn('expires_in', response.data)
        
        # Verify audit log
        log = DelegationAuditLog.objects.filter(user=self.doctor).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, 'issued')
    
    def test_invalid_bot_credentials(self):
        """Test rejection with invalid bot credentials."""
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': 'wrong_secret',
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': ['patient:read']
        }, format='json')
        
        self.assertEqual(response.status_code, 401)
    
    def test_unknown_matrix_id(self):
        """Test rejection with unknown Matrix ID."""
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': self.bot_secret,
            'matrix_id': '@unknown:matrix.hospital.br',
            'scopes': ['patient:read']
        }, format='json')
        
        self.assertEqual(response.status_code, 403)
    
    def test_inactive_user(self):
        """Test rejection when user is inactive."""
        self.doctor.is_active = False
        self.doctor.save()
        
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': self.bot_secret,
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': ['patient:read']
        }, format='json')
        
        self.assertEqual(response.status_code, 403)
        self.assertIn('inactive', response.data['error'].lower())
    
    def test_unauthorized_scope(self):
        """Test rejection when requesting unauthorized scope."""
        response = self.client.post('/auth/api/delegated-token/', {
            'client_id': self.bot.client.client_id,
            'client_secret': self.bot_secret,
            'matrix_id': '@doctor:matrix.hospital.br',
            'scopes': ['prescription:draft']  # Bot doesn't have this
        }, format='json')
        
        self.assertEqual(response.status_code, 403)
```

### Task 6.6: Run Migration

```bash
uv run python manage.py makemigrations botauth
uv run python manage.py migrate botauth
```

## Files to Create

1. `apps/botauth/tokens.py` - JWT generation/validation
2. `apps/botauth/api_views.py` - DelegatedTokenView

## Files to Modify

1. `apps/botauth/models.py` - Add DelegationAuditLog
2. `apps/botauth/urls.py` - Add API routes
3. `apps/botauth/tests/test_delegation.py` - Tests

## Acceptance Criteria

- [x] Bot can authenticate with client_id + client_secret
- [x] Endpoint looks up user via Matrix binding
- [x] User status is validated (is_active, account_status)
- [x] Scopes are validated against bot permissions and user role
- [x] JWT is issued with correct claims (sub, azp, scope, exp)
- [x] Token TTL is enforced (max 10 minutes)
- [x] All requests are audit logged
- [x] Rate limiting prevents abuse
- [x] All tests pass

## Verification Commands

```bash
# Run migrations
uv run python manage.py migrate botauth

# Run tests
uv run pytest apps/botauth/tests/test_delegation.py -v

# Test endpoint manually (requires setup)
curl -X POST http://localhost:8000/auth/api/delegated-token/ \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "bot_xxx",
    "client_secret": "xxx",
    "matrix_id": "@doctor:matrix.hospital.br",
    "scopes": ["patient:read"]
  }'
```
