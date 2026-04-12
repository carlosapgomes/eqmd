Execute ONLY Slice 08 as described in `slice-08.md`.

## Required pre-read order

1. `AGENTS.md`
2. `openspec/changes/improve-patient-context-and-timeline-filters/specs/patient-timeline/spec.md`
3. `openspec/changes/improve-patient-context-and-timeline-filters/design.md`
4. `openspec/changes/improve-patient-context-and-timeline-filters/slices/slice-08.md`

## Rules

- Follow TDD strictly (RED -> GREEN -> CLEAN -> VERIFY).
- Stay inside the listed files and scope.
- Remove only the fixed desktop sidebar in this slice.
- Keep test changes focused in `apps/patients/tests/test_patient_timeline_filter_ui.py`.
- Keep the desktop offcanvas trigger, IDs, and offcanvas filter content working.
- Remove the desktop sidebar wrapper from the layout so the timeline content can
  use the freed desktop width.
- Keep the mobile filter markup and behavior unchanged.
- Preserve the current desktop offcanvas filter semantics and the shared partial
  usage introduced in Slice 07.
- Do not change filter parameter names, GET semantics, backend filter logic, or
  add new JavaScript in this slice.
- Do not start Slice 09 until the planner reviews your implementation report.

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
   - brief notes about sidebar removal, widened event layout, and preserved
     offcanvas behavior
7. `## Out-of-scope check`
   - explicit statement confirming no out-of-scope work was done
8. `## Blockers or follow-ups`
   - bullets, or `None`

If blocked or failed, explain the first blocking point clearly and stop.

### STOP RULE

- [ ] stop here and do NOT start next slice
- [ ] hand back the implementation report for planner review
