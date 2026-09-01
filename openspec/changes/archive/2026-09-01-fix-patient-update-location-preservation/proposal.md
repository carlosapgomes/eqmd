# Proposal: fix patient update location preservation

## Why

Existe uma regressão grave no fluxo de edição de paciente.

Quando um paciente internado (com admissão ativa) tem seus dados pessoais
editados na tela de update, os campos de localização (`ward` e `bed`) podem ser
apagados. Isso força uma nova transferência interna manual e gera inconsistência
operacional.

Também existe uma inconsistência de sincronização no signal
`update_patient_admission_status`: ao salvar uma admissão ativa, o paciente era
sincronizado com `bed`, mas não com `ward`.

## What Changes

- Introduzir um form específico para atualização de perfil
  (`PatientProfileForm`) sem campos de localização hospitalar.
- Passar `PatientUpdateView` a usar `PatientProfileForm`.
- Ajustar o signal `update_patient_admission_status` para sincronizar
  `patient.ward` e `patient.bed` quando a admissão estiver ativa.
- Adicionar testes de regressão focados para:
  - preservar ala/leito ao editar dados pessoais de paciente internado;
  - garantir sincronização de ala/leito via signal de admissão ativa.

## Capabilities

### Modified Capabilities

- `patient-profile-update`: deixa de permitir alteração implícita de localização
  de internação ao editar dados cadastrais.
- `patient-admission-denormalization-sync`: passa a sincronizar consistentemente
  `ward` e `bed` no paciente durante admissão ativa.

## Impact

- Apps afetados: `apps/patients`
- Sem migração de banco
- Sem alteração de rotas
- Mudança comportamental restrita ao fluxo de update de perfil e ao signal de
  denormalização de admissão
- Cobertura adicional com testes focados de regressão
