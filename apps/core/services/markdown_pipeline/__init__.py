"""
Markdown rendering pipeline — public API.

Usage::

    from apps.core.services.markdown_pipeline import parse_markdown, render_markdown_html

    doc = parse_markdown(markdown_text)
    html = render_markdown_html(markdown_text)
"""

from apps.core.services.markdown_pipeline.html_renderer import render_html as render_markdown_html
from apps.core.services.markdown_pipeline.parser import parse_markdown
from apps.core.services.markdown_pipeline.profile import (
    EASYMD_V1_PROFILE,
    get_supported_constructs,
)

__all__ = [
    "EASYMD_V1_PROFILE",
    "get_supported_constructs",
    "parse_markdown",
    "render_markdown_html",
]
