"""
JWT token generation and validation for delegated bot authentication.
"""

import jwt
import uuid
import logging
from datetime import datetime, timedelta, timezone
from django.conf import settings

logger = logging.getLogger('security.delegation.tokens')


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
        
        logger.info(
            f"Generated delegated token: user={user.email}, "
            f"bot={bot_profile.display_name}, scopes={scopes}, ttl={ttl_seconds}s"
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
        try:
            payload = jwt.decode(
                token,
                settings.DELEGATED_TOKEN_SECRET,
                algorithms=[settings.DELEGATED_TOKEN_ALGORITHM],
                audience=settings.DELEGATED_TOKEN_AUDIENCE,
                issuer=settings.DELEGATED_TOKEN_ISSUER
            )
            
            logger.debug(f"Decoded delegated token: jti={payload.get('jti')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Attempted to decode expired delegated token")
            raise
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid delegated token: {str(e)}")
            raise
    
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
    
    @classmethod
    def extract_bot_client_id(cls, payload):
        """Extract bot client ID from token payload."""
        return payload.get('azp', '')
    
    @classmethod
    def validate_token_for_user(cls, token, user):
        """
        Validate that a token belongs to the given user.
        
        Returns:
            bool: True if token is valid for this user
        """
        try:
            payload = cls.decode_token(token)
            token_user_id = cls.extract_user_id(payload)
            return str(token_user_id) == str(user.id)
        except jwt.InvalidTokenError:
            return False