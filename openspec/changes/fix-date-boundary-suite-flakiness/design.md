# Design: fix-date-boundary-suite-flakiness

## Context

Verified failure mechanism (2026-08-30, reproduced independently):

1. `apps/dailynotes/templatetags/dailynote_tags.py` line 57:
   `today = timezone.now().date()` is the UTC calendar date, but
   `DailyNote.objects.filter(event_datetime__date=today)` evaluates
   `__date` in the active timezone (`settings.TIME_ZONE`,
   `America/Bahia`). With `USE_TZ = True`, the two bases disagree while
   the UTC clock is past local midnight (local `[21:00, 24:00)`) and the
   fixtures (`now - 1h`, `now - 2h`) extend the mismatch until local
   `02:00`. Union failure window: `UTC [00:00, 05:00)`.
2. Six detail-context tests (`dailynotes`, `historyandphysicals`,
   `simplenotes` x2 each) and one patients timeline test compute expected
   strings via `<aware-datetime>.strftime('%d/%m/%Y')` (UTC rendering)
   while the rendered page shows the project-timezone date. Failure
   window for these: local `[21:00, 24:00)`.

Empirical matrix (same code, only `TIME_ZONE` changed):
`America/Bahia` 21:xx FAIL, `Etc/GMT`-style UTC at 00:2x FAIL,
`Asia/Tokyo` OK. Full suite at 00:31 UTC: exit 1 with exactly these 8
tests; the same suite at 23:50 UTC the previous day: 2699 OK.

## Goals

- Full suite green at any wall-clock time under the project timezone.
- Day-scoped dashboard tags count the project-timezone day (single
  timezone basis per day scope).
- Regression proof that does not depend on waiting for a wall-clock
  window: a divergent-timezone run must pass after the fix.

## Non-Goals

- Changing `settings.TIME_ZONE`, `USE_TZ`, or template rendering.
- Fixing the other `timezone.now().date()` occurrences with different
  semantics (date-delta comparisons in `accounts`, `patients`,
  `dischargereports`); they compare two dates on the same basis and are
  not part of the proven flake.
- Adding test coverage for the `historyandphysicals`/`simplenotes` count
  tags (none exists today; their `created_at` is `auto_now_add`, and
  backdating would need clock freezing - out of scope). The identical
  one-line fix is applied and verified by inspection.
- Timezone-awareness refactors of unrelated assertions.

## Decisions

- **D1 - `timezone.localdate()` in the three tags.** It returns the
  active-timezone date, matching what `__date` lookups and template
  filters use. Alternative rejected: forcing UTC on both sides
  (`timezone.override`) - changes user-facing day semantics and touches
  more code.
- **D2 - localtime anchors in tests.** `timezone.localtime(dt).strftime`
  uses exactly the basis the template used to render, so the assertion
  holds in any active timezone.
- **D3 - local-midnight fixture anchors.**
  `DailyNoteIntegrationTestCase` re-anchors:
  `dailynote1 = local midnight`, `dailynote2 = local midnight + 30min`,
  `dailynote3 = local midnight - 1s` (local yesterday). Properties:
  always in the past or negligible future, local-date stable at any run
  time, timezone independent, and the rolling 7-day
  `dailynotes_count_week` count stays exactly 3 (midnight - 1s is always
  within 7 days). Subclasses only reference the fixtures by pk/content,
  so ordering-sensitive assertions are unaffected (dailynote2 remains
  the most recent).
- **D4 - deterministic RED via divergent timezone.** The flake cannot be
  reproduced on demand by waiting for a window, so the RED run executes
  the focused modules under a `TIME_ZONE` chosen so local time lands in
  `[21:30, 23:30)`. With `k = (utc_hour - 22) mod 24`, use `Etc/GMT+{k}`
  (UTC-k) for `1 <= k <= 12` and `Etc/GMT-{24-k}` (UTC+(24-k)) for
  `13 <= k <= 23`. Example: at 06:00 UTC, `k = 8` -> `Etc/GMT+8`.
  Pre-fix, the 8 tests fail under this zone; post-fix they pass under
  both the project zone and the divergent zone.

## Risks / Trade-offs

- `dailynote2` at local midnight + 30 minutes can be a few minutes in
  the future for runs just after local midnight. `DailyNote.event_datetime`
  has no future-validation (only admissions do), and the count filters
  are date-scoped, so behavior is unchanged.
- Fixture re-anchoring changes absolute timestamps for every subclass of
  `DailyNoteIntegrationTestCase`; verified by inspection that no
  assertion depends on wall-clock-relative values.
- `outpatientprescriptions/tests/test_models.py` and
  `patients/tests/test_record_tracking_models.py` contain the same
  `strftime` pattern but compare UTC-with-UTC on both sides; both passed
  inside the failure window (full suite 2026-08-30 00:31 UTC), proving
  they are not flaky. Excluded deliberately.

## Migration Plan

No schema or data changes. Straight one-slice implementation.

## Open Questions

None.
