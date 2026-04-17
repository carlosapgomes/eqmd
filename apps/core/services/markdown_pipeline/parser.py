"""
Markdown parser that converts text into a normalized IR.

Uses **mistune 3** with ``renderer=None`` to obtain token dicts, then
walks the token tree to produce our frozen-dataclass IR.

The parser is deterministic: the same input always produces the same IR.
"""

from __future__ import annotations

from typing import Union

import mistune
from mistune.plugins import import_plugin

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
from apps.core.services.markdown_pipeline.profile import EASYMD_V1_PROFILE

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


def parse_markdown(
    markdown_text: str,
    profile_name: str = "easymd_v1",
) -> DocumentNode:
    """Parse *markdown_text* into a normalized IR tree.

    Parameters
    ----------
    markdown_text:
        Raw markdown source.
    profile_name:
        Dialect profile to use.  Currently only ``"easymd_v1"`` is supported.

    Returns
    -------
    DocumentNode
        Frozen, deterministic IR tree.
    """
    if profile_name != EASYMD_V1_PROFILE.name:
        raise ValueError(f"Unknown profile: {profile_name!r}")

    md = _create_mistune_parser()
    tokens, _state = md.parse(markdown_text)

    children = _convert_tokens(tokens)
    return DocumentNode(children=tuple(children))


# ---------------------------------------------------------------------------
# Parser factory
# ---------------------------------------------------------------------------


def _create_mistune_parser() -> mistune.Markdown:
    """Build a mistune Markdown instance configured for easymd_v1."""
    md = mistune.Markdown(renderer=None)
    md.use(import_plugin("table"))
    md.use(import_plugin("task_lists"))
    md.use(import_plugin("strikethrough"))
    return md


# ---------------------------------------------------------------------------
# Token → IR conversion
# ---------------------------------------------------------------------------


def _convert_tokens(tokens: list[dict]) -> list[BlockNode]:
    """Convert a list of block-level tokens to block IR nodes."""
    results: list[BlockNode] = []
    for tok in tokens:
        node = _convert_block_token(tok)
        if node is not None:
            results.append(node)
    return results


def _convert_block_token(tok: dict) -> BlockNode | None:
    """Convert a single block-level token to an IR node."""
    tok_type = tok.get("type", "")

    if tok_type == "heading":
        return _convert_heading(tok)
    if tok_type == "paragraph":
        return _convert_paragraph(tok)
    if tok_type in ("list",):
        return _convert_list(tok)
    if tok_type == "block_quote":
        return _convert_block_quote(tok)
    if tok_type == "block_code":
        return _convert_block_code(tok)
    if tok_type == "table":
        return _convert_table(tok)
    if tok_type == "thematic_break":
        return ThematicBreakNode()
    if tok_type in ("blank_line", "block_html"):
        return None
    # Unknown token types are skipped
    return None


# -- heading ---------------------------------------------------------------


def _convert_heading(tok: dict) -> HeadingNode:
    level = tok.get("attrs", {}).get("level", 1)
    inline = _convert_inline_tokens(tok.get("children", []))
    return HeadingNode(level=level, children=tuple(inline))


# -- paragraph -------------------------------------------------------------


def _convert_paragraph(tok: dict) -> ParagraphNode:
    inline = _convert_inline_tokens(tok.get("children", []))
    return ParagraphNode(children=tuple(inline))


# -- list ------------------------------------------------------------------


def _convert_list(tok: dict) -> ListNode:
    attrs = tok.get("attrs", {})
    ordered = attrs.get("ordered", False)
    children: list[ListItemNode] = []
    for child_tok in tok.get("children", []):
        children.append(_convert_list_item(child_tok))
    return ListNode(ordered=ordered, children=tuple(children))


def _convert_list_item(tok: dict) -> ListItemNode:
    tok_type = tok.get("type", "")
    checked: bool | None = None

    if tok_type == "task_list_item":
        checked = tok.get("attrs", {}).get("checked", False)

    children: list = []
    for child_tok in tok.get("children", []):
        child_type = child_tok.get("type", "")
        if child_type == "list":
            children.append(_convert_list(child_tok))
        elif child_type == "paragraph":
            # Flatten paragraph inline content directly into list item
            inline = _convert_inline_tokens(child_tok.get("children", []))
            children.extend(inline)
        elif child_type == "block_text":
            # Loose list items wrap text in block_text
            inline = _convert_inline_tokens(child_tok.get("children", []))
            children.extend(inline)
        elif child_type in ("task_list_item", "list_item"):
            children.append(_convert_list_item(child_tok))
        elif child_type == "block_quote":
            children.append(_convert_block_quote(child_tok))
        elif child_type == "block_code":
            children.append(_convert_block_code(child_tok))
        elif child_type == "table":
            children.append(_convert_table(child_tok))

    return ListItemNode(checked=checked, children=tuple(children))


# -- block quote -----------------------------------------------------------


def _convert_block_quote(tok: dict) -> QuoteNode:
    children: list = []
    for child_tok in tok.get("children", []):
        child_type = child_tok.get("type", "")
        if child_type == "paragraph":
            inline = _convert_inline_tokens(child_tok.get("children", []))
            children.append(ParagraphNode(children=tuple(inline)))
        elif child_type == "block_quote":
            children.append(_convert_block_quote(child_tok))
        elif child_type == "blank_line":
            continue
        elif child_type == "list":
            children.append(_convert_list(child_tok))
        elif child_type == "block_code":
            children.append(_convert_block_code(child_tok))
        elif child_type == "heading":
            children.append(_convert_heading(child_tok))
        elif child_type == "thematic_break":
            children.append(ThematicBreakNode())
        elif child_type == "table":
            children.append(_convert_table(child_tok))
        else:
            node = _convert_block_token(child_tok)
            if node is not None:
                children.append(node)
    return QuoteNode(children=tuple(children))


# -- code block ------------------------------------------------------------


def _convert_block_code(tok: dict) -> CodeBlockNode:
    attrs = tok.get("attrs", {})
    language = attrs.get("info", "") if attrs else ""
    content = tok.get("raw", "")
    return CodeBlockNode(language=language, content=content)


# -- table -----------------------------------------------------------------


def _convert_table(tok: dict) -> TableNode:
    headers: list[tuple] = []
    rows: list[tuple[tuple, ...]] = []

    for child_tok in tok.get("children", []):
        child_type = child_tok.get("type", "")
        if child_type == "table_head":
            for cell_tok in child_tok.get("children", []):
                if cell_tok.get("type") == "table_cell":
                    inline = _convert_inline_tokens(
                        cell_tok.get("children", [])
                    )
                    headers.append(tuple(inline))
        elif child_type == "table_body":
            for row_tok in child_tok.get("children", []):
                if row_tok.get("type") == "table_row":
                    cells: list[tuple] = []
                    for cell_tok in row_tok.get("children", []):
                        if cell_tok.get("type") == "table_cell":
                            inline = _convert_inline_tokens(
                                cell_tok.get("children", [])
                            )
                            cells.append(tuple(inline))
                    if cells:
                        rows.append(tuple(cells))

    return TableNode(headers=tuple(headers), rows=tuple(rows))


# ---------------------------------------------------------------------------
# Inline token conversion
# ---------------------------------------------------------------------------


def _convert_inline_tokens(tokens: list[dict]) -> list[InlineNode]:
    """Convert inline-level tokens to inline IR nodes."""
    results: list[InlineNode] = []
    for tok in tokens:
        node = _convert_inline_token(tok)
        if node is not None:
            results.append(node)
    return results


def _convert_inline_token(tok: dict) -> InlineNode | None:
    """Convert a single inline token to an inline IR node."""
    tok_type = tok.get("type", "")

    if tok_type == "text":
        return TextNode(text=tok.get("raw", ""))
    if tok_type == "strong":
        children = _convert_inline_tokens(tok.get("children", []))
        return StrongNode(children=tuple(children))
    if tok_type == "emphasis":
        children = _convert_inline_tokens(tok.get("children", []))
        return EmphasisNode(children=tuple(children))
    if tok_type == "strikethrough":
        children = _convert_inline_tokens(tok.get("children", []))
        return StrikeNode(children=tuple(children))
    if tok_type == "codespan":
        return CodeInlineNode(text=tok.get("raw", ""))
    if tok_type == "link":
        attrs = tok.get("attrs", {})
        href = attrs.get("url", "") if attrs else ""
        title = attrs.get("title", "") if attrs else ""
        children = _convert_inline_tokens(tok.get("children", []))
        return LinkNode(href=href, title=title, children=tuple(children))
    if tok_type == "image":
        attrs = tok.get("attrs", {})
        href = attrs.get("url", "") if attrs else ""
        alt = tok.get("attrs", {}).get("alt", "")
        return LinkNode(
            href=href, title=alt, children=(TextNode(text=alt),)
        )
    if tok_type == "linebreak":
        return HardBreakNode()
    if tok_type == "softbreak":
        # Soft break becomes a space in the text flow
        return TextNode(text=" ")
    if tok_type == "inline_html":
        return TextNode(text=tok.get("raw", ""))

    return None
