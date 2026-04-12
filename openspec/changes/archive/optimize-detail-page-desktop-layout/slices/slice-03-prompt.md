Execute ONLY Slice 03 as described in `slice-03.md`.

## Required pre-read order

1. `AGENTS.md`
2. `openspec/changes/optimize-detail-page-desktop-layout/specs/detail-page-desktop-layout/spec.md`
3. `openspec/changes/optimize-detail-page-desktop-layout/design.md`
4. `openspec/changes/optimize-detail-page-desktop-layout/slices/slice-03.md`

## Rules

- Follow TDD strictly (RED -> GREEN -> CLEAN -> VERIFY).
- Stay inside the listed files and scope.
- Keep test changes focused in
  `apps/historyandphysicals/tests/test_detail_context_ui.py`.
- Replace only the desktop sidebar layout in `historyandphysical_detail`.
- Remove the desktop-only sidebar layout structure and classes such as
  `desktop-layout`, `patient-sidebar`, and `content-main` if they are no longer
  needed after the refactor.
- Render the shared patient context summary as a full-width desktop top card.
- Render the H&P metadata card as a full-width desktop top card below it.
- Keep the content card below those top cards.
- Preserve the shared patient context include and keep page-specific metadata
  outside the shared component.
- Keep H&P actions and event datetime visible.
- Keep mobile markup and behavior unchanged.
- Do not change the shared component contract in
  `templates/components/_patient_context_summary.html` in this slice.
- Do not touch `dailynote_detail` or `simplenote_detail` in this slice.
- Do not redesign breadcrumbs, action buttons, or event content rendering.
- Do not introduce a new shared layout partial in this slice.
- Do not start any next slice until the planner reviews your implementation
  report.

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
   - brief notes about removed desktop sidebar classes, full-width top cards,
     and mobile preservation
7. `## Out-of-scope check`
   - explicit statement confirming no out-of-scope work was done
8. `## Blockers or follow-ups`
   - bullets, or `None`

If blocked or failed, explain the first blocking point clearly and stop.

### STOP RULE

- [ ] stop here and do NOT start next slice
- [ ] hand back the implementation report for planner review
