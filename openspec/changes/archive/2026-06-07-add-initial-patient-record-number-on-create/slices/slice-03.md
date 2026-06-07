# Slice 03 - Alinhar testes ao prontuário obrigatório

## Goal

Atualizar os testes do app `patients` que exercitam o fluxo de criação de
paciente para refletir a nova regra: `initial_record_number` é obrigatório no
POST de criação via `PatientCreateView`.

## Scope boundaries

### Included

- Testes que fazem POST para a rota de criação de paciente e agora falham por
  ausência de `initial_record_number`.
- Helpers de teste locais, se existirem, usados para montar payloads de criação
  de paciente via formulário.
- Relatório temporário atualizado com a triagem das falhas restantes.

### Excluded

- Alterações em código de produção.
- Alterações em models, forms, views, templates ou URLs.
- Alterar testes que criam `Patient.objects.create(...)` diretamente, exceto se
  o teste também submeter o formulário de criação.
- Mascarar falhas não relacionadas com skips ou asserts frouxos.

## Files allowed

Preferencialmente apenas testes em `apps/patients/tests/`, especialmente:

- `apps/patients/tests/test_tag_navigation.py`
- outros arquivos em `apps/patients/tests/` que façam POST para
  `patients:patient_create` sem `initial_record_number`

Relatório obrigatório:

- `/tmp/add-initial-patient-record-number-on-create-report.md`

Do not touch production files in this slice. If a production bug is discovered,
stop and ask for guidance.

## Tests/workflow to perform FIRST

1. Rode a suíte do app para identificar falhas atuais:

   ```bash
   ./scripts/test.sh apps.patients
   ```

2. Identifique apenas falhas causadas por payload de criação de paciente sem
   `initial_record_number`.
3. Atualize esses testes/payloads para enviar números válidos e únicos quando
   necessário.
4. Não modifique expectativas de negócio além do necessário.

## Implementation guidance

- Use valores simples e válidos, por exemplo `REC001`, `REC002`, ou strings
  únicas por teste quando houver múltiplas criações.
- Se houver loop criando pacientes, derive o record number do índice, por
  exemplo `REC{i:03d}`.
- Se o teste segue redirect e espera conteúdo em detalhe do paciente, mantenha o
  comportamento esperado; apenas acrescente o campo obrigatório ao POST.
- Não adicione `initial_record_number` em testes de update, salvo quando o teste
  explicitamente comprova que update ignora payload inesperado.
- Não transforme falhas em skips.

## Acceptance criteria

- Todos os testes que falhavam por ausência de `initial_record_number` no POST
  de criação foram atualizados.
- `./scripts/test.sh apps.patients` passa, ou as falhas restantes são
  documentadas com evidência de que não são relacionadas a este change.
- Nenhum arquivo de produção foi alterado.
- O relatório temporário lista:
  - arquivos de teste ajustados;
  - falhas corrigidas;
  - falhas restantes, se houver, com classificação de relação/não relação com o
    change.

## Quality gates

Run:

```bash
./scripts/test.sh apps.patients
```

If it passes, run final project verification:

```bash
./scripts/test.sh
```

## Required report update

Atualize `/tmp/add-initial-patient-record-number-on-create-report.md` com uma
seção adicional chamada `Slice 03 - Test Alignment`, contendo:

- arquivos alterados;
- padrão de correção aplicado;
- comandos executados e resultados;
- falhas restantes e classificação;
- checklist de aceite.

## Self-review checklist

- [ ] Apenas testes/relatório foram alterados
- [ ] Nenhum skip foi adicionado para ocultar falha relacionada
- [ ] Payloads de criação via `PatientCreateView` incluem record number válido
- [ ] Números de prontuário em testes são únicos quando necessário
- [ ] `./scripts/test.sh apps.patients` passa ou blockers são documentados
- [ ] `./scripts/test.sh` passa ou blockers são documentados
- [ ] Relatório temporário foi atualizado
