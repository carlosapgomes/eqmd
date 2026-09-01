# Slice 01 - Preservar ala/leito no update de perfil

## Goal

Evitar que a edição de dados pessoais apague a localização (`ward`/`bed`) de
pacientes internados com admissão ativa.

## Scope boundaries

- Included:
  - `apps/patients/forms.py`
  - `apps/patients/views.py`
  - teste de regressão do fluxo de update de perfil
- Excluded:
  - mudanças em transferência interna
  - mudanças em signals de admissão

## Files to create/modify

- `apps/patients/forms.py`
- `apps/patients/views.py`
- `apps/patients/tests/test_patient_profile_update_preserves_location.py` (novo)

## Tests to write FIRST (TDD)

- `test_update_personal_data_preserves_inpatient_location`

## Implementation steps

1. Criar `PatientProfileForm` sem campos de localização hospitalar.
2. Reusar padrão de widgets e parsing de data do formulário principal.
3. Trocar `PatientUpdateView` para `PatientProfileForm`.
4. Garantir por teste que `ward`/`bed` não são alterados no update de perfil.

## Verification commands

- `./scripts/test.sh apps.patients.tests.test_patient_profile_update_preserves_location`
