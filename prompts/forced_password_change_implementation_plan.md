# Forced Password Change Implementation Plan - Option 2

## Overview

This plan implements a forced password change system that integrates seamlessly with Django allauth. When admins create users with temporary passwords, users must change their password after email confirmation before accessing the application.

## Architecture

### Flow Diagram

```
Admin creates user + temp password →
User receives login credentials →
User logs in with temp password →
User confirms email via allauth →
Middleware detects password_change_required=True →
User redirected to password change form →
User sets new password →
Flag cleared, user continues normally
```

### Key Components

- **Model Field**: `password_change_required` boolean flag
- **Middleware**: Intercepts requests and enforces password change
- **View**: Custom password change view that clears the flag
- **Admin Integration**: Sets flag when admin creates users

## Implementation Steps

### Phase 1: Database Schema Changes

#### Step 1.1: Add Model Field

**File**: `apps/accounts/models.py`

```python
class EqmdCustomUser(AbstractUser):
    # ... existing fields ...

    # Security: Force password change for admin-created users
    password_change_required = models.BooleanField(
        default=True,  # New users must change password
        help_text="User must change password before accessing the system"
    )
```

**Reasoning**:

- `default=True` ensures all new users must change password
- Existing users get `False` via migration
- Clear help text for admin interface

#### Step 1.2: Create Migration

**Command**:

```bash
uv run python manage.py makemigrations accounts --name add_password_change_required
```

**Migration Content**:

```python
# Generated migration will include:
operations = [
    migrations.AddField(
        model_name='eqmdcustomuser',
        name='password_change_required',
        field=models.BooleanField(default=True, help_text='User must change password before accessing the system'),
    ),
    # Data migration to set existing users to False
    migrations.RunPython(
        set_existing_users_password_change_not_required,
        reverse_code=migrations.RunPython.noop,
    ),
]
```

#### Step 1.3: Apply Migration

**Command**:

```bash
uv run python manage.py migrate accounts
```

### Phase 2: Middleware Implementation

#### Step 2.1: Create Password Change Middleware

**File**: `apps/core/middleware.py` (add to existing file)

```python
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext as _

class PasswordChangeRequiredMiddleware:
    """
    Middleware that enforces password change for users with password_change_required=True.

    Integrates with existing allauth flow and hospital security requirements.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip middleware for unauthenticated users
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Skip middleware if user doesn't need password change
        if not getattr(request.user, 'password_change_required', False):
            return self.get_response(request)

        # Allow access to password change related URLs
        password_change_urls = [
            reverse('password_change_required'),
            reverse('account_change_password'),
            reverse('account_logout'),
            '/admin/logout/',  # Allow admin logout
        ]

        # Allow static files and media files
        if (request.path_info.startswith('/static/') or
            request.path_info.startswith('/media/') or
            request.path_info in password_change_urls):
            return self.get_response(request)

        # Redirect to password change page
        messages.warning(
            request,
            _('Por segurança, você deve alterar sua senha antes de continuar.')
        )
        return redirect('password_change_required')
```

**Key Features**:

- Only affects authenticated users with `password_change_required=True`
- Allows access to password change URLs and logout
- Allows static/media files for styling
- Portuguese messaging for medical staff
- Clear security messaging

#### Step 2.2: Register Middleware

**File**: `config/settings.py`

Add to `MIDDLEWARE` list:

```python
MIDDLEWARE = [
    # ... existing middleware ...
    'apps.core.middleware.PasswordChangeRequiredMiddleware',  # Add after authentication
    # ... rest of middleware ...
]
```

**Position**: After `AuthenticationMiddleware`, before `MessageMiddleware`

### Phase 3: Views and URLs

#### Step 3.1: Create Password Change Required View

**File**: `apps/core/views.py` (add to existing file)

```python
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from allauth.account.views import PasswordChangeView

@method_decorator(login_required, name='dispatch')
class PasswordChangeRequiredView(PasswordChangeView):
    """
    Custom password change view that clears the password_change_required flag.

    Extends allauth's PasswordChangeView to integrate with our security flow.
    """
    template_name = 'core/password_change_required.html'
    success_url = reverse_lazy('core:dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': _('Alteração de Senha Obrigatória'),
            'subtitle': _('Por segurança, você deve escolher uma nova senha'),
            'is_required_change': True,
        })
        return context

    def form_valid(self, form):
        """Clear the password change flag after successful password change."""
        response = super().form_valid(form)

        # Clear the flag
        self.request.user.password_change_required = False
        self.request.user.save(update_fields=['password_change_required'])

        # Success message
        messages.success(
            self.request,
            _('Senha alterada com sucesso! Bem-vindo ao sistema.')
        )

        return response

    def get_form_kwargs(self):
        """Add any additional form configuration."""
        kwargs = super().get_form_kwargs()
        return kwargs
```

**Features**:

- Extends allauth's proven PasswordChangeView
- Clears flag only after successful password change
- Portuguese messaging for hospital staff
- Redirects to dashboard after success
- Proper error handling through allauth

#### Step 3.2: Add URL Pattern

**File**: `apps/core/urls.py`

```python
from .views import PasswordChangeRequiredView

app_name = 'core'

urlpatterns = [
    # ... existing URLs ...
    path(
        'password-change-required/',
        PasswordChangeRequiredView.as_view(),
        name='password_change_required'
    ),
    # ... rest of URLs ...
]
```

### Phase 4: Template Implementation

#### Step 4.1: Create Password Change Required Template

**File**: `templates/core/password_change_required.html`

```html
{% extends "base.html" %} {% load i18n %} {% load bootstrap5 %} {% block title
%}{% trans "Alteração de Senha Obrigatória" %} - {{ hospital.name }}{% endblock
%} {% block content %}
<div class="container mt-5">
  <div class="row justify-content-center">
    <div class="col-md-6">
      <div class="card shadow">
        <div class="card-header bg-warning text-dark">
          <h4 class="mb-0">
            <i class="bi bi-shield-exclamation me-2"></i>
            {% trans "Alteração de Senha Obrigatória" %}
          </h4>
        </div>
        <div class="card-body">
          <div class="alert alert-info mb-4">
            <i class="bi bi-info-circle me-2"></i>
            {% blocktrans %} Por medidas de segurança hospitalares, você deve
            escolher uma nova senha antes de acessar o sistema pela primeira
            vez. {% endblocktrans %}
          </div>

          <form method="post" novalidate>
            {% csrf_token %}

            <div class="mb-3">{% bootstrap_field form.oldpassword %}</div>

            <div class="mb-3">{% bootstrap_field form.password1 %}</div>

            <div class="mb-3">{% bootstrap_field form.password2 %}</div>

            <div class="d-grid gap-2">
              <button type="submit" class="btn btn-primary">
                <i class="bi bi-shield-check me-2"></i>
                {% trans "Alterar Senha e Continuar" %}
              </button>
            </div>
          </form>

          <div class="mt-3 text-center">
            <a
              href="{% url 'account_logout' %}"
              class="btn btn-outline-secondary"
            >
              {% trans "Sair do Sistema" %}
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

**Features**:

- Professional medical theme styling
- Clear security messaging in Portuguese
- Bootstrap 5 integration matching existing design
- Proper form validation display
- Option to logout if needed
- Responsive design for mobile devices

### Phase 5: Admin Interface Integration

#### Step 5.1: Update User Admin

**File**: `apps/accounts/admin.py`

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import EqmdCustomUser

@admin.register(EqmdCustomUser)
class EqmdCustomUserAdmin(UserAdmin):
    # ... existing configuration ...

    fieldsets = UserAdmin.fieldsets + (
        (_('Segurança'), {
            'fields': (
                'password_change_required',
            ),
            'description': _('Configurações de segurança para usuários do hospital')
        }),
        # ... existing custom fieldsets ...
    )

    list_display = UserAdmin.list_display + (
        'password_change_required',
        'profession_type',
    )

    list_filter = UserAdmin.list_filter + (
        'password_change_required',
        'profession_type',
    )

    def save_model(self, request, obj, form, change):
        """
        Custom save logic for user creation by admins.

        When admin creates a new user, ensure password_change_required is True
        unless explicitly set otherwise.
        """
        if not change:  # New user creation
            # Set flag to require password change for new users
            if not hasattr(obj, 'password_change_required'):
                obj.password_change_required = True

        super().save_model(request, obj, form, change)
```

**Features**:

- Adds security section to admin form
- Shows password change status in user list
- Filtering by password change requirement
- Automatic flag setting for new users
- Portuguese labels for hospital context

#### Step 5.2: Add Admin Help Text

**File**: `apps/accounts/admin.py` (additional method)

```python
def get_form(self, request, obj=None, **kwargs):
    """Customize form with helpful information for admins."""
    form = super().get_form(request, obj, **kwargs)

    if 'password_change_required' in form.base_fields:
        form.base_fields['password_change_required'].help_text = _(
            'Marque para forçar o usuário a alterar a senha no primeiro login. '
            'Recomendado para usuários criados pelos administradores.'
        )

    return form
```

### Phase 6: Security Enhancements

#### Step 6.1: Add Logging

**File**: `apps/core/middleware.py` (update existing middleware)

```python
import logging

logger = logging.getLogger('security.password_change')

class PasswordChangeRequiredMiddleware:
    # ... existing code ...

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        if not getattr(request.user, 'password_change_required', False):
            return self.get_response(request)

        # Log security event
        logger.info(
            f'Password change required redirect for user {request.user.username} '
            f'from IP {request.META.get("REMOTE_ADDR")} '
            f'accessing {request.path_info}'
        )

        # ... rest of middleware logic ...
```

#### Step 6.2: Add Audit History Integration

**File**: `apps/core/views.py` (update existing view)

```python
def form_valid(self, form):
    """Clear the password change flag and log the security event."""
    response = super().form_valid(form)

    # Clear the flag with history tracking
    self.request.user.password_change_required = False
    self.request.user._change_reason = 'Mandatory password change completed'
    self.request.user.save(update_fields=['password_change_required'])

    # Security logging
    logger.info(
        f'Mandatory password change completed for user {self.request.user.username} '
        f'from IP {self.request.META.get("REMOTE_ADDR")}'
    )

    messages.success(
        self.request,
        _('Senha alterada com sucesso! Bem-vindo ao sistema.')
    )

    return response
```

### Phase 7: Testing Strategy

#### Step 7.1: Unit Tests

**File**: `apps/accounts/tests/test_password_change_required.py`

```python
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages

User = get_user_model()

class PasswordChangeRequiredTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@hospital.com',
            password='temppass123',
            password_change_required=True
        )

    def test_middleware_redirects_when_password_change_required(self):
        """Test that middleware redirects users who need to change password."""
        self.client.login(username='testuser', password='temppass123')

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('password_change_required'))

    def test_password_change_clears_flag(self):
        """Test that successful password change clears the requirement flag."""
        self.client.login(username='testuser', password='temppass123')

        response = self.client.post(reverse('password_change_required'), {
            'oldpassword': 'temppass123',
            'password1': 'newpassword123!',
            'password2': 'newpassword123!',
        })

        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)

        # Flag should be cleared
        self.user.refresh_from_db()
        self.assertFalse(self.user.password_change_required)

    def test_allows_access_after_password_change(self):
        """Test that users can access the system after changing password."""
        self.user.password_change_required = False
        self.user.save()

        self.client.login(username='testuser', password='temppass123')
        response = self.client.get(reverse('core:dashboard'))

        # Should access dashboard normally
        self.assertEqual(response.status_code, 200)
```

#### Step 7.2: Integration Tests

**File**: `apps/accounts/tests/test_user_creation_flow.py`

```python
def test_complete_user_creation_flow(self):
    """Test the complete flow from admin user creation to password change."""
    # Admin creates user
    admin_user = User.objects.create_superuser(
        username='admin',
        email='admin@hospital.com',
        password='admin123'
    )

    # Simulate admin creating user
    new_user = User.objects.create_user(
        username='newdoctor',
        email='doctor@hospital.com',
        password='temporary123',
        password_change_required=True,  # Set by admin
        profession_type=User.MEDICAL_DOCTOR
    )

    # User logs in
    self.client.login(username='newdoctor', password='temporary123')

    # User tries to access dashboard
    response = self.client.get(reverse('core:dashboard'))
    self.assertRedirects(response, reverse('password_change_required'))

    # User changes password
    response = self.client.post(reverse('password_change_required'), {
        'oldpassword': 'temporary123',
        'password1': 'newsecurepass123!',
        'password2': 'newsecurepass123!',
    })

    # Should redirect to dashboard
    self.assertRedirects(response, reverse('core:dashboard'))

    # User can now access dashboard
    response = self.client.get(reverse('core:dashboard'))
    self.assertEqual(response.status_code, 200)
```

### Phase 8: Documentation and Deployment

#### Step 8.1: Update CLAUDE.md

Add to testing section:

```bash
# Test password change requirement
DJANGO_SETTINGS_MODULE=config.test_settings uv run pytest apps/accounts/tests/test_password_change_required.py
```

#### Step 8.2: Admin Documentation

**File**: `docs/admin/user-management.md`

```markdown
# User Management - Password Security

## Creating New Users

When creating users through the Django admin:

1. Create user with temporary password
2. Ensure "Password change required" is checked
3. User will be forced to change password on first login
4. User cannot access system until password is changed

## Password Change Flow

1. Admin creates user → `password_change_required = True`
2. User logs in with temporary password
3. System redirects to password change form
4. User must change password to continue
5. Flag is automatically cleared after successful change
```

#### Step 8.3: Environment Variables

No additional environment variables needed - uses existing allauth configuration.

## Implementation Timeline

### Week 1: Core Implementation

- Phase 1: Database changes
- Phase 2: Middleware implementation
- Phase 3: Views and URLs

### Week 2: UI and Admin

- Phase 4: Template implementation
- Phase 5: Admin interface integration

### Week 3: Security and Testing

- Phase 6: Security enhancements
- Phase 7: Comprehensive testing
- Phase 8: Documentation

## Risk Mitigation

### Low Risk Areas

- Uses Django's built-in password validation
- Leverages allauth's proven password change system
- Simple boolean flag logic
- Standard middleware patterns

### Potential Issues and Solutions

1. **Middleware Performance**: Minimal impact - single database field check
2. **Password Policies**: Uses existing Django password validators
3. **Session Management**: Leverages existing allauth session handling
4. **Mobile Compatibility**: Bootstrap responsive design

## Success Criteria

✅ **Security**: Users must change admin-set passwords before system access
✅ **UX**: Clear, professional interface in Portuguese
✅ **Integration**: Works seamlessly with existing allauth flow
✅ **Maintainability**: Minimal code changes, follows Django patterns
✅ **Testing**: Comprehensive test coverage for all scenarios
✅ **Documentation**: Clear admin procedures and user guidance

## Post-Implementation

### Monitoring

- Check logs for password change completion rates
- Monitor for users stuck in the flow
- Track admin user creation patterns

### Maintenance

- Review password policies periodically
- Update templates for any UI changes
- Monitor for allauth updates that might affect the flow

This implementation provides strong security while maintaining excellent user experience and system maintainability.
