"""
Normalized intermediate representation (IR) for the markdown pipeline.

Each node is a frozen dataclass that describes one markdown construct.
The tree is deterministic: no node relies on insertion-order of sets or
dicts.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Inline nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TextNode:
    """Plain text span."""

    text: str
    children: tuple[()] = field(default=(), repr=False)


@dataclass(frozen=True)
class StrongNode:
    """**bold** content."""

    children: tuple = field(default=())


@dataclass(frozen=True)
class EmphasisNode:
    """*italic* content."""

    children: tuple = field(default=())


@dataclass(frozen=True)
class StrikeNode:
    """~~strikethrough~~ content."""

    children: tuple = field(default=())


@dataclass(frozen=True)
class CodeInlineNode:
    """`inline code`."""

    text: str
    children: tuple[()] = field(default=(), repr=False)


@dataclass(frozen=True)
class LinkNode:
    """[text](href) — keeps the resolved href."""

    href: str
    title: str = ""
    children: tuple = field(default=())


@dataclass(frozen=True)
class HardBreakNode:
    """Explicit hard break (two trailing spaces or ``\\``)."""

    children: tuple[()] = field(default=(), repr=False)


# ---------------------------------------------------------------------------
# Block nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeadingNode:
    """# Heading — level 1..6."""

    level: int
    children: tuple = field(default=())


@dataclass(frozen=True)
class ParagraphNode:
    """Block of inline content."""

    children: tuple = field(default=())


@dataclass(frozen=True)
class ListNode:
    """Ordered or unordered list (including task lists)."""

    ordered: bool
    children: tuple = field(default=())


@dataclass(frozen=True)
class ListItemNode:
    """Single list item. ``checked`` is ``True``/``False`` for task items,
    ``None`` for regular items."""

    checked: bool | None
    children: tuple = field(default=())


@dataclass(frozen=True)
class QuoteNode:
    """Blockquote (may be nested)."""

    children: tuple = field(default=())


@dataclass(frozen=True)
class CodeBlockNode:
    """Fenced code block with optional language tag."""

    language: str
    content: str
    children: tuple[()] = field(default=(), repr=False)


# TableNode uses lists for headers/rows because the cells contain inline
# content that can be arbitrarily complex (links, emphasis, etc.).
# Each cell is a tuple of inline nodes.


@dataclass(frozen=True)
class TableNode:
    """GFM-style table."""

    headers: tuple[tuple, ...]  # each header cell is tuple of inline nodes
    rows: tuple[tuple[tuple, ...], ...]  # each row is tuple of cells
    children: tuple[()] = field(default=(), repr=False)


@dataclass(frozen=True)
class ThematicBreakNode:
    """--- / *** / ___."""

    children: tuple[()] = field(default=(), repr=False)


@dataclass(frozen=True)
class DocumentNode:
    """Root node of a parsed markdown document."""

    children: tuple = field(default=())
