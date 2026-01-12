# Permission Decorator Bot Behavior Analysis

## Date: 2025-01-12

## Current Permission Decorators

### @patient_access_required
**Location**: `apps/core/permissions/decorators.py:22-50`

**Current Behavior**: 
- Checks if user can access patient via `can_access_patient(request.user, patient)`
- Uses `@login_required` first, then custom patient access logic
- Returns 403 Forbidden if access denied

**Bot Behavior Requirements**:
- **ALLOW** - Bots should be able to access patient data with proper scope
- **Requires**: `patient:read` scope
- **Implementation**: Add bot detection and scope checking after patient access check
- **Special Consideration**: Universal access model means this should generally allow bots with proper delegation

**Future Implementation**: 
```python
# Enhanced decorator logic for bots
if is_bot_request(request):
    if not has_scope(request, 'patient:read'):
        return HttpResponseForbidden("Scope required: patient:read")
    # Additional: Verify bot is acting on behalf of physician with access
```

### @doctor_required
**Location**: `apps/core/permissions/decorators.py:53-65`

**Current Behavior**:
- Checks if user is doctor via `is_doctor(request.user)`
- Returns 403 for non-doctors
- Uses `@login_required` as base

**Bot Behavior Requirements**:
- **DENY** - Bots are never doctors and should never pass this check
- **Rationale**: Medical decisions require human physician judgment
- **Implementation**: Explicit bot rejection before doctor check
- **Special Consideration**: This decorator marks functions that require clinical judgment

**Future Implementation**:
```python
# Enhanced decorator logic for bots
if is_bot_request(request):
    return HttpResponseForbidden("Clinical decisions require human physicians")
```

### @can_edit_event_required
**Location**: `apps/core/permissions/decorators.py:68-96`

**Current Behavior**:
- Checks if user can edit event via `can_edit_event(request.user, event)`
- Enforces 24-hour edit window
- Checks event ownership and permissions
- Returns 403 if edit not allowed

**Bot Behavior Requirements**:
- **CONDITIONAL** - Bots can only edit their own draft events
- **Requires**: Draft scope (`dailynote:draft`, `dischargereport:draft`, etc.)
- **Implementation**: Check if event is draft AND created by this bot
- **Special Consideration**: Time-based restrictions still apply to bot drafts
- **Forbidden**: Cannot edit definitive events (is_draft=False)

**Future Implementation**:
```python
# Enhanced decorator logic for bots
if is_bot_request(request):
    if not event.is_draft:
        return HttpResponseForbidden("Bots cannot edit definitive events")
    if event.draft_created_by_bot != get_bot_client_id(request):
        return HttpResponseForbidden("Bots can only edit their own drafts")
    if not has_scope(request, get_draft_scope_for_event(event)):
        return HttpResponseForbidden("Draft scope required")
```

### @patient_data_change_required
**Location**: `apps/core/permissions/decorators.py:101-129`

**Current Behavior**:
- Checks if user can change patient personal data
- Uses `can_change_patient_personal_data(request.user, patient)`
- More restrictive than general patient access
- Returns 403 if personal data change not allowed

**Bot Behavior Requirements**:
- **DENY** - Bots must never change patient personal data
- **Rationale**: Patient identity changes require verification and human oversight
- **Implementation**: Explicit bot rejection before permission check
- **Special Consideration**: This is a critical security boundary

**Future Implementation**:
```python
# Enhanced decorator logic for bots
if is_bot_request(request):
    log_security_event("bot_attempted_patient_data_change", request)
    return HttpResponseForbidden("Bots cannot modify patient personal data")
```

### @can_delete_event_required
**Location**: `apps/core/permissions/decorators.py:132-160`

**Current Behavior**:
- Checks if user can delete event via `can_delete_event(request.user, event)`
- Enforces ownership and time-based restrictions
- Returns 403 if deletion not allowed

**Bot Behavior Requirements**:
- **DENY** - Bots must never delete events
- **Rationale**: Deletion destroys audit trail and clinical information
- **Implementation**: Explicit bot rejection before permission check
- **Special Consideration**: Audit trail integrity is critical

**Future Implementation**:
```python
# Enhanced decorator logic for bots
if is_bot_request(request):
    log_security_event("bot_attempted_event_deletion", request)
    return HttpResponseForbidden("Bots cannot delete clinical events")
```

## Cross-Cutting Bot Behavior Patterns

### Bot Detection Requirements
All decorators need a consistent way to detect bot requests:
```python
def is_bot_request(request):
    """Check if request is from a delegated bot"""
    return hasattr(request, 'actor') and hasattr(request, 'scopes')
```

### Scope Checking Requirements  
Consistent scope validation across decorators:
```python
def has_scope(request, required_scope):
    """Check if bot request has required scope"""
    if not is_bot_request(request):
        return True  # Humans don't need scope checks
    return required_scope in request.scopes
```

### Bot Identity Requirements
Extract bot identity from delegated token:
```python
def get_bot_client_id(request):
    """Get bot client_id from delegated request"""
    return request.actor if is_bot_request(request) else None
```

### Security Logging Requirements
All bot permission denials should be logged:
```python
def log_bot_denial(request, decorator_name, reason):
    """Log bot access denial for security monitoring"""
    security_logger.warning(
        f"Bot access denied: {decorator_name} | "
        f"Bot: {get_bot_client_id(request)} | "
        f"Physician: {request.user.email} | "
        f"Reason: {reason}"
    )
```

## Decorator Behavior Matrix

| Decorator | Bot Access | Scope Required | Time Restrictions | Audit Requirements |
|-----------|------------|----------------|-------------------|-------------------|
| `@patient_access_required` | ALLOW | `patient:read` | None | Log all patient data access |
| `@doctor_required` | DENY | N/A | N/A | Log all access attempts |
| `@can_edit_event_required` | DRAFT ONLY | Event-specific draft scope | 24h window applies | Log draft edits |
| `@patient_data_change_required` | DENY | N/A | N/A | Log as security event |
| `@can_delete_event_required` | DENY | N/A | N/A | Log as security event |

## Implementation Priority

### Phase 1 (Critical - Implement First)
1. **Bot detection infrastructure** - Required for all decorator enhancements
2. **`@doctor_required` enhancement** - Clinical decision boundary
3. **`@patient_data_change_required` enhancement** - Patient identity protection

### Phase 2 (High Priority)
4. **`@can_delete_event_required` enhancement** - Audit trail protection
5. **`@patient_access_required` enhancement** - Safe bot access pattern

### Phase 3 (Complex)
6. **`@can_edit_event_required` enhancement** - Complex draft logic requires Event model changes

## Testing Requirements

Each enhanced decorator must have tests for:
1. Normal human access continues to work
2. Bot access without proper delegation is denied
3. Bot access with proper delegation and scope is allowed (where applicable)
4. Security logging occurs for all bot access attempts
5. Error messages are appropriate for bot vs human access

## Compatibility Notes

- All existing decorator functionality must be preserved
- Bot checks should be additive, not replace existing logic
- Performance impact should be minimal for human users
- Decorator order matters: bot checks before expensive database operations