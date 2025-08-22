# Subtle Hospital Customization Implementation Plan

## Overview
Minimal customization to maintain EquipeMed branding while adding subtle hospital-specific information. Focus on hospital identification in manifest and landing page without changing color themes or major branding elements.

## Design Philosophy
- **Keep EquipeMed as primary brand** - No color or major visual changes
- **Add hospital context** - Users know which hospital instance they're using
- **Maintain consistency** - All instances look and feel like EquipeMed
- **Minimal implementation** - Simple, maintainable changes

## Current State Analysis

### Already Working Well
- ✅ `HOSPITAL_CONFIG` with name, address, phone, email
- ✅ `hospital_tags.py` with basic template tags
- ✅ Hospital header in authenticated pages (`base_app.html`)
- ✅ EquipeMed branding and color scheme

### Needs Subtle Enhancement
1. **PWA Manifest** - Show hospital context in short_name (e.g., "HgrsEqmd")
2. **Landing Page** - Add hospital name/location info
3. **Template Tags** - Add hospital short name support

## Implementation Steps

### Phase 1: Add Hospital Short Name Environment Variable

#### Step 1.1: Update Hospital Configuration
**File**: `config/settings.py`

Add single new environment variable to existing `HOSPITAL_CONFIG`:
```python
HOSPITAL_CONFIG = {
    'name': os.getenv('HOSPITAL_NAME', 'Medical Center'),
    'address': os.getenv('HOSPITAL_ADDRESS', '123 Medical Street, Medical City'),
    'phone': os.getenv('HOSPITAL_PHONE', '+1 (555) 123-4567'),
    'email': os.getenv('HOSPITAL_EMAIL', 'info@medicalcenter.com'),
    'website': os.getenv('HOSPITAL_WEBSITE', ''),
    'logo_path': os.getenv('HOSPITAL_LOGO_PATH', 'static/images/hospital-logo.png'),
    'logo_url': os.getenv('HOSPITAL_LOGO_URL', ''),
    # NEW: Hospital short identifier for PWA
    'short_identifier': os.getenv('HOSPITAL_SHORT_ID', ''),  # e.g., "hgrs", "hmc"
}
```

**Environment Variables Examples**:
```bash
# Hospital Regional do Sertão (hgrs.domain.com)
HOSPITAL_NAME="Hospital Geral Regional do Sertão"
HOSPITAL_SHORT_ID="hgrs"
HOSPITAL_ADDRESS="Av. Hospital Regional, 123, Petrolina, PE"

# Hospital Municipal Central (hmc.domain.com)  
HOSPITAL_NAME="Hospital Municipal Central"
HOSPITAL_SHORT_ID="hmc"
HOSPITAL_ADDRESS="Rua Central, 456, Salvador, BA"
```

### Phase 2: Extend Template Tags (Minimal)

#### Step 2.1: Add PWA Short Name Template Tag
**File**: `apps/core/templatetags/hospital_tags.py`

Add single new template tag:
```python
@register.simple_tag
def hospital_pwa_short_name():
    """Generate PWA short name combining hospital short ID with EquipeMed brand"""
    hospital_config = getattr(settings, 'HOSPITAL_CONFIG', {})
    short_id = hospital_config.get('short_identifier', '').lower()
    
    if short_id:
        # e.g., "hgrs" -> "HgrsEqmd"
        return f"{short_id.capitalize()}Eqmd"
    else:
        # Default EquipeMed branding
        return "EquipeMed"
```

### Phase 3: Update PWA Manifest (Subtle Change)

#### Step 3.1: Create Dynamic Manifest View
**New File**: `apps/core/views/manifest.py`
```python
from django.http import JsonResponse
from django.conf import settings

def manifest_json(request):
    """Serve dynamic PWA manifest with subtle hospital customization"""
    hospital_config = getattr(settings, 'HOSPITAL_CONFIG', {})
    short_id = hospital_config.get('short_identifier', '').lower()
    
    # Generate PWA short name
    if short_id:
        short_name = f"{short_id.capitalize()}Eqmd"
        name = f"EquipeMed - {hospital_config.get('name', 'Plataforma Médica')}"
    else:
        short_name = "EquipeMed"
        name = "EquipeMed - Plataforma Médica"
    
    manifest = {
        "name": name,
        "short_name": short_name,
        "description": "Plataforma de colaboração médica para rastreamento de pacientes e gestão hospitalar",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#2E5BBA",  # Keep EquipeMed theme color
        "orientation": "portrait-primary",
        "scope": "/",
        "categories": ["medical", "health", "productivity"],
        "lang": "pt-BR",
        "icons": [
            # Keep existing EquipeMed icons - no hospital-specific icons needed
            {
                "src": "/static/images/pwa/icon-72x72.png",
                "sizes": "72x72",
                "type": "image/png",
                "purpose": "any"
            },
            # ... (all existing icons remain the same)
        ]
    }
    
    return JsonResponse(manifest)
```

#### Step 3.2: Add URL Route
**File**: `apps/core/urls.py`
```python
from .views import manifest

urlpatterns = [
    # ... existing patterns
    path('manifest.json', manifest.manifest_json, name='manifest_json'),
]
```

#### Step 3.3: Update Base Template Manifest Link
**File**: `templates/base.html`

Change line 26:
```html
<!-- OLD -->
<link rel="manifest" href="{% static 'manifest.json' %}">

<!-- NEW -->
<link rel="manifest" href="{% url 'apps.core:manifest_json' %}">
```

### Phase 4: Enhance Landing Page (Subtle Hospital Info)

#### Step 4.1: Add Hospital Context to Landing Page
**File**: `apps/core/templates/core/landing_page.html`

**Option A: Add hospital info in hero section** (Recommended)

Around line 41, after the security indicator:
```html
<div class="d-flex align-items-center text-muted">
  <i class="bi bi-shield-check text-medical-green me-2"></i>
  <small>Plataforma segura com monitoramento de auditoria</small>
</div>

<!-- NEW: Add hospital context -->
{% hospital_name as hospital %}
{% if hospital and hospital != "Medical Center" %}
<div class="d-flex align-items-center text-muted mt-2">
  <i class="bi bi-hospital text-medical-teal me-2"></i>
  <small>{{ hospital }}</small>
</div>
{% endif %}
```

**Option B: Add hospital info in features section**

Around line 66, update the lead text:
```html
<!-- OLD -->
<p class="lead text-medical-gray">
  Ferramentas especializadas que facilitam o trabalho da equipe médica e melhoram o atendimento ao paciente.
</p>

<!-- NEW -->
<p class="lead text-medical-gray">
  {% hospital_name as hospital %}
  {% if hospital and hospital != "Medical Center" %}
    Ferramentas especializadas do {{ hospital }} que facilitam o trabalho da equipe médica e melhoram o atendimento ao paciente.
  {% else %}
    Ferramentas especializadas que facilitam o trabalho da equipe médica e melhoram o atendimento ao paciente.
  {% endif %}
</p>
```

### Phase 5: Testing and Validation

#### Step 5.1: Test Default Behavior
**Action**: Verify without environment variables:
- PWA short name = "EquipeMed"
- Landing page shows no hospital-specific info
- Manifest works correctly

#### Step 5.2: Test with Hospital Configuration
**Action**: Test with environment variables set:
- PWA short name = "HgrsEqmd" (if HOSPITAL_SHORT_ID="hgrs")
- Landing page shows hospital name
- Manifest includes hospital in full name

#### Step 5.3: PWA Installation Testing
**Action**: Test PWA installation on mobile:
- App shows correct short name on home screen
- Installation prompt shows hospital-specific name

### Phase 6: Clean Up Static Manifest

#### Step 6.1: Remove Static Manifest
**Action**: Delete or rename `static/manifest.json` to avoid conflicts

## Files Modified Summary

### Minimal Changes Required
1. **`config/settings.py`** - Add `short_identifier` to `HOSPITAL_CONFIG`
2. **`apps/core/templatetags/hospital_tags.py`** - Add `hospital_pwa_short_name` tag
3. **`apps/core/views/manifest.py`** - New file for dynamic manifest
4. **`apps/core/urls.py`** - Add manifest route
5. **`templates/base.html`** - Update manifest link (1 line change)
6. **`apps/core/templates/core/landing_page.html`** - Add subtle hospital info
7. **`static/manifest.json`** - Remove static file

## Environment Variable Examples

### Hospital Regional do Sertão
```bash
HOSPITAL_NAME="Hospital Geral Regional do Sertão"
HOSPITAL_SHORT_ID="hgrs"
HOSPITAL_ADDRESS="Av. Hospital Regional, 123, Petrolina, PE"
HOSPITAL_PHONE="+55 (87) 3866-5000"
```
**Result**: PWA shows "HgrsEqmd", landing page shows hospital name

### Hospital Municipal Central  
```bash
HOSPITAL_NAME="Hospital Municipal Central"
HOSPITAL_SHORT_ID="hmc"
HOSPITAL_ADDRESS="Rua Central, 456, Salvador, BA"
HOSPITAL_PHONE="+55 (71) 3202-1000"
```
**Result**: PWA shows "HmcEqmd", landing page shows hospital name

### Default (No Environment Variables)
**Result**: PWA shows "EquipeMed", no hospital-specific info shown

## Benefits of This Approach

### ✅ Maintains Brand Consistency
- All visual elements remain EquipeMed branded
- Same colors, same logo, same overall design
- Users recognize it as EquipeMed platform

### ✅ Adds Hospital Context
- PWA installation clearly shows which hospital
- Landing page provides hospital identification
- Staff know which instance they're using

### ✅ Minimal Implementation
- Only 1 new environment variable
- 1 new template tag
- Mostly existing functionality leveraged
- Easy to test and maintain

### ✅ Backward Compatible
- Works perfectly without any environment variables
- No breaking changes to existing deployments
- Falls back to standard EquipeMed branding

## Timeline Estimate

- **Phase 1**: 30 minutes (Add environment variable)
- **Phase 2**: 30 minutes (Add template tag)
- **Phase 3**: 1 hour (Dynamic manifest implementation)
- **Phase 4**: 30 minutes (Landing page updates)
- **Phase 5**: 1 hour (Testing)
- **Phase 6**: 15 minutes (Clean up)

**Total**: 3.5 hours for complete implementation

## Success Criteria

1. ✅ PWA installation shows hospital-specific short name (e.g., "HgrsEqmd")
2. ✅ Landing page subtly indicates which hospital
3. ✅ EquipeMed branding completely preserved
4. ✅ No visual design changes
5. ✅ Works perfectly without environment variables
6. ✅ Easy to configure per hospital instance
7. ✅ No regression in existing functionality