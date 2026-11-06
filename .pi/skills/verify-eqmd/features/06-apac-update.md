# J6 — APAC update view prefills the persisted submission

APAC (national form) submissions joined the normal event semantics: a real
update view opens from the stored submission, prefilled with the persisted
values, and a draft is edited in place rather than re-captured.

## Sub-features

- Capture: `/pdf-forms/apac/<patient-uuid>/` with a procedure autocomplete
  (`.procedure-search-input`, results in `.procedure-results`), an ICD-10
  autocomplete (`.icd10-search-input`, results in `#icd10-results-main`), and
  `textarea[name="main_diagnosis"]`.
- Patient identity fields are prefilled from the patient row
  (`patient_name`, `patient_gender`, `patient_birth_date`).
- Saving redirects to the submission detail
  `/pdf-forms/submission/<uuid>/` and confirms
  `Formulário APAC criado com sucesso!`.
- Update: `/pdf-forms/apac/submission/<uuid>/edit/` prefills the persisted
  `form_data` (`patient_name`, `main_diagnosis`, the selected
  `main_procedure`/`main_icd_id` hidden ids).
- A student's submission stays a supervised draft: the update view shows the
  `Rascunho aguardando aprovação` banner and only `Salvar rascunho`
  (`button[name="save_final"]` is physician-only).
- Editing one line, saving the draft, and reopening the update view shows the
  edited value; the row keeps `is_draft=true` and the student as author.

## How to get to it (user POV)

1. As a student, open the patient timeline and choose **Criar Evento →
  Formulário APAC** (`/pdf-forms/apac/<patient-uuid>/`).
2. Type part of a procedure name, pick a suggestion, type part of a diagnosis,
   pick an ICD-10 suggestion, and fill the main diagnosis plus the other APAC
   fields.
3. Press **Salvar Formulário APAC** and confirm the browser prompt
   (`Confirma o envio do formulário?`).
4. On the submission page use **Editar** to reach
   `/pdf-forms/apac/submission/<uuid>/edit/`; the fields are already filled.
5. Change the diagnosis, press **Salvar rascunho**, confirm the prompt, and
   reopen the update view to see the new value.

## Driving it with the Playwright harness

```bash
cd .pi/skills/verify-eqmd/harness
npm run doctor && npm run setup
npm run journey:j6
```

What the script does (`journey-j6-apac-update.mjs`):

1. Picks the first procedure suggestion (`consulta`) and the first ICD-10
   suggestion (`hipertensao`) by clicking real `.dropdown-item` entries, fills
   `main_diagnosis`, and submits.
2. Waits for `/pdf-forms/submission/<uuid>/`, derives the update URL, and
   asserts no `Selecione …` dialog was raised (the JS blocks the submit when a
   hidden id is missing).
3. Opens the update view: banner present, exactly one submit button
   (`Salvar rascunho`), and the prefilled values equal what was submitted.
4. Edits `main_diagnosis`, saves the draft, reopens the view, and asserts the
   new value plus the `atualizado com sucesso` confirmation.
5. Probes the row: one `Formulário PDF` event, `is_draft=true`, author = the
   student.

Evidence: `j6-apac-update-prefill/` (`apac-submission-detail.png`,
`apac-update-prefilled.png`, `apac-update-after-edit.png`, `report.json`) and
`db/after-j6-update.json`.

## Gotchas

- The submit is gated by JavaScript: a missing procedure or ICD-10 selection
  triggers `alert('Selecione …')` and `preventDefault()`. The harness records
  every native dialog in `report.json`, and the journey fails if one starts with
  `Selecione`. Filling only the visible text field is not enough — the hidden
  `main_procedure` / `main_icd_id` must be set by clicking a suggestion.
- The save fires a `confirm()` (`Confirma o envio do formulário?`). Playwright's
  dialog handler accepts it; without a handler the navigation never happens.
- Autocomplete suggestions come from `/api/procedures/search/` and
  `/api/icd10/search/`; the seed data must contain matches for the query terms
  used (`consulta`, `hipertensao`). If the search returns nothing, the journey
  fails with a timeout on the dropdown item — do not fall back to typing raw
  text.
- The APAC form posts to its own URL (`<form method="post" id="apac-form">`, no
  `action`), so the create and update views share the template and differ only
  by `is_update`/`is_draft_submission`.
- The "Aguardando aprovação" text lives in the update template, not on the
  submission detail page. Assert the banner on the edit screen.
- `main_diagnosis` is the only free-text required field; patient identity comes
  from the patient row, so the scaffold patient (unnamed gender, birthday
  1980-01-01) is what appears prefilled.
