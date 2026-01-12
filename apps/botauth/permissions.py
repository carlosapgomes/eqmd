"""
DRF Permission classes for bot authorization.
"""

from rest_framework.permissions import BasePermission
from .scopes import get_scope, is_draft_scope


class HasScope(BasePermission):
    """
    Permission class that checks for required scopes.
    
    Usage in views:
        permission_classes = [HasScope]
        required_scopes = ['patient:read']
    
    Or as a decorator:
        @permission_classes([HasScope.with_scopes('patient:read')])
    """
    
    required_scopes = []
    
    def has_permission(self, request, view):
        # Get required scopes from view or class attribute
        required = getattr(view, 'required_scopes', None) or self.required_scopes
        
        if not required:
            return True
        
        # Get scopes from request (set by DelegatedJWTAuthentication)
        request_scopes = getattr(request, 'scopes', set())
        
        if not request_scopes:
            # No scopes on request - might be session auth (human user)
            # Allow if user is authenticated via session
            if request.user.is_authenticated and not hasattr(request, 'actor'):
                return True
            return False
        
        # Check all required scopes are present
        return all(scope in request_scopes for scope in required)
    
    @classmethod
    def with_scopes(cls, *scopes):
        """Create a permission class with specific required scopes."""
        class ScopedPermission(cls):
            required_scopes = list(scopes)
        return ScopedPermission


class HasAnyScope(BasePermission):
    """
    Permission class that checks for at least one of the required scopes.
    
    Usage:
        permission_classes = [HasAnyScope]
        any_of_scopes = ['patient:read', 'exam:read']
    """
    
    any_of_scopes = []
    
    def has_permission(self, request, view):
        required = getattr(view, 'any_of_scopes', None) or self.any_of_scopes
        
        if not required:
            return True
        
        request_scopes = getattr(request, 'scopes', set())
        
        if not request_scopes:
            if request.user.is_authenticated and not hasattr(request, 'actor'):
                return True
            return False
        
        return any(scope in request_scopes for scope in required)


class IsDelegatedRequest(BasePermission):
    """
    Permission that only allows delegated (bot) requests.
    Useful for endpoints that should ONLY be accessed via delegation.
    """
    
    def has_permission(self, request, view):
        return hasattr(request, 'actor') and request.actor is not None


class IsHumanRequest(BasePermission):
    """
    Permission that only allows human (non-bot) requests.
    Use for endpoints that bots must never access.
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user.is_authenticated:
            return False
        # Must NOT have an actor (bot)
        return not hasattr(request, 'actor') or request.actor is None


class CanCreateDrafts(BasePermission):
    """
    Permission that checks if the request can create drafts.
    
    For delegated requests: checks for draft scopes
    For human requests: checks if user has permission to create the document type
    """
    
    document_type = None  # Set in view: 'dailynote', 'dischargereport', etc.
    
    def has_permission(self, request, view):
        doc_type = getattr(view, 'document_type', None) or self.document_type
        
        if not doc_type:
            return False
        
        # Delegated request
        if hasattr(request, 'actor') and request.actor:
            draft_scope = f"{doc_type}:draft"
            request_scopes = getattr(request, 'scopes', set())
            return draft_scope in request_scopes
        
        # Human request - use existing permission system
        # Doctors and residents can create all document types
        from apps.core.permissions.utils import is_doctor_or_resident
        if is_doctor_or_resident(request.user):
            return True
        
        # Other roles have restrictions based on document type
        # (implement based on existing permission rules)
        return False


class DenyBotAccess(BasePermission):
    """
    Explicitly deny all bot access to an endpoint.
    Use this for sensitive endpoints that bots must never reach.
    """
    
    message = "This endpoint is not accessible via bot delegation."
    
    def has_permission(self, request, view):
        if hasattr(request, 'actor') and request.actor:
            return False
        return request.user.is_authenticated