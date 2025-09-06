from django import template
from ..views import can_edit_discharge_report, can_delete_discharge_report

register = template.Library()


@register.simple_tag
def can_edit_discharge_report_tag(user, report):
    """Template tag to check if user can edit discharge report"""
    return can_edit_discharge_report(user, report)


@register.simple_tag
def can_delete_discharge_report_tag(user, report):
    """Template tag to check if user can delete discharge report"""
    return can_delete_discharge_report(user, report)