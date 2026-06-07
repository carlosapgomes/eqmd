# Slice 03 Prompt - Alinhar testes ao prontuário obrigatório

Implemente **somente** esta slice. O objetivo é ajustar testes desatualizados
pela nova regra de negócio: criação de paciente via formulário exige
`initial_record_number`.

## Pre-read obrigatório

1. `AGENTS.md`
2. `docs/workflows/coding-standards.md`
3. `openspec/changes/add-initial-patient-record-number-on-create/design.md`
4. `openspec/changes/add-initial-patient-record-number-on-create/specs/patients/spec.md`
5. `openspec/changes/add-initial-patient-record-number-on-create/slices/slice-03.md`

## Objetivo

Fazer a suíte `apps.patients` deixar de falhar por testes que fazem POST de
criação de paciente sem informar o número inicial de prontuário.

## Arquivos permitidos

- Testes em `apps/patients/tests/` que façam POST para criação de paciente.
- `/tmp/add-initial-patient-record-number-on-create-report.md`

Não altere código de produção nesta slice. Se achar que precisa alterar
produção, pare e peça orientação.

## Passo inicial obrigatório

Rode:

```bash
./scripts/test.sh apps.patients
```

Use o resultado para identificar falhas relacionadas à ausência de
`initial_record_number` em POST para `patients:patient_create`.

## Regras de correção

- Para cada teste que cria paciente via formulário, acrescente
  `initial_record_number` válido no payload.
- Use números simples e válidos, por exemplo `REC001`, `REC002`, etc.
- Em loops, gere números únicos, por exemplo `REC{i:03d}`.
- Não altere testes que usam `Patient.objects.create(...)` diretamente, salvo se
  o mesmo teste também submeter o formulário de criação.
- Não adicione skips para falhas relacionadas a esta mudança.
- Não afrouxe asserts de comportamento.
- Não toque em templates, forms, views, models ou URLs.

## Verificação obrigatória

Depois dos ajustes, rode:

```bash
./scripts/test.sh apps.patients
```

Se passar, rode também:

```bash
./scripts/test.sh
```

Se ainda houver falhas, classifique cada falha restante no relatório como:

- relacionada a este change; ou
- não relacionada, com evidência curta.

## Relatório obrigatório

Atualize `/tmp/add-initial-patient-record-number-on-create-report.md` adicionando
a seção:

```markdown
## Slice 03 - Test Alignment
```

Inclua:

- arquivos alterados;
- testes/payloads ajustados;
- comandos executados e resultados;
- falhas restantes e classificação;
- checklist de aceite.

## Critérios de aceite

- Testes que criam paciente via formulário incluem `initial_record_number`.
- Suíte `apps.patients` passa, ou falhas restantes são documentadas como não
  relacionadas com evidência.
- Nenhum arquivo de produção foi alterado.
- Relatório temporário atualizado.

## Handoff esperado

Reporte:

- arquivos alterados;
- testes executados e resultado;
- caminho do relatório atualizado;
- falhas restantes, se houver;
- confirmação de que não houve alteração em produção.
