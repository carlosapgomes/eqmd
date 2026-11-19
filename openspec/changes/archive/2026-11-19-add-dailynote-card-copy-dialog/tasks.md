# Tasks: add-dailynote-card-copy-dialog

## 1. Planning artifacts (complete)

- [x] 1.1 Proposal written (`proposal.md`)
- [x] 1.2 Design written (`design.md`, decisions D1-D10, normative
      algorithm and dialog UX, reviewer-hardened)
- [x] 1.3 Spec delta written (`specs/dailynote-card-copy/spec.md`, all
      requirements ADDED)
- [x] 1.4 Slice defined (`slices/slice-01.md` +
      `slices/slice-01-prompt.md`)
- [x] 1.5 Independent plan review (pi-subagents reviewer,
      `openai-codex/gpt-6.1-terra:high`) applied: capacity warning
      semantics, splitter contract, honest helper extraction, automated
      harness, separator preservation, RED expectations, lint

## 2. Implementation (slice-01, TDD)

- [x] 2.1 Write the automated splitter harness first
      (`apps/dailynotes/tests/dailynote_chunks_harness.cjs`, modeled on
      `apps/core/tests/page_navigation_loading_harness.cjs`) plus its
      Django wrapper (`test_dailynote_chunks_harness.py`, modeled on
      `test_page_navigation_loading.py`): RED because the chunks module
      does not exist yet (direct `node` run fails; the Django test skips
      without node or fails when the harness fails)
- [x] 2.2 Write the template tests in
      `apps/dailynotes/tests/test_card_copy_dialog.py`: RED for the two
      DailyNote hook tests (final and draft card render
      `copy-dailynote-btn` with `data-content`, assertions scoped to the
      card article); the SimpleNote regression test
      (`copy-content-btn` kept) is green from the start
- [x] 2.3 Implement the pure splitter `assets/js/dailynote-chunks.js`
      (CommonJS; constants 4000/3900/4; `shouldOpenCopyDialog`;
      `splitDailyNoteIntoParts` per the design.md algorithm with
      preserved unit separators): harness GREEN
- [x] 2.4 Rename the DailyNote card copy button hook from
      `copy-content-btn` to `copy-dailynote-btn` in
      `apps/events/templates/events/partials/event_card_dailynote.html`
      (keep `data-content`, tooltip, icons, and all other buttons):
      template tests GREEN
- [x] 2.5 Extract `showToast` and `showClipboardFeedback` verbatim from
      `assets/index.js` into the new `assets/js/clipboard-utils.js`;
      derive `copyTextToClipboard(text)` from the body of the existing
      `copyToClipboard(button)`; make `assets/index.js` import them
      (generic `.copy-content-btn` behavior unchanged)
- [x] 2.6 Create `assets/js/dailynote-copy.js`: delegated
      `.copy-dailynote-btn` click flow (direct copy vs dialog per
      `shouldOpenCopyDialog`) and the Bootstrap 5 dialog built on demand
      (labels, pt-BR counts, copied states, uncovered-content warning per
      design.md "Dialog UX"; `textContent` only)
- [x] 2.7 Import and initialize `initDailyNoteCopy()` in
      `assets/index.js` (DOMContentLoaded, alongside the existing
      clipboard init)
- [x] 2.8 Rebuild the bundle on the host with `npm run build`; confirm
      `static/main-bundle.js` contains the new code
- [x] 2.9 Run regressions: full `apps.dailynotes` suite and
      `apps.events.tests.test_card_attribution_card_partials`

## 3. Verification (slice-01)

- [x] 3.1 `node apps/dailynotes/tests/dailynote_chunks_harness.cjs`
      passes on the host (exit 0, JSON summary without failures; 12
      fixtures, re-verified independently by the parent)
- [x] 3.2 `./scripts/test.sh apps.dailynotes.tests.test_card_copy_dialog`
      passes (3 tests; run against the dedicated workspace container
      `eqmd_dev_dncopy`)
- [x] 3.3 `./scripts/test.sh apps.dailynotes` passes (174 tests,
      skipped=1: the in-container node wrapper, as designed); includes
      the harness wrapper where node is available
- [x] 3.4 `./scripts/test.sh apps.events.tests.test_card_attribution_card_partials`
      passes (4 tests, run against the dedicated workspace container)
- [x] 3.5 Browser evidence complete: 11/11 checks passed against the
      dedicated stack (`http://127.0.0.1:8791`) covering all nine design.md
      steps; executed with the verify-eqmd Playwright harness convention
      (system Chrome, headless) because the Chrome DevTools MCP profile
      was held by the operator's running browser. Screenshots and report:
      `.pi/skills/verify-eqmd/harness/evidence/dncopy-slice01/`
- [x] 3.6 All change artifacts pass `npx markdownlint-cli2` when linted
      explicitly (kept at 80 columns with top-level headings); re-run
      after implementation: 0 errors
