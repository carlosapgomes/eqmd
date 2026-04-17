"""
Shared Django template filter and tag for markdown rendering.

Usage in templates::

    {% load markdown_tags %}

    {{ note.content|markdown }}
    {{ note.content|markdown:"easymd_v1" }}
"""

from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

from apps.core.services.markdown_pipeline.html_renderer import render_html

register = template.Library()


@register.filter(name="markdown")
def markdown_filter(value: str, profile: str = "easymd_v1") -> str:
    """Render *value* as markdown to safe HTML.

    The output is already sanitized, so we mark it safe for Django
    template rendering.
    """
    if not value:
        return ""
    return mark_safe(render_html(value, profile=profile))
