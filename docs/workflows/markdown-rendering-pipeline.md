# Markdown Rendering Pipeline

Unified server-side pipeline for rendering markdown content consistently across
web (HTML) and PDF outputs in the EquipeMed application.

## Architecture Overview

The pipeline follows a **parse once, render many** pattern:

```text
Markdown text
       |
       v
+----------+    easymd_v1 profile
|  Parser  |-------------------------> IR (DocumentNode tree)
+----------+
       |
       +---> HTML Renderer ---> Sanitizer ---> Safe HTML
       |
       +---> PDF Renderer ---> ReportLab Flowables
```

### Components

| Component     | Module                                             | Purpose                                                  |
| ------------- | -------------------------------------------------- | -------------------------------------------------------- |
| Profile       | `core/services/markdown_pipeline/profile.py`       | Defines easymd_v1 dialect and supported constructs       |
| Parser        | `core/services/markdown_pipeline/parser.py`        | Converts markdown text to frozen IR tree via mistune 3   |
| IR            | `core/services/markdown_pipeline/ir.py`            | Frozen dataclass nodes (DocumentNode, HeadingNode, etc.) |
| HTML Renderer | `core/services/markdown_pipeline/html_renderer.py` | IR to safe HTML                                          |
| Sanitizer     | `core/services/markdown_pipeline/sanitizer.py`     | Allowlist-based HTML sanitizer                           |
| PDF Renderer  | `core/services/markdown_pipeline/pdf_renderer.py`  | IR to ReportLab flowables                                |
| Public API    | `core/services/markdown_pipeline/__init__.py`      | Convenience imports                                      |

## Dialect Profile: easymd_v1

The `easymd_v1` profile defines the canonical markdown dialect supported by the
pipeline. It is versioned so future changes can be explicit and migration-safe.

### Supported Constructs

| Construct          | Markdown Syntax                    |
| ------------------ | ---------------------------------- |
| Headings           | `#` through `######`               |
| Paragraphs         | Blank-line separated text          |
| Strong             | `**bold**` or `__bold__`           |
| Emphasis           | `*italic*` or `_italic_`           |
| Strikethrough      | `~~strike~~`                       |
| Links              | `[text](url)`                      |
| Inline code        | `` `code` ``                       |
| Fenced code blocks | triple-backtick with optional lang |
| Ordered lists      | `1. item`                          |
| Unordered lists    | `- item` or `* item`               |
| Nested lists       | Indented sub-items                 |
| Blockquotes        | `> quote`                          |
| Tables             | GFM pipe tables                    |
| Task lists         | `- [x] done` / `- [ ] todo`        |
| Thematic breaks    | `---` / `***` / `___`              |
| Hard breaks        | Two trailing spaces or backslash   |

### Fallbacks for PDF Rendering

Some constructs have constrained PDF styling support:

| Construct       | PDF Fallback                             |
| --------------- | ---------------------------------------- |
| Tables          | ReportLab `Table` with plain cell text   |
| Blockquotes     | Indented Paragraph with bar prefix       |
| Code blocks     | Monospace Paragraph with grey background |
| Task lists      | `[x]` / `[ ]` text markers               |
| Thematic breaks | Spacer only                              |

## Public API

```python
from apps.core.services.markdown_pipeline import (
    parse_markdown,
    render_markdown_html,
    render_markdown_pdf_flowables,
)
```

### `parse_markdown(markdown_text, profile="easymd_v1")`

Parse markdown text into a normalized IR tree (DocumentNode).

```python
doc = parse_markdown("**bold** and *italic*")
# doc is a frozen DocumentNode with children
```

### `render_markdown_html(markdown_text, profile="easymd_v1")`

Convert markdown text to safe HTML in a single call.

```python
html = render_markdown_html("## Title\n\nParagraph.")
# "<h2>Title</h2>\n<p>Paragraph.</p>"
```

### `render_markdown_pdf_flowables(document, styles, options=None)`

Render a parsed DocumentNode into a flat list of ReportLab flowables.

```python
from reportlab.lib.styles import getSampleStyleSheet

doc = parse_markdown("# Title\n\n- item 1\n  - nested")
styles = getSampleStyleSheet()
flowables = render_markdown_pdf_flowables(doc, styles)
```

## How to Integrate in a New App

### Web (HTML) Rendering

1. Create a template tag or use the shared pipeline directly:

```python
# myapp/templatetags/myapp_extras.py
from django import template
from django.utils.safestring import mark_safe
from apps.core.services.markdown_pipeline import render_markdown_html

register = template.Library()

@register.filter
def markdown(value):
    if not value:
        return ""
    return mark_safe(render_markdown_html(value))
```

1. Use in templates:

```django
{% load myapp_extras %}
<div class="markdown-content">
    {{ object.content|markdown }}
</div>
```

### PDF Rendering

1. Import the pipeline in your PDF generator:

```python
from apps.core.services.markdown_pipeline import parse_markdown
from apps.core.services.markdown_pipeline.pdf_renderer import (
    render_markdown_pdf_flowables,
)
```

1. Parse and render:

```python
def build_content(self, markdown_text):
    doc = parse_markdown(markdown_text)
    return render_markdown_pdf_flowables(doc, self.styles)
```

### Integration Checklist

- [ ] Import from `apps.core.services.markdown_pipeline` (not legacy parser)
- [ ] Web detail uses `render_markdown_html` (not `|linebreaks`)
- [ ] PDF generator uses `parse_markdown` + `render_markdown_pdf_flowables`
- [ ] Template filter returns `mark_safe()` output from pipeline
- [ ] Test web rendering preserves nested lists, inline formatting, tables
- [ ] Test PDF rendering preserves text tokens in source order
- [ ] Test web and PDF parity for the same markdown input
- [ ] Verify sanitization (no `<script>`, `javascript:`, `on*` attributes)
- [ ] Add cross-app regression test if the app has both web and PDF outputs

## Compatibility Matrix

| App               | Web    | PDF    | Status   |
| ----------------- | ------ | ------ | -------- |
| Daily Notes       | Shared | Shared | Migrated |
| Reports           | Shared | Shared | Migrated |
| Consent Forms     | N/A    | Legacy | Pending  |
| Discharge Reports | N/A    | Legacy | Pending  |
| PDF Generator     | N/A    | Legacy | Pending  |

## Test Strategy

### Test Modules

| Module                                             | Purpose                             |
| -------------------------------------------------- | ----------------------------------- |
| `core/.../test_markdown_dialect_contract.py`       | Fixture corpus, metadata validation |
| `core/.../test_markdown_pipeline_parser.py`        | Parser IR correctness, determinism  |
| `core/.../test_markdown_pipeline_html.py`          | HTML renderer, sanitization         |
| `core/.../test_markdown_pipeline_regression.py`    | Cross-app bundle, legacy, perf      |
| `dailynotes/.../test_detail_markdown_rendering.py` | Daily Note web detail integration   |
| `dailynotes/.../test_pdf_markdown_parity.py`       | Daily Note PDF parity               |
| `reports/.../test_markdown_parity.py`              | Reports web + PDF parity            |

### Verification Commands

```bash
# Full pipeline tests
./scripts/test.sh apps.core.tests.test_markdown_dialect_contract \
  apps.core.tests.test_markdown_pipeline_parser \
  apps.core.tests.test_markdown_pipeline_html \
  apps.core.tests.test_markdown_pipeline_regression

# App-specific tests
./scripts/test.sh apps.dailynotes.tests.test_detail_markdown_rendering \
  apps.dailynotes.tests.test_pdf_markdown_parity
./scripts/test.sh apps.reports.tests.test_markdown_parity

# Regression bundle (Slice 07 verification)
./scripts/test.sh apps.core.tests.test_markdown_pipeline_regression \
  apps.dailynotes.tests apps.reports.tests
```

### Fixture Corpus

Fixtures live in `tests/fixtures/markdown/easymd_v1/` and cover:

- `nested_lists.md` — Multi-level ordered/unordered nesting
- `inline_formatting.md` — Bold, italic, strike, code, links, breaks
- `blockquote_code.md` — Blockquotes and fenced code blocks
- `tables_links.md` — GFM tables and hyperlinks
- `task_lists.md` — Checked and unchecked task items
- `mixed_clinical_note.md` — Comprehensive clinical document

Each fixture has a companion `.meta.json` with `constructs` and
`expected_semantic_tokens` for contract validation.

## Legacy Code Deprecation

`apps/pdfgenerator/services/markdown_parser.py` (`MarkdownToPDFParser`) is
**deprecated**. It remains in the codebase only because `consentforms`,
`dischargereports`, and `pdfgenerator/views` still depend on it.

Once those consumers migrate to the shared pipeline, the entire module can be
removed.
