# Slice 02 Prompt - Sincronizar `ward` no signal de admissão

Implemente **somente** esta slice.

## Objetivo

Corrigir inconsistência de denormalização no signal de admissão ativa,
sincronizando `ward` e `bed` no paciente.

## Arquivos permitidos

- `apps/patients/signals.py`
- `apps/patients/tests/test_admission_signal_syncs_patient_location.py` (novo)

## Regras de implementação

- Não alterar formulários/views de update de perfil nesta slice.
- Ajustar apenas o branch `instance.is_active` no signal
  `update_patient_admission_status`.
- Escrever teste de regressão primeiro (TDD).

## Verificação obrigatória

- `./scripts/test.sh apps.patients.tests.test_admission_signal_syncs_patient_location`

## Critério de pronto

- Ao salvar admissão ativa com `ward` e bed, o paciente fica sincronizado com os
  dois campos.
