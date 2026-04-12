Execute ONLY Slice 07 as described in `slice-07.md`.

## Required pre-read order

1. `AGENTS.md`
2. `openspec/changes/improve-patient-context-and-timeline-filters/specs/patient-timeline/spec.md`
3. `openspec/changes/improve-patient-context-and-timeline-filters/design.md`
4. `openspec/changes/improve-patient-context-and-timeline-filters/slices/slice-07.md`

## Rules

- Follow TDD strictly (RED -> GREEN -> CLEAN -> VERIFY).
- Stay inside the listed files and scope.
- Move only the desktop filter form into shared offcanvas content.
- Keep test changes focused in `apps/patients/tests/test_patient_timeline_filter_ui.py`.
- Reuse one canonical desktop filter partial for the existing desktop sidebar and
  the desktop offcanvas content.
- If the partial is rendered twice on the same page, ensure all HTML `id`
  attributes remain unique via context variables or a prefix strategy.
- Preserve existing filter parameter names (`types`, `quick_date`, `date_from`,
  `date_to`, `creator`), GET method, checked or selected state, and clear-filter
  URL semantics.
- Keep Slice 06 IDs unchanged: `desktop-filter-trigger`,
  `desktop-filter-offcanvas`, and `desktop-filter-offcanvas-label`.
- Do not remove the old desktop sidebar wrapper or change the desktop layout in
  this slice.
- Keep current mobile filter markup and behavior unchanged.
- Do not add new JavaScript or backend filter logic in this slice.
- Do not start Slice 08 until the planner reviews your implementation report.

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
   - brief notes about the shared filter partial, unique ID strategy if used,
     and preserved query semantics
7. `## Out-of-scope check`
   - explicit statement confirming no out-of-scope work was done
8. `## Blockers or follow-ups`
   - bullets, or `None`

If blocked or failed, explain the first blocking point clearly and stop.

### STOP RULE

- [ ] stop here and do NOT start next slice
- [ ] hand back the implementation report for planner review
