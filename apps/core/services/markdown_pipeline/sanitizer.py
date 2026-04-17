"""
HTML sanitizer using an explicit allowlist of tags and attributes.

Only tags and attributes on the allowlist are preserved. All other
HTML is stripped (content kept, tags removed). Dangerous protocols
like ``javascript:`` and ``data:`` are blocked in ``href`` attributes.
"""

from __future__ import annotations

from html import escape as html_escape
from html.parser import HTMLParser
from io import StringIO


# ---------------------------------------------------------------------------
# Allowlist policy
# ---------------------------------------------------------------------------

#: Tags that are allowed to pass through sanitization.
ALLOWED_TAGS: frozenset[str] = frozenset({
    # Block
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "blockquote", "pre",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "th", "td",
    "hr",
    # Inline
    "strong", "b", "em", "i", "del", "s",
    "code",
    "a",
    "br",
    "img",
    # Task list checkbox
    "input",
    # Semantic wrappers
    "div", "span",
})

#: Attributes allowed per tag.  ``*`` means allowed on every allowed tag.
ALLOWED_ATTRS: dict[str, frozenset[str]] = {
    "*": frozenset(),
    "a": frozenset({"href", "title"}),
    "img": frozenset({"src", "alt", "title"}),
    "td": frozenset({"align", "colspan", "rowspan"}),
    "th": frozenset({"align", "colspan", "rowspan"}),
    "input": frozenset({"type", "checked", "disabled"}),
    "code": frozenset({"class"}),
    "pre": frozenset({"class"}),
}

#: Protocols allowed in href/src attributes.
ALLOWED_PROTOCOLS: frozenset[str] = frozenset({
    "http", "https", "mailto", "tel", "",
})


# ---------------------------------------------------------------------------
# Sanitizer implementation
# ---------------------------------------------------------------------------


class _SanitizingParser(HTMLParser):
    """HTMLParser that rebuilds HTML keeping only allowed tags/attrs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._out = StringIO()
        self._tag_stack: list[str] = []

    def get_output(self) -> str:
        return self._out.getvalue()

    # -- tag events ---------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag not in ALLOWED_TAGS:
            return  # strip disallowed tag, content flows through
        allowed = ALLOWED_ATTRS.get(tag, ALLOWED_ATTRS.get("*", frozenset()))
        global_allowed = ALLOWED_ATTRS.get("*", frozenset())
        all_allowed = allowed | global_allowed

        safe_attrs: list[tuple[str, str]] = []
        for attr_name, attr_value in attrs:
            attr_name = attr_name.lower()
            # Block any on* event attributes
            if attr_name.startswith("on"):
                continue
            if attr_name not in all_allowed:
                continue
            if attr_value is None:
                attr_value = ""
            # Validate protocol for href/src
            if attr_name in ("href", "src"):
                if not _is_safe_protocol(attr_value):
                    continue
            safe_attrs.append((attr_name, attr_value))

        self._out.write(f"<{tag}")
        for attr_name, attr_value in safe_attrs:
            escaped = attr_value.replace("&", "&amp;").replace('"', "&quot;")
            self._out.write(f' {attr_name}="{escaped}"')
        self._out.write(">")
        self._tag_stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag not in ALLOWED_TAGS:
            return
        self._out.write(f"</{tag}>")
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        self._out.write(html_escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        self._out.write(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._out.write(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        pass  # strip HTML comments

    def handle_decl(self, decl: str) -> None:
        pass  # strip declarations

    def handle_pi(self, data: str) -> None:
        pass  # strip processing instructions

    def unknown_decl(self, data: str) -> None:
        pass


def _is_safe_protocol(url: str) -> bool:
    """Return True if *url* uses an allowed protocol."""
    stripped = url.strip()
    # Relative URLs and fragments are fine
    if not stripped or stripped.startswith(("#", "/", "?", ".")):
        return True
    colon_idx = stripped.find(":")
    if colon_idx == -1:
        return True  # no protocol — relative
    proto = stripped[:colon_idx].lower()
    return proto in ALLOWED_PROTOCOLS


def sanitize_html(html: str) -> str:
    """Sanitize *html* keeping only allowed tags and attributes.

    Content text is always preserved; only unsafe markup is removed.
    """
    parser = _SanitizingParser()
    parser.feed(html)
    return parser.get_output()
