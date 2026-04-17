"""
PDF renderer — converts the pipeline IR into ReportLab flowables.

Walks the parsed IR tree and produces a flat list of ReportLab
``Flowable`` objects suitable for inclusion in any Platypus story.

Design decisions
----------------
- **Inline semantics** (bold, italic, strikethrough, inline code,
  link text) are rendered as ReportLab paragraph markup (``<b>``,
  ``<i>``, ``<strike>``, ``<font>``, ``<a>``).
- **Nested lists** are rendered with cumulative left-indent per nesting
  level so hierarchy is visible in the PDF.
- **Fallbacks** for constructs with constrained PDF styling:
    - *Tables* → ``Table`` flowable with plain cell text.
    - *Blockquotes* → indented ``Paragraph`` prefixed with a vertical
      bar character.
    - *Code blocks* → monospace ``Paragraph`` with the raw content.
- The renderer is decoupled from page layout; it only produces
  content-level flowables.

Usage::

    from apps.core.services.markdown_pipeline import parse_markdown
    from apps.core.services.markdown_pipeline.pdf_renderer import (
        render_markdown_pdf_flowables,
    )

    doc = parse_markdown(text)
    flowables = render_markdown_pdf_flowables(doc, styles, options)
"""

from __future__ import annotations

from html import escape as html_escape
from typing import Any

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Flowable,
)

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

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

LIST_INDENT_PER_LEVEL = 12  # pt per nesting level
COMPACT_BODY_SIZE = 10
COMPACT_LEADING = 12
COMPACT_PARA_SPACER = 2
COMPACT_SECTION_SPACER = 4
CODE_FONT = "Courier"
MONO_FONT_SIZE = 9

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

FlowableList = list[Flowable]


def render_markdown_pdf_flowables(
    document: DocumentNode,
    styles: Any,
    options: dict | None = None,
) -> FlowableList:
    """Render a parsed IR *document* into ReportLab flowables.

    Parameters
    ----------
    document:
        A ``DocumentNode`` returned by ``parse_markdown``.
    styles:
        A ReportLab ``StyleSheet`` (or compatible mapping).  The renderer
        expects the following styles to exist or will create them lazily:
        ``CompactSectionBar``, ``CompactBody``, ``CompactList``.
    options:
        Optional dict for future extensions (currently unused).

    Returns
    -------
    list[Flowable]
        A flat list of ReportLab flowables.
    """
    opts = options or {}
    ctx = _RenderingContext(styles, opts)
    return ctx.render_document(document)


# ---------------------------------------------------------------------------
# Rendering context
# ---------------------------------------------------------------------------


class _RenderingContext:
    """Accumulates flowables while walking the IR tree."""

    def __init__(self, styles: Any, options: dict) -> None:
        self.styles = styles
        self.options = options
        self._ensure_styles()

    # -- style bootstrap ---------------------------------------------------

    def _ensure_styles(self) -> None:
        """Ensure the compact paragraph styles exist in the stylesheet."""
        existing = {s.name for s in self.styles.byName.values()}
        if "CompactSectionBar" not in existing:
            self.styles.add(ParagraphStyle(
                name="CompactSectionBar",
                parent=self.styles["Normal"],
                fontSize=COMPACT_BODY_SIZE,
                fontName="Times-Bold",
                spaceBefore=COMPACT_PARA_SPACER,
                spaceAfter=COMPACT_PARA_SPACER,
                leading=COMPACT_LEADING,
                alignment=TA_LEFT,
            ))
        if "CompactBody" not in existing:
            self.styles.add(ParagraphStyle(
                name="CompactBody",
                parent=self.styles["Normal"],
                fontSize=COMPACT_BODY_SIZE,
                fontName="Times-Roman",
                spaceBefore=COMPACT_PARA_SPACER,
                spaceAfter=COMPACT_PARA_SPACER,
                leading=COMPACT_LEADING,
                alignment=TA_JUSTIFY,
            ))
        if "CompactList" not in existing:
            self.styles.add(ParagraphStyle(
                name="CompactList",
                parent=self.styles["Normal"],
                fontSize=COMPACT_BODY_SIZE,
                fontName="Times-Roman",
                spaceBefore=COMPACT_PARA_SPACER,
                spaceAfter=COMPACT_PARA_SPACER,
                leading=COMPACT_LEADING,
                leftIndent=LIST_INDENT_PER_LEVEL,
                alignment=TA_LEFT,
            ))

    # -- document ----------------------------------------------------------

    def render_document(self, doc: DocumentNode) -> FlowableList:
        flowables: FlowableList = []
        for child in doc.children:
            flowables.extend(self._render_block(child))
        return flowables

    # -- block dispatch ----------------------------------------------------

    def _render_block(self, node: Any) -> FlowableList:
        if isinstance(node, HeadingNode):
            return self._render_heading(node)
        if isinstance(node, ParagraphNode):
            return self._render_paragraph(node)
        if isinstance(node, ListNode):
            return self._render_list(node, level=0)
        if isinstance(node, QuoteNode):
            return self._render_quote(node)
        if isinstance(node, CodeBlockNode):
            return self._render_code_block(node)
        if isinstance(node, TableNode):
            return self._render_table(node)
        if isinstance(node, ThematicBreakNode):
            return self._render_thematic_break()
        return []

    # -- heading -----------------------------------------------------------

    def _render_heading(self, node: HeadingNode) -> FlowableList:
        markup = self._render_inline_children(node.children)
        para = Paragraph(
            f"<b>{markup}</b>",
            self.styles["CompactSectionBar"],
        )
        return [Spacer(1, COMPACT_SECTION_SPACER), para,
                Spacer(1, COMPACT_PARA_SPACER)]

    # -- paragraph ---------------------------------------------------------

    def _render_paragraph(self, node: ParagraphNode) -> FlowableList:
        markup = self._render_inline_children(node.children)
        para = Paragraph(markup, self.styles["CompactBody"])
        return [para]

    # -- list (with nesting) -----------------------------------------------

    def _render_list(self, node: ListNode, level: int = 0) -> FlowableList:
        flowables: FlowableList = [Spacer(1, COMPACT_PARA_SPACER)]
        for idx, item in enumerate(node.children, 1):
            flowables.extend(
                self._render_list_item(item, node.ordered, idx, level)
            )
        flowables.append(Spacer(1, COMPACT_PARA_SPACER))
        return flowables

    def _render_list_item(
        self,
        node: ListItemNode,
        ordered: bool,
        index: int,
        level: int,
    ) -> FlowableList:
        flowables: FlowableList = []

        # Separate inline children from nested block children
        inline_parts: list[str] = []
        block_children: list[Any] = []

        for child in node.children:
            if isinstance(child, (
                HeadingNode, ParagraphNode, ListNode, QuoteNode,
                CodeBlockNode, TableNode, ThematicBreakNode,
            )):
                block_children.append(child)
            else:
                inline_parts.append(self._render_inline(child))

        # Build bullet / number prefix
        if node.checked is True:
            prefix = "[x] "
        elif node.checked is False:
            prefix = "[ ] "
        elif ordered:
            prefix = f"{index}. "
        else:
            prefix = "\u2022 "  # • BULLET

        inline_markup = "".join(inline_parts)
        indent = LIST_INDENT_PER_LEVEL * (level + 1)

        style = ParagraphStyle(
            f"CompactList_L{level}_{id(node)}",
            parent=self.styles["CompactList"],
            leftIndent=indent,
        )
        para = Paragraph(f"{prefix}{inline_markup}", style)
        flowables.append(para)

        # Render nested block children
        for child in block_children:
            if isinstance(child, ListNode):
                flowables.extend(self._render_list(child, level=level + 1))
            elif isinstance(child, ParagraphNode):
                # Nested paragraph within list item: render inline
                nested_markup = self._render_inline_children(child.children)
                nested_style = ParagraphStyle(
                    f"CompactList_NestedPara_{id(child)}",
                    parent=self.styles["CompactList"],
                    leftIndent=indent + LIST_INDENT_PER_LEVEL,
                )
                flowables.append(Paragraph(nested_markup, nested_style))
            else:
                flowables.extend(self._render_block(child))

        return flowables

    # -- blockquote --------------------------------------------------------

    def _render_quote(self, node: QuoteNode) -> FlowableList:
        """Fallback: render blockquote as indented paragraph with │ prefix."""
        flowables: FlowableList = [Spacer(1, COMPACT_PARA_SPACER)]
        for child in node.children:
            if isinstance(child, ParagraphNode):
                markup = self._render_inline_children(child.children)
                style = ParagraphStyle(
                    f"QuotePara_{id(child)}",
                    parent=self.styles["CompactBody"],
                    leftIndent=LIST_INDENT_PER_LEVEL * 2,
                    textColor=colors.grey,
                )
                para = Paragraph(f"\u2502 {markup}", style)
                flowables.append(para)
            elif isinstance(child, QuoteNode):
                # Nested quote: add extra indent
                nested_style_base = ParagraphStyle(
                    f"QuoteNested_{id(child)}",
                    parent=self.styles["CompactBody"],
                    leftIndent=LIST_INDENT_PER_LEVEL * 3,
                    textColor=colors.grey,
                )
                for sub in child.children:
                    if isinstance(sub, ParagraphNode):
                        markup = self._render_inline_children(sub.children)
                        flowables.append(
                            Paragraph(f"\u2502 {markup}", nested_style_base)
                        )
            else:
                flowables.extend(self._render_block(child))
        flowables.append(Spacer(1, COMPACT_PARA_SPACER))
        return flowables

    # -- code block --------------------------------------------------------

    def _render_code_block(self, node: CodeBlockNode) -> FlowableList:
        """Fallback: render code block in monospace font."""
        flowables: FlowableList = [Spacer(1, COMPACT_PARA_SPACER)]
        escaped = html_escape(node.content)
        # Replace newlines with <br/> for ReportLab
        content = escaped.replace("\n", "<br/>")
        style = ParagraphStyle(
            f"CodeBlock_{id(node)}",
            parent=self.styles["Normal"],
            fontName=CODE_FONT,
            fontSize=MONO_FONT_SIZE,
            leading=MONO_FONT_SIZE + 2,
            leftIndent=LIST_INDENT_PER_LEVEL,
            spaceBefore=2,
            spaceAfter=2,
            backColor=colors.Color(0.95, 0.95, 0.95),
        )
        flowables.append(Paragraph(content, style))
        flowables.append(Spacer(1, COMPACT_PARA_SPACER))
        return flowables

    # -- table -------------------------------------------------------------

    def _render_table(self, node: TableNode) -> FlowableList:
        """Fallback: render table as a ReportLab Table flowable."""
        flowables: FlowableList = [Spacer(1, COMPACT_PARA_SPACER)]

        # Build cell data
        data: list[list[str]] = []

        # Header row
        if node.headers:
            header_cells = []
            for cell in node.headers:
                header_cells.append(
                    self._render_inline_children(cell)
                )
            data.append(header_cells)

        # Body rows
        for row in node.rows:
            row_cells = []
            for cell in row:
                row_cells.append(
                    self._render_inline_children(cell)
                )
            data.append(row_cells)

        if not data:
            return flowables

        # Column count from first row
        num_cols = len(data[0])
        col_width = 450 / max(num_cols, 1)
        col_widths = [col_width] * num_cols

        table = Table(data, colWidths=col_widths)

        style_cmds = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("BOX", (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ]

        # Bold header row if present
        if node.headers:
            style_cmds.append(
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold")
            )

        table.setStyle(TableStyle(style_cmds))
        flowables.append(table)
        flowables.append(Spacer(1, COMPACT_PARA_SPACER))
        return flowables

    # -- thematic break ----------------------------------------------------

    def _render_thematic_break(self) -> FlowableList:
        """Render a horizontal rule as a thin line."""
        return [Spacer(1, COMPACT_PARA_SPACER)]

    # -- inline rendering --------------------------------------------------

    def _render_inline_children(self, children: tuple) -> str:
        parts: list[str] = []
        for child in children:
            parts.append(self._render_inline(child))
        return "".join(parts)

    def _render_inline(self, node: Any) -> str:
        if isinstance(node, TextNode):
            return html_escape(node.text)
        if isinstance(node, StrongNode):
            inner = self._render_inline_children(node.children)
            return f"<b>{inner}</b>"
        if isinstance(node, EmphasisNode):
            inner = self._render_inline_children(node.children)
            return f"<i>{inner}</i>"
        if isinstance(node, StrikeNode):
            inner = self._render_inline_children(node.children)
            return f"<strike>{inner}</strike>"
        if isinstance(node, CodeInlineNode):
            escaped = html_escape(node.text)
            return (
                f'<font face="{CODE_FONT}" size="{MONO_FONT_SIZE}">'
                f"{escaped}</font>"
            )
        if isinstance(node, LinkNode):
            content = self._render_inline_children(node.children)
            href = html_escape(node.href)
            # ReportLab Paragraph supports <a> with href
            return f'<a href="{href}" color="blue">{content}</a>'
        if isinstance(node, HardBreakNode):
            return "<br/>"
        # Fallback for unknown inline nodes
        if hasattr(node, "text"):
            return html_escape(node.text)
        return ""
