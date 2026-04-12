Execute ONLY Slice 02 as described in `slice-02.md`.

## Required pre-read order

1. `AGENTS.md`
2. `openspec/changes/improve-patient-context-and-timeline-filters/specs/patient-context-ui/spec.md`
3. `openspec/changes/improve-patient-context-and-timeline-filters/specs/patient-timeline/spec.md`
4. `openspec/changes/improve-patient-context-and-timeline-filters/design.md`
5. `openspec/changes/improve-patient-context-and-timeline-filters/slices/slice-02.md`

## Rules

- Follow TDD strictly (RED -> GREEN -> CLEAN -> VERIFY).
- Stay inside the listed files and scope.
- Maintain the same component created in Slice 01; extend it instead of
  creating a second patient-context component.
- Do not broaden into detail pages.
- Do not start filter offcanvas work.
- Focus only on the expandable details behavior:
  - birth date
  - gender
  - admission date only for active admission
  - admission duration only for active admission
- Stop after completion.
- Do not start Slice 03 until the planner reviews your implementation report.

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
   - brief notes about expanded-field behavior and active-admission conditions
7. `## Out-of-scope check`
   - explicit statement confirming no out-of-scope work was done
8. `## Blockers or follow-ups`
   - bullets, or `None`

If blocked or failed, explain the first blocking point clearly and stop.

### STOP RULE

- [ ] stop here and do NOT start next slice
- [ ] hand back the implementation report for planner review
