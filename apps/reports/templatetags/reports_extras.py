"""
Template tags for reports app.
"""

from django import template
from django.utils.safestring import mark_safe

from apps.core.services.markdown_pipeline import render_markdown_html
from apps.reports.services.permissions import can_manage_report_templates as can_manage

register = template.Library()


@register.filter
def can_manage_report_templates(user):
    """Template filter to check if user can manage report templates."""
    return can_manage(user)


@register.filter
def markdown_filter(value):
    """
    Render markdown text to safe HTML via the shared pipeline.

    Args:
        value: Markdown text string

    Returns:
        Safe HTML string
    """
    if not value:
        return ""

    html = render_markdown_html(value)
    return mark_safe(html)
