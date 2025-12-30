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
    # Hospital short identifier for PWA customization
    'short_identifier': os.getenv('HOSPITAL_SHORT_ID', ''),
}
```

## Template Tags

Available in `apps/core/templatetags/hospital_tags.py`:

```django
{% load hospital_tags %}
{% hospital_name %}           # Get configured hospital name
{% hospital_address %}        # Get configured hospital address
{% hospital_phone %}          # Get configured hospital phone
{% hospital_email %}          # Get configured hospital email
{% hospital_logo %}           # Get configured hospital logo URL
{% hospital_header %}         # Render hospital header with configuration
{% hospital_branding %}       # Get complete hospital branding info
{% hospital_pwa_short_name %} # Get PWA short name (e.g., "HgrsEqmd")
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

# PWA Customization (optional)
HOSPITAL_SHORT_ID="hgrs"  # Creates PWA short name "HgrsEqmd"

# Django Site Framework (for email templates and django-allauth)
SITE_DOMAIN="yourhospital.com"  # Your actual domain name
SITE_NAME="Your Hospital Name"  # Name shown in email templates
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

# Django Site Framework
SITE_DOMAIN="stmarysmc.org"
SITE_NAME="St. Mary's Medical Center"
```

### Development Setup

```bash
# .env file for development
HOSPITAL_NAME="Development Hospital"
HOSPITAL_ADDRESS="123 Dev Street, Test City, TC 12345"
HOSPITAL_PHONE="+1-555-DEV-TEST"
HOSPITAL_EMAIL="dev@localhost"
HOSPITAL_LOGO_PATH="static/images/dev-logo.png"

# Django Site Framework (for development)
SITE_DOMAIN="localhost:8778"
SITE_NAME="Development Hospital"
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

## PWA Customization

EquipeMed supports subtle PWA (Progressive Web App) customization for multi-hospital deployments while maintaining the EquipeMed brand identity.

### Hospital Short Identifier

Use `HOSPITAL_SHORT_ID` to create hospital-specific PWA short names:

```bash
# Hospital Regional do Sertão
HOSPITAL_SHORT_ID="hgrs"
# Results in PWA short name: "HgrsEqmd"

# Hospital Municipal Central  
HOSPITAL_SHORT_ID="hmc"
# Results in PWA short name: "HmcEqmd"

# No short ID (default)
# Results in PWA short name: "EquipeMed"
```

### PWA Manifest

The system automatically generates a dynamic PWA manifest at `/manifest.json` that includes:

- **name**: `"EquipeMed - [Hospital Name]"` or `"EquipeMed - Plataforma Médica"`
- **short_name**: `"[ShortId]Eqmd"` or `"EquipeMed"`
- **theme_color**: Always `"#2E5BBA"` (EquipeMed brand color)
- **description**: Standard EquipeMed description
- **icons**: Standard EquipeMed icon set

### Landing Page Context

When `HOSPITAL_SHORT_ID` is configured, the landing page subtly displays the hospital name to provide context without changing the overall EquipeMed branding.

### Multi-Hospital Deployment Example

```bash
# Hospital A (hospitala.domain.com)
HOSPITAL_NAME="Hospital Regional do Sertão"
HOSPITAL_SHORT_ID="hgrs"
HOSPITAL_ADDRESS="Av. Hospital Regional, 123, Petrolina, PE"

# Hospital B (hospitalb.domain.com)  
HOSPITAL_NAME="Hospital Municipal Central"
HOSPITAL_SHORT_ID="hmc"
HOSPITAL_ADDRESS="Rua Central, 456, Salvador, BA"
```

**Benefits:**

- ✅ Maintains EquipeMed branding consistency
- ✅ Users can distinguish between hospital instances
- ✅ PWA installations show hospital context
- ✅ Backward compatible (works without configuration)
- ✅ No visual design changes required

## Django Site Framework Configuration

EquipeMed automatically configures Django's Site Framework for proper email templates and django-allauth integration.

### Email Template Configuration

The `SITE_DOMAIN` and `SITE_NAME` environment variables control how emails appear:

- **SITE_DOMAIN**: Your actual domain name (e.g., `yourhospital.com`)
- **SITE_NAME**: Hospital name shown in email templates

### Automatic Configuration

The system automatically updates the Django Site object when the container starts:

1. **On container startup**: Checks if `SITE_DOMAIN` or `SITE_NAME` are set
2. **Updates database**: Creates or updates the Site object with ID=1
3. **Email templates**: Django-allauth uses the Site object for email subjects and content

### Before/After Email Examples

**Before configuration** (shows "example.com"):

```
Subject: [example.com] Confirme seu endereço de email
```

**After configuration** with `SITE_DOMAIN=yourhospital.com`:

```
Subject: [yourhospital.com] Confirme seu endereço de email
```

### Manual Override (if needed)

If automatic configuration doesn't work, you can manually set the site via Django admin:

1. Go to `/admin/sites/site/1/change/`
2. Update "Domain name" and "Display name"
3. Save changes

### Troubleshooting

- **Emails still show example.com**: Check that `SITE_DOMAIN` is set in `.env` and container was restarted
- **Site not updating**: Check Django logs for database errors during startup
- **Multiple sites**: Ensure `SITE_ID=1` in environment (default)
