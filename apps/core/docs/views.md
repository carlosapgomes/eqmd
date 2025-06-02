# Core App Views Documentation

This document provides detailed information about all views in the Core app.

## Overview

The Core app contains two main views that handle the primary user interfaces:

1. **Landing Page View**: Public homepage
2. **Dashboard View**: Authenticated user interface

## View Functions

### `landing_page(request)`

**Location**: `apps/core/views.py:4-11`

#### Purpose
Renders the public-facing landing page for EquipeMed, serving as the main entry point for new users.

#### Function Signature
```python
def landing_page(request):
```

#### Parameters
- `request` (HttpRequest): The HTTP request object

#### Authentication
- **Required**: No
- **Decorators**: None
- **Access**: Public (anyone can access)

#### Return Value
- **Type**: HttpResponse
- **Template**: `core/landing_page.html`
- **Context**: Dictionary with page metadata

#### Context Variables
```python
context = {
    'page_title': 'Bem-vindo ao EquipeMed',
}
```

#### Template Features
The landing page template includes:
- Hero section with main value proposition
- Feature showcase cards
- Benefits overview
- Call-to-action buttons
- Contact information
- Responsive design

#### URL Mapping
- **Pattern**: `/`
- **Name**: `landing_page`
- **Namespace**: `core:landing_page`

#### Example Usage
```python
# In templates
<a href="{% url 'core:landing_page' %}">Home</a>

# In views
from django.urls import reverse
redirect_url = reverse('core:landing_page')
```

#### SEO Considerations
- Page title is set for search engines
- Meta descriptions should be added
- Structured data could be implemented

---

### `dashboard_view(request)`

**Location**: `apps/core/views.py:13-21`

#### Purpose
Renders the main dashboard interface for authenticated users, providing access to core application features.

#### Function Signature
```python
@login_required
def dashboard_view(request):
```

#### Parameters
- `request` (HttpRequest): The HTTP request object

#### Authentication
- **Required**: Yes
- **Decorators**: `@login_required`
- **Access**: Authenticated users only
- **Redirect**: Unauthenticated users redirected to login page

#### Return Value
- **Type**: HttpResponse
- **Template**: `core/dashboard.html`
- **Context**: Dictionary with page metadata and user data

#### Context Variables
```python
context = {
    'page_title': 'Painel Principal',
}
```

#### Template Features
The dashboard template includes:
- Welcome message with user name
- Sidebar navigation
- Quick stats cards
- Recent activity feed
- Quick action buttons
- Responsive layout

#### URL Mapping
- **Pattern**: `/dashboard/`
- **Name**: `dashboard`
- **Namespace**: `core:dashboard`

#### Example Usage
```python
# In templates
<a href="{% url 'core:dashboard' %}">Dashboard</a>

# In views
from django.urls import reverse
redirect_url = reverse('core:dashboard')
```

#### Login Redirect
This view is configured as the default login redirect:
```python
# In settings.py
LOGIN_REDIRECT_URL = 'core:dashboard'
```

## View Patterns and Best Practices

### Context Data Pattern
Both views follow a consistent pattern for context data:

```python
def view_function(request):
    context = {
        'page_title': 'Page Title',
        # Additional context variables
    }
    return render(request, 'template.html', context)
```

### Authentication Handling
The app uses Django's built-in authentication:

```python
from django.contrib.auth.decorators import login_required

@login_required
def protected_view(request):
    # View logic here
    pass
```

### Template Rendering
All views use Django's `render` shortcut:

```python
from django.shortcuts import render

def view_function(request):
    return render(request, 'app/template.html', context)
```

## Future Enhancements

### Planned View Improvements

#### Dashboard Enhancements
1. **User-specific Data**: Display user's actual data instead of placeholder
2. **Dynamic Stats**: Real-time statistics from database
3. **Personalization**: User preferences and customization
4. **Activity Feed**: Recent user actions and notifications

#### Additional Views
1. **Settings View**: User preferences and configuration
2. **Help View**: Documentation and tutorials
3. **Search View**: Global search functionality
4. **Profile View**: User profile management

### Context Improvements
Future context data might include:

```python
# Enhanced dashboard context
context = {
    'page_title': 'Painel Principal',
    'user_stats': {
        'total_patients': user.patients.count(),
        'recent_activities': user.activities.recent(),
        'pending_tasks': user.tasks.pending(),
    },
    'notifications': user.notifications.unread(),
    'quick_actions': get_user_quick_actions(user),
}
```

## Error Handling

### Current Implementation
The views currently rely on Django's default error handling:

- **404 errors**: Handled by Django's default 404 page
- **500 errors**: Handled by Django's default 500 page
- **Authentication errors**: Handled by `@login_required` decorator

### Recommended Improvements
1. **Custom Error Pages**: Create branded error templates
2. **Logging**: Add proper logging for debugging
3. **User Feedback**: Provide helpful error messages
4. **Graceful Degradation**: Handle missing data gracefully

## Performance Considerations

### Current Performance
- Views are simple and fast
- No database queries in current implementation
- Templates are cached by Django

### Optimization Opportunities
1. **Database Optimization**: Use select_related/prefetch_related for future queries
2. **Caching**: Implement view-level caching for static content
3. **Pagination**: Add pagination for large datasets
4. **Lazy Loading**: Implement lazy loading for dashboard widgets

## Security Considerations

### Current Security
- Authentication properly enforced with decorators
- CSRF protection enabled by default
- No direct database access in views

### Security Best Practices
1. **Input Validation**: Validate all user inputs
2. **Permission Checks**: Add granular permission checking
3. **Rate Limiting**: Implement rate limiting for API endpoints
4. **Audit Logging**: Log user actions for security

## Testing

### Test Coverage
Current test coverage is minimal. Recommended tests:

```python
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

class CoreViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_landing_page_accessible(self):
        response = self.client.get(reverse('core:landing_page'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_accessible_when_logged_in(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
```

## Related Documentation

- [Templates Documentation](templates.md)
- [URL Patterns Documentation](urls.md)
- [Core App Overview](README.md)
