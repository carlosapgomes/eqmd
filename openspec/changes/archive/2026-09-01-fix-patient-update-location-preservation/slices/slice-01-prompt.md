# Slice 01 Prompt - Preservar localização no update de perfil

Implemente **somente** esta slice.

## Objetivo

Evitar que a edição de dados pessoais apague `ward`/`bed` de paciente internado.

## Arquivos permitidos

- `apps/patients/forms.py`
- `apps/patients/views.py`
- `apps/patients/tests/test_patient_profile_update_preserves_location.py` (novo)

## Regras de implementação

- Não alterar fluxo de transferência interna.
- Não alterar signals nesta slice.
- Criar form específico para update de perfil sem `ward`/`bed`.
- Fazer `PatientUpdateView` usar o novo form.
- Escrever teste de regressão primeiro (TDD).

## Verificação obrigatória

- `./scripts/test.sh apps.patients.tests.test_patient_profile_update_preserves_location`

## Critério de pronto

- Edição de dados pessoais preserva `ward` e `bed` quando há admissão ativa.
