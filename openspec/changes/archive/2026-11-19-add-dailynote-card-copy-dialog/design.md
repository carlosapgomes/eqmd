# Design: add-dailynote-card-copy-dialog

## Context

The DailyNote timeline card
(`apps/events/templates/events/partials/event_card_dailynote.html`) embeds
the full note content in the copy button's `data-content` attribute. A
global delegated handler in `assets/index.js` (bundled to
`static/main-bundle.js` by webpack) serves every `.copy-content-btn` card
button with the same flow: write the full text to the clipboard, swap the
button icon for two seconds, show a toast.

The hospital system receiving DailyNote content has four dedicated fields
with a hard limit of 4,000 characters each. There is no backend
involvement in the copy today: the text is already in the browser when
the button is activated, so the fragmentation problem is purely a
client-side text-splitting problem.

Automated JavaScript coverage has a precedent in this repo:
`apps/core/tests/test_page_navigation_loading.py` runs
`page_navigation_loading_harness.cjs` through `node`, loading the real
script into a `vm` sandbox with stubbed globals. The webpack bundle
output is tracked in git (`git ls-files static/main-bundle.js`), so every
frontend change must rebuild it. The DailyNote detail page carries its
own self-contained inline copy script (it defines its own `showToast`),
so refactoring `assets/index.js` does not reach it.

## Goals / Non-Goals

- Goals:
  - Let users copy a long DailyNote in up to four parts that each fit one
    hospital field (target ~3,900, hard limit 4,000 characters).
  - Preserve today's one-click copy for every note that fits a single
    field.
  - Keep the split paragraph-aware so part boundaries look natural.
  - Make progress trackable: per-part character counts and a copied
    indicator that persists while the dialog is open.
  - Make uncovered content explicit and never truncate silently.
  - Zero backend changes; zero behavior change for non-DailyNote cards
    and the DailyNote detail page.
- Non-Goals:
  - No backend endpoint, API, model, or permission changes.
  - No changes to other event card types (simplenote, history and
    physical, discharge report, prescription): they keep direct copy.
  - No changes to the DailyNote detail page copy buttons.
  - No in-dialog preview of part contents (possible follow-up; counts
    plus copied state cover the paste workflow).
  - No automatic truncation or summarization of oversized notes.

## Decisions

- **D1 - Client-side split, no endpoint.** The full content is already in
  the card's `data-content` when the button is activated; splitting is a
  pure function of that string. A backend endpoint would add a round trip,
  a new permission surface, and a new draft-gating decision for zero
  user-visible benefit.
- **D2 - Dedicated hook class `copy-dailynote-btn`.** The DailyNote card
  button switches from `copy-content-btn` to `copy-dailynote-btn`. The
  generic handler in `assets/index.js` can then never intercept
  DailyNote card clicks, which makes "other cards untouched" a
  structural guarantee instead of an `if` branch. The hook class carries
  no styling (buttons keep `btn btn-outline-secondary btn-sm`).
- **D3 - Shared clipboard helpers, honest extraction.** `showToast` and
  `showClipboardFeedback` move verbatim into
  `assets/js/clipboard-utils.js`. There is no `copyTextToClipboard` in
  `assets/index.js` today: the write and the `execCommand` fallback live
  inside `copyToClipboard(button)` together with the feedback. The plan
  therefore derives `copyTextToClipboard(text)` from that body and keeps
  a button-feedback adapter in the generic flow. The DailyNote detail
  page keeps its own inline script and is unaffected.
- **D4 - Dialog DOM built by the JS module.**
  `assets/js/dailynote-copy.js` builds one modal element on first use
  (appended to `body`, Bootstrap 5 `Modal` API) instead of adding markup
  to the 1,200-line timeline template. Precedent: the JS-created toast
  container in `assets/index.js`. The modal resets part state on every
  open.
- **D5 - Three-module layout, pure core in CommonJS.**
  - `assets/js/dailynote-chunks.js`: constants and the pure splitter,
    written in CommonJS (`module.exports`) so the Node harness can
    `vm`-load it exactly like `page_navigation_loading_harness.cjs`
    loads `page-loading.js`; webpack consumes it from ESM via default
    interop. Exports: `HOSPITAL_FIELD_LIMIT = 4000`,
    `PART_TARGET = 3900`, `MAX_PART_BUTTONS = 4`,
    `shouldOpenCopyDialog(raw)`, `splitDailyNoteIntoParts(raw)`.
  - `assets/js/dailynote-copy.js`: ESM; delegated click flow and the
    dialog; imports the chunks module and the clipboard helpers;
    initialized by `initDailyNoteCopy()` called from `assets/index.js`
    (no top-level side effects).
  - `assets/js/clipboard-utils.js`: shared helpers per D3.
- **D6 - Splitter contract: decision and shape.** The dialog decision
  uses the raw attribute: `shouldOpenCopyDialog(raw)` is true iff
  `raw.length > 4000`, independent of splitting. The splitter always
  returns the same shape
  `{ parts, totalLength, coveredLength, uncoveredLength }` for any input,
  including zero parts (whitespace-only content) and a single part; the
  click flow, not the splitter, decides dialog versus direct copy.
- **D7 - Units keep their original separators.** Splitting must not
  invent or destroy text. Each unit (paragraph, or line, sentence, hard
  cut piece of an oversized paragraph) carries the separator that
  preceded it in the normalized content: `"\n\n"` for paragraph
  boundaries (blank-line runs normalize to exactly one blank line),
  `"\n"` for line pieces, `" "` for sentence pieces, `""` for hard cuts.
  A part is the concatenation of its units with those separators;
  inter-part separators are dropped from the pasted text but recorded
  for the reassembly invariant and coverage math.
- **D8 - Character counting.** JavaScript string `length` (UTF-16 code
  units). This over-counts emoji and lone surrogates relative to
  code-point counters, which is the safe direction, and the
  100-character margin (3,900 target vs 4,000 limit) also absorbs CRLF
  differences reintroduced by editors.
- **D9 - Human drafts stay copyable.** The timeline shows human drafts
  (existing design), the card embeds their content, and the detail
  screen displays them; copying a draft is a screen-level convenience,
  not record export. Draft cards therefore use the same dialog flow as
  final notes. The PDF export gating for drafts does not apply and is
  deliberately not imported.
- **D10 - Uncovered content is warned about, never truncated.** The
  warning is driven by `uncoveredLength > 0` (parts dropped by the
  four-button cap), not by a raw length threshold: paragraph packing can
  leave content uncovered below 16,000 characters (for example five
  3,000-character paragraphs yield five parts for a 15,000-character
  note). The message names total and covered characters; when the total
  exceeds 16,000 it also cites the hospital capacity (four fields x
  4,000). "Copiar tudo" always writes the raw content verbatim.

## Splitting Algorithm (normative)

```text
shouldOpenCopyDialog(raw):
    return raw.length > HOSPITAL_FIELD_LIMIT (4000)

splitDailyNoteIntoParts(raw):
    normalized = raw with every "\r\n" replaced by "\n", then outer
    whitespace trimmed once
    if normalized is empty:
        return { parts: [], totalLength: 0, coveredLength: 0,
                 uncoveredLength: 0 }
    units = []
    for each block in normalized.split(/\n{2,}/):
        if block.length <= 4000:
            units.push({ text: block, sep: "\n\n" })   # paragraph
        else:
            units.push(...splitOversizedBlock(block))   # first piece
            # keeps the "\n\n" separator; inner pieces keep their own

splitOversizedBlock(block):
    pieces = block.split("\n")                    # lines, no blank lines
    for each line longer than 4000:
        sentences = line.split(/(?<=[.!?…])\s+/)  # sentence runs
        for each sentence longer than 4000:
            hard-cut the sentence into 4000-character chunks (sep "")
        line pieces get sep " "
    line pieces get sep "\n"
    return pieces with the first piece keeping the block's "\n\n"

greedy fill into parts:
    part = ""
    for each unit:
        if part is empty:
            part = unit.text
        else if part.length + unit.sep.length + unit.text.length
                 <= PART_TARGET (3900):
            part = part + unit.sep + unit.text
        else:
            close part; part = unit.text
        the closed part records the next part's first-unit separator
        as its separatorToNextPart
    close trailing part

result:
    totalLength = normalized.length
    shown = first MAX_PART_BUTTONS (4) parts
    coveredLength = characters through the end of the last shown part
    uncoveredLength = totalLength - coveredLength
```

Invariants (asserted by the automated harness on every fixture):

- Every part is at most 4,000 characters: a part with two or more units
  is filled only up to the 3,900 target; a single-unit part holds one
  unit, and the oversized cascade caps units at 4,000.
- Reassembly: walking the shown units in order (part texts plus the
  recorded inter-part separators) reproduces the trimmed normalized
  content exactly, up to the covered length.
- The dialog decision depends only on the raw length, even when CRLF
  normalization would shrink the text to 4,000 or less (raw 4,001 with
  one CRLF: dialog opens, one part button).

Edge behavior made explicit:

- Content of 4,000 characters or fewer: direct copy, no dialog.
- Content of 4,001 characters: dialog.
- Whitespace-only content: zero parts, the click flow shows the
  "Nenhum conteúdo para copiar" error toast, no dialog.

## Dialog UX (normative)

- Title: "Copiar evolução". Body intro: "Cada campo do sistema
  hospitalar aceita até 4.000 caracteres."
- Buttons: "Copiar tudo (N caracteres)" and part buttons labeled "P1",
  "P2", ..., each showing "n/4.000" (pt-BR grouping via
  `toLocaleString("pt-BR")`).
- Copy feedback: success toast on every copy; part and full buttons
  switch to a copied state (success style plus a check indicator) that
  persists while the dialog is open and resets on the next open.
- When `uncoveredLength > 0`: a warning states the total character
  count, the covered character count, and that only the first four
  parts are shown; when `totalLength > 16000` it also cites the hospital
  capacity of four fields x 4,000 characters.
- Any text rendered from note content uses `textContent`, never
  `innerHTML`.
- Accessibility: Bootstrap 5 modal focus management; each part button
  carries an `aria-label` such as "Copiar parte 1 da evolução (3.850
  caracteres)"; close button "Fechar".
- Empty or whitespace-only `data-content`: error toast "Nenhum conteúdo
  para copiar", no dialog (parity with the current generic flow).

## Alternatives Considered

- **Backend endpoint returning full text plus parts (original
  proposal):** rejected: the content is already client-side at click
  time; the endpoint adds latency, a new URL/permission surface, and an
  explicit draft-gating decision, with no user-visible gain.
- **Server-side split embedded per card (template filter plus
  `json_script`, only for long notes):** rejected: couples the split
  policy to render time and doubles the DOM payload of every long note.
- **Generic dialog for every card type:** rejected for this change: the
  four-field constraint is a DailyNote workflow; other cards keep their
  simpler direct copy. The shared helpers module keeps the door open for
  reuse.

## Risks / Trade-offs

- **`assets/index.js` is shared by all cards.** Mitigation:
  extraction-only refactor (helpers moved or derived, listener and
  behavior unchanged), plus a template regression test asserting other
  cards keep `copy-content-btn`, plus browser evidence on a
  non-DailyNote card.
- **`static/main-bundle.js` is tracked in git.** The implementer must
  run `npm run build` on the host and include the rebuilt bundle.
- **Splitter correctness is the core risk.** Mitigated by the automated
  harness (fixtures below), which runs in the Django suite like the
  page-loading harness, plus boundary cases in the browser evidence.
- **Clipboard API requires a secure context.** The existing
  `execCommand` fallback moves verbatim into the shared helper.
- **Service worker caching (`assets/sw.js` is cache-first for static
  assets).** Templates load the bundle through a content-versioned URL
  (`versioned_static`), so a rebuilt bundle changes the URL; browser
  evidence still confirms the fresh bundle is served.

## Test Strategy

- **Automated splitter harness (written first, RED while the module is
  missing):** `apps/dailynotes/tests/dailynote_chunks_harness.cjs`
  `vm`-loads `assets/js/dailynote-chunks.js` (model:
  `apps/core/tests/page_navigation_loading_harness.cjs`) and runs
  table-driven fixtures, printing a JSON summary:
  - exactly 4,000 and 4,001 characters (direct copy vs dialog);
  - raw above 4,000 that normalizes to 4,000 or fewer (CRLF edge:
    dialog opens, single part);
  - multi-paragraph note: boundaries on blank lines, every part within
    the limits;
  - oversized paragraph: line, sentence, and hard-cut fallbacks with
    preserved separators, every part within 4,000;
  - whitespace-only content: zero parts;
  - five 3,000-character paragraphs (15,000 total): five parts,
    uncovered content flagged with a 4-button cap;
  - note above 16,000 characters: cap at four parts, uncovered flagged;
  - reassembly invariant on every fixture.
    `apps/dailynotes/tests/test_dailynote_chunks_harness.py` (model:
    `test_page_navigation_loading.py`) runs the harness through `node`
    with `skipUnless(shutil.which("node"))` and asserts exit code plus
    the JSON summary.
- **pytest (template regression):**
  `apps/dailynotes/tests/test_card_copy_dialog.py` modeled on
  `test_draft_card_actions.py`:
  - final DailyNote card renders `copy-dailynote-btn` with
    `data-content` (RED before the template change);
  - draft DailyNote card renders it too (RED before the change);
  - a SimpleNote card on the same timeline keeps the generic
    `copy-content-btn` (green from the start: pure regression guard);
  - assertions are scoped to the respective card article, not the whole
    page.
    Existing coverage already guards the detail page
    (`test_detail_markdown_rendering` asserts `copy-content-btn` there,
    unchanged by this change).
- **Regressions:** `./scripts/test.sh apps.dailynotes` and
  `./scripts/test.sh apps.events.tests.test_card_attribution_card_partials`
  (renders every card partial).
- **Browser evidence (Chrome DevTools MCP against
  `http://127.0.0.1:8779`, users from the `verify-eqmd` harness setup):**
  1. Short note (at most 4,000 characters): click copies directly, toast
     shows, no dialog.
  2. Long note (above 4,000 characters, several paragraphs): dialog
     opens; part count matches expectation; every part button count is
     at most 4.000; P1 and P2 copied states toggle; "Copiar tudo"
     writes the raw content.
  3. Note with a single paragraph above 4,000 characters: dialog opens
     with all parts at most 4.000.
  4. Five 3,000-character paragraphs: warning visible naming total
     (15.000) and covered characters, four part buttons.
  5. Note above 16,000 characters: warning also cites the 16.000
     hospital capacity; "Copiar tudo" present.
  6. Close and reopen the dialog: copied states reset.
  7. Clipboard failure (stub `navigator.clipboard.writeText` to
     reject): error toast, no copied state.
  8. A non-DailyNote card (simplenote): click copies directly, no
     dialog.
  9. Hard reload: the rebuilt bundle URL is served (no stale service
     worker cache).
