Execute ONLY Slice 09 as described in `slice-09.md`.

## Required pre-read order

1. `AGENTS.md`
2. `openspec/changes/improve-patient-context-and-timeline-filters/specs/patient-timeline/spec.md`
3. `openspec/changes/improve-patient-context-and-timeline-filters/design.md`
4. `openspec/changes/improve-patient-context-and-timeline-filters/slices/slice-09.md`

## Rules

- Follow TDD strictly (RED -> GREEN -> CLEAN -> VERIFY).
- Stay inside the listed files and scope.
- Add only the desktop active-filter state and clear-filter flow refinements in
  this slice.
- Keep test changes focused in `apps/patients/tests/test_patient_timeline_filter_ui.py`.
- Reuse the existing active-filter condition already used by the mobile badge:
  `current_filters.types or current_filters.quick_date or current_filters.date_from or current_filters.date_to or current_filters.creator`.
- Apply the active state only to the desktop trigger; do not redesign the mobile
  badge or mobile toggle in this slice.
- Preserve the current offcanvas trigger IDs and labels:
  `desktop-filter-trigger`, `desktop-filter-offcanvas`, and
  `desktop-filter-offcanvas-label`.
- Preserve the offcanvas filter partial and clear-filter link behavior already in
  place.
- Keep filter names, GET method, clear-filter URL semantics, and backend logic
  unchanged.
- Do not add new JavaScript or broader layout refactors in this slice.
- Stop after completion.
- Do not start any next slice until the planner reviews your implementation report.

## Checklist

### Spec

- [ ] requirements understood

### Tests (RED)

- [ ] failing tests written
- [ ] tests cover behavior and edge cases

### Implementation (GREEN)

- [ ] minimal code added
- [ ] tests pass

### Refactor (CLEAN)

- [ ] responsibilities separated
- [ ] duplication removed
- [ ] functions small
- [ ] naming improved

### Verification

- [ ] verification command passes

### Required handoff report

Return a markdown report with exactly these sections:

1. `## Slice status`
   - one line: `complete`, `blocked`, or `failed`
2. `## Summary`
   - 3-6 bullets describing what was implemented
3. `## Files changed`
   - paths only, one per bullet
4. `## Tests written or updated`
   - test names only, one per bullet
5. `## Verification`
   - exact command(s) run
   - pass/fail result for each command
6. `## Notable implementation details`
   - brief notes about the desktop active-state condition, trigger presentation,
     and preserved clear-filter flow
7. `## Out-of-scope check`
   - explicit statement confirming no out-of-scope work was done
8. `## Blockers or follow-ups`
   - bullets, or `None`

If blocked or failed, explain the first blocking point clearly and stop.

### STOP RULE

- [ ] stop here and do NOT start next slice
- [ ] hand back the implementation report for planner review
