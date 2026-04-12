Execute ONLY Slice 05 as described in `slice-05.md`.

## Required pre-read order

1. `AGENTS.md`
2. `openspec/changes/improve-patient-context-and-timeline-filters/specs/patient-context-ui/spec.md`
3. `openspec/changes/improve-patient-context-and-timeline-filters/design.md`
4. `openspec/changes/improve-patient-context-and-timeline-filters/slices/slice-05.md`

## Rules

- Follow TDD strictly (RED -> GREEN -> CLEAN -> VERIFY).
- Stay inside the listed files and scope.
- Reuse the same shared patient context component created in Slices 01 and 02.
- Replace both the mobile and desktop duplicated patient context blocks in the
  history and physical detail page.
- Preserve the current mobile/desktop layout structure.
- Create the focused test module
  `apps/historyandphysicals/tests/test_detail_context_ui.py` for this slice
  instead of broadening existing test files unnecessarily.
- Keep H&P-specific metadata and actions outside the shared component,
  including event datetime, phone, RG, description, created-by/updater info,
  action buttons, and breadcrumb.
- Use unique collapse IDs for mobile and desktop contexts to avoid collisions.
- Do not spend scope on residual CSS cleanup unless it is strictly necessary to
  keep the adopted page working correctly.
- Do not start filter work.
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
   - brief notes about how the shared component was reused
   - how both mobile and desktop duplicated context blocks were handled
   - how H&P-specific metadata/actions were kept outside it
7. `## Out-of-scope check`
   - explicit statement confirming no out-of-scope work was done
8. `## Blockers or follow-ups`
   - bullets, or `None`

If blocked or failed, explain the first blocking point clearly and stop.

### STOP RULE

- [ ] stop here and do NOT start next slice
- [ ] hand back the implementation report for planner review
