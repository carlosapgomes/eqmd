# J2 — drafts-only timeline filter and role-dependent draft actions

The patient timeline mixes definitive events with supervised drafts. A
`drafts_only` filter narrows it to drafts, and the same draft exposes different
actions depending on who is looking at it.

## Sub-features

- Filter checkbox **Somente rascunhos** (`name="drafts_only"`, value `1`) in the
  filter panel; the desktop offcanvas copy is `#oc-drafts_only`, the mobile
  collapse copy is `#mobile_drafts_only`.
- The filter is a plain GET parameter: `/patients/<id>/timeline/?drafts_only=1`
  is shareable and survives reloads.
- Active-filter indicator: the filter trigger shows a badge with the text
  `Ativos`.
- Only draft cards remain in the results; definitive notes disappear even
  though they exist in the database.
- Same draft, two roles: the student sees the supervision banner and only
  `Salvar rascunho`; a doctor sees the same banner plus `Salvar definitivo`.

## How to get to it (user POV)

1. Log in as a doctor and create a note (**Criar Evento → Nota/Observação**) —
   a physician-authored note is definitive immediately and carries no badge.
2. Log in as a student and create a second note — it is a draft.
3. Open the timeline: both cards are present, only the student's is badged.
4. Click **Filtros** (`#desktop-filter-trigger`), tick **Somente rascunhos**,
   and apply. The URL gains `?drafts_only=1` and only the draft card remains.
5. Click **Revisar** on the draft as the student, then open the same
   `/simplenotes/<uuid>/update/` URL as the doctor.

## Driving it with the Playwright harness

```bash
cd .pi/skills/verify-eqmd/harness
npm run doctor && npm run setup
npm run journey:j2
```

What the script does (`journey-j2-drafts-only.mjs`):

1. Doctor session creates a definitive note (`createSimplenote` on the create
   URL); asserts the timeline has no `.draft-badge`.
2. Student session creates a draft through the timeline dropdown; asserts one
   `.draft-badge`.
3. Navigates to `?drafts_only=1`; asserts exactly one `article.timeline-card`,
   that its text is the student draft, that the definitive note's text is absent
   from the whole page, that `#oc-drafts_only` is checked, and that the
   `Ativos` badge is rendered.
4. Opens the draft as the student (banner, only `Salvar rascunho`), then opens
   the same URL as the doctor (banner plus `Salvar definitivo`).

Evidence: `j2-drafts-only-filter/` (screenshots `timeline-mixed.png`,
`timeline-drafts-only.png`, `doctor-review-same-draft.png`, `report.json`).

## Gotchas

- Two filter panels render the same fields: the desktop offcanvas
  (`id` prefix `oc-`) and the mobile collapse (prefix `mobile_`). Read or set
  the desktop copy (`#oc-drafts_only`) — the mobile one is visible only under
  `lg`.
- `drafts_only` is truthy for any non-empty value; the app checks
  `request.GET.get("drafts_only")`, so `?drafts_only=1` and
  `?drafts_only=true` behave the same.
- A physician-created note is definitive on the spot (the create view never
  marks it a draft). That is how the mixed timeline in this journey is built —
  do not try to make a doctor's fresh note a draft via the UI.
- The `Ativos` badge appears for any active filter (types, dates, creator,
  drafts), so its presence alone does not prove the drafts filter is on; the
  checked checkbox and the reduced card set are the real assertions.
- Empty patient timelines cache filter/count data for 60–300 seconds
  (`cache.set` in `PatientEventsTimelineView`). If a rerun looks stale, use a
  fresh scaffold patient (`npm run setup` after `npm run cleanup`) rather than
  waiting on the cache.
