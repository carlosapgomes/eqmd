# Shared execution and report contract (compact-tag-selector-results)

Single-slice change. The loop protocol is the same used by
`add-specialty-team-tag-governance`: one approved slice per worker run, TDD
where a test surface exists, fresh read-only reviewer, parent-executed
acceptance gates, `tasks.md` updated only by the parent after acceptance, no
commits by agents.

## Report schema

Workers report to `/tmp/eqmd-compact-tags-slice-001-report.md` with: status
(`READY_FOR_REVIEW` or `BLOCKED_NEEDS_DECISION`), requirement matrix, files
touched, evidence log paths, command exit statuses, verification screenshots
and any honest limitations. Evidence logs go to `/tmp/eqmd-compact-tags-logs/`.

## Completion marker

The worker's final message ends with exactly:

```text
READY_FOR_REVIEW
REPORT_PATH=/tmp/eqmd-compact-tags-slice-001-report.md
```

## Slices

- S1 — [slice-001-compact-results.md](slice-001-compact-results.md):
  compact non-redundant selector results, keyboard operation and polite
  announcements on list and map. No dependencies.

## Escalation

Stop with `BLOCKED_NEEDS_DECISION` (via `contact_supervisor`) if the change
requires backend/payload changes, new dependencies, template rewrites beyond
attribute additions, or any contract listed in design D6 to be broken.
