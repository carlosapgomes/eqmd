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
from .audit import AuditLogger, AuditEventType
from .killswitch import KillSwitchService

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
                ip_address=ip_address,
                request=request
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
                ip_address=ip_address,
                request=request
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
                ip_address=ip_address,
                request=request
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
                ip_address=ip_address,
                request=request
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
                ip_address=ip_address,
                request=request
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
        from datetime import datetime, timezone as dt_timezone
        expires_at = datetime.fromtimestamp(
            payload['exp'], tz=dt_timezone.utc
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
        
        # New centralized audit logging
        AuditLogger.log(
            event_type=AuditEventType.TOKEN_ISSUED,
            request=request,
            user=user,
            bot=bot_profile,
            details={
                'scopes': requested_scopes,
                'expires_in': expires_in,
                'matrix_id': matrix_id
            }
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
        from apps.core.permissions.utils import is_doctor
        # Note: Non-doctors can still delegate read-only scopes
        # This is checked per-scope in validate_delegation_scopes
        
        return None
    
    def _log_denial(self, client_id, matrix_id, scopes, status, error,
                    ip_address, bot_name='', user=None, request=None):
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
        
        # New centralized audit logging
        AuditLogger.log(
            event_type=AuditEventType.DELEGATION_DENIED,
            request=request,
            user=user,
            details={
                'client_id': client_id,
                'bot_name': bot_name,
                'matrix_id': matrix_id,
                'scopes': scopes,
                'status': status,
                'error': error
            },
            success=False,
            error=error
        )
    
    def _get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')