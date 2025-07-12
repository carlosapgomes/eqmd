from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def hospital_name():
    """Get the configured hospital name from settings"""
    return getattr(settings, 'HOSPITAL_CONFIG', {}).get('name', 'EquipeMed Hospital')

@register.simple_tag
def hospital_address():
    """Get the configured hospital address from settings"""
    return getattr(settings, 'HOSPITAL_CONFIG', {}).get('address', '')

@register.simple_tag
def hospital_phone():
    """Get the configured hospital phone from settings"""
    return getattr(settings, 'HOSPITAL_CONFIG', {}).get('phone', '')

@register.simple_tag
def hospital_email():
    """Get the configured hospital email from settings"""
    return getattr(settings, 'HOSPITAL_CONFIG', {}).get('email', '')

@register.simple_tag
def hospital_logo():
    """Get the configured hospital logo URL from settings"""
    hospital_config = getattr(settings, 'HOSPITAL_CONFIG', {})
    if hospital_config.get('logo_url'):
        return hospital_config['logo_url']
    elif hospital_config.get('logo_path'):
        return settings.STATIC_URL + hospital_config['logo_path']
    return settings.STATIC_URL + 'images/logo.png'

@register.inclusion_tag('core/partials/hospital_header.html')
def hospital_header():
    """Render hospital header with configuration from settings"""
    hospital_config = getattr(settings, 'HOSPITAL_CONFIG', {})
    return {
        'hospital': hospital_config,
        'hospital_name': hospital_config.get('name', 'EquipeMed Hospital'),
        'hospital_address': hospital_config.get('address', ''),
        'hospital_phone': hospital_config.get('phone', ''),
        'hospital_email': hospital_config.get('email', ''),
    }

@register.simple_tag
def hospital_branding():
    """Get complete hospital branding info as dict"""
    return getattr(settings, 'HOSPITAL_CONFIG', {})