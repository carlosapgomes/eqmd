# Hospital Configuration Examples

This file provides examples of how hospital configuration will be used throughout the application after the single-hospital refactor.

## Environment Variables (.env)

```bash
# Hospital Information
HOSPITAL_NAME="São Paulo Medical Center"
HOSPITAL_ADDRESS="Av. Paulista, 1234 - Bela Vista, São Paulo - SP, 01310-100"
HOSPITAL_PHONE="+55 11 3456-7890"
HOSPITAL_EMAIL="contato@spmedicalcenter.com.br"
HOSPITAL_WEBSITE="https://www.spmedicalcenter.com.br"

# Hospital Logo for Reports
HOSPITAL_LOGO_PATH="static/images/hospital-logo.png"
# Alternative: Use URL for external logo
# HOSPITAL_LOGO_URL="https://cdn.spmedicalcenter.com.br/logo.png"
```

## Template Usage Examples

### Hospital Header Partial (`apps/core/templates/core/partials/hospital_header.html`)

```django
{% load hospital_tags %}
<div class="hospital-header d-flex align-items-center mb-3">
    <img src="{% hospital_logo %}" alt="Hospital Logo" class="hospital-logo me-3" style="height: 50px;">
    <div>
        <h5 class="mb-0">{% hospital_name %}</h5>
        <small class="text-muted">{% hospital_address %}</small>
    </div>
</div>
```

### Report Header Example

```django
{% load hospital_tags %}
<!DOCTYPE html>
<html>
<head>
    <title>Patient Report - {% hospital_name %}</title>
    <style>
        .report-header { border-bottom: 2px solid #dee2e6; padding-bottom: 20px; margin-bottom: 30px; }
        .hospital-logo { max-height: 80px; }
        .hospital-info { text-align: right; }
    </style>
</head>
<body>
    <div class="report-header">
        <div class="row">
            <div class="col-6">
                <img src="{% hospital_logo %}" alt="{% hospital_name %}" class="hospital-logo">
            </div>
            <div class="col-6 hospital-info">
                <h4>{% hospital_name %}</h4>
                <p>{% hospital_address %}<br>
                   Phone: {{ hospital.phone }}<br>
                   Email: {{ hospital.email }}</p>
            </div>
        </div>
    </div>
    
    <!-- Report content -->
    <div class="report-content">
        <!-- Patient information, daily notes, etc. -->
    </div>
</body>
</html>
```

### Navigation with Hospital Branding

```django
{% load hospital_tags %}
<nav class="navbar navbar-expand-lg navbar-dark bg-primary">
    <div class="container-fluid">
        <a class="navbar-brand d-flex align-items-center" href="{% url 'core:dashboard' %}">
            <img src="{% hospital_logo %}" alt="Logo" height="30" class="me-2">
            {% hospital_name %}
        </a>
        <!-- Rest of navigation -->
    </div>
</nav>
```

### Patient Detail with Hospital Context

```django
{% load hospital_tags %}
<div class="patient-header">
    <div class="row">
        <div class="col-md-8">
            <h2>{{ patient.full_name }}</h2>
            <p class="text-muted">Patient ID: {{ patient.id }}</p>
        </div>
        <div class="col-md-4 text-end">
            <small class="text-muted">
                <strong>{% hospital_name %}</strong><br>
                {% hospital_address %}
            </small>
        </div>
    </div>
</div>
```

## Template Tags Reference

### Available Template Tags (`apps/core/templatetags/hospital_tags.py`)

```python
# Simple tags
{% hospital_name %}        # Returns hospital name
{% hospital_address %}     # Returns hospital address  
{% hospital_phone %}       # Returns hospital phone
{% hospital_email %}       # Returns hospital email
{% hospital_website %}     # Returns hospital website
{% hospital_logo %}        # Returns logo URL/path

# Inclusion tag
{% hospital_header %}      # Renders hospital header partial
```

## Settings Configuration

```python
# settings.py
import os

# Hospital Configuration
HOSPITAL_CONFIG = {
    'name': os.getenv('HOSPITAL_NAME', 'Medical Center'),
    'address': os.getenv('HOSPITAL_ADDRESS', ''),
    'phone': os.getenv('HOSPITAL_PHONE', ''),
    'email': os.getenv('HOSPITAL_EMAIL', ''),
    'website': os.getenv('HOSPITAL_WEBSITE', ''),
    'logo_path': os.getenv('HOSPITAL_LOGO_PATH', 'static/images/default-logo.png'),
    'logo_url': os.getenv('HOSPITAL_LOGO_URL', ''),
}

# Make hospital config available in templates
TEMPLATES = [
    {
        'OPTIONS': {
            'context_processors': [
                # ... other processors
                'apps.core.context_processors.hospital_context',
            ],
        },
    },
]
```

## Context Processor Example

```python
# apps/core/context_processors.py
from django.conf import settings

def hospital_context(request):
    """Add hospital configuration to template context."""
    return {
        'hospital': settings.HOSPITAL_CONFIG
    }
```

## Logo File Organization

```
static/
└── images/
    ├── hospital-logo.png          # Main logo (recommended: 200x80px)
    ├── hospital-logo-small.png    # Small logo for navbar (recommended: 40x40px)
    ├── hospital-logo-print.png    # High-res for reports (recommended: 400x160px)
    └── default-logo.png           # Fallback logo
```

## PDF Report Integration

For PDF reports using ReportLab or WeasyPrint:

```python
# In report generation
from django.conf import settings
from django.templatetags.static import static

def generate_patient_report(patient):
    hospital_config = settings.HOSPITAL_CONFIG
    logo_path = hospital_config['logo_path']
    
    # Use in PDF generation
    html_template = f"""
    <div class="header">
        <img src="{static(logo_path)}" style="height: 60px;">
        <h2>{hospital_config['name']}</h2>
        <p>{hospital_config['address']}</p>
    </div>
    """
```

## Benefits of This Approach

- **Simple Configuration**: Single environment file setup
- **Consistent Branding**: Hospital info available throughout app
- **Report Ready**: Easy integration with PDF/print reports  
- **Template Flexibility**: Use hospital info anywhere with template tags
- **Multi-Environment**: Different hospital configs per environment
- **Logo Support**: Both local files and external URLs supported
- **Fallback Values**: Sensible defaults if config missing
