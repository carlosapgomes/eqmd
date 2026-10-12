# Tasks: Duplicate Outpatient Prescription

## S1 — Duplicate endpoint (clone + guards + redirect)

- [x] 1.1 POST clones header/items per D2, redirects to copy edit
      Contract: `slices/slice-001-duplicate-endpoint.md` (ACCEPTED)
- [x] 1.2 Guards: patient access, `add_event`, GET rejected, no
      `usage_count` change
      Contract: `slices/slice-001-duplicate-endpoint.md` (ACCEPTED)

## S2 — Duplicate button on detail

- [x] 2.1 Inline POST "Duplicar" control, gated on `add_event`
      Contract: `slices/slice-002-duplicate-button.md` (ACCEPTED)
- [x] 2.2 Visibility tests (shown/hidden) through the detail view
      Contract: `slices/slice-002-duplicate-button.md` (ACCEPTED)
