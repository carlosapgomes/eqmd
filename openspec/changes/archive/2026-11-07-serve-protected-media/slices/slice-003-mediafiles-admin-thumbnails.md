# Slice 003 — mediafiles admin previews via FilePond URLs

## Identity

- Slice: `slice-003-mediafiles-admin-thumbnails`
- Change: `serve-protected-media`
- Tasks: `tasks.md` items 3.1–3.3 (Contract: this file)

## Objective

Render the `Photo` and photo-series admin previews through
the models' `get_thumbnail_url()` (the tested FilePond
`mediafiles:serve_thumbnail` route) with minimal stale-ref
repair so the pages render. No new views. `MediaFileAdmin`
is explicitly untouched (design D4 deferral).

## Read first

- `AGENTS.md`
- `openspec/changes/serve-protected-media/proposal.md`
- `openspec/changes/serve-protected-media/design.md` (D4, D5)
- `openspec/changes/serve-protected-media/specs/mediafiles/spec.md`
  (scenarios are the behavioral contract)
- `apps/mediafiles/models.py` (`Photo` and `PhotoSeriesFile`:
  FilePond `file_id`/`thumbnail_path`, `get_thumbnail_url()`;
  note NEITHER has a `media_file` FK)
- `apps/mediafiles/admin.py` (`PhotoAdmin` previews,
  `search_fields`, `fieldsets`, queryset; photo-series file
  inline preview; file-info display helpers)
- `apps/mediafiles/urls.py` (`serve_thumbnail` route name
  and `file_id` kwarg)
- `apps/mediafiles/views.py::serve_thumbnail` (FilePond
  permission contract)
- Existing admin/view tests under `apps/mediafiles/tests/`
  (extend rather than duplicate)

## Requirements

- **R1 — Photo previews**: `PhotoAdmin.thumbnail_preview`
  and `PhotoAdmin.thumbnail_preview_large` render
  `obj.get_thumbnail_url()` (None → existing placeholder
  texts, byte-for-byte). Evidence: admin preview tests.
- **R2 — Series inline**: the photo-series file inline
  preview validates BOTH `obj.file_id` and
  `obj.thumbnail_path` before calling
  `obj.get_thumbnail_url()` (missing either → existing
  placeholder; never call the getter unguarded — D4).
  Evidence: admin preview tests, incl. a
  path-without-id case.
- **R3 — Stale-ref repair (minimal)**: replace `media_file`
  dereferences that break page rendering in `PhotoAdmin`
  (`search_fields`, `fieldsets`, queryset
  `select_related`, file-info displays), the series inline
  `fields` list, and `PhotoSeriesAdmin.get_queryset()`'s
  `photoseriesfile_set__media_file` prefetch with the
  current FilePond fields; keep the repair to what
  rendering the changelist/change pages needs.
  `MediaFileAdmin`, `VideoClipAdmin`, models, and serve
  views stay untouched. Evidence: the Photo AND PhotoSeries
  admin pages render in tests.
- **R4 — Tests**: extend existing admin tests (or add a
  focused module if none cover these methods) asserting:
  Photo changelist/change-page and PhotoSeries change-page
  render 200; their previews contain the model's
  `get_thumbnail_url()`; the emitted `<img src>` is FETCHED
  and returns 200 for authorized staff (not just
  string-compared); empty `file_id`/`thumbnail_path` —
  EACH independently, incl. path-without-id — renders the
  placeholder without exception. Do NOT re-test
  `serve_thumbnail` itself beyond what its existing tests
  cover (verify they exist; report if missing).
- **R5 — No regressions**: serve views, upload flows,
  end-user photo/video pages, `MediaFileAdmin` untouched;
  admin behavior identical except the `<img src>` targets
  in R1–R2 and the R3 repairs. Evidence: focused + full
  suite.
- **R6 — Post-conditions**: `rg -n "media_file"
apps/mediafiles/admin.py` shows no remaining reference
  inside `PhotoAdmin`, the series inline, or
  `PhotoSeriesAdmin.get_queryset` (other `MediaFileAdmin`
  hits are the documented deferral);
  `rg -n "thumbnail\.url" apps/mediafiles/admin.py`
  returns nothing for the R1–R2 sites.

## Expected blast radius

Expected surfaces: `apps/mediafiles/admin.py`, extended
test module(s). Sensitive surfaces that must not change
(escalate first): models, migrations, serve views, upload
logic, end-user templates, `MediaFileAdmin`,
`VideoClipAdmin`, any other app. Extra files need
justification in the report.

## Failing-before plan

Reproduce BEFORE implementing (record outputs):

- render (via Django test client as staff) the Photo
  changelist → record the outcome: stale `media_file`
  dereference (likely 500) or raw `/media/` `<img src>`
  (404 in production).

## Implementation constraints

- No new views, no new routes, no permission changes —
  reuse the models' `get_thumbnail_url()` exactly as the
  end-user surfaces do.
- Keep placeholder texts and admin layout untouched;
  `MediaFileAdmin` byte-identical (D4 deferral).
- No commits/pushes; no dependency installs; no new deps;
  no migrations; do not update `tasks.md`.

## Validation

- Focused: `./scripts/test.sh apps.mediafiles` — green.
- Project gates: full suite (`./scripts/test.sh`) shows no
  NEW failures vs the pre-change baseline (record both);
  `ruff check` on changed `.py` files — zero new findings.

## Acceptance criteria

- [ ] AC1: Photo (both sizes) + series-inline previews use
      `get_thumbnail_url()` and the fetched URLs return 200
      (test-asserted).
- [ ] AC2: empty-reference placeholders preserved
      (test-asserted).
- [ ] AC3: Photo + PhotoSeries admin pages render (R3
      greps + test-asserted).
- [ ] AC4: `MediaFileAdmin` untouched (diff-asserted).
- [ ] AC5: focused suite green; full suite no-new-failures;
      ruff zero new findings.
- [ ] AC6: diff limited to expected blast radius (extras
      justified).

## Escalation conditions

Stop and return `BLOCKED_NEEDS_DECISION` with evidence if:
`get_thumbnail_url()` cannot serve an admin case; the R3
repair spreads beyond rendering needs (e.g. broken form
save paths that deserve their own change — do NOT fix
`PhotoForm.save()` here); existing `serve_thumbnail` test
coverage is missing and the gap blocks confidence; blast
radius must expand materially.

## Evidence report

Report: status, R1–R6 → evidence, failing-before +
passing-after, commands + exit codes, `git diff --stat`,
deviations, risks. End with `READY_FOR_REVIEW` and
`REPORT_PATH=<path>`.
