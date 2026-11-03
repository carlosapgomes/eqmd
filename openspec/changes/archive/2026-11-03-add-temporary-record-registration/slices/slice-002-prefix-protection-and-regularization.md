# Slice 002: prefix protection and regularization

## Handoff para implementador LLM com contexto zero

Você está implementando um slice do change
`add-temporary-record-registration` no projeto Django `eqmd`
(hospitalar, PostgreSQL). O slice 001 já está mergeado: existe
`apps/patients/services/temporary_record.py` com
`generate_temporary_record_number()` e `is_temporary_record_number()`,
e a constante `TEMPORARY_RECORD_PREFIX = "TMP-"` vive em
`apps/patients/validators.py`.

Leia primeiro (nesta ordem):

1. `AGENTS.md`
2. `openspec/changes/add-temporary-record-registration/proposal.md`
3. `openspec/changes/add-temporary-record-registration/design.md`
   (decisões D5 e D6 são obrigatórias para este slice)
4. `openspec/changes/add-temporary-record-registration/slices/slice-001-temporary-record-creation.md`
   (contexto do que já existe)

Estado atual relevante:

- Portas manuais de escrita de número:
  - `apps/patients/forms.py` → `PatientForm.clean_initial_record_number`
    (criação), `PatientRecordNumberForm.clean_record_number`,
    `QuickRecordNumberUpdateForm.clean_record_number`.
  - `apps/patients/models.py` → `Patient.update_current_record_number`
    (porta gerenciada; valida formato e conflito antes de escrever;
    `_replace_current_record` troca a linha corrente preservando a antiga
    com `is_current=False` e `previous_record_number`).
- `apps/patients/templates/patients/patient_detail.html` é o template de
  detalhe do paciente.
- Rota existente de troca rápida de número:
  `patients:quick_record_number_update`
  (`<uuid:patient_id>/record-number/quick-update/`).

Objetivo exato: reservar o prefixo `TMP-` para números gerados pelo
sistema e dar ao usuário de paciente temporário um caminho visível de
regularização via fluxo existente.

Limites de escopo: NÃO toque em migrações, views, urls, outros apps;
NÃO crie endpoint novo de regularização (D6); NÃO implemente o dashboard
(slice 003).

## Protocolo obrigatório para implementador DeepSeek4-Flash

Este slice será implementado por um modelo rápido e com tendência a
concluir cedo demais. Siga este protocolo literalmente. **Se qualquer item
falhar, o slice está INCOMPLETO**: não marque `tasks.md`, não faça
commit/push e responda com bloqueio + evidência.

1. **Plano antes de editar**: matriz `Requisito → arquivo(s) → teste(s)`
   no relatório. Sem teste, sem implementação.
2. **Baseline antes de editar**: `BASE_REF=$(git rev-parse HEAD)` e
   `./scripts/test.sh` completo; registre exit code e resumo. Falha no
   baseline → pare e reporte BLOQUEADO.
3. **RED real**: crie
   `apps/patients/tests/test_temporary_record_prefix_protection.py`
   primeiro; rode
   `./scripts/test.sh apps.patients.tests.test_temporary_record_prefix_protection`;
   ao menos um teste novo deve falhar pelo motivo esperado.
4. **GREEN mínimo**: apenas o necessário; sem refactor amplo.
5. **Verificação por inspeção**: rode os `rg` da seção específica.
6. **Quality gate completo**: ruff/mypy sem novos findings;
   `./scripts/test.sh` exit 0, zero failures/errors, passed ≥ baseline.
7. **Relatório com evidência** + `Handoff para verificador` +
   `Status: COMPLETE` apenas se tudo comprovado.

## Objetivo do slice

Fluxo end-to-end: qualquer tentativa de digitar manualmente um número
`TMP-...` em qualquer porta é rejeitada com mensagem clara; um usuário
que abre o detalhe de um paciente temporário vê um banner explicando o
estado e um link para o fluxo existente de troca de número; ao
regularizar (TMP → número definitivo), a linha temporária é preservada no
histórico.

## Contexto técnico atual

- `validate_record_number_format` (validators.py) é chamado por todas as
  portas listadas; a nova validação de prefixo é SEPARADA dela (o gerador
  temporário também passa pela validação de formato — o prefixo só é
  proibido nas portas manuais, não no formato base).
- `Patient.update_current_record_number(self, record_number, user,
reason="", effective_date=None)` já valida
  `validate_record_number_format(record_number)` no topo, antes da
  transação: é o ponto exato para acrescentar a validação permanente.
- A troca de número é auditada por linha (`change_reason`,
  `previous_record_number`, `created_by`/`updated_by`) e pelo evento de
  timeline criado por signal.

## Escopo funcional

- **R1**: `apps/patients/validators.py` ganha
  `validate_permanent_record_number(record_number)`: levanta
  `ValidationError` com mensagem
  "Números iniciados em TMP- são reservados para registros temporários
  gerados pelo sistema." quando
  `record_number.strip().upper().startswith(TEMPORARY_RECORD_PREFIX)`;
  caso contrário, não faz nada. Função pura, sem I/O.
- **R2**: aplicar `validate_permanent_record_number` nas quatro portas
  manuais, imediatamente após `validate_record_number_format`:
  1. `PatientForm.clean_initial_record_number` (somente quando NÃO for
     fluxo temporário do slice 001 — quando `use_temporary_record` está
     marcado o campo é ignorado e retorna vazio antes);
  2. `PatientRecordNumberForm.clean_record_number`;
  3. `QuickRecordNumberUpdateForm.clean_record_number`;
  4. `Patient.update_current_record_number` (models.py, junto à
     validação de formato existente).
- **R3**: `Patient.is_temporary_record` (property no model, usando
  `is_temporary_record_number(self.current_record_number)` importado do
  serviço) — sem coluna nova, sem migração.
- **R4**: `patients/patient_detail.html`: quando
  `patient.is_temporary_record`, exibe banner de alerta (padrão visual
  `alert alert-warning` já usado no projeto) com texto explicando que o
  registro é temporário e botão/link para `patients:quick_record_number_update`
  do paciente (fluxo existente, nenhuma rota nova).
- **R5**: testes `apps/patients/tests/test_temporary_record_prefix_protection.py`:
  1. `PatientForm` com `initial_record_number="TMP-12345678"` sem
     checkbox temporário → erro citando a reserva do prefixo;
  2. `QuickRecordNumberUpdateForm` com `TMP-00000001` → erro;
  3. `PatientRecordNumberForm` com `TMP-00000001` → erro;
  4. `Patient.update_current_record_number(patient, "TMP-00000001", user)`
     → `ValidationError` e nenhuma escrita (número corrente inalterado);
  5. regularização: paciente criado com número gerado temporário →
     `update_current_record_number(patient, "REC999", user,
reason="Regularização...")` → corrente vira `REC999`; a linha
     temporária persiste com `is_current=False`; a nova linha tem
     `previous_record_number` igual ao número temporário;
  6. `is_temporary_record` `True` para paciente TMP e `False` para
     paciente `REC001`;
  7. validador puro: `validate_permanent_record_number("tmp-abc")`
     (minúsculo) também rejeita — normalização case-insensitive.

## Arquivos esperados

- `apps/patients/validators.py`
- `apps/patients/forms.py`
- `apps/patients/models.py` (apenas a property + 1 linha na
  `update_current_record_number`)
- `apps/patients/templates/patients/patient_detail.html`
- `apps/patients/tests/test_temporary_record_prefix_protection.py` (novo)

Fora de escopo/proibidos: migrações, views, urls, services (exceto
import), outros apps. Arquivo extra exige justificativa no relatório.

## TDD obrigatório

- **RED**: testes de R5 primeiro; rode
  `./scripts/test.sh apps.patients.tests.test_temporary_record_prefix_protection`;
  registre as falhas (esperado: sem a validação nova, os testes 1–4 e 7
  falham porque os valores TMP são aceitos).
- **GREEN**: R1–R4 na ordem; alvo verde.
- **REFACTOR**: validar duplicação entre as quatro portas — se surgir
  repetição, extraia helper privado no form/models conforme melhor
  encaixe, sem mudar contratos.

## Checks de inspeção obrigatórios antes de concluir

```bash
rg -n "validate_permanent_record_number" \
  apps/patients/validators.py apps/patients/forms.py apps/patients/models.py
rg -n "is_temporary_record" apps/patients/models.py apps/patients/templates/patients/patient_detail.html
rg -n "quick_record_number_update" apps/patients/templates/patients/patient_detail.html
rg -n "class Migration" apps/patients/migrations/ | tail -3
```

Interprete: a primeira deve mostrar 1 definição + 4 usos (criação,
dois forms de troca, porta gerenciada); a segunda, a property e o uso no
template; a terceira, o link do banner para a rota existente; a quarta
deve mostrar que NENHUMA migração nova foi criada (última continua sendo
a `0003`).

## Critérios de sucesso

- [ ] R1–R5 implementados e verdes no alvo.
- [ ] Suíte completa exit 0, zero failures/errors, passed ≥ baseline.
- [ ] Ruff e mypy sem novos findings em `apps/patients`.
- [ ] Nenhuma migração criada.
- [ ] Regularização preserva histórico (teste 5).
- [ ] Fluxo temporário do slice 001 continua verde (sem regressão).

## Gates de autoavaliação

1. A validação de prefixo roda em TODAS as quatro portas manuais?
2. O validador é case-insensitive e ignora espaços nas bordas?
3. O formato base (`validate_record_number_format`) continua aceitando
   números gerados (não houve fusão incorreta das validações)?
4. O banner aparece SOMENTE para pacientes temporários e aponta para a
   rota existente?
5. A regularização não criou porta/endpoint novo (D6)?
6. Há duplicação evitável entre as portas? Foi extraída sem mudar
   contratos?

## Condições automáticas de INCOMPLETO

Marque como incompleto se ocorrer qualquer uma destas situações:

- teste planejado não escrito ou não executado;
- baseline completo antes de editar não registrado (exit code + resumo);
- quality gate completo não executado;
- qualquer teste/lint/mypy novo falhou;
- suíte final com exit code ≠ 0, `failed > 0`, `errors > 0` ou
  `passed` < baseline;
- relatório sem declaração explícita de zero failures/errors e exit 0;
- alguma porta manual sem a validação de prefixo (verificado por teste E
  inspeção `rg`);
- validação de prefixo aplicada ao formato base (quebrando o gerador);
- `tasks.md` marcado com pendência;
- migração criada ou rota/endpoint novo adicionado;
- comportamento preservado (regularização com histórico) sem teste de
  regressão;
- arquivo fora da lista tocado sem justificativa;
- relatório não criado em `/tmp/`.

## Relatório obrigatório

Crie `/tmp/add-temporary-record-registration-slice-002-report.md` com:
Status, matriz requisito→arquivo→teste, evidência RED/GREEN (comandos e
resumos), snippets antes/depois das quatro portas e do validador novo,
checks de inspeção com interpretação (incluindo a prova de que nenhuma
migração foi criada), baseline vs final do pytest, quality gate,
respostas aos gates e `Handoff para verificador` (arquivos alterados,
comandos exatos para rerun, riscos, checklist R1–R5).

## Prompt pronto para implementador LLM

```text
Read AGENTS.md and the four files under
openspec/changes/add-temporary-record-registration/
(proposal.md, design.md, tasks.md,
slices/slice-002-prefix-protection-and-regularization.md) first.
Implement ONLY slice 002. Follow the DeepSeek4-Flash protocol in the
slice file: plan matrix, full-suite baseline before editing, real RED on
apps.patients.tests.test_temporary_record_prefix_protection, minimal
GREEN, inspection rg checks, full quality gate (docker exec eqmd_dev
ruff check apps/patients; docker exec eqmd_dev mypy apps/patients;
./scripts/test.sh) with no NEW findings and passed_final >=
passed_baseline.
Touch only the files listed in "Arquivos esperados". No migrations, no
new endpoints/urls/views, no dashboard.
Preserve slice 001 behavior and add regression coverage for
regularization history.
Create /tmp/add-temporary-record-registration-slice-002-report.md with all
required evidence and Handoff para verificador.
Update tasks.md only after every criterion passes. If any gate fails,
report INCOMPLETE with evidence, do not update tasks.md, do not commit.
Reply with REPORT_PATH=<path> and STOP for planner review.
```
