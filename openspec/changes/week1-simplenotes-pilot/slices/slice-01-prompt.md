Execute ONLY Slice 01 as described in slice-01.md.

Rules:
- Follow TDD strictly (RED -> GREEN -> REFACTOR).
- Keep functions <= 25 lines where feasible in touched code.
- No scope creep outside listed files.
- Run the verification command listed in the slice.
- Stop after this slice is green.

Checklist:
Spec
- [ ] requirements understood

Tests (RED)
- [ ] failing tests written
- [ ] tests cover behavior and edge cases

Implementation (GREEN)
- [ ] minimal code added
- [ ] tests pass

Refactor (CLEAN)
- [ ] responsibilities separated
- [ ] duplication removed
- [ ] functions small
- [ ] naming improved

Verification
- [ ] verification command passes

STOP RULE
- [ ] stop here and do NOT start next slice
