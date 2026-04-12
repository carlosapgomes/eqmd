Execute ONLY Slice 03 as described in `slice-03.md`.

## Required pre-read order

1. `AGENTS.md`
2. `openspec/changes/improve-patient-context-and-timeline-filters/specs/patient-context-ui/spec.md`
3. `openspec/changes/improve-patient-context-and-timeline-filters/design.md`
4. `openspec/changes/improve-patient-context-and-timeline-filters/slices/slice-03.md`

## Rules

- Follow TDD strictly (RED -> GREEN -> CLEAN -> VERIFY).
- Stay inside the listed files and scope.
- Reuse the same shared patient context component created in Slices 01 and 02.
- Replace both the mobile and desktop duplicated patient context blocks in the
  daily note detail page.
- Preserve the current mobile/desktop layout structure.
- Keep daily note-specific metadata and actions outside the shared component.
- Do not start simple note, H&P, or filter work.
- Stop after completion.
- Do not start Slice 04 until the planner reviews your implementation report.

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
   - brief notes about how the shared component was reused
   - how both mobile and desktop duplicated context blocks were handled
   - how daily note-specific metadata/actions were kept outside it
7. `## Out-of-scope check`
   - explicit statement confirming no out-of-scope work was done
8. `## Blockers or follow-ups`
   - bullets, or `None`

If blocked or failed, explain the first blocking point clearly and stop.

### STOP RULE

- [ ] stop here and do NOT start next slice
- [ ] hand back the implementation report for planner review
