# Proposal: add-dailynote-card-copy-dialog

## Why

The DailyNote timeline card's copy button copies the whole note to the
clipboard in one piece. The hospital system where users paste DailyNote
content has four dedicated fields, each accepting at most 4,000 characters.
Notes above 4,000 characters cannot be pasted into a single field, so
users split the text by hand today: slow and error-prone.

## What Changes

- Give the DailyNote timeline card copy button its own click flow via a
  dedicated hook class (`copy-dailynote-btn`) served by new webpack
  modules:
  - Content up to 4,000 characters copies directly, exactly as today
    (no dialog).
  - Content above 4,000 characters opens a Bootstrap 5 dialog with a
    "Copiar tudo" button plus numbered part buttons (`P1..P4`).
- Split parts client-side at paragraph boundaries, targeting ~3,900
  characters per part with a hard cap of 4,000, and at most 4 part
  buttons.
- Each part button shows its character count and keeps a copied indicator
  while the dialog is open, so users can track which parts were already
  pasted into the hospital fields.
- When the four part buttons do not cover the full content, the dialog
  shows an explicit warning naming total and covered characters (the
  16,000-character hospital capacity is cited when the total exceeds it);
  content is never silently truncated.
- Share clipboard helpers with the generic card flow: `showToast` and
  `showClipboardFeedback` move verbatim from `assets/index.js` into
  `assets/js/clipboard-utils.js`, while `copyTextToClipboard(text)` is
  derived from the body of the existing `copyToClipboard(button)`; the
  generic card copy flow keeps its current behavior.
- Cover the splitting algorithm with an automated Node harness inside the
  Django suite, following the `page_navigation_loading_harness.cjs`
  precedent, and rebuild the webpack bundle (`static/main-bundle.js`).

## Impact

- Affected specs: `dailynote-card-copy` (new capability; all requirements
  ADDED)
- Affected code:
  - `apps/events/templates/events/partials/event_card_dailynote.html`:
    copy button hook class only; `data-content`, tooltip and icons stay
    unchanged
  - `assets/js/clipboard-utils.js` (new): helpers shared with index.js
  - `assets/js/dailynote-chunks.js` (new): pure splitter in CommonJS, so
    the Node harness can load it the same way the existing page-loading
    harness loads its script
  - `assets/js/dailynote-copy.js` (new): click flow plus dialog
  - `assets/index.js`: imports shared helpers and `initDailyNoteCopy()`;
    generic `.copy-content-btn` flow unchanged
  - `static/main-bundle.js`: rebuilt via `npm run build` (bundle is
    tracked in git, confirmed with `git ls-files`)
  - `apps/dailynotes/tests/test_card_copy_dialog.py` (new): template
    regression tests
  - `apps/dailynotes/tests/dailynote_chunks_harness.cjs` and
    `apps/dailynotes/tests/test_dailynote_chunks_harness.py` (new):
    automated splitter coverage wrapped into the Django suite
- Explicitly unchanged: other event card partials (simplenote, history and
  physical, discharge report, prescription), the generic
  `.copy-content-btn` flow, the DailyNote detail page copy buttons (its
  inline script is self-contained), and all backend code (no new endpoint,
  no model or permission changes).
