"""
DRF Authentication backend for delegated JWT tokens.
"""

import logging
import jwt
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .tokens import DelegatedTokenGenerator
from .models import BotClientProfile

logger = logging.getLogger('security.delegation')
User = get_user_model()


class DelegatedJWTAuthentication(BaseAuthentication):
    """
    DRF Authentication backend for delegated bot tokens.
    
    After authentication:
    - request.user = the physician who delegated
    - request.actor = the bot client_id
    - request.scopes = set of granted scopes
    - request.is_delegated = True
    """
    
    keyword = 'Bearer'
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith(f'{self.keyword} '):
            return None
        
        token = auth_header[len(self.keyword) + 1:]
        
        try:
            payload = DelegatedTokenGenerator.decode_token(token)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailed('Invalid token')
        
        user_id = DelegatedTokenGenerator.extract_user_id(payload)
        if not user_id:
            raise AuthenticationFailed('Token missing user identifier')
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')
        
        if not user.is_active:
            raise AuthenticationFailed('User account is inactive')
        
        bot_client_id = payload.get('azp')
        bot_profile = BotClientProfile.get_by_client_id(bot_client_id)
        if not bot_profile or not bot_profile.is_active:
            raise AuthenticationFailed('Bot is no longer active')
        
        scopes = DelegatedTokenGenerator.extract_scopes(payload)
        
        request.actor = bot_client_id
        request.actor_name = bot_profile.display_name
        request.scopes = scopes
        request.is_delegated = True
        request.delegation_jti = payload.get('jti')
        
        return (user, DelegatedAuthInfo(payload, bot_client_id, bot_profile.display_name, scopes))
    
    def authenticate_header(self, request):
        return f'{self.keyword} realm="eqmd-api"'


class DelegatedAuthInfo:
    def __init__(self, token_payload, bot_client_id, bot_name, scopes):
        self.token_payload = token_payload
        self.bot_client_id = bot_client_id
        self.bot_name = bot_name
        self.scopes = scopes
    
    @property
    def is_delegated(self):
        return True