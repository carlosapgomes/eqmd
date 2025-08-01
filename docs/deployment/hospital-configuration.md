# Hospital Configuration

**Environment-based single hospital configuration**

## Hospital Settings

Located in `config/settings.py` as `HOSPITAL_CONFIG`:

```python
HOSPITAL_CONFIG = {
    'name': os.getenv('HOSPITAL_NAME', 'Hospital Name'),
    'address': os.getenv('HOSPITAL_ADDRESS', ''),
    'phone': os.getenv('HOSPITAL_PHONE', ''),
    'email': os.getenv('HOSPITAL_EMAIL', ''),
    'website': os.getenv('HOSPITAL_WEBSITE', ''),
    'logo_path': os.getenv('HOSPITAL_LOGO_PATH', ''),
    'logo_url': os.getenv('HOSPITAL_LOGO_URL', ''),
}
```

## Template Tags

Available in `apps/core/templatetags/hospital_tags.py`:

```django
{% load hospital_tags %}
{% hospital_name %}        # Get configured hospital name
{% hospital_address %}     # Get configured hospital address
{% hospital_phone %}       # Get configured hospital phone
{% hospital_email %}       # Get configured hospital email
{% hospital_logo %}        # Get configured hospital logo URL
{% hospital_header %}      # Render hospital header with configuration
{% hospital_branding %}    # Get complete hospital branding info
```

## Environment Variables

```bash
# Hospital Configuration
HOSPITAL_NAME="Your Hospital Name"
HOSPITAL_ADDRESS="123 Medical Center Drive, City, State 12345"
HOSPITAL_PHONE="+1-555-123-4567"
HOSPITAL_EMAIL="info@yourhospital.com"
HOSPITAL_WEBSITE="https://www.yourhospital.com"
HOSPITAL_LOGO_PATH="static/images/hospital-logo.png"
HOSPITAL_LOGO_URL="https://cdn.yourhospital.com/logo.png"
```

## Configuration Examples

### Production Setup
```bash
# .env file for production
HOSPITAL_NAME="St. Mary's Medical Center"
HOSPITAL_ADDRESS="456 Healthcare Blvd, Medical City, MC 54321"
HOSPITAL_PHONE="+1-555-MEDICAL"
HOSPITAL_EMAIL="contact@stmarysmc.org"
HOSPITAL_WEBSITE="https://www.stmarysmc.org"
HOSPITAL_LOGO_URL="https://cdn.stmarysmc.org/logo-header.png"
```

### Development Setup
```bash
# .env file for development
HOSPITAL_NAME="Development Hospital"
HOSPITAL_ADDRESS="123 Dev Street, Test City, TC 12345"
HOSPITAL_PHONE="+1-555-DEV-TEST"
HOSPITAL_EMAIL="dev@localhost"
HOSPITAL_LOGO_PATH="static/images/dev-logo.png"
```

## Usage in Templates

### Basic Hospital Information
```django
{% load hospital_tags %}
<h1>{% hospital_name %}</h1>
<address>{% hospital_address %}</address>
<p>Phone: {% hospital_phone %}</p>
<p>Email: {% hospital_email %}</p>
```

### Hospital Branding
```django
{% load hospital_tags %}
{% hospital_header %}  <!-- Renders complete hospital header -->

<!-- Or custom branding -->
{% hospital_branding as hospital %}
<img src="{{ hospital.logo }}" alt="{{ hospital.name }}">
<h1>{{ hospital.name }}</h1>
```

## Customization

### Adding New Configuration Options
1. Add environment variable to `HOSPITAL_CONFIG` in settings
2. Create corresponding template tag in `hospital_tags.py`
3. Update templates to use new configuration

### Logo Handling
- **logo_path**: Use for local static files
- **logo_url**: Use for external CDN or URL-based logos
- Template tags automatically handle both cases