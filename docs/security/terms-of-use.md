# Terms of Use System

## Overview

EquipeMed implements a comprehensive terms of use acceptance system that ensures legal compliance and maintains an audit trail of user consent. The system enforces terms acceptance for all authenticated users before they can access protected content.

## Architecture

### Database Model

The terms acceptance system extends the `EqmdCustomUser` model with two fields:

```python
# apps/accounts/models.py
class EqmdCustomUser(AbstractUser):
    # ... existing fields ...
    
    # Terms acceptance for legal compliance
    terms_accepted = models.BooleanField(
        default=False,
        help_text="User has accepted the terms of use"
    )
    terms_accepted_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the user accepted the terms"
    )
```

**Key Features:**

- `terms_accepted`: Boolean flag tracking acceptance status
- `terms_accepted_at`: Timestamp of when terms were accepted
- Both fields are included in audit history via `simple-history`
- Default: `terms_accepted=False` for all new users

### Middleware Enforcement

The `TermsAcceptanceRequiredMiddleware` enforces terms acceptance:

```python
# apps/core/middleware.py
class TermsAcceptanceRequiredMiddleware:
    """
    Middleware that enforces terms acceptance for authenticated users.
    Users must accept terms before accessing any protected content.
    """
```

**Enforcement Logic:**

1. Skip unauthenticated users
2. Allow users who have already accepted terms
3. Allow access to terms-related URLs and logout
4. Respect password change priority (password change comes first)
5. Block all other access until terms are accepted
6. Log all enforcement actions for security audit

**Allowed URLs without terms acceptance:**

- `/accept-terms/` - Terms acceptance page
- `/terms-of-use/` - Full terms document
- `/account/logout/` - User logout
- `/admin/logout/` - Admin logout
- Password change URLs (if required)
- Static and media files

## User Flow

### Authentication Sequence

1. **User Login** → **Password Change (if required)** → **Terms Acceptance** → **Dashboard**

### Terms Acceptance Process

1. User encounters terms acceptance page (`/accept-terms/`)
2. Page shows terms summary and link to full terms
3. User must check mandatory checkbox
4. User clicks "Aceitar e Continuar"
5. System records acceptance with timestamp and IP
6. User redirected to dashboard or intended destination

### Navigation Flow

**From Accept Terms Page:**

- "Ler Termos Completos" → `/terms-of-use/` (same tab)
- "Voltar" on terms page → Returns to `/accept-terms/`

**Direct Access:**

- Direct navigation to `/terms-of-use/` → "Voltar" goes to login page

## URL Structure

| URL | View | Purpose |
|-----|------|---------|
| `/terms-of-use/` | `terms_of_use` | Full terms document (public access) |
| `/accept-terms/` | `accept_terms` | Interactive terms acceptance (login required) |

## Templates

### Terms of Use (`templates/core/terms_of_use.html`)

**Features:**

- Complete legal document
- Medical-themed professional styling
- Dual navigation (top and bottom)
- Smart "Voltar" button with server-side URL detection
- Hospital-independent language ("EquipeMed" as service provider)

**Content Structure:**

1. Service positioning as "Sistema de Informação Clínica"
2. Legal boundaries and responsibilities
3. Confidentiality and LGPD compliance
4. Professional usage guidelines
5. Monitoring and audit notices
6. Support and contact information

### Terms Acceptance (`templates/core/accept_terms.html`)

**Features:**

- Interactive acceptance interface
- Terms summary with key points
- Mandatory checkbox validation
- Link to full terms document
- Professional medical styling
- Dual-action buttons (Accept/Cancel)

**Validation:**

- JavaScript checkbox validation
- Server-side POST processing
- CSRF protection
- Required field enforcement

## Legal Compliance

### Service Positioning

**Independent Service Provider:**

- EquipeMed positioned as independent "Sistema de Informação Clínica"
- Clear boundaries: not hospital management software
- Supplementary tool, doesn't replace official hospital systems
- Respect for institutional authority

**Legal Language:**

- LGPD compliance references
- Professional responsibility emphasis
- Medical ethics integration
- Clear consequences for misuse

### Audit Trail

**Database Tracking:**

- Acceptance timestamp (`terms_accepted_at`)
- Boolean status (`terms_accepted`)
- Historical changes via `simple-history`
- User identification and tracking

**Security Logging:**

```python
logger.info(
    f'Terms accepted by user {request.user.username} '
    f'from IP {get_client_ip(request)} '
    f'at {timezone.now()}'
)
```

**Audit Information Captured:**

- Username and user ID
- IP address (via `get_client_ip`)
- Exact timestamp
- Change reason in history
- All middleware enforcement events

## Configuration

### Middleware Setup

Add to `settings.py`:

```python
MIDDLEWARE = [
    # ... other middleware ...
    "apps.core.middleware.PasswordChangeRequiredMiddleware",  # Must come before terms
    "apps.core.middleware.TermsAcceptanceRequiredMiddleware",
    # ... remaining middleware ...
]
```

**Order Requirements:**

- Must come after authentication middleware
- Must come after password change middleware
- Must come before final request processing

### Migration

The feature includes migration `0003_add_terms_acceptance.py`:

```bash
# Apply terms acceptance fields
uv run python manage.py migrate accounts
```

## Security Features

### Enforcement Security

1. **Comprehensive Blocking**: All protected content blocked until acceptance
2. **IP Logging**: All access attempts logged with IP addresses
3. **Change Tracking**: Complete audit history of acceptance status
4. **Middleware Priority**: Respects authentication and password change flow

### Attack Prevention

1. **CSRF Protection**: All forms include CSRF tokens
2. **URL Validation**: Only allowed URLs accessible without terms
3. **Session Security**: Integrates with existing session management
4. **Logout Protection**: Users can always logout safely

## Testing

### Manual Testing Scenarios

1. **New User Flow**:
   - Create new user → Login → Password change → Terms acceptance → Dashboard

2. **Existing User Flow**:
   - Existing user without terms → Login → Terms acceptance → Dashboard

3. **Navigation Testing**:
   - Accept terms page → Terms page → Back to acceptance
   - Direct terms access → Back to login

4. **Security Testing**:
   - Attempt to access dashboard without terms → Redirected to acceptance
   - Check audit logs for all actions

### Database Verification

```python
# Check terms acceptance status
from apps.accounts.models import EqmdCustomUser
user = EqmdCustomUser.objects.get(username='test_user')
print(f'Terms accepted: {user.terms_accepted}')
print(f'Accepted at: {user.terms_accepted_at}')

# Check history
for record in user.history.all():
    print(f'{record.history_date}: {record.history_change_reason}')
```

## Maintenance

### Updating Terms

1. Update terms content in `templates/core/terms_of_use.html`
2. Update `last_updated` date in both view functions:
   - `terms_of_use()` in `apps/core/views.py`
   - `accept_terms()` in `apps/core/views.py`
3. Consider notifying existing users of changes
4. Optionally reset `terms_accepted` for significant changes

### Monitoring

**Key Metrics to Monitor:**

- Terms acceptance rate
- Users stuck at terms page
- Middleware enforcement frequency
- Security log alerts

**Log Locations:**

- Application logs: Terms acceptance events
- Security logs: Enforcement actions
- Database history: Acceptance tracking

## Integration Points

### Existing Systems

**Authentication Integration:**

- Works with `allauth` authentication system
- Integrates with password change requirements
- Respects existing permission system

**Audit Integration:**

- Uses existing `simple-history` infrastructure
- Leverages existing IP tracking system
- Integrates with security logging framework

**UI Integration:**

- Consistent with medical theme styling
- Uses existing Bootstrap components
- Follows established template patterns

## Future Enhancements

### Potential Improvements

1. **Terms Versioning**: Track different versions of terms
2. **Partial Acceptance**: Allow acceptance of specific term sections
3. **Periodic Re-acceptance**: Require re-acceptance after time periods
4. **Multi-language Support**: Support for terms in multiple languages
5. **Digital Signature**: Enhanced legal validation with digital signatures

### API Extensions

Future API endpoints could include:

- `GET /api/terms/status/` - Check user's terms acceptance status
- `POST /api/terms/accept/` - API-based terms acceptance
- `GET /api/terms/history/` - Terms acceptance history for user

## Troubleshooting

### Common Issues

**Issue: Users stuck in redirect loop**

- Check middleware order in settings
- Verify URL patterns are correct
- Check for circular redirects in views

**Issue: Terms not being enforced**

- Verify middleware is enabled
- Check user authentication status
- Confirm `terms_accepted` field exists

**Issue: Navigation buttons not working**

- Check URL reversals in templates
- Verify view context includes `return_url`
- Test JavaScript console for errors

**Issue: Acceptance not recording**

- Check database field permissions
- Verify CSRF tokens in forms
- Check form validation logic

### Debug Commands

```bash
# Check middleware configuration
uv run python manage.py check

# Verify URL patterns
uv run python manage.py show_urls | grep terms

# Test user terms status
uv run python manage.py shell -c "
from apps.accounts.models import EqmdCustomUser
for user in EqmdCustomUser.objects.all()[:5]:
    print(f'{user.username}: {user.terms_accepted}')
"
```

## Summary

The EquipeMed terms of use system provides comprehensive legal compliance with:

- **Database audit trail** for legal documentation
- **Middleware enforcement** ensuring universal coverage  
- **Professional UI** appropriate for medical contexts
- **Service-appropriate positioning** as independent clinical information system
- **Security integration** with existing audit and logging systems
- **Flexible navigation** supporting various user flows

This implementation satisfies legal requirements while maintaining excellent user experience and system security.
