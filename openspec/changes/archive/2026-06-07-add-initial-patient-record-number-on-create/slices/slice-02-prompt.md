# Slice 02 Prompt - UI exclusiva de criação e relatório final

Implemente **somente** esta slice. Comece com contexto zero e leia os arquivos
na ordem indicada.

## Pre-read obrigatório

1. `AGENTS.md`
2. `docs/workflows/coding-standards.md`
3. `openspec/changes/add-initial-patient-record-number-on-create/design.md`
4. `openspec/changes/add-initial-patient-record-number-on-create/specs/patients/spec.md`
5. `openspec/changes/add-initial-patient-record-number-on-create/slices/slice-02.md`

## Objetivo

Exibir `initial_record_number` somente na tela atual de criação de paciente e
comprovar que a edição de paciente não expõe nem altera o prontuário.

## Arquivos permitidos

- `apps/patients/templates/patients/patient_create.html`
- `apps/patients/tests/test_templates.py`
- `apps/patients/tests/test_views.py`
- Opcional, se mais claro:
  - `apps/patients/tests/test_initial_record_number_create.py`
- Relatório obrigatório:
  - `/tmp/add-initial-patient-record-number-on-create-report.md`

Não altere `patient_update.html`.

## TDD obrigatório

Escreva/ajuste testes antes de implementar:

- create GET mostra seção "Prontuário Hospitalar";
- create GET mostra input `initial_record_number`;
- update GET não mostra `initial_record_number`;
- update POST com `initial_record_number` inesperado não cria novo
  `PatientRecordNumber` nem altera o atual;
- create POST com número válido cria paciente com sucesso.

## Regras de implementação

- Renderize o campo apenas em
  `apps/patients/templates/patients/patient_create.html`.
- Use a copy aprovada:
  - seção: "Prontuário Hospitalar";
  - label: "Número do Prontuário";
  - mensagem: "Informe o número inicial do prontuário hospitalar. Alterações
    futuras devem ser feitas pelo fluxo próprio de prontuário."
- Renderize erros do campo como os demais campos da página.
- Não altere rotas, models ou fluxo dedicado de prontuário.
- Não refatore template além do necessário.

## Verificação obrigatória

Execute:

```bash
./scripts/test.sh apps.patients
./scripts/test.sh
```

Se editar Markdown durante a implementação, execute `markdownlint-cli2` nos
Markdown alterados. Documente qualquer indisponibilidade no relatório.

## Relatório obrigatório

Crie `/tmp/add-initial-patient-record-number-on-create-report.md` contendo:

- change name;
- arquivos alterados;
- resumo do que foi feito;
- testes criados/alterados;
- comandos executados e resultados;
- checklist de aceite com pass/fail;
- desvios, riscos ou blockers.

## Critérios de aceite

- Campo aparece na criação.
- Campo não aparece na edição.
- Criação com número válido funciona.
- Edição não altera prontuário mesmo com POST inesperado.
- Suíte focada e suíte final foram executadas ou blockers foram documentados.
- Relatório temporário foi criado.

## Handoff final

Ao terminar, reporte:

- arquivos alterados;
- testes executados e resultado;
- caminho do relatório temporário;
- qualquer falha/blocker;
- confirmação de que não houve trabalho fora do escopo.
