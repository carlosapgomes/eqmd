"""
HTML renderer — converts the pipeline IR into safe HTML.

Uses the parser (Slice 02) to obtain the IR, then walks the tree to
produce HTML. The result is then passed through the sanitizer to
guarantee safe output even if the input contains malicious markdown.
"""

from __future__ import annotations

from html import escape as html_escape
from typing import Union

from apps.core.services.markdown_pipeline.ir import (
    CodeBlockNode,
    CodeInlineNode,
    DocumentNode,
    EmphasisNode,
    HardBreakNode,
    HeadingNode,
    LinkNode,
    ListNode,
    ListItemNode,
    ParagraphNode,
    QuoteNode,
    StrikeNode,
    StrongNode,
    TableNode,
    TextNode,
    ThematicBreakNode,
)
from apps.core.services.markdown_pipeline.parser import parse_markdown
from apps.core.services.markdown_pipeline.sanitizer import sanitize_html


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

InlineNode = Union[
    TextNode,
    StrongNode,
    EmphasisNode,
    StrikeNode,
    CodeInlineNode,
    LinkNode,
    HardBreakNode,
]

BlockNode = Union[
    HeadingNode,
    ParagraphNode,
    ListNode,
    QuoteNode,
    CodeBlockNode,
    TableNode,
    ThematicBreakNode,
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_html(
    markdown_text: str,
    profile: str = "easymd_v1",
) -> str:
    """Convert *markdown_text* to safe HTML.

    Parses the text through the shared pipeline, renders to HTML, then
    applies sanitization.
    """
    if not markdown_text:
        return ""

    doc = parse_markdown(markdown_text, profile_name=profile)
    raw_html = _render_document(doc)
    return sanitize_html(raw_html)


# ---------------------------------------------------------------------------
# Document rendering
# ---------------------------------------------------------------------------


def _render_document(doc: DocumentNode) -> str:
    parts: list[str] = []
    for child in doc.children:
        parts.append(_render_block(child))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Block rendering
# ---------------------------------------------------------------------------


def _render_block(node: BlockNode) -> str:
    if isinstance(node, HeadingNode):
        return _render_heading(node)
    if isinstance(node, ParagraphNode):
        return _render_paragraph(node)
    if isinstance(node, ListNode):
        return _render_list(node)
    if isinstance(node, QuoteNode):
        return _render_quote(node)
    if isinstance(node, CodeBlockNode):
        return _render_code_block(node)
    if isinstance(node, TableNode):
        return _render_table(node)
    if isinstance(node, ThematicBreakNode):
        return "<hr>"
    # Fallback — should not happen
    return ""


def _render_heading(node: HeadingNode) -> str:
    tag = f"h{node.level}"
    content = _render_inline_children(node.children)
    return f"<{tag}>{content}</{tag}>"


def _render_paragraph(node: ParagraphNode) -> str:
    content = _render_inline_children(node.children)
    return f"<p>{content}</p>"


def _render_list(node: ListNode) -> str:
    tag = "ol" if node.ordered else "ul"
    items_html: list[str] = []
    for item in node.children:
        items_html.append(_render_list_item(item))
    inner = "\n".join(items_html)
    return f"<{tag}>\n{inner}\n</{tag}>"


def _render_list_item(node: ListItemNode) -> str:
    # Separate inline content from nested block content
    inline_parts: list[str] = []
    block_parts: list[str] = []

    for child in node.children:
        if isinstance(child, (HeadingNode, ParagraphNode, ListNode, QuoteNode,
                              CodeBlockNode, TableNode, ThematicBreakNode)):
            block_parts.append(_render_block(child))
        else:
            inline_parts.append(_render_inline(child))

    inline_html = "".join(inline_parts)

    # Task list checkbox
    prefix = ""
    if node.checked is not None:
        if node.checked:
            prefix = '<input type="checkbox" checked disabled> '
        else:
            prefix = '<input type="checkbox" disabled> '

    content = prefix + inline_html
    if block_parts:
        content += "\n".join(block_parts)

    return f"<li>{content}</li>"


def _render_quote(node: QuoteNode) -> str:
    parts: list[str] = []
    for child in node.children:
        parts.append(_render_block(child))
    inner = "\n".join(parts)
    return f"<blockquote>\n{inner}\n</blockquote>"


def _render_code_block(node: CodeBlockNode) -> str:
    escaped = html_escape(node.content)
    lang_class = f' class="language-{html_escape(node.language)}"' if node.language else ""
    return f"<pre><code{lang_class}>{escaped}</code></pre>"


def _render_table(node: TableNode) -> str:
    parts: list[str] = ["<table>"]

    # Header
    if node.headers:
        parts.append("<thead>")
        parts.append("<tr>")
        for cell in node.headers:
            cell_html = _render_inline_children(cell)
            parts.append(f"<th>{cell_html}</th>")
        parts.append("</tr>")
        parts.append("</thead>")

    # Body
    if node.rows:
        parts.append("<tbody>")
        for row in node.rows:
            parts.append("<tr>")
            for cell in row:
                cell_html = _render_inline_children(cell)
                parts.append(f"<td>{cell_html}</td>")
            parts.append("</tr>")
        parts.append("</tbody>")

    parts.append("</table>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Inline rendering
# ---------------------------------------------------------------------------


def _render_inline_children(children: tuple) -> str:
    parts: list[str] = []
    for child in children:
        parts.append(_render_inline(child))
    return "".join(parts)


def _render_inline(node: InlineNode) -> str:
    if isinstance(node, TextNode):
        return html_escape(node.text)
    if isinstance(node, StrongNode):
        return f"<strong>{_render_inline_children(node.children)}</strong>"
    if isinstance(node, EmphasisNode):
        return f"<em>{_render_inline_children(node.children)}</em>"
    if isinstance(node, StrikeNode):
        return f"<del>{_render_inline_children(node.children)}</del>"
    if isinstance(node, CodeInlineNode):
        return f"<code>{html_escape(node.text)}</code>"
    if isinstance(node, LinkNode):
        href = html_escape(node.href)
        title_attr = f' title="{html_escape(node.title)}"' if node.title else ""
        content = _render_inline_children(node.children)
        return f'<a href="{href}"{title_attr}>{content}</a>'
    if isinstance(node, HardBreakNode):
        return "<br>"
    # Fallback
    return html_escape(str(node))
