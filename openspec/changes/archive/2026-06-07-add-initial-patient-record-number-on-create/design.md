## Context

`PatientCreateView` usa `PatientForm` e renderiza
`patients/patient_create.html`. `PatientUpdateView` já usa `PatientProfileForm`
e renderiza `patients/patient_update.html`.

O `PatientForm` já possui o campo `initial_record_number` e seu `save()` já cria
um `PatientRecordNumber` quando o campo é informado. Porém, o campo não é
renderizado na UI atual de criação e ainda precisa dos seguintes endurecimentos:

- tornar o campo obrigatório no fluxo de criação;
- validar o formato com `validate_record_number_format`;
- garantir que `Patient` e `PatientRecordNumber` sejam persistidos de forma
  atômica.

## Goals

1. Permitir informar o número de prontuário hospitalar inicial na criação do
   paciente.
2. Tornar o número inicial obrigatório na criação.
3. Criar o `PatientRecordNumber` correto, vinculado ao paciente criado.
4. Validar o formato com o validador existente.
5. Garantir rollback completo se a criação do número de prontuário falhar.
6. Manter o fluxo de edição de paciente sem campo/opção para alterar
   prontuário.

## Non-Goals

- Alterar o modelo `PatientRecordNumber`.
- Alterar rotas ou permissões.
- Criar novo fluxo de edição de prontuário.
- Renderizar o campo em templates legados como `patient_form.html`.
- Permitir alteração de prontuário em `PatientUpdateView` ou
  `patient_update.html`.
- Refatorar arquitetura ampla de pacientes.

## Solution Overview

### Slice 01 - Backend obrigatório, validado e atômico

- Ajustar `PatientForm.initial_record_number` para `required=True`.
- Adicionar `clean_initial_record_number()` reutilizando
  `validate_record_number_format`.
- Envolver a persistência de `Patient` + `PatientRecordNumber` em
  `transaction.atomic()` no menor escopo possível.
- Atualizar/adicionar testes de formulário para:
  - campo obrigatório;
  - formato inválido;
  - criação do `PatientRecordNumber` inicial;
  - rollback quando a criação do record number falhar.

### Slice 02 - UI exclusiva de criação e relatório final

- Renderizar seção "Prontuário Hospitalar" em `patient_create.html`.
- Não alterar `patient_update.html`.
- Adicionar teste de template/fluxo para garantir que a criação renderiza o
  campo e a edição não renderiza `initial_record_number`.
- Executar validações finais e criar relatório temporário exigido.

## Detailed Notes

### Atomicidade

A implementação deve garantir que, se `PatientRecordNumber.objects.create()`
falhar após `Patient.save()`, o paciente não permaneça salvo sem o registro de
prontuário inicial.

A solução preferida é envolver o bloco de persistência em `transaction.atomic()`
no `PatientForm.save(commit=True)`, mantendo o comportamento existente de
`PatientCreateView` simples e evitando duplicar lógica na view.

### Validação

`PatientForm.clean_initial_record_number()` deve:

- receber o valor limpo;
- chamar `validate_record_number_format(record_number)` quando houver valor;
- retornar o valor original se válido.

Como o campo será obrigatório, a ausência deve produzir erro de campo padrão ou
mensagem equivalente clara.

### Edição de paciente

A edição já usa `PatientProfileForm`. A implementação não deve adicionar
`initial_record_number` ao `PatientProfileForm` nem renderizar o campo em
`patient_update.html`.

## Risks and Mitigations

- **Risco:** quebrar testes existentes que criam paciente sem prontuário.
  - **Mitigação:** atualizar apenas testes de formulário/view relacionados ao
    fluxo de criação para incluir `initial_record_number`.
- **Risco:** introduzir alteração indireta no fluxo de edição.
  - **Mitigação:** teste garantindo ausência do campo no update e nenhuma
    alteração de `PatientRecordNumber` via update.
- **Risco:** paciente salvo sem prontuário se o segundo insert falhar.
  - **Mitigação:** teste com falha simulada em `PatientRecordNumber.objects.create`
    e rollback verificado.

## Verification Strategy

- TDD por slice.
- Durante as slices: `./scripts/test.sh apps.patients`.
- Verificação final: `./scripts/test.sh`.
- Criar relatório temporário:
  `/tmp/add-initial-patient-record-number-on-create-report.md`.
