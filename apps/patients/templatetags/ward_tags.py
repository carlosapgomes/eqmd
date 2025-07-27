from django import template
from apps.patients.models import Ward

register = template.Library()

@register.inclusion_tag("patients/partials/ward_badge.html")
def ward_badge(ward):
    """Display a ward badge with abbreviation and name"""
    return {"ward": ward}

@register.simple_tag
def ward_patient_count(ward):
    """Get current patient count for a ward"""
    return ward.get_current_patients_count()

@register.simple_tag
def get_active_wards():
    """Get all active wards"""
    return Ward.objects.filter(is_active=True).order_by("name")