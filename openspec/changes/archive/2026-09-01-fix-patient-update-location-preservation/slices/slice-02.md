# Slice 02 - Sincronizar `ward` no signal de admissão ativa

## Goal

Garantir consistência de denormalização da localização do paciente ao salvar
admissão ativa: sincronizar `ward` e `bed` no `Patient`.

## Scope boundaries

- Included:
  - `apps/patients/signals.py`
  - teste de regressão de sincronização de localização por signal
- Excluded:
  - formulários e views de update de perfil
  - fluxo de transferência interna

## Files to create/modify

- `apps/patients/signals.py`
- `apps/patients/tests/test_admission_signal_syncs_patient_location.py` (novo)

## Tests to write FIRST (TDD)

- `test_active_admission_updates_patient_ward_and_bed`

## Implementation steps

1. Ajustar branch `instance.is_active` em `update_patient_admission_status`.
2. Incluir `ward` no dicionário `updates`, junto com `bed`.
3. Validar por teste que admissão ativa sincroniza `ward` e `bed`.

## Verification commands

- `./scripts/test.sh apps.patients.tests.test_admission_signal_syncs_patient_location`
