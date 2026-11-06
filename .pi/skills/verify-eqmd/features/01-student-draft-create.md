# J1 — a student's SimpleNote lands as a draft

A user with `profession_type = student` can create clinical notes, but nothing
they save enters the definitive record on its own: the row persists with
`is_draft=True` and waits for a physician. The timeline shows that state
immediately, and the review screen offers drafts-only actions.

## Sub-features

- Timeline card carries the draft tint (`timeline-card-draft`, warning border
  and cream background) and a warning badge reading `Rascunho · há …`.
- The badge includes the age of the draft (`timesince`, so a fresh draft reads
  `Rascunho · há 0 minuto`).
- The card action group swaps "Editar" for `Revisar` (aria-label
  `Revisar rascunho da nota`), i.e. there is no one-click approve on the
  timeline.
- Drafts are not duplicable: the copy action is hidden until the note is final.
- The review screen shows the supervision banner
  (`[data-draft-supervision-banner]`, text `Rascunho aguardando aprovação`) and
  offers a single action, `Salvar rascunho`.
- Persisted row: `is_draft=True`, `created_by` = the student,
  `draft_promoted_by` still empty.

## How to get to it (user POV)

1. Log in at `/accounts/login/` with a student account (e-mail + password,
   landing on `/dashboard/`).
2. Open the patient timeline: `/patients/<patient-uuid>/timeline/` (from
   `/patients/`, or directly with the scaffold patient id).
3. Click **Criar Evento** (`#createEventDropdownDesktop`).
4. Choose **Nota/Observação** under "Notas Clínicas" — the link goes to
   `/simplenotes/patient/<patient-uuid>/create/`.
5. Type the note in the editor and press **Salvar Nota**.
6. You are redirected back to the timeline, where the new card is tinted and
   badged as a draft.

## Driving it with the Playwright harness

```bash
cd .pi/skills/verify-eqmd/harness
npm run doctor && npm run setup
npm run journey:j1
```

What the script does (`journey-j1-draft-create.mjs`):

1. Asserts the create screen renders exactly one submit button (`Salvar Nota`)
   and no `button[name="save_final"]`.
2. Clicks `.CodeMirror` and types with the keyboard (EasyMDE replaced the
   textarea), then submits.
3. Asserts on the timeline: `article.timeline-card.timeline-card-draft` exists,
   `.draft-badge` text matches `/^Rascunho · há /`,
   `a[aria-label="Revisar rascunho da nota"]` exists, the duplicate action is
   absent.
4. Probes the database (read-only ORM): one row of type `Nota/Observação`,
   `is_draft=true`, `created_by` = `verify.student@eqmd-verify.invalid`.
5. Opens the review screen and asserts the banner plus exactly one submit
   button, `Salvar rascunho`.

Evidence: `${EQMD_VERIFY_EVIDENCE_ROOT:-/tmp/eqmd-verify}/<run-id>/`
`j1-student-creates-draft/` (screenshots, trace, `report.json`) and
`db/after-j1-create.json`.

## Gotchas

- The create screen has **one** button (`Salvar Nota`). "Salvar definitivo"
  only exists later, on the draft review screen, and only for physicians. Do
  not look for it here.
- EasyMDE wraps `#id_content` in CodeMirror. `page.fill('#id_content', …)` times
  out because the textarea is hidden; click `.CodeMirror` and use the keyboard.
- Every create link appears twice: a mobile dropdown
  (`#createEventDropdownMobile`) and a desktop one
  (`#createEventDropdownDesktop`). `.first()` resolves to the invisible mobile
  item and the click hangs — always scope selectors to
  `ul[aria-labelledby="createEventDropdownDesktop"]`.
- Content shorter than 10 characters is rejected by `SimpleNoteForm.clean_content`
  and the note is not saved. The journey text is deliberately longer.
- `event_datetime` defaults to "now" in the form; a future timestamp is
  rejected, so never back-date the scaffold patient's chart into the future.
- The badge age comes from `timesince`, so its text is locale- and
  minute-dependent (`há 0 minuto`, `há 1 minuto`); assert the prefix
  `Rascunho · há`, not a fixed string.
- The scaffold patient must start with zero events, so `setup` never adopts an
  existing row: if a patient named `VERIFICACAO Skill <run-id>` already exists (a
  failed attempt, or a same-second run-id collision) it exits non-zero, names
  that row and creates nothing. `npm run cleanup` deletes by the id `setup`
  recorded in `scaffold.json` and re-verifies name and creator first, so an
  equal-named row this run did not create cannot be deleted by mistake. Clear a
  stale patient by re-running cleanup under the id that created it
  (`EQMD_VERIFY_RUN_ID=<old-id> npm run cleanup`, plus
  `EQMD_VERIFY_PATIENT_ID=<uuid>` if that run's `scaffold.json` is gone); a
  cleanup under a new run id deliberately leaves it alone.
