# Proposal: fix-date-boundary-suite-flakiness

## Why

The full test suite fails during a daily wall-clock window because day-scoped
dashboard tags and date assertions mix two timezone bases:

- `dailynotes_count_today` computes `today = timezone.now().date()` (UTC
  calendar date) while Django `__date` lookups evaluate in the project
  `TIME_ZONE` (`America/Bahia`), so between 21:00 and 02:00 local the tag
  counts the wrong day (production behavior bug, not only a test bug).
- Seven tests anchor expected `%d/%m/%Y` strings with `strftime` on the aware
  UTC datetime while templates render the same instant in the project
  timezone.

Empirically verified 2026-08-30 00:29-00:34 UTC: the full suite exits 1 with
exactly 8 failures inside the window `UTC [00:00, 05:00)` (local
`[21:00, 02:00)`), and the same tests pass under a shifted timezone
(`Asia/Tokyo`). The identical in-window run at 2026-08-29 23:50 UTC (20:50
local, outside the window) passed all 2699 tests.

This flakiness already blocked a critical slice dispatch
(`harden-patient-identity-and-duplicate-prevention` slice 004 stopped at its
mandatory green-baseline gate with zero edits) and forces every full-suite
comparison into a restricted daily window.

## What Changes

- Replace `timezone.now().date()` with `timezone.localdate()` in the three
  day-scoped dashboard tags (`dailynotes`, `historyandphysicals`,
  `simplenotes`), making the day basis consistent with `__date` lookups.
- Anchor the seven affected date assertions with
  `timezone.localtime(<datetime>).strftime('%d/%m/%Y')` so the expected string
  always matches template rendering.
- Re-anchor the `DailyNoteIntegrationTestCase` fixtures to local-midnight
  instants so `test_dailynotes_count_today` (notes at `now-1h/now-2h`) and
  the rolling week count are deterministic at any wall-clock time in any
  timezone.

## Impact

- Affected apps: `dailynotes`, `historyandphysicals`, `simplenotes`,
  `patients` (one test file each plus the dailynotes integration file).
- No schema, migration, URL, permission, or template changes; production
  change is three one-line edits.
- After this change the full suite must be green at any wall-clock time
  (removes the `UTC [00:00, 05:00)` dispatch restriction).
