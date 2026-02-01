Execute ONLY Slice 01 as described in slice-01.md.

Rules:
- Follow TDD strictly (tests first).
- Keep functions <= 25 lines, no duplication, no business logic in views.
- Use services for business logic.
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
- [ ] business logic only in services

Verification
- [ ] pytest passes
- [ ] lint/ruff/flake8 passes (if configured)
- [ ] type checks (mypy) pass (if configured)

STOP RULE
- [ ] stop here and do NOT start next slice
