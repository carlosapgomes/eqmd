# Verification: add-dailynote-card-copy-dialog

## Environment and Fixtures

Dedicated dev container (operator-approved, because the shared eqmd_dev
stack is bind-mounted to another Orca workspace): eqmd_dev_dncopy, same
image and network as eqmd_dev, /app bound to this checkout, published at
127.0.0.1:8791, isolated test database test_eqmd_dncopy. Every
./scripts/test.sh call used EQMD_DOCKER_SERVICE=eqmd_dev_dncopy. The
shared stack, its dev database eqmd_dev and the operator's manual
fixtures stayed untouched.

Host toolchain: node v24.16.0; npm ci from package-lock.json
(operator-approved); webpack build validated to a temp output before
the in-place rebuild of the git-tracked static/main-bundle.js.

## Gates (RED -> GREEN)

RED, before implementation:

- node apps/dailynotes/tests/dailynote_chunks_harness.cjs -> ENOENT
  (assets/js/dailynote-chunks.js absent), exit 1
- EQMD_DOCKER_SERVICE=eqmd_dev_dncopy ./scripts/test.sh
  apps.dailynotes.tests.test_card_copy_dialog -> 2 failures (hook class
  missing on the final and draft DailyNote cards); the SimpleNote
  regression guard was green from the start, as planned

GREEN, final (template tests, harness and suites re-run independently
by the parent):

- node apps/dailynotes/tests/dailynote_chunks_harness.cjs -> 12
  fixtures passed, failed [], exit 0
- EQMD_DOCKER_SERVICE=eqmd_dev_dncopy ./scripts/test.sh
  apps.dailynotes.tests.test_card_copy_dialog -> 3 tests OK
- EQMD_DOCKER_SERVICE=eqmd_dev_dncopy ./scripts/test.sh
  apps.dailynotes -> 174 tests OK (skipped=1: the node wrapper skips
  inside the container by design, mirroring
  test_page_navigation_loading)
- EQMD_DOCKER_SERVICE=eqmd_dev_dncopy ./scripts/test.sh
  apps.events.tests.test_card_attribution_card_partials -> 4 tests OK
- npm run build -> exit 0; static/main-bundle.js contains
  copy-dailynote-btn; 19 pre-existing size warnings only
- npx markdownlint-cli2 on the change artifacts -> 0 errors

## Browser Evidence

Executed with the verify-eqmd Playwright convention (system Chrome,
headless) against <http://127.0.0.1:8791>, because the Chrome DevTools
MCP profile was held by the operator's running browser (not killed).
Screenshots and report.json were kept under
.pi/skills/verify-eqmd/harness/evidence/dncopy-slice01/ (untracked by
convention; the scratch evidence script was deleted after the run).

11/11 checks passed, covering the nine design.md steps:

1. short note (101 chars) copies directly, no dialog, success toast
2. 4900-char note opens the dialog; every part count at most 4.000
   2b. P1/P2 clicks flip the copied state; copied texts at most 4000 chars
   2c. "Copiar tudo" writes the raw content verbatim
3. reopening the dialog resets the copied states
4. single 8359-char paragraph splits with all parts at most 4.000
5. 15008 chars (5 x 3000): warning names 15.008 total and 12.006
   covered, four part buttons
6. 20038 chars: warning also cites the 16.000 hospital capacity
7. clipboard failure stub: error toast, no copied state
8. SimpleNote card copies directly with no dialog
9. served main-bundle.js contains the new hook

## Independent Review

Plan reviewed before implementation by a pi-subagents reviewer
(openai-codex/gpt-6.1-terra:high, read-only): verdict "REQUER
TRABALHO"; all seven findings were applied to the artifacts first
(uncovered-content warning semantics, splitter contract and return
shape, honest helper extraction, automated Node harness, preserved
separators in the oversized cascade, RED expectations per test, lint
compliance).

## Cleanup (operator-approved)

After acceptance, the disposable fixture was hard-deleted from the
shared dev database with zero-row assertions: 6 events, 1 patient, 1
doctor user, 4 user-history rows and the allauth EmailAddress. The
isolated test database test_eqmd_dncopy was dropped and the container
eqmd_dev_dncopy was removed. The dev database eqmd_dev and every other
operator dataset were untouched.
