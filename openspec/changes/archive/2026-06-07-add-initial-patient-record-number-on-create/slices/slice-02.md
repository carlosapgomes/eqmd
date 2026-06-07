# Slice 02 - UI exclusiva de criação e relatório final

## Goal

Exibir o campo obrigatório de número inicial de prontuário apenas na tela atual
de criação de paciente, garantir que edição de paciente não exponha nem altere o
prontuário, e registrar evidências finais em relatório temporário.

## Scope boundaries

### Included

- UI em `patient_create.html` para `initial_record_number`.
- Testes de renderização no create e ausência no update.
- Teste de defesa: update ignora POST inesperado de `initial_record_number`.
- Relatório temporário de implementação.

### Excluded

- Alterações em `patient_update.html`.
- Alterações em templates legados (`patient_form.html`).
- Alterações no fluxo dedicado de `PatientRecordNumber`.
- Refatoração ampla de templates.

## Files allowed

- `apps/patients/templates/patients/patient_create.html`
- `apps/patients/tests/test_templates.py`
- `apps/patients/tests/test_views.py`
- Opcional, se mais claro:
  - `apps/patients/tests/test_initial_record_number_create.py`
- Relatório obrigatório:
  - `/tmp/add-initial-patient-record-number-on-create-report.md`

Do not touch other files in this slice.

## Tests to write FIRST (TDD)

Add or update tests covering:

1. `patient_create` GET renders a "Prontuário Hospitalar" section.
2. `patient_create` GET renders an input named `initial_record_number`.
3. `patient_update` GET does not render `initial_record_number`.
4. Posting `initial_record_number` to `patient_update` does not create a new
   `PatientRecordNumber` and does not change the current record number.
5. `patient_create` POST includes `initial_record_number` and creates the
   patient successfully.

## Implementation guidance

- Add a focused section after identification/documents or before form actions.
- Use the approved copy:
  - Section title: "Prontuário Hospitalar"
  - Field label: "Número do Prontuário"
  - Help text/message: "Informe o número inicial do prontuário hospitalar.
    Alterações futuras devem ser feitas pelo fluxo próprio de prontuário."
- Render errors for `form.initial_record_number` consistently with the rest of
  `patient_create.html`.
- Do not add this field to `patient_update.html`.
- Keep CSS/template changes minimal and consistent with existing Bootstrap
  classes.

## Acceptance criteria

- Creation page displays the record-number section and field.
- Creation POST with valid data and record number succeeds.
- Update page does not display the field or section.
- Update POST cannot alter record number via unexpected
  `initial_record_number` payload.
- No templates other than `patient_create.html` are changed.
- `/tmp/add-initial-patient-record-number-on-create-report.md` exists and is
  complete.

## Quality gates

Run:

```bash
./scripts/test.sh apps.patients
./scripts/test.sh
```

If Markdown files are changed during implementation, run `markdownlint-cli2` on
those changed Markdown files. The required `/tmp/...report.md` is temporary
implementation evidence and should still be linted if feasible; document if the
local lint command is unavailable.

## Required report

Create `/tmp/add-initial-patient-record-number-on-create-report.md` with:

- change name;
- files changed;
- summary of implementation;
- tests written/updated;
- commands executed and results;
- acceptance checklist with pass/fail for each criterion;
- any deviations or blockers.

## Self-review checklist

- [ ] TDD followed: tests were written/updated before implementation
- [ ] Only allowed files were touched
- [ ] No unrelated refactor was performed
- [ ] `patient_update.html` was not changed
- [ ] Record number update remains restricted to dedicated flow after creation
- [ ] UI copy matches the slice guidance
- [ ] `./scripts/test.sh apps.patients` passes or blocker is documented
- [ ] `./scripts/test.sh` passes or blocker is documented
- [ ] Temporary report file was created
- [ ] Stop after this slice and report final status
