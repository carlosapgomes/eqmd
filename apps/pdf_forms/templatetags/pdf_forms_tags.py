from django import template
from django.conf import settings

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key.""" 
    return dictionary.get(key)


@register.simple_tag
def pdf_forms_enabled():
    """Check if PDF forms are enabled for this hospital."""
    return getattr(settings, 'PDF_FORMS_CONFIG', {}).get('enabled', False)


@register.filter
def filesizeformat(bytes_value):
    """Format file size in human readable format."""
    try:
        bytes_value = int(bytes_value)
    except (ValueError, TypeError):
        return '0 bytes'

    if bytes_value < 1024:
        return f"{bytes_value} bytes"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.1f} KB"
    elif bytes_value < 1024 * 1024 * 1024:
        return f"{bytes_value / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_value / (1024 * 1024 * 1024):.1f} GB"


@register.inclusion_tag('pdf_forms/partials/pdf_forms_menu.html', takes_context=True)
def pdf_forms_menu(context):
    """Render PDF forms menu items."""
    request = context['request']
    return {
        'user': request.user,
        'enabled': pdf_forms_enabled(),
    }


@register.simple_tag
def get_pdf_form_count():
    """Get count of active PDF form templates."""
    from apps.pdf_forms.models import PDFFormTemplate
    return PDFFormTemplate.objects.filter(is_active=True, hospital_specific=True).count()


@register.simple_tag  
def pdf_forms_config(key=None):
    """Get PDF forms configuration value."""
    config = getattr(settings, 'PDF_FORMS_CONFIG', {})
    if key:
        return config.get(key)
    return config


@register.simple_tag
def pdf_forms_max_file_size():
    """Get maximum file size for PDF forms."""
    return getattr(settings, 'PDF_FORMS_CONFIG', {}).get('max_file_size', 10 * 1024 * 1024)


@register.filter
def pdf_form_file_size_check(file_size):
    """Check if file size is within PDF forms limits."""
    max_size = pdf_forms_max_file_size()
    return file_size <= max_size