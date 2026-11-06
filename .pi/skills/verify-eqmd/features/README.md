# Feature map — verify-eqmd

Index of the user-facing journeys this skill can drive in the running EquipeMed
app. Each file answers, from the user's point of view: what the feature is, how
to reach it, how to drive it with the Playwright harness, and what proves it
works. Read the matching `journey-j*.mjs` next to it for the executable spine.

Harness: `.pi/skills/verify-eqmd/harness` (Node + Playwright 1.65.0, system
Chrome through `channel: "chrome"`). Every journey assumes `npm run doctor` is
green and `npm run setup` has created the scaffold users and patient.

- **J1 — student note lands as a draft.** `01-student-draft-create.md`,
  script `journey-j1-draft-create.mjs`.
- **J2 — drafts-only filter and role-dependent actions.**
  `02-drafts-only-filter.md`, script `journey-j2-drafts-only.mjs`.
- **J3 — doctor finalizes a draft.** `03-doctor-finalizes-draft.md`,
  script `journey-j3-finalize.mjs`.
- **J4 — a student cannot finalize a discharge report.**
  `04-discharge-report-draft.md`, script `journey-j4-discharge.mjs`.
- **J5 — photo draft: upload, inline view, download denial, hard delete.**
  `05-photo-draft.md`, script `journey-j5-photo-draft.mjs`.
- **J6 — APAC update view prefills the persisted submission.**
  `06-apac-update.md`, script `journey-j6-apac-update.mjs`.

All six were executed against the running dev stack and passed; the evidence of
the last full run is under `/tmp/eqmd-verify/<run-id>/`.

Run them all:

```bash
cd .pi/skills/verify-eqmd/harness
npm run verify -- --all
```

Source of truth for the behaviour: `openspec/changes/add-student-draft-supervision/`
(proposal, design D1–D13, and the `student-drafts` spec). If a journey and the
spec disagree, the journey fails and the reason belongs in that feature's
Gotchas — never relax the journey.

## Not yet mapped

These user-facing surfaces exist but have no scripted journey yet; add a
`journey-j*.mjs` next to the others before claiming them:

- Dailynote and H&P draft flows (same selectors as J1, different create URLs:
  `/dailynotes/patient/<id>/create/` and
  `/historyandphysicals/patient/<id>/create/`).
- Consent form and outpatient prescription drafts.
- Photo series and video clip drafts (FilePond, multiple files).
- Timeline tag badges and the temporary-record registration flow.
- Matrix/bot promotion path (`/botauth/`), which deliberately keeps bot drafts
  out of the human supervision flow.

## Known console noise

Every page load logs one `404` network error in the browser console. It is a
pre-existing template bug unrelated to the draft flows: the dashboard requests
`/dashboard/%22%22` (a literal `""` used as a URL). Journeys record console
errors in `report.json` but do not fail on them; ignore this one when reading a
report and investigate anything else.
