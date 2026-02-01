"""
Template tags for reports app.
"""

from django import template

from apps.reports.services.permissions import can_manage_report_templates as can_manage

register = template.Library()


@register.filter
def can_manage_report_templates(user):
    """Template filter to check if user can manage report templates."""
    return can_manage(user)
