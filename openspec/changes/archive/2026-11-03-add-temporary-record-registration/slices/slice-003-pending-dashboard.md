# Slice 003: pending dashboard

## Handoff para implementador LLM com contexto zero

Você está implementando um slice do change
`add-temporary-record-registration` no projeto Django `eqmd`
(hospitalar, PostgreSQL). Os slices 001 e 002 já estão mergeados: existe o
fluxo de criação com número temporário `TMP-XXXXXXXX` + motivo gravado no
`change_reason`, a constante `TEMPORARY_RECORD_PREFIX = "TMP-"` em
`apps/patients/validators.py`,
`is_temporary_record_number()` em
`apps/patients/services/temporary_record.py` e a property
`Patient.is_temporary_record`.

Leia primeiro (nesta ordem):

1. `AGENTS.md`
2. `openspec/changes/add-temporary-record-registration/proposal.md`
3. `openspec/changes/add-temporary-record-registration/design.md`
   (decisão D7 é obrigatória para este slice)
4. `openspec/changes/add-temporary-record-registration/slices/slice-001-temporary-record-creation.md`
   e `slice-002-prefix-protection-and-regularization.md` (contexto)

Estado atual relevante:

- `apps/patients/views.py` → views de lista usam
  `LoginRequiredMixin` + `PermissionRequiredMixin` com
  `permission_required = "patients.view_patient"` (ver
  `PatientListView` como referência de estilo da casa).
- `apps/patients/urls.py` → `app_name = "patients"`; rotas nomeadas
  (ex.: `patient_list`, `patient_detail`, `patient_create`).
- `Patient` tem `current_record_number` (denormalizado, indexado),
  `created_at`, `created_by` (FK para usuário) e soft-delete
  (`is_deleted`); o `PatientRecordNumber` corrente de um paciente é
  acessível via `patient.current_record_number_obj` (property
  existente) e carrega `change_reason` e `created_by`.
- Templates da casa ficam em `apps/patients/templates/patients/` e usam
  Bootstrap (classes como `table`, `badge`, `alert`).

Objetivo exato: um dashboard staff-only listando pacientes com registro
temporário pendente (mais antigos primeiro), com idade da pendência,
motivo e criador, mais agregado por criador.

Limites de escopo: NÃO crie migrações, permissões novas, paginação,
filtros, exportação ou jobs agendados; NÃO altere outros apps.

## Protocolo obrigatório para implementador DeepSeek4-Flash

Este slice será implementado por um modelo rápido e com tendência a
concluir cedo demais. Siga este protocolo literalmente. **Se qualquer item
falhar, o slice está INCOMPLETO**: não marque `tasks.md`, não faça
commit/push e responda com bloqueio + evidência.

1. **Plano antes de editar**: matriz `Requisito → arquivo(s) → teste(s)`
   no relatório.
2. **Baseline antes de editar**: `BASE_REF=$(git rev-parse HEAD)` e
   `./scripts/test.sh` completo; registre exit code e resumo. Falha no
   baseline → BLOQUEADO.
3. **RED real**: crie `apps/patients/tests/test_temporary_record_list.py`
   primeiro; rode
   `./scripts/test.sh apps.patients.tests.test_temporary_record_list`;
   ao menos um teste novo deve falhar pelo motivo esperado (view/rota
   ainda não existem).
4. **GREEN mínimo**: apenas o necessário.
5. **Verificação por inspeção**: rode os `rg` da seção específica.
6. **Quality gate completo**: ruff/mypy sem novos findings;
   `./scripts/test.sh` exit 0, zero failures/errors, passed ≥ baseline.
7. **Relatório com evidência** + `Handoff para verificador` +
   `Status: COMPLETE` apenas se tudo comprovado.

## Objetivo do slice

Fluxo end-to-end: membro do staff abre `/patients/temporary-records/`,
vê a lista de pacientes com número corrente `TMP-...` ordenada do mais
antigo para o mais novo, com número temporário, nome do paciente, dias
pendentes, motivo informado na criação e criador, além da contagem
agregada por criador; usuários não-staff recebem acesso negado.

## Contexto técnico atual

- O acesso é gerencial, não clínico: por D7 do design, use
  `UserPassesTestMixin` com `test_func` exigindo `is_staff`
  (documentado no design; sem objeto de permissão novo).
- "Dias pendentes" = `timezone.now() - patient.created_at` (idade do
  registro do paciente), exibido como inteiro de dias.
- O motivo exibível está no `change_reason` do
  `PatientRecordNumber` corrente (`patient.current_record_number_obj`).
- Soft-delete: pacientes com `is_deleted=True` não devem aparecer.

## Escopo funcional

- **R1**: `apps/patients/views.py` ganha `TemporaryRecordListView`
  herdando `LoginRequiredMixin`, `UserPassesTestMixin`, `ListView`:
  - `model = Patient`,
  - `template_name = "patients/temporary_record_list.html"`,
  - `context_object_name = "patients"`,
  - `test_func` exigindo `self.request.user.is_staff`,
  - queryset: pacientes com `is_deleted=False` e
    `current_record_number__istartswith=TEMPORARY_RECORD_PREFIX`,
    ordenados por `created_at` ascendente (mais antigo primeiro);
  - `get_context_data` acrescenta `aggregate_by_creator`: lista de pares
    `(username, count)` derivada do queryset, ordenada por count
    decrescente (use `Counter` sobre
    `values_list("created_by__username", flat=True)`; usuários sem
    username não ocorrem — todos têm).
- **R2**: `apps/patients/urls.py` ganha
  `path("temporary-records/", views.TemporaryRecordListView.as_view(),
name="temporary_record_list")`, posicionada antes das rotas com
  `<uuid:pk>` por clareza (não há conflito real: o converter uuid não
  casa "temporary-records").
- **R3**: `apps/patients/templates/patients/temporary_record_list.html`:
  página com título, tabela (Número temporário, Paciente, Dias
  pendentes, Motivo, Criado por) usando as classes Bootstrap da casa,
  link do nome do paciente para `patients:patient_detail`, estado vazio
  amigável ("Nenhum registro temporário pendente.") e seção de agregado
  por criador (contagens). Sem paginação, sem filtros (YAGNI).
- **R4**: testes `apps/patients/tests/test_temporary_record_list.py`
  (padrão das views existentes; crie pacientes com números `TMP-`
  gerados por `generate_temporary_record_number()` e pacientes
  `REC001` como controle):
  1. staff autenticado → 200 e o paciente temporário aparece na
     resposta; o paciente definitivo não aparece;
  2. usuário autenticado sem `is_staff` → acesso negado (302/403
     conforme o mixin; afirme o efeito, não o código HTTP exato, OU
     fixe o comportamento observado e justifique);
  3. anônimo → redirecionado para login;
  4. dois temporários criados em instantes distintos → o mais antigo
     aparece primeiro na resposta;
  5. paciente temporário soft-deleted (`is_deleted=True`) não aparece;
  6. `aggregate_by_creator` contém o username do criador com a contagem
     correta (verifique via contexto da view ou conteúdo da resposta).

## Arquivos esperados

- `apps/patients/views.py`
- `apps/patients/urls.py`
- `apps/patients/templates/patients/temporary_record_list.html` (novo)
- `apps/patients/tests/test_temporary_record_list.py` (novo)

Fora de escopo/proibidos: models, migrations, forms, services, outros
apps, JS. Arquivo extra exige justificativa no relatório.

## TDD obrigatório

- **RED**: testes de R4 primeiro; rode o alvo; registre as falhas
  (esperado: `NoReverseMatch`/404/AttributeError — view e rota não
  existem).
- **GREEN**: R1–R3 na ordem; alvo verde.
- **REFACTOR**: queryset e agregado coesos, sem duplicação; nomes claros.

## Checks de inspeção obrigatórios antes de concluir

```bash
rg -n "TemporaryRecordListView|temporary_record_list" apps/patients/views.py apps/patients/urls.py
rg -n "is_staff|UserPassesTestMixin" apps/patients/views.py | head -5
rg -n "istartswith|TEMPORARY_RECORD_PREFIX|created_at" apps/patients/views.py
rg -n "Nenhum registro temporário|aggregate_by_creator" \
  apps/patients/templates/patients/temporary_record_list.html
rg -n "paginate_by|filters" \
  apps/patients/templates/patients/temporary_record_list.html \
  || echo "sem paginacao/filtros (YAGNI ok)"
```

Interprete: view e rota presentes; gate staff presente (e não
`permission_required` de view clínica); query usa o prefixo importado
(não string mágica); template tem estado vazio e agregado; sem
paginação/filtros antecipados.

## Critérios de sucesso

- [ ] R1–R4 implementados e verdes no alvo.
- [ ] Suíte completa exit 0, zero failures/errors, passed ≥ baseline.
- [ ] Ruff e mypy sem novos findings em `apps/patients`.
- [ ] Nenhuma migração; nenhum arquivo fora da lista.
- [ ] Não-staff não acessa; soft-deleted excluído; ordem mais antigo
      primeiro comprovada.

## Gates de autoavaliação

1. O queryset filtra EXATAMENTE por prefixo temporário + não deletado?
2. O gate de acesso é `is_staff` (D7) e não uma permissão clínica ampla?
3. O agregado deriva do MESMO queryset da lista (consistência)?
4. O estado vazio existe e o template não assume lista sempre cheia?
5. Dias pendentes são inteiros derivados de `created_at`?
6. Algum YAGNI violado (paginação, filtros, export, job)?

## Condições automáticas de INCOMPLETO

Marque como incompleto se ocorrer qualquer uma destas situações:

- teste planejado não escrito ou não executado;
- baseline completo antes de editar não registrado (exit code + resumo);
- quality gate completo não executado;
- qualquer teste/lint/mypy novo falhou;
- suíte final com exit code ≠ 0, `failed > 0`, `errors > 0` ou
  `passed` < baseline;
- relatório sem declaração explícita de zero failures/errors e exit 0;
- view acessível por usuário autenticado sem `is_staff`;
- paciente definitivo ou soft-deleted aparecendo na lista;
- ordenação não verificada por teste;
- agregado ausente ou derivado de fonte divergente do queryset;
- `tasks.md` marcado com pendência;
- arquivo fora da lista tocado sem justificativa;
- relatório não criado em `/tmp/`.

## Relatório obrigatório

Crie `/tmp/add-temporary-record-registration-slice-003-report.md` com:
Status, matriz requisito→arquivo→teste, evidência RED/GREEN (comandos e
resumos), snippets antes/depois de views/urls e o template novo, checks
de inspeção com interpretação, baseline vs final do pytest, quality
gate, respostas aos gates e `Handoff para verificador` (arquivos
alterados, comandos exatos para rerun, riscos, checklist R1–R4).

## Prompt pronto para implementador LLM

```text
Read AGENTS.md and the four files under
openspec/changes/add-temporary-record-registration/
(proposal.md, design.md, tasks.md,
slices/slice-003-pending-dashboard.md) first.
Implement ONLY slice 003. Follow the DeepSeek4-Flash protocol in the
slice file: plan matrix, full-suite baseline before editing, real RED on
apps.patients.tests.test_temporary_record_list, minimal GREEN, inspection
rg checks, full quality gate (docker exec eqmd_dev ruff check
apps/patients; docker exec eqmd_dev mypy apps/patients; ./scripts/test.sh)
with no NEW findings and passed_final >= passed_baseline.
Touch only the files listed in "Arquivos esperados". No migrations, no
pagination/filters/export, no other apps.
Gate the view with is_staff per design D7; exclude soft-deleted patients;
oldest first; aggregate derived from the same queryset.
Create /tmp/add-temporary-record-registration-slice-003-report.md with all
required evidence and Handoff para verificador.
Update tasks.md only after every criterion passes. If any gate fails,
report INCOMPLETE with evidence, do not update tasks.md, do not commit.
Reply with REPORT_PATH=<path> and STOP for planner review.
```
