# J4 — a student cannot finalize a discharge report

Discharge reports used to be creatable and finalizable by anyone with patient
access, which let a student close a chart. Now the create screen offers students
only **Salvar Rascunho**, and the finalize action is refused server-side even if
a tampered form submits it.

## Sub-features

- Student create screen (`/dischargereports/patient/<id>/create/`) renders one
  submit button, `Salvar Rascunho`; `button[name="save_final"]` is absent
  (`can_finalize` is `is_doctor_or_resident(request.user)`).
- A crafted POST that adds `save_final=1` is answered with `403` and the
  `Acesso Negado / Permissão Insuficiente` page.
- The legitimate draft save persists `is_draft=True`, no approver, and the
  timeline card shows the draft badge plus the `Rascunho` marker inside the
  card body.
- The draft update view (`/dischargereports/<uuid>/update/`) also hides
  `save_final` for the student, and its edit link title reads
  `Editar rascunho`.
- PDF generation/download only exists for finalized reports, so it is absent on
  a student's draft card.

## How to get to it (user POV)

1. As a student, open the patient timeline and click
   **Criar Evento → Relatório de Alta**, or go straight to
   `/dischargereports/patient/<patient-uuid>/create/`.
2. Fill the required fields (dates, specialty, history, diagnosis, exams,
   procedures, inpatient course, discharge status and recommendations) — all of
   them are `required` in the form.
3. Press **Salvar Rascunho** and land on the timeline with a badged draft card.
4. Click the card's pencil action (`title="Editar rascunho"`) to reach the
   update screen; there is still no finalize button.

## Driving it with the Playwright harness

```bash
cd .pi/skills/verify-eqmd/harness
npm run doctor && npm run setup
npm run journey:j4
```

What the script does (`journey-j4-discharge.mjs`):

1. Loads the create screen and asserts the button set is exactly
   `["Salvar Rascunho"]` with no `button[name="save_final"]`.
2. Fills the form and injects `<input type="hidden" name="save_final">` into the
   form, then submits through the real `Salvar Rascunho` button; asserts the
   navigation response status is `403` and the body says `Acesso Negado`.
3. Reloads the create screen, fills it again, saves with `save_draft`, and
   asserts the timeline draft badge.
4. Reads the row: one `Relatório de Alta` event with `is_draft=true` and no
   `draft_promoted_by`.
5. Opens the draft update view and asserts `button[name="save_final"]` is
   absent.

Evidence: `j4-discharge-finalize-denied/` (`discharge-create-screen.png`,
`discharge-crafted-post-403.png`, `timeline-discharge-draft.png`,
`discharge-draft-review.png`, `report.json`) and `db/after-j4-draft.json`.

## Gotchas

- Every discharge field is required by the model form. Fill them through their
  `name` attributes (`admission_date`, `discharge_date`, `medical_specialty`,
  `problems_and_diagnosis`, `admission_history`, `exams_list`,
  `procedures_list`, `inpatient_medical_history`, `discharge_status`,
  `discharge_recommendations`) or the POST silently re-renders with errors and
  the 403 never happens.
- The crafted POST must still be a **valid** form: `form_valid` is only reached
  after validation, so an empty form produces `200` plus field errors instead of
  the permission failure. That distinction is the point of the journey.
- Injecting the hidden field with `page.evaluate` is deliberate: it is what a
  tampered client can do. The assertion is that the server refuses it.
- Dates must not be in the future relative to the dev container clock; the
  journey uses fixed dates in the current year.
- Draft-to-final for discharge reports is a physician act
  (`_deny_non_physician_finalization`); a student POSTing `save_final` on an
  existing draft also gets `403`.
- The discharge card's pencil has no aria-label, only `title="Editar rascunho"`;
  select it by that title.
