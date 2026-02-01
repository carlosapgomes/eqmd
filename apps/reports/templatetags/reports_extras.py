"""
Template tags for reports app.
"""

import markdown

from django import template
from django.utils.safestring import mark_safe

from apps.reports.services.permissions import can_manage_report_templates as can_manage

register = template.Library()


@register.filter
def can_manage_report_templates(user):
    """Template filter to check if user can manage report templates."""
    return can_manage(user)


@register.filter
def markdown_filter(value):
    """
    Render markdown text to HTML.

    Args:
        value: Markdown text string

    Returns:
        Safe HTML string
    """
    if not value:
        return ""

    md = markdown.Markdown(extensions=['extra', 'nl2br'])
    html = md.convert(value)
    return mark_safe(html)
