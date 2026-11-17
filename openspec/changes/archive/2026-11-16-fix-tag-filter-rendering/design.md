# Tag filter rendering correction

## Context

The archived improve-tag-filter-discovery-ux implementation added a hidden
parent option panel. Its current script unhides both parent and list; the older
script only unhides the list. Stable unversioned asset URLs allow those versions
to mix. A clean-browser baseline succeeds, while legacy-script reproduction
must pin the reported found-but-invisible failure. Multiline `{# ... #}`
comments in reports render as visible text. Existing narrow Bootstrap columns
and bottom alignment amplify that text and otherwise squeeze actions/modes.

## Decisions

- Add a small reports/patients-consumed `versioned_static` template tag in
  core. Reuse Django's static URL, append a SHA-256 content token for locally
  discoverable built files, cache hashing by path/mtime/size and preserve
  storage-provided URLs. Missing/nonlocal files retain their existing URL.
  Apply to main.css and the participating selector/host/discovery scripts.
  Do not redesign global static storage, service workers or unrelated assets.
- Keep existing JS/state/auth contracts. Position the existing panel inside
  a relative wrapper containing only its search input. Keep bounded scrolling,
  hidden state, keyboard handling, chip hooks and no-JS selects.
- Patient/map use a top name/status-or-ward row, full-width tag section with
  wide search and mode columns, and wrapping action footer. Reports use the
  same top-aligned hierarchy with adequate mode/button widths. Avoid duplicate
  embedded clear controls where the reports host already owns that action.
- Use `{% comment %}` blocks for multiline Django comments. Never blanket-strip
  user model content or change markdown rendering.

## Verification and Environment

Baseline served /app is /projects/dev/eqmd at the same initial revision as this
worktree, but it is a separate directory. Do not edit, remount or restart that
checkout. Execute changed Django code in an isolated /tmp copy inside eqmd_dev,
using PostgreSQL and existing installed dependencies. Baseline standard
`./scripts/test.sh` is not evidence of changed worktree code.

Browser evidence uses installed Playwright/system Chrome, disposable accounts
from the official verify-eqmd setup/cleanup, GET-only feature interactions and
card-only screenshots. Compare current versus legacy script delivery. For
changed components/assets, use isolated Django-rendered fixtures or explicitly
labelled browser preview routing; do not claim preview is a deployed live fix.
Record viewport geometry, actual visibility/hit testing, keyboard selection,
first load on each surface and report-creation content preservation. Clean up
the exact owned scaffold after success or failure.

## Rollback

Revert source/template/helper deployment and rebuild assets. Retain no data
changes. This correction has no migration or persisted-state rollback.
