## Phase 1 - Validate the new desktop top-card layout

- [x] 1.1 Add OpenSpec artifacts for desktop detail layout refinement
- [x] 1.2 Slice 01: replace the desktop sidebar layout in `dailynote_detail`
- [x] 1.3 Review Slice 01 implementation report and visual consistency before
      expanding the pattern
- [x] 1.4 Slice 02: adopt the same desktop top-card layout in
      `simplenote_detail`
- [x] 1.5 Review Slice 02 before touching `historyandphysical_detail`
- [x] 1.6 Slice 03: adopt the same desktop top-card layout in
      `historyandphysical_detail`
- [x] 1.7 Review Slice 03 and confirm cross-page consistency

## Verification notes

- Implement exactly one slice at a time with TDD.
- Read `AGENTS.md` -> spec/design -> current slice before implementation.
- Only files listed in the current slice may be touched, plus minimal context
  files.
- Use `./scripts/test.sh <target>` for slice verification.
- If Markdown files are changed, run `markdownlint-cli2` and fix all reported
  errors.
- Keep mobile behavior unchanged in this change.
