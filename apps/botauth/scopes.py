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
    from apps.core.permissions.utils import is_doctor
    
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