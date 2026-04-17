"""
Dialect profile descriptor for ``easymd_v1``.

This is the single source of truth for which markdown constructs the
pipeline supports.  Other modules (contract tests, renderers, etc.) must
import from here instead of maintaining their own lists.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DialectProfile:
    """Immutable descriptor for a markdown dialect."""

    name: str
    supported_constructs: tuple[str, ...]


# ---------------------------------------------------------------------------
# easymd_v1 profile
# ---------------------------------------------------------------------------

EASYMD_V1_PROFILE = DialectProfile(
    name="easymd_v1",
    supported_constructs=(
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
    ),
)


def get_supported_constructs() -> tuple[str, ...]:
    """Return the supported constructs for the default profile."""
    return EASYMD_V1_PROFILE.supported_constructs
