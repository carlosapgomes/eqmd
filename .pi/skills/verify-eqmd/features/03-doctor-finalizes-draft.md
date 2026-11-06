# J3 — a doctor finalizes a student draft

Approval happens inside the edit screen, not on the timeline: a physician opens
the draft and uses **Salvar definitivo**. The record then joins the chart with
its original author intact and the approver recorded.

## Sub-features

- `Salvar definitivo` (`button[name="save_final"]`) is rendered only when the
  record is a draft **and** the viewer is a doctor or resident; the student sees
  only `Salvar rascunho`.
- On success the timeline badge and the draft tint disappear, `Revisar` is
  replaced by the normal edit action, and the flash message reads
  `Nota para <paciente> aprovada e registrada no prontuário.`
- The author does not change: `created_by` stays the student.
- The approver is recorded: `draft_promoted_by` = the doctor,
  `draft_promoted_at` = the approval timestamp.
- The approved card footer names both people: `Criado por Estudante
  Verificação` (the student created it) and `Aprovado por Médico Verificação em
  <data>` (the doctor approved it). Those exact strings come from the scaffold
  display names, so the assertions never depend on a username fallback.
- A draft card shows no approver line at all, even while the approval metadata
  is still empty.
- The student is locked out afterwards: the edit URL returns `403` with the
  `Acesso Negado / Permissão Insuficiente` page, because post-finalization
  ownership belongs to the finalizer within the 24h window.

## How to get to it (user POV)

1. As a student, create a note (**Criar Evento → Nota/Observação**) and land on
   the timeline with the draft badge.
2. As that student, click **Revisar** — you see the supervision banner and only
   `Salvar rascunho`.
3. As a doctor, open the same patient timeline and click **Revisar** on the same
   card. The same page now also offers **Salvar definitivo**.
4. Click **Salvar definitivo**: you return to the timeline, the card is a normal
   final event, and the success message confirms the approval. The card footer
   now reads `Criado por Estudante Verificação` and `Aprovado por Médico
   Verificação em <data> <hora>`.
5. Back as the student, reload the edit URL — `403`.

## Driving it with the Playwright harness

```bash
cd .pi/skills/verify-eqmd/harness
npm run doctor && npm run setup
npm run verify -- --journeys j3     # recommended proof journey
```

What the script does (`journey-j3-finalize.mjs`):

1. Student session creates the note from the timeline dropdown and asserts the
   badge/tint/`Revisar` state (the J1 checkpoints), plus a footer that names the
   student and carries no approver line.
2. Student review screen: banner present, exactly one submit button
   (`Salvar rascunho`), no `button[name="save_final"]`.
3. Doctor session: same card is badged, `Revisar` opens the same URL, banner
   present, `Salvar definitivo` present.
4. Doctor clicks `save_final`; timeline has no `.draft-badge`, no
   `timeline-card-draft`, no `Revisar`, and shows the approval message.
5. The approved card footer is read from the DOM: `.event-creator` is
   `Estudante Verificação`, `.event-approver` is `Médico Verificação`, and the
   footer text matches `Aprovado por Médico Verificação em dd/mm/aaaa hh:mm`
   (screenshot `timeline-approved-card-attribution.png`).
6. Read-only probe: one `Nota/Observação` row with `is_draft=false`,
   `created_by=verify.student@…`, `draft_promoted_by=verify.doctor@…`,
   `draft_promoted_at` set.
7. Student re-opens the edit URL and gets `403` with `Acesso Negado` on screen.

Evidence: `j3-doctor-finalizes-draft/` (seven screenshots including
`timeline-approved-card-attribution.png`, the two context traces, `report.json`)
plus `db/after-j3-finalize.json`.

## Gotchas

- The students group holds `events.change_event`, so the update view is not
  blocked by the Django permission — the lockout after approval comes from the
  object-level `can_edit_event` rule (finalizer's 24h window). A student who
  expects to keep editing their own approved note is correctly refused.
- The approval gate is server-side as well: injecting `save_final` into the POST
  as a student raises `PermissionDenied`. J4 proves that for discharge reports;
  the same rule lives in `SimpleNoteUpdateView.form_valid`.
- Two sessions are required. Reusing the student context for the doctor step
  would prove nothing about role differences.
- `draft_promoted_at` is only written on the draft→final flip; a note created
  directly as definitive by a physician has it empty. Do not assert it there.
- The success message text is asserted verbatim
  (`aprovada e registrada no prontuário`); if the copy changes, update the
  journey and this page together.
- The two attribution strings depend on the scaffold display names
  (`scaffold.py`): "Estudante Verificação" and "Médico Verificação". Without
  them the footer falls back to the `.invalid` username, which the assertions
  would reject.
- The 403 page is the project's own template (`Acesso Negado`,
  `Permissão Insuficiente`), not Django's debug page — `DEBUG` is irrelevant
  here, the status code is what matters.
