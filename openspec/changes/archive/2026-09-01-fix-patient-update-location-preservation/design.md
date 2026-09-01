# Design: fix patient update location preservation

## Context

O problema acontece porque `PatientUpdateView` usava `PatientForm`, que inclui
`ward` e `bed` no `Meta.fields`, enquanto o template `patient_update.html` não
renderiza esses campos.

No POST da edição de perfil, os campos ausentes eram normalizados pelo Django
como vazio (`ward=None`, `bed=''`), sobrescrevendo a localização atual.

## Goals

1. Garantir que edição de perfil não altere localização de internação.
2. Garantir sincronização consistente de denormalização entre admissão ativa e
   paciente (`ward` + `bed`).
3. Cobrir os dois comportamentos com testes de regressão específicos.

## Non-Goals

- Alterar fluxo de transferência interna.
- Alterar modelos de admissão/internação.
- Alterar timeline, permissões ou UX de localização.

## Solution Overview

### Slice 01 - Isolar update de perfil de localização

- Criar `PatientProfileForm` com apenas campos pessoais e de contato.
- Manter widgets e parsing de `birthday` compatíveis com o formulário atual.
- Atualizar `PatientUpdateView` para usar `PatientProfileForm`.

**Efeito esperado:** salvar dados pessoais não toca em `ward`/`bed`.

### Slice 02 - Corrigir sincronização do signal de admissão

- No signal `update_patient_admission_status`, ao processar admissão ativa,
  atualizar `ward` e `bed` no paciente.

**Efeito esperado:** admissão ativa sempre reflete localização completa no
paciente denormalizado.

## Risks and Mitigations

- **Risco:** divergência entre formulários de criação e edição.
  - **Mitigação:** manter `PatientForm` para criação e `PatientProfileForm` só
    no update de perfil.
- **Risco:** regressão silenciosa de sincronização futura em signals.
  - **Mitigação:** adicionar teste específico para sincronização de `ward`.

## Verification Strategy

- Teste focado de regressão do update de perfil preservando localização.
- Teste focado de sincronização de `ward`/`bed` por signal.
- Execução dos módulos de teste dedicados em comando isolado.
