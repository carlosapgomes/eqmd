"""
Unit tests for the markdown pipeline parser, IR, and profile.

TDD – written FIRST (RED phase). These tests define the contract
that the parser, IR nodes, and profile descriptor must satisfy.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.test import SimpleTestCase

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "tests/fixtures/markdown/easymd_v1"
)

# ---------------------------------------------------------------------------
# Imports under test – will fail until implementation exists (RED)
# ---------------------------------------------------------------------------

from apps.core.services.markdown_pipeline.ir import (  # noqa: E402
    DocumentNode,
    HeadingNode,
    ParagraphNode,
    ListNode,
    ListItemNode,
    QuoteNode,
    CodeBlockNode,
    TableNode,
    ThematicBreakNode,
    TextNode,
    StrongNode,
    EmphasisNode,
    StrikeNode,
    CodeInlineNode,
    LinkNode,
    HardBreakNode,
)
from apps.core.services.markdown_pipeline.parser import (  # noqa: E402
    parse_markdown,
)
from apps.core.services.markdown_pipeline.profile import (  # noqa: E402
    EASYMD_V1_PROFILE,
    get_supported_constructs,
)


# ===========================================================================
# Helper
# ===========================================================================


def _fixture(name: str) -> str:
    """Return the markdown text for a fixture stem."""
    path = FIXTURES_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


# ===========================================================================
# Profile tests
# ===========================================================================


class TestEasymdV1Profile(SimpleTestCase):
    """Validate profile descriptor correctness."""

    def test_profile_name(self) -> None:
        self.assertEqual(EASYMD_V1_PROFILE.name, "easymd_v1")

    def test_profile_has_supported_constructs(self) -> None:
        constructs = get_supported_constructs()
        self.assertIsInstance(constructs, tuple)
        self.assertGreater(len(constructs), 0)

    def test_profile_constructs_are_frozen(self) -> None:
        """SUPPORTED_CONSTRUCTS must be an immutable sequence."""
        constructs = get_supported_constructs()
        with self.assertRaises((TypeError, AttributeError)):
            constructs[0] = "mutated"  # type: ignore[index]

    def test_profile_covers_all_design_constructs(self) -> None:
        """Ensure the profile covers every construct listed in the design."""
        expected = {
            "headings",
            "paragraphs",
            "emphasis",
            "strong",
            "strikethrough",
            "links",
            "inline_code",
            "fenced_code_blocks",
            "ordered_lists",
            "unordered_lists",
            "nested_lists",
            "blockquotes",
            "tables",
            "task_lists",
            "thematic_breaks",
            "hard_breaks",
        }
        actual = set(get_supported_constructs())
        self.assertSetEqual(actual, expected)


# ===========================================================================
# Parser core tests (mandatory from slice prompt)
# ===========================================================================


class TestParserPreservesNestedListHierarchy(SimpleTestCase):
    """Nested lists must produce an IR tree that preserves nesting depth."""

    def test_nested_list_hierarchy(self) -> None:
        """test_parser_preserves_nested_list_hierarchy"""
        md = _fixture("nested_lists")
        doc = parse_markdown(md)

        # Collect all list nodes
        lists = _collect_nodes(doc, ListNode)
        self.assertGreater(len(lists), 0, "Expected list nodes in IR")

        # Find a list item that contains a nested list
        found_nested = False
        for li in _collect_nodes(doc, ListItemNode):
            child_lists = [c for c in li.children if isinstance(c, ListNode)]
            if child_lists:
                found_nested = True
                # The nested list should itself contain list items
                nested_items = [
                    c
                    for c in child_lists[0].children
                    if isinstance(c, ListItemNode)
                ]
                self.assertGreater(
                    len(nested_items),
                    0,
                    "Nested list must contain list items",
                )
                break

        self.assertTrue(found_nested, "No nested list hierarchy found in IR")

    def test_ordered_list_preserves_type(self) -> None:
        md = "1. First\n2. Second\n3. Third\n"
        doc = parse_markdown(md)
        lists = _collect_nodes(doc, ListNode)
        self.assertEqual(len(lists), 1)
        self.assertEqual(lists[0].ordered, True)

    def test_unordered_list_preserves_type(self) -> None:
        md = "- Alpha\n- Beta\n- Gamma\n"
        doc = parse_markdown(md)
        lists = _collect_nodes(doc, ListNode)
        self.assertEqual(len(lists), 1)
        self.assertEqual(lists[0].ordered, False)

    def test_mixed_nesting_depth_3(self) -> None:
        """Three levels of nesting must all appear in the IR."""
        md = "- Level 1\n  - Level 2\n    - Level 3\n"
        doc = parse_markdown(md)
        lists = _collect_nodes(doc, ListNode)
        # At least 3 list nodes: outer, middle, inner
        self.assertGreaterEqual(len(lists), 3)

    def test_list_item_text_content(self) -> None:
        md = "1. First item\n2. Second item\n"
        doc = parse_markdown(md)
        items = _collect_nodes(doc, ListItemNode)
        texts = []
        for item in items:
            for child in item.children:
                if isinstance(child, TextNode):
                    texts.append(child.text)
        self.assertIn("First item", texts)
        self.assertIn("Second item", texts)


class TestParserEmitsInlineNodesForCoreFormatting(SimpleTestCase):
    """Inline formatting must produce specific inline node types."""

    def test_inline_nodes_for_core_formatting(self) -> None:
        """test_parser_emits_inline_nodes_for_core_formatting"""
        md = _fixture("inline_formatting")
        doc = parse_markdown(md)

        # Must contain Strong nodes
        strongs = _collect_nodes(doc, StrongNode)
        self.assertGreater(len(strongs), 0, "Expected Strong nodes")

        # Must contain Emphasis nodes
        ems = _collect_nodes(doc, EmphasisNode)
        self.assertGreater(len(ems), 0, "Expected Emphasis nodes")

        # Must contain Strike nodes
        strikes = _collect_nodes(doc, StrikeNode)
        self.assertGreater(len(strikes), 0, "Expected Strike nodes")

        # Must contain CodeInline nodes
        codes = _collect_nodes(doc, CodeInlineNode)
        self.assertGreater(len(codes), 0, "Expected CodeInline nodes")

        # Must contain Link nodes
        links = _collect_nodes(doc, LinkNode)
        self.assertGreater(len(links), 0, "Expected Link nodes")

        # Must contain HardBreak nodes
        breaks = _collect_nodes(doc, HardBreakNode)
        self.assertGreater(len(breaks), 0, "Expected HardBreak nodes")

    def test_strong_node_contains_text(self) -> None:
        md = "This is **bold text** here.\n"
        doc = parse_markdown(md)
        strongs = _collect_nodes(doc, StrongNode)
        self.assertEqual(len(strongs), 1)
        text_children = [
            c for c in strongs[0].children if isinstance(c, TextNode)
        ]
        self.assertTrue(
            any("bold text" in t.text for t in text_children),
            "Strong node should contain 'bold text'",
        )

    def test_emphasis_node_contains_text(self) -> None:
        md = "This is *italic text* here.\n"
        doc = parse_markdown(md)
        ems = _collect_nodes(doc, EmphasisNode)
        self.assertEqual(len(ems), 1)
        text_children = [
            c for c in ems[0].children if isinstance(c, TextNode)
        ]
        self.assertTrue(
            any("italic text" in t.text for t in text_children),
            "Emphasis node should contain 'italic text'",
        )

    def test_strike_node_contains_text(self) -> None:
        md = "This is ~~strikethrough~~ text.\n"
        doc = parse_markdown(md)
        strikes = _collect_nodes(doc, StrikeNode)
        self.assertEqual(len(strikes), 1)
        text_children = [
            c for c in strikes[0].children if isinstance(c, TextNode)
        ]
        self.assertTrue(
            any("strikethrough" in t.text for t in text_children),
            "Strike node should contain 'strikethrough'",
        )

    def test_link_node_has_href(self) -> None:
        md = "Visit [example](https://example.com) for info.\n"
        doc = parse_markdown(md)
        links = _collect_nodes(doc, LinkNode)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].href, "https://example.com")

    def test_inline_code_node_has_text(self) -> None:
        md = "Use `print()` to output.\n"
        doc = parse_markdown(md)
        codes = _collect_nodes(doc, CodeInlineNode)
        self.assertEqual(len(codes), 1)
        self.assertEqual(codes[0].text, "print()")


class TestParserHandlesTablesQuotesAndCodeBlocks(SimpleTestCase):
    """Tables, blockquotes, and fenced code blocks must parse correctly."""

    def test_tables_quotes_and_code_blocks(self) -> None:
        """test_parser_handles_tables_quotes_and_code_blocks"""
        md = _fixture("blockquote_code")
        doc = parse_markdown(md)

        # Must contain QuoteNode
        quotes = _collect_nodes(doc, QuoteNode)
        self.assertGreater(len(quotes), 0, "Expected Quote nodes")

        # Must contain CodeBlockNode
        code_blocks = _collect_nodes(doc, CodeBlockNode)
        self.assertGreater(len(code_blocks), 0, "Expected CodeBlock nodes")

    def test_table_parsing(self) -> None:
        md = _fixture("tables_links")
        doc = parse_markdown(md)
        tables = _collect_nodes(doc, TableNode)
        self.assertGreater(len(tables), 0, "Expected Table nodes")

    def test_code_block_preserves_language(self) -> None:
        md = "```python\nprint('hello')\n```\n"
        doc = parse_markdown(md)
        code_blocks = _collect_nodes(doc, CodeBlockNode)
        self.assertEqual(len(code_blocks), 1)
        self.assertEqual(code_blocks[0].language, "python")

    def test_code_block_preserves_content(self) -> None:
        md = "```\nsome code\n```\n"
        doc = parse_markdown(md)
        code_blocks = _collect_nodes(doc, CodeBlockNode)
        self.assertEqual(len(code_blocks), 1)
        self.assertIn("some code", code_blocks[0].content)

    def test_blockquote_preserves_text(self) -> None:
        md = "> This is quoted.\n> Second line.\n"
        doc = parse_markdown(md)
        quotes = _collect_nodes(doc, QuoteNode)
        self.assertGreater(len(quotes), 0)
        # Check text content exists somewhere in the quote tree
        texts = _collect_nodes(quotes[0], TextNode)
        combined = " ".join(t.text for t in texts)
        self.assertIn("quoted", combined)

    def test_table_has_rows_and_cells(self) -> None:
        md = (
            "| A | B |\n"
            "| - | - |\n"
            "| 1 | 2 |\n"
        )
        doc = parse_markdown(md)
        tables = _collect_nodes(doc, TableNode)
        self.assertEqual(len(tables), 1)
        table = tables[0]
        # Must have headers and rows
        self.assertGreater(len(table.headers), 0)
        self.assertGreater(len(table.rows), 0)

    def test_thematic_break(self) -> None:
        md = "Para above.\n\n---\n\nPara below.\n"
        doc = parse_markdown(md)
        breaks = _collect_nodes(doc, ThematicBreakNode)
        self.assertEqual(len(breaks), 1)

    def test_heading_levels(self) -> None:
        md = "# H1\n\n## H2\n\n### H3\n"
        doc = parse_markdown(md)
        headings = _collect_nodes(doc, HeadingNode)
        levels = [h.level for h in headings]
        self.assertIn(1, levels)
        self.assertIn(2, levels)
        self.assertIn(3, levels)


# ===========================================================================
# Determinism tests
# ===========================================================================


class TestParserDeterminism(SimpleTestCase):
    """Parser output must be deterministic across repeated calls."""

    def test_deterministic_output(self) -> None:
        md = _fixture("mixed_clinical_note")
        doc1 = parse_markdown(md)
        doc2 = parse_markdown(md)
        self.assertEqual(
            _node_signature(doc1),
            _node_signature(doc2),
            "Parser output must be deterministic",
        )


# ===========================================================================
# Task list tests
# ===========================================================================


class TestParserHandlesTaskLists(SimpleTestCase):
    """Task list checkboxes must be captured in the IR."""

    def test_task_list_checked_and_unchecked(self) -> None:
        md = _fixture("task_lists")
        doc = parse_markdown(md)
        items = _collect_nodes(doc, ListItemNode)
        checked = [i for i in items if i.checked is True]
        unchecked = [i for i in items if i.checked is False]
        self.assertGreater(len(checked), 0, "Expected checked task items")
        self.assertGreater(len(unchecked), 0, "Expected unchecked task items")

    def test_regular_list_item_not_checked(self) -> None:
        md = "- Normal item\n- Another item\n"
        doc = parse_markdown(md)
        items = _collect_nodes(doc, ListItemNode)
        for item in items:
            self.assertIsNone(item.checked)


# ===========================================================================
# Contract hardening tests (3 reforços do Slice 01)
# ===========================================================================


class TestContractHardening(SimpleTestCase):
    """Hardening tests required by slice prompt reinforcements."""

    def test_detect_orphan_meta_json(self) -> None:
        """Fail if a .meta.json exists without a corresponding .md file."""
        meta_files = sorted(FIXTURES_DIR.glob("*.meta.json"))
        for meta_file in meta_files:
            # "foo.meta.json" → "foo.md" (strip .meta.json, add .md)
            md_file = meta_file.with_name(
                meta_file.name[: -len(".meta.json")] + ".md"
            )
            self.assertTrue(
                md_file.exists(),
                f"Orphan .meta.json detected: {meta_file.name} "
                f"has no corresponding .md file",
            )

    def test_constructs_non_empty_in_every_meta(self) -> None:
        """Every .meta.json must have a non-empty 'constructs' list."""
        meta_files = sorted(FIXTURES_DIR.glob("*.meta.json"))
        self.assertGreater(len(meta_files), 0, "No .meta.json files found")
        for meta_file in meta_files:
            with self.subTest(file=meta_file.name):
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                constructs = meta.get("constructs", [])
                self.assertIsInstance(
                    constructs,
                    list,
                    f"{meta_file.name}: 'constructs' must be a list",
                )
                self.assertGreater(
                    len(constructs),
                    0,
                    f"{meta_file.name}: 'constructs' must not be empty",
                )

    def test_contract_test_uses_centralized_supported_constructs(self) -> None:
        """Contract test SUPPORTED_CONSTRUCTS must match the profile's
        centralized source, eliminating duplication."""
        from apps.core.tests.test_markdown_dialect_contract import (
            SUPPORTED_CONSTRUCTS as contract_constructs,
        )

        profile_constructs = set(get_supported_constructs())
        contract_set = set(contract_constructs)
        self.assertSetEqual(
            profile_constructs,
            contract_set,
            f"Contract SUPPORTED_CONSTRUCTS diverges from profile: "
            f"extra in contract={contract_set - profile_constructs}, "
            f"missing from contract={profile_constructs - contract_set}",
        )


# ===========================================================================
# IR node structure tests
# ===========================================================================


class TestIRNodeStructure(SimpleTestCase):
    """Verify IR node basic properties."""

    def test_document_node_has_children(self) -> None:
        md = "# Title\n\nParagraph.\n"
        doc = parse_markdown(md)
        self.assertIsInstance(doc, DocumentNode)
        self.assertGreater(len(doc.children), 0)

    def test_heading_node_has_level_and_children(self) -> None:
        md = "## My Heading\n"
        doc = parse_markdown(md)
        headings = _collect_nodes(doc, HeadingNode)
        h = headings[0]
        self.assertEqual(h.level, 2)
        texts = [c for c in h.children if isinstance(c, TextNode)]
        self.assertTrue(
            any("My Heading" in t.text for t in texts),
        )

    def test_paragraph_contains_inline_nodes(self) -> None:
        md = "Hello **world**.\n"
        doc = parse_markdown(md)
        paras = _collect_nodes(doc, ParagraphNode)
        self.assertGreater(len(paras), 0)
        para = paras[0]
        has_text = any(isinstance(c, TextNode) for c in para.children)
        has_strong = any(isinstance(c, StrongNode) for c in para.children)
        self.assertTrue(has_text, "Paragraph should contain TextNode")
        self.assertTrue(has_strong, "Paragraph should contain StrongNode")


# ===========================================================================
# Helpers
# ===========================================================================


def _collect_nodes(node: object, node_type: type) -> list:
    """Recursively collect all nodes of a given type from the IR tree."""
    results: list = []
    if isinstance(node, node_type):
        results.append(node)
    children = getattr(node, "children", [])
    for child in children:
        results.extend(_collect_nodes(child, node_type))
    # Handle TableNode rows (not in children)
    if isinstance(node, TableNode):
        for row in node.rows:
            for cell in row:
                results.extend(_collect_nodes(cell, node_type))
    return results


def _node_signature(node: object, depth: int = 0) -> str:
    """Produce a deterministic string signature for an IR tree."""
    if isinstance(node, DocumentNode):
        inner = "|".join(_node_signature(c, depth + 1) for c in node.children)
        return f"DOC[{inner}]"
    if isinstance(node, HeadingNode):
        inner = "|".join(_node_signature(c, depth + 1) for c in node.children)
        return f"H{node.level}[{inner}]"
    if isinstance(node, ParagraphNode):
        inner = "|".join(_node_signature(c, depth + 1) for c in node.children)
        return f"P[{inner}]"
    if isinstance(node, ListNode):
        inner = "|".join(_node_signature(c, depth + 1) for c in node.children)
        prefix = "OL" if node.ordered else "UL"
        return f"{prefix}[{inner}]"
    if isinstance(node, ListItemNode):
        inner = "|".join(_node_signature(c, depth + 1) for c in node.children)
        check = f":checked={node.checked}" if node.checked is not None else ""
        return f"LI{check}[{inner}]"
    if isinstance(node, QuoteNode):
        inner = "|".join(_node_signature(c, depth + 1) for c in node.children)
        return f"QUOTE[{inner}]"
    if isinstance(node, CodeBlockNode):
        return f"CODE[{node.language}:{node.content!r}]"
    if isinstance(node, TableNode):
        hdr = ",".join(
            ",".join(_node_signature(c, depth + 1) for c in col)
            for col in node.headers
        )
        rows = ";".join(
            ",".join(
                ",".join(_node_signature(c, depth + 1) for c in cell)
                for cell in row
            )
            for row in node.rows
        )
        return f"TABLE[hdr={hdr}|rows={rows}]"
    if isinstance(node, ThematicBreakNode):
        return "HR"
    if isinstance(node, TextNode):
        return f"T({node.text!r})"
    if isinstance(node, StrongNode):
        inner = "|".join(_node_signature(c, depth + 1) for c in node.children)
        return f"STRONG[{inner}]"
    if isinstance(node, EmphasisNode):
        inner = "|".join(_node_signature(c, depth + 1) for c in node.children)
        return f"EM[{inner}]"
    if isinstance(node, StrikeNode):
        inner = "|".join(_node_signature(c, depth + 1) for c in node.children)
        return f"STRIKE[{inner}]"
    if isinstance(node, CodeInlineNode):
        return f"CI({node.text!r})"
    if isinstance(node, LinkNode):
        inner = "|".join(_node_signature(c, depth + 1) for c in node.children)
        return f"LINK[{node.href}:{inner}]"
    if isinstance(node, HardBreakNode):
        return "BR"
    return f"?{type(node).__name__}"
