# Slice 01 - Backend obrigatório, validado e atômico

## Goal

Garantir que o backend de criação de paciente exija, valide e persista o número
inicial de prontuário hospitalar junto com o paciente em uma transação atômica.

## Scope boundaries

### Included

- Obrigatoriedade de `PatientForm.initial_record_number`.
- Validação com `validate_record_number_format`.
- Atomicidade de `Patient` + `PatientRecordNumber`.
- Testes focados de formulário/persistência.

### Excluded

- Renderização do campo na UI.
- Alterações em `patient_update.html`.
- Alterações no fluxo dedicado de alteração de prontuário.
- Refatorações amplas em patients.

## Files allowed

- `apps/patients/forms.py`
- `apps/patients/tests/test_forms.py`
- Opcional, se necessário para teste mais claro:
  - `apps/patients/tests/test_initial_record_number_create.py` (novo)

Do not touch other files in this slice.

## Tests to write FIRST (TDD)

Add or update tests covering:

1. `PatientForm` is invalid when `initial_record_number` is missing.
2. `PatientForm` is invalid when `initial_record_number` violates
   `validate_record_number_format`.
3. Saving a valid `PatientForm` creates exactly one current
   `PatientRecordNumber` linked to the new patient.
4. Saving a valid `PatientForm` updates `patient.current_record_number`.
5. If `PatientRecordNumber.objects.create()` raises after `Patient.save()` has
   started, no partial `Patient` remains persisted.

## Implementation guidance

- Keep changes minimal.
- Prefer adding `clean_initial_record_number()` to `PatientForm`.
- Prefer wrapping the `commit=True` persistence branch in
  `transaction.atomic()` inside `PatientForm.save()`.
- Preserve existing audit behavior using `current_user`, `created_by` and
  `updated_by`.
- Do not introduce new services unless the implementation would otherwise
  duplicate logic.
- Do not change `PatientProfileForm`.

## Acceptance criteria

- `initial_record_number` is required by `PatientForm`.
- Invalid record number format produces a field validation error.
- Valid form save creates:
  - one `Patient`;
  - one related `PatientRecordNumber`;
  - `PatientRecordNumber.is_current=True`;
  - `Patient.current_record_number` equal to the submitted value.
- Simulated record-number persistence failure rolls back patient creation.
- No UI/template changes are included in this slice.

## Quality gates

- Run using Docker-aware project command:

```bash
./scripts/test.sh apps.patients
```

## Self-review checklist

- [ ] TDD followed: tests were written/updated before implementation
- [ ] Only allowed files were touched
- [ ] No unrelated refactor was performed
- [ ] `validate_record_number_format` is reused; validation is not duplicated
- [ ] Transaction scope is minimal and covers both writes
- [ ] Functions remain small and readable
- [ ] `./scripts/test.sh apps.patients` passes or blocker is documented
- [ ] Stop after this slice; do not start Slice 02
