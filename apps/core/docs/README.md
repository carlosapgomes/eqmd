# Core App Documentation

The Core app provides the main application functionality for EquipeMed, including the landing page, dashboard interface, and reference data management.

## Overview

The Core app serves as the central hub of the EquipeMed application, providing:

- **Landing Page**: Public-facing homepage with feature descriptions
- **Dashboard**: Main authenticated user interface
- **Base Templates**: Shared template infrastructure
- **URL Routing**: Core application routing
- **Reference Data**: ICD-10 codes and medical procedures management
- **Caching**: Dashboard and ward mapping cache systems

## App Structure

```
apps/core/
├── docs/                    # Documentation files
│   ├── README.md           # This file
│   ├── views.md            # Views documentation
│   ├── templates.md        # Templates documentation
│   └── urls.md             # URL patterns documentation
├── templates/core/         # App-specific templates
│   ├── landing_page.html   # Public landing page
│   └── dashboard.html      # Authenticated dashboard
├── models/                  # Data models
│   ├── cache.py            # Cache models
│   ├── icd10_code.py       # ICD-10 diagnosis codes
│   ├── medical_procedure.py # Medical procedures
│   └── renewal_request.py  # Account renewal requests
├── api/                     # API endpoints
├── management/              # Django management commands
│   ├── import_icd10_codes.py
│   ├── import_procedures.py
│   └── populate_sample_data.py
├── admin.py               # Django admin configuration
├── apps.py                # App configuration
├── tests/                 # Test cases
├── urls.py                # URL patterns
└── views.py               # View functions
```

## Key Features

### 1. Landing Page

- **Purpose**: Public-facing homepage for EquipeMed
- **URL**: `/` (root URL)
- **Template**: `core/landing_page.html`
- **Authentication**: Not required
- **Features**:
  - Hero section with call-to-action
  - Feature showcase
  - Benefits overview
  - Contact information

### 2. Dashboard

- **Purpose**: Main interface for authenticated users
- **URL**: `/dashboard/`
- **Template**: `core/dashboard.html`
- **Authentication**: Required (`@login_required`)
- **Features**:
  - Welcome message
  - Quick stats overview
  - Recent activity
  - Navigation to main features

## Configuration

### App Registration

The app is registered in `config/settings.py`:

```python
INSTALLED_APPS = [
    # ...
    "apps.core",  # Core functionality
    # ...
]
```

### URL Configuration

The app URLs are included in the main `config/urls.py`:

```python
urlpatterns = [
    path('', include('apps.core.urls', namespace='core')),
    # ...
]
```

### Login Redirect

After successful login, users are redirected to the dashboard:

```python
LOGIN_REDIRECT_URL = 'core:dashboard'
```

## Dependencies

### Internal Dependencies

- **Base Templates**: Uses `templates/base.html` and `templates/base_app.html`
- **Authentication**: Integrates with `apps.accounts` for user authentication

### External Dependencies

- **Django**: Core framework
- **django-allauth**: Authentication system
- **Bootstrap**: UI framework (via templates)
- **Bootstrap Icons**: Icon library

## Template Hierarchy

```
templates/base.html                    # Root base template
├── templates/base_app.html           # App-specific base (extends base.html)
│   └── core/dashboard.html           # Dashboard (extends base_app.html)
└── core/landing_page.html            # Landing page (extends base.html)
```

## URL Patterns

| URL | View | Name | Description |
|-----|------|------|-------------|
| `/` | `landing_page` | `landing_page` | Public homepage |
| `/dashboard/` | `dashboard_view` | `dashboard` | User dashboard |

## Views

### `landing_page(request)`

- **Purpose**: Renders the public landing page
- **Authentication**: Not required
- **Context**: `page_title`
- **Template**: `core/landing_page.html`

### `dashboard_view(request)`

- **Purpose**: Renders the authenticated user dashboard
- **Authentication**: Required (`@login_required`)
- **Context**: `page_title`
- **Template**: `core/dashboard.html`

## Templates

### Landing Page Features

- **Responsive Design**: Mobile-first approach
- **Hero Section**: Main call-to-action
- **Feature Cards**: Key application features
- **Benefits Section**: Value propositions
- **CTA Sections**: Multiple conversion points

### Dashboard Features

- **Sidebar Navigation**: Main app navigation
- **Welcome Section**: Personalized greeting
- **Stats Cards**: Key metrics overview
- **Recent Activity**: Latest user actions
- **Quick Actions**: Common tasks

## Styling

The app uses a custom medical-themed color scheme:

- **Primary**: Medical blue (`text-medical-primary`)
- **Teal**: Accent color (`text-medical-teal`)
- **Gray**: Text color (`text-medical-gray`)
- **Light**: Background (`bg-medical-light`)

## Security

### Authentication

- Dashboard requires user authentication
- Landing page is publicly accessible
- Uses Django's built-in authentication decorators

### CSRF Protection

- All forms include CSRF tokens
- Protected by Django's CSRF middleware

## Reference Data

The Core app manages reference data used throughout the system:

- **ICD-10 Codes**: Diagnosis codes (14,242 codes)
- **Medical Procedures**: Standardized procedure codes
- **Import Commands**: CSV/JSON import with batch processing
- **Search API**: Full-text search for both reference types

For detailed information on importing and managing reference data, see [Reference Data Management](../../docs/reference-data.md).

### Quick Import Commands

```bash
# Import ICD-10 codes
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv

# Import medical procedures
uv run python manage.py import_procedures --file=fixtures/procedimentos.csv

# Preview imports
uv run python manage.py import_icd10_codes --file=fixtures/cid.csv --dry-run
```

### Search API Endpoints

- `/api/icd10/search/?q=query` - Search ICD-10 codes
- `/api/procedures/search/?q=query` - Search medical procedures

## Testing

## Future Enhancements

### Planned Features

1. **Analytics Dashboard**: User activity metrics
2. **Notification Center**: System notifications
3. **Quick Search**: Global search functionality
4. **User Preferences**: Customizable dashboard
5. **Help System**: Integrated help and tutorials

### Template Improvements

1. **Progressive Web App**: PWA capabilities
2. **Dark Mode**: Theme switching
3. **Accessibility**: WCAG compliance
4. **Performance**: Lazy loading and optimization

## Related Documentation

- [Views Documentation](views.md)
- [Templates Documentation](templates.md)
- [URL Patterns Documentation](urls.md)
- [API Reference](api-reference.md)
- [Accounts App Documentation](../../accounts/docs/README.md)
- [Reference Data Management](../../docs/reference-data.md)

## Troubleshooting

### Common Issues

1. **Template Not Found**: Ensure templates are in `apps/core/templates/core/`
2. **Static Files**: Run `collectstatic` for production
3. **Authentication**: Check `LOGIN_REDIRECT_URL` setting
4. **URL Conflicts**: Verify namespace usage in templates

### Debug Mode

Enable debug mode in development:

```python
DEBUG = True
```

## Contributing

When contributing to the Core app:

1. Follow Django best practices
2. Update documentation for new features
3. Add tests for new functionality
4. Maintain template consistency
5. Follow the established naming conventions
