## Why

No fluxo atual de trabalho, a criação de um paciente e o cadastro do número de
prontuário hospitalar inicial exigem passos separados: primeiro cria-se o
paciente, depois acessa-se o detalhe do paciente para adicionar o
`PatientRecordNumber`.

A equipe usuária pediu que o número de prontuário inicial seja informado já na
criação do paciente para reduzir um passo operacional diário. O cuidado central
é manter o fluxo de edição de paciente isolado: editar dados pessoais do
paciente não deve permitir alterar o prontuário. Alterações posteriores de
prontuário devem continuar usando o fluxo próprio de `PatientRecordNumber`.

## What Changes

- Tornar o campo `initial_record_number` obrigatório no `PatientForm` usado na
  criação de paciente.
- Renderizar o campo somente em `apps/patients/templates/patients/patient_create.html`.
- Reutilizar `validate_record_number_format` para validar o número inicial no
  `PatientForm`.
- Garantir atomicidade: criação do `Patient` e do `PatientRecordNumber` inicial
  devem ocorrer na mesma transação.
- Adicionar testes focados para criação com prontuário inicial, validação de
  formato, rollback transacional e ausência do campo no fluxo de edição.
- Exigir relatório temporário de implementação em
  `/tmp/add-initial-patient-record-number-on-create-report.md`.

## Capabilities

### Modified Capabilities

- `patient-create`: passa a exigir número de prontuário hospitalar inicial e a
  criar o registro relacionado durante a criação do paciente.
- `patient-record-number-tracking`: passa a receber o primeiro número de
  prontuário pelo fluxo de criação do paciente, mantendo alterações posteriores
  no fluxo próprio de prontuário.
- `patient-profile-update`: permanece sem opção para alterar número de
  prontuário.

## Impact

- Apps afetados: `apps/patients`
- Sem migração de banco
- Sem alteração de rotas
- Arquivos esperados:
  - `apps/patients/forms.py`
  - `apps/patients/templates/patients/patient_create.html`
  - testes em `apps/patients/tests/`
- Verificação focada: `./scripts/test.sh apps.patients`
- Verificação final: `./scripts/test.sh`
