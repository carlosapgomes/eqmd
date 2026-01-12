# Phase 05 – Scope System

## Goal

Define and implement the authorization scope system that controls what actions bots can perform. This includes the scope registry, validation utilities, and DRF permission classes.

## Prerequisites

- Phase 04 completed (Bot client registration)
- All existing tests passing

## Context

Scopes are the authorization backbone for bot delegation. They define:
1. What resources a bot can access
2. What operations a bot can perform
3. Granular control per bot and per delegation request

## Tasks

### Task 5.1: Create Scope Registry

Create `apps/botauth/scopes.py`:

```python
"""
Scope definitions and registry for EQMD bot authorization.

Scopes follow the pattern: resource:action
- resource: The type of data or entity
- action: The permitted operation (read, draft, generate)

IMPORTANT: Bots can only create drafts, never definitive documents.
"""

from dataclasses import dataclass
from typing import Dict, List, Set
from enum import Enum


class ScopeAction(Enum):
    """Possible actions in scopes."""
    READ = 'read'
    DRAFT = 'draft'
    GENERATE = 'generate'
    WRITE = 'write'      # FORBIDDEN for bots
    FINALIZE = 'finalize'  # FORBIDDEN for bots
    SIGN = 'sign'        # FORBIDDEN for bots


@dataclass
class ScopeDefinition:
    """Definition of a single scope."""
    name: str
    description: str
    resource: str
    action: ScopeAction
    allowed_for_bots: bool = True
    requires_doctor: bool = False  # Only doctors can delegate this scope


# =============================================================================
# SCOPE REGISTRY
# =============================================================================

SCOPE_DEFINITIONS: Dict[str, ScopeDefinition] = {
    # --- READ SCOPES (allowed) ---
    'patient:read': ScopeDefinition(
        name='patient:read',
        description='Read patient demographics, status, and basic information',
        resource='patient',
        action=ScopeAction.READ,
        allowed_for_bots=True
    ),
    'exam:read': ScopeDefinition(
        name='exam:read',
        description='Read exam results and requests',
        resource='exam',
        action=ScopeAction.READ,
        allowed_for_bots=True
    ),
    'dailynote:read': ScopeDefinition(
        name='dailynote:read',
        description='Read daily evolution notes',
        resource='dailynote',
        action=ScopeAction.READ,
        allowed_for_bots=True
    ),
    'dischargereport:read': ScopeDefinition(
        name='dischargereport:read',
        description='Read discharge reports',
        resource='dischargereport',
        action=ScopeAction.READ,
        allowed_for_bots=True
    ),
    'prescription:read': ScopeDefinition(
        name='prescription:read',
        description='Read prescriptions',
        resource='prescription',
        action=ScopeAction.READ,
        allowed_for_bots=True
    ),
    
    # --- DRAFT SCOPES (allowed, create drafts only) ---
    'dailynote:draft': ScopeDefinition(
        name='dailynote:draft',
        description='Create daily note drafts',
        resource='dailynote',
        action=ScopeAction.DRAFT,
        allowed_for_bots=True,
        requires_doctor=True  # Only doctors can delegate note creation
    ),
    'dischargereport:draft': ScopeDefinition(
        name='dischargereport:draft',
        description='Create discharge report drafts',
        resource='dischargereport',
        action=ScopeAction.DRAFT,
        allowed_for_bots=True,
        requires_doctor=True
    ),
    'prescription:draft': ScopeDefinition(
        name='prescription:draft',
        description='Create prescription drafts',
        resource='prescription',
        action=ScopeAction.DRAFT,
        allowed_for_bots=True,
        requires_doctor=True
    ),
    
    # --- GENERATE SCOPES (allowed, derive data from existing) ---
    'summary:generate': ScopeDefinition(
        name='summary:generate',
        description='Generate summaries from existing patient data',
        resource='summary',
        action=ScopeAction.GENERATE,
        allowed_for_bots=True
    ),
    
    # --- FORBIDDEN SCOPES (never issued to bots) ---
    'patient:write': ScopeDefinition(
        name='patient:write',
        description='Modify patient data',
        resource='patient',
        action=ScopeAction.WRITE,
        allowed_for_bots=False
    ),
    'note:finalize': ScopeDefinition(
        name='note:finalize',
        description='Create definitive clinical notes',
        resource='note',
        action=ScopeAction.FINALIZE,
        allowed_for_bots=False
    ),
    'prescription:sign': ScopeDefinition(
        name='prescription:sign',
        description='Sign prescriptions',
        resource='prescription',
        action=ScopeAction.SIGN,
        allowed_for_bots=False
    ),
    'discharge:finalize': ScopeDefinition(
        name='discharge:finalize',
        description='Finalize discharge reports',
        resource='discharge',
        action=ScopeAction.FINALIZE,
        allowed_for_bots=False
    ),
}


# =============================================================================
# SCOPE UTILITIES
# =============================================================================

def get_scope(name: str) -> ScopeDefinition:
    """Get a scope definition by name."""
    if name not in SCOPE_DEFINITIONS:
        raise ValueError(f"Unknown scope: {name}")
    return SCOPE_DEFINITIONS[name]


def get_allowed_bot_scopes() -> List[str]:
    """Get all scopes that can be assigned to bots."""
    return [
        name for name, defn in SCOPE_DEFINITIONS.items()
        if defn.allowed_for_bots
    ]


def get_forbidden_bot_scopes() -> List[str]:
    """Get all scopes that must never be assigned to bots."""
    return [
        name for name, defn in SCOPE_DEFINITIONS.items()
        if not defn.allowed_for_bots
    ]


def get_doctor_only_scopes() -> List[str]:
    """Get scopes that only doctors can delegate."""
    return [
        name for name, defn in SCOPE_DEFINITIONS.items()
        if defn.requires_doctor
    ]


def is_scope_allowed_for_bots(scope: str) -> bool:
    """Check if a scope can be assigned to bots."""
    if scope not in SCOPE_DEFINITIONS:
        return False
    return SCOPE_DEFINITIONS[scope].allowed_for_bots


def is_draft_scope(scope: str) -> bool:
    """Check if a scope is for creating drafts."""
    if scope not in SCOPE_DEFINITIONS:
        return False
    return SCOPE_DEFINITIONS[scope].action == ScopeAction.DRAFT


def parse_scope(scope: str) -> tuple:
    """Parse a scope into (resource, action)."""
    if ':' not in scope:
        raise ValueError(f"Invalid scope format: {scope}")
    parts = scope.split(':', 1)
    return parts[0], parts[1]


def validate_scopes(scopes: List[str], for_bot: bool = True) -> tuple:
    """
    Validate a list of scopes.
    
    Returns (valid, errors) where:
    - valid: bool indicating if all scopes are valid
    - errors: list of error messages
    """
    errors = []
    
    for scope in scopes:
        if scope not in SCOPE_DEFINITIONS:
            errors.append(f"Unknown scope: {scope}")
            continue
        
        if for_bot and not SCOPE_DEFINITIONS[scope].allowed_for_bots:
            errors.append(f"Scope not allowed for bots: {scope}")
    
    return len(errors) == 0, errors


def validate_delegation_scopes(scopes: List[str], user, bot_profile) -> tuple:
    """
    Validate scopes for a delegation request.
    
    Checks:
    1. All scopes are known
    2. All scopes are allowed for bots
    3. Bot is allowed to request these scopes
    4. User can delegate these scopes (e.g., doctor-only scopes)
    
    Returns (valid, errors)
    """
    from apps.core.permissions import is_doctor
    
    errors = []
    
    for scope in scopes:
        # Check scope exists
        if scope not in SCOPE_DEFINITIONS:
            errors.append(f"Unknown scope: {scope}")
            continue
        
        defn = SCOPE_DEFINITIONS[scope]
        
        # Check scope allowed for bots
        if not defn.allowed_for_bots:
            errors.append(f"Scope not allowed for bots: {scope}")
            continue
        
        # Check bot is allowed this scope
        if not bot_profile.can_request_scope(scope):
            errors.append(f"Bot not authorized for scope: {scope}")
            continue
        
        # Check user can delegate this scope
        if defn.requires_doctor and not is_doctor(user):
            errors.append(f"Only doctors can delegate scope: {scope}")
            continue
    
    return len(errors) == 0, errors


# =============================================================================
# SCOPE SETS (for convenience)
# =============================================================================

# Scopes for a bot that creates daily note drafts
DAILYNOTE_BOT_SCOPES = [
    'patient:read',
    'dailynote:read',
    'dailynote:draft',
    'summary:generate',
]

# Scopes for a bot that creates discharge report drafts
DISCHARGE_BOT_SCOPES = [
    'patient:read',
    'dailynote:read',
    'dischargereport:read',
    'dischargereport:draft',
    'summary:generate',
]

# Scopes for a bot that creates prescription drafts
PRESCRIPTION_BOT_SCOPES = [
    'patient:read',
    'prescription:read',
    'prescription:draft',
]

# Scopes for a read-only bot (summaries, lookups)
READONLY_BOT_SCOPES = [
    'patient:read',
    'exam:read',
    'dailynote:read',
    'summary:generate',
]
```

### Task 5.2: Create DRF Permission Classes

Create `apps/botauth/permissions.py`:

```python
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
        from apps.core.permissions import is_doctor
        if is_doctor(request.user):
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
```

### Task 5.3: Create Scope Checking Decorators

Create `apps/botauth/decorators.py`:

```python
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
```

### Task 5.4: Create Tests for Scope System

Create `apps/botauth/tests/test_scopes.py`:

```python
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
```

### Task 5.5: Update Bot Service to Use Scope Registry

Update `apps/botauth/bot_service.py` to import from scopes module:

```python
# Replace the scope constants at the top of bot_service.py with:

from .scopes import get_allowed_bot_scopes, get_forbidden_bot_scopes

# Use these functions instead of hardcoded lists
ALLOWED_BOT_SCOPES = get_allowed_bot_scopes()
FORBIDDEN_BOT_SCOPES = get_forbidden_bot_scopes()
```

## Files to Create

1. `apps/botauth/scopes.py` - Scope registry and utilities
2. `apps/botauth/permissions.py` - DRF permission classes
3. `apps/botauth/decorators.py` - Scope checking decorators
4. `apps/botauth/tests/test_scopes.py` - Tests

## Files to Modify

1. `apps/botauth/bot_service.py` - Import from scopes module

## Acceptance Criteria

- [x] Scope registry defines all allowed and forbidden scopes
- [x] `get_scope()` returns scope definitions correctly
- [x] `validate_scopes()` correctly identifies invalid/forbidden scopes
- [x] `validate_delegation_scopes()` checks bot permissions and user role
- [x] `HasScope` permission class works for DRF views
- [x] `DenyBotAccess` permission blocks bot requests
- [x] Decorators (`@require_scopes`, `@deny_bot_access`) work correctly
- [x] All tests pass

## Phase Status: ✅ COMPLETED

All acceptance criteria have been met. Phase 05 implementation is complete and verified.

## Verification Commands

```bash
# Run scope tests
uv run pytest apps/botauth/tests/test_scopes.py -v

# Verify scope registry
uv run python manage.py shell -c "
from apps.botauth.scopes import get_allowed_bot_scopes, get_forbidden_bot_scopes
print('Allowed:', get_allowed_bot_scopes())
print('Forbidden:', get_forbidden_bot_scopes())
"

# Run all botauth tests
uv run pytest apps/botauth/tests/ -v
```

## Notes

- Draft scopes (`*:draft`) require doctor role to delegate
- Read scopes can be delegated by any authorized user
- The scope system is the foundation for Phase 06 (Delegated Token Endpoint)
