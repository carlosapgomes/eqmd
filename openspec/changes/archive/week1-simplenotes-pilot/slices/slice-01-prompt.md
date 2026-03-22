Execute ONLY Slice 01 as described in slice-01.md.

Rules:
- Follow TDD strictly (RED -> GREEN -> REFACTOR).
- Keep functions <= 25 lines where feasible in touched code.
- No scope creep outside listed files.
- Run the verification command listed in the slice.
- Stop after this slice is green.

Checklist:
Spec
- [x] requirements understood

Tests (RED)
- [x] failing tests written
- [x] tests cover behavior and edge cases

Implementation (GREEN)
- [x] minimal code added
- [x] tests pass

Refactor (CLEAN)
- [x] responsibilities separated
- [x] duplication removed
- [x] functions small
- [x] naming improved

Verification
- [x] verification command passes

STOP RULE
- [x] stop here and do NOT start next slice
