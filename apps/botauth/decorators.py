"""
Decorators for scope-based authorization.
"""

from functools import wraps
from django.http import JsonResponse
from rest_framework import status


def require_scopes(*scopes):
    """
    Decorator that requires specific scopes for a view.
    
    Usage:
        @require_scopes('patient:read', 'dailynote:draft')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get scopes from request
            request_scopes = getattr(request, 'scopes', set())
            
            # If no scopes but user is authenticated without actor, allow
            # (human user via session)
            if not request_scopes:
                if request.user.is_authenticated and not hasattr(request, 'actor'):
                    return view_func(request, *args, **kwargs)
                return JsonResponse(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check all required scopes
            missing = set(scopes) - request_scopes
            if missing:
                return JsonResponse(
                    {
                        'error': 'Insufficient scopes',
                        'required': list(scopes),
                        'missing': list(missing)
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def deny_bot_access(view_func):
    """
    Decorator that denies access to bots.
    
    Usage:
        @deny_bot_access
        def sensitive_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if hasattr(request, 'actor') and request.actor:
            return JsonResponse(
                {'error': 'This endpoint is not accessible via bot delegation'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def bot_only(view_func):
    """
    Decorator that only allows bot access.
    
    Usage:
        @bot_only
        def bot_specific_endpoint(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'actor') or not request.actor:
            return JsonResponse(
                {'error': 'This endpoint requires bot delegation'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper