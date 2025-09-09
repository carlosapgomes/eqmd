from django import template
from ..views import can_edit_discharge_report, can_delete_discharge_report
from ..utils import clean_text_field

register = template.Library()


@register.simple_tag
def can_edit_discharge_report_tag(user, report):
    """Template tag to check if user can edit discharge report"""
    return can_edit_discharge_report(user, report)


@register.simple_tag
def can_delete_discharge_report_tag(user, report):
    """Template tag to check if user can delete discharge report"""
    return can_delete_discharge_report(user, report)


@register.filter
def clean_text(value):
    """Template filter to clean text fields for proper display"""
    if not value:
        return value
    return clean_text_field(value)