# Phase 07 – DRF Authentication Backend

## Goal

Create a custom DRF authentication backend that validates delegated JWT tokens and populates the request with user, actor (bot), and scopes.

## Prerequisites

- Phase 06 completed (Delegated token endpoint)
- All existing tests passing

## Tasks

### Task 7.1: Create DelegatedJWTAuthentication

Create `apps/botauth/authentication.py`:

```python
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
```

### Task 7.2: Configure DRF

Update `config/settings.py`:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'apps.botauth.authentication.DelegatedJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

### Task 7.3: Create Middleware

Create `apps/botauth/middleware.py`:

```python
import logging
import time

logger = logging.getLogger('security.delegation')

class DelegatedRequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        
        if getattr(request, 'is_delegated', False):
            duration = time.time() - start_time
            logger.info(
                f"DELEGATED: {request.method} {request.path} "
                f"user={request.user.email} bot={request.actor_name} "
                f"status={response.status_code} duration={duration:.3f}s"
            )
        
        return response
```

## Acceptance Criteria

- [ ] Valid tokens populate request.user with physician
- [ ] Valid tokens populate request.actor with bot client_id
- [ ] Valid tokens populate request.scopes
- [ ] Valid tokens set request.is_delegated = True
- [ ] Expired tokens return 401
- [ ] Tokens for inactive users rejected
- [ ] Tokens for suspended bots rejected
- [ ] Session auth still works for humans
- [ ] All tests pass

## Verification Commands

```bash
uv run pytest apps/botauth/tests/test_authentication.py -v
```
