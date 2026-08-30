# Tasks: fix-date-boundary-suite-flakiness

## 1. Slice 01 - Timezone-consistent day scope and anchors

- [x] 1.1 Make the three day-scoped dashboard tags use the active-timezone
      local date (`timezone.localdate()`)
- [x] 1.2 Anchor the seven UTC-rendered date assertions to
      `timezone.localtime(<datetime>)` so expected strings match template
      rendering
- [x] 1.3 Re-anchor `DailyNoteIntegrationTestCase` fixtures to local-midnight
      instants so today/week counts are deterministic at any wall-clock time
- [x] 1.4 Prove RED under a divergent `TIME_ZONE`, GREEN under both zones,
      run every gate, and create
      `/tmp/fix-date-boundary-suite-flakiness-slice-01-report.md`

Verifier note (2026-08-30, third LLM): verified COMPLETE. Waiver on the
in-window baseline ratified (failing set was exactly the eight
pre-verified targets of this change; final gates prove the outcome).
Ruff/format parity re-proven via targeted stash (14 frozen findings,
zero NEW vs BASE_REF; stdin-based proof is unreliable in this setup).
Full suite 2699 OK (skipped=25) reproduced under BOTH the project zone
and a divergent zone (Etc/GMT-11), the strongest wall-clock independence
proof short of the real window.
