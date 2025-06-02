# Core App URL Patterns Documentation

This document provides detailed information about URL patterns, routing, and navigation in the Core app.

## Overview

The Core app defines URL patterns for the main application interfaces and integrates with the project's overall URL structure.

## URL Configuration Files

### App URLs: `apps/core/urls.py`

**Location**: `apps/core/urls.py`
**Purpose**: Defines URL patterns specific to the Core app

```python
from django.urls import path
from . import views

app_name = 'apps.core'  # Namespace for URL reversing

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]
```

### Project URLs: `config/urls.py`

**Location**: `config/urls.py`
**Purpose**: Includes Core app URLs in the main project routing

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('apps.core.urls', namespace='core')),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.account.urls')),
    path('profiles/', include('apps.accounts.urls', namespace='apps.accounts')),
]
```

## URL Patterns

### Landing Page

**Pattern**: `/`
**View**: `views.landing_page`
**Name**: `landing_page`
**Full Name**: `core:landing_page`

#### Details
- **Purpose**: Public homepage for EquipeMed
- **Authentication**: Not required
- **HTTP Methods**: GET
- **Template**: `core/landing_page.html`

#### URL Reversing
```python
# In views
from django.urls import reverse
url = reverse('core:landing_page')

# In templates
<a href="{% url 'core:landing_page' %}">Home</a>

# With namespace
{% url 'apps.core:landing_page' %}
```

#### Example URLs
- `http://example.com/`
- `https://app.sispep.com/`

### Dashboard

**Pattern**: `/dashboard/`
**View**: `views.dashboard_view`
**Name**: `dashboard`
**Full Name**: `core:dashboard`

#### Details
- **Purpose**: Main authenticated user interface
- **Authentication**: Required (`@login_required`)
- **HTTP Methods**: GET
- **Template**: `core/dashboard.html`

#### URL Reversing
```python
# In views
from django.urls import reverse
url = reverse('core:dashboard')

# In templates
<a href="{% url 'core:dashboard' %}">Dashboard</a>

# With namespace
{% url 'apps.core:dashboard' %}
```

#### Example URLs
- `http://example.com/dashboard/`
- `https://app.sispep.com/dashboard/`

## Namespace Configuration

### App Namespace
The Core app uses the namespace `apps.core` for explicit identification:

```python
app_name = 'apps.core'
```

### Benefits of Namespacing
1. **Collision Avoidance**: Prevents URL name conflicts
2. **Explicit Routing**: Clear identification of app URLs
3. **Maintainability**: Easier to manage in large projects
4. **Consistency**: Matches the app directory structure

### Usage Examples
```python
# Explicit namespace (recommended)
reverse('apps.core:landing_page')
reverse('apps.core:dashboard')

# Short namespace (also works)
reverse('core:landing_page')
reverse('core:dashboard')
```

## URL Integration

### Login Redirect Configuration
The dashboard is configured as the default login redirect:

```python
# In config/settings.py
LOGIN_REDIRECT_URL = 'core:dashboard'
```

### Navigation Links
Common navigation patterns in templates:

```html
<!-- Main navigation -->
<a href="{% url 'core:landing_page' %}" class="navbar-brand">EquipeMed</a>
<a href="{% url 'core:dashboard' %}" class="nav-link">Dashboard</a>

<!-- Conditional navigation -->
{% if user.is_authenticated %}
    <a href="{% url 'core:dashboard' %}">Dashboard</a>
{% else %}
    <a href="{% url 'account_login' %}">Login</a>
{% endif %}
```

## URL Parameters and Query Strings

### Current Implementation
The current URL patterns don't use parameters or query strings:

```python
# Simple patterns without parameters
path('', views.landing_page, name='landing_page'),
path('dashboard/', views.dashboard_view, name='dashboard'),
```

### Future Enhancements
Potential URL patterns for future features:

```python
# User-specific dashboard
path('dashboard/<str:username>/', views.user_dashboard, name='user_dashboard'),

# Dashboard sections
path('dashboard/patients/', views.patients_dashboard, name='patients_dashboard'),
path('dashboard/reports/', views.reports_dashboard, name='reports_dashboard'),

# Search functionality
path('search/', views.search_view, name='search'),
path('search/<str:query>/', views.search_results, name='search_results'),
```

## HTTP Methods

### Current Support
All current URLs support only GET requests:

```python
# GET requests only
def landing_page(request):
    return render(request, 'core/landing_page.html', context)

def dashboard_view(request):
    return render(request, 'core/dashboard.html', context)
```

### Future HTTP Method Support
Potential additions for interactive features:

```python
# POST for form submissions
def dashboard_view(request):
    if request.method == 'POST':
        # Handle form submission
        pass
    return render(request, 'core/dashboard.html', context)

# API endpoints
def api_dashboard_data(request):
    if request.method == 'GET':
        # Return JSON data
        pass
```

## URL Security

### Authentication Requirements
- **Landing Page**: Public access (no authentication)
- **Dashboard**: Requires authentication (`@login_required`)

### CSRF Protection
All POST requests are protected by Django's CSRF middleware:

```python
# In settings.py
MIDDLEWARE = [
    # ...
    'django.middleware.csrf.CsrfViewMiddleware',
    # ...
]
```

### URL Access Control
```python
from django.contrib.auth.decorators import login_required

# Protected view
@login_required
def dashboard_view(request):
    # Only authenticated users can access
    pass
```

## Error Handling

### 404 Errors
Django automatically handles 404 errors for undefined URLs:

```python
# Undefined URLs return 404
# Example: /nonexistent-page/ -> 404 Not Found
```

### Custom Error Pages
Future implementation could include custom error templates:

```python
# In urls.py
handler404 = 'apps.core.views.custom_404'
handler500 = 'apps.core.views.custom_500'
```

## URL Testing

### Test Examples
Recommended tests for URL patterns:

```python
from django.test import TestCase
from django.urls import reverse, resolve
from django.contrib.auth import get_user_model

class CoreURLsTestCase(TestCase):
    def test_landing_page_url_resolves(self):
        url = reverse('core:landing_page')
        self.assertEqual(url, '/')
        
    def test_dashboard_url_resolves(self):
        url = reverse('core:dashboard')
        self.assertEqual(url, '/dashboard/')
        
    def test_landing_page_view_resolves(self):
        view = resolve('/')
        self.assertEqual(view.view_name, 'core:landing_page')
        
    def test_dashboard_requires_login(self):
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
```

## Performance Considerations

### URL Routing Performance
- **Simple Patterns**: Current patterns are simple and fast
- **Regex Patterns**: Avoid complex regex when possible
- **URL Caching**: Django caches URL patterns automatically

### Optimization Tips
1. **Order Patterns**: Place most common patterns first
2. **Avoid Regex**: Use simple string patterns when possible
3. **Namespace Usage**: Use namespaces for better organization

## SEO and URL Structure

### Current URL Structure
- **Root URL**: `/` (good for SEO)
- **Dashboard**: `/dashboard/` (descriptive and clean)

### SEO Best Practices
1. **Descriptive URLs**: Use meaningful path segments
2. **Consistent Structure**: Maintain consistent URL patterns
3. **Canonical URLs**: Implement canonical URL handling
4. **Sitemap**: Generate XML sitemap for search engines

### Future URL Improvements
```python
# SEO-friendly URLs
path('about/', views.about_page, name='about'),
path('features/', views.features_page, name='features'),
path('contact/', views.contact_page, name='contact'),
path('help/', views.help_page, name='help'),
```

## API Endpoints

### Future API URLs
Potential API endpoints for the Core app:

```python
# API URL patterns
path('api/dashboard/stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
path('api/dashboard/activity/', views.dashboard_activity_api, name='dashboard_activity_api'),
path('api/search/', views.search_api, name='search_api'),
```

### API Versioning
```python
# Versioned API URLs
path('api/v1/dashboard/', include('apps.core.api.v1.urls')),
path('api/v2/dashboard/', include('apps.core.api.v2.urls')),
```

## Related Documentation

- [Views Documentation](views.md)
- [Templates Documentation](templates.md)
- [Core App Overview](README.md)
- [Django URL Documentation](https://docs.djangoproject.com/en/stable/topics/http/urls/)

## Troubleshooting

### Common URL Issues

1. **NoReverseMatch Error**
   ```python
   # Problem: Incorrect URL name
   reverse('dashboard')  # Missing namespace
   
   # Solution: Use correct namespace
   reverse('core:dashboard')
   ```

2. **404 Not Found**
   ```python
   # Check URL pattern matches exactly
   path('dashboard/', ...)  # Requires trailing slash
   ```

3. **Redirect Loops**
   ```python
   # Check LOGIN_REDIRECT_URL setting
   LOGIN_REDIRECT_URL = 'core:dashboard'
   ```

### Debug Tips
1. **URL Debug**: Use `django.urls.reverse` in Django shell
2. **Pattern Testing**: Test URL patterns with `resolve()`
3. **Middleware**: Check middleware order for authentication
4. **Settings**: Verify URL configuration in settings
