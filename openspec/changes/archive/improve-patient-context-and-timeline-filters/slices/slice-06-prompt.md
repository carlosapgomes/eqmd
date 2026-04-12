Execute ONLY Slice 06 as described in `slice-06.md`.

## Required pre-read order

1. `AGENTS.md`
2. `openspec/changes/improve-patient-context-and-timeline-filters/specs/patient-timeline/spec.md`
3. `openspec/changes/improve-patient-context-and-timeline-filters/design.md`
4. `openspec/changes/improve-patient-context-and-timeline-filters/slices/slice-06.md`

## Rules

- Follow TDD strictly (RED -> GREEN -> CLEAN -> VERIFY).
- Stay inside the listed files and scope.
- Add only the desktop trigger and offcanvas shell in this slice.
- Create the focused test module `apps/patients/tests/test_patient_timeline_filter_ui.py`
  for this slice instead of broadening unrelated test files.
- Do not move the existing desktop filter form yet.
- Do not remove or hide the existing desktop filter sidebar in this slice.
- The new offcanvas shell should not contain duplicated filter form fields yet.
- Keep the current mobile filter collapse unchanged.
- Do not start Slice 07 until the planner reviews your implementation report.

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
   - brief notes about trigger placement, offcanvas IDs, and accessibility
7. `## Out-of-scope check`
   - explicit statement confirming no out-of-scope work was done
8. `## Blockers or follow-ups`
   - bullets, or `None`

If blocked or failed, explain the first blocking point clearly and stop.

### STOP RULE

- [ ] stop here and do NOT start next slice
- [ ] hand back the implementation report for planner review
