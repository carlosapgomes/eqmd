# Slice 001: temporary record creation

## Handoff para implementador LLM com contexto zero

Você está implementando um slice do change
`add-temporary-record-registration` no projeto Django `eqmd`
(hospitalar, PostgreSQL, sem SQLite).

Leia primeiro (nesta ordem):

1. `AGENTS.md` (raiz do repo) — regras operacionais e comandos.
2. `openspec/changes/add-temporary-record-registration/proposal.md`
3. `openspec/changes/add-temporary-record-registration/design.md`
   (decisões D1–D4 são obrigatórias para este slice).

Estado atual relevante:

- `apps/patients/forms.py` → `PatientForm` (classe começa com o comentário
  "Add record number field to patient form") define
  `initial_record_number = forms.CharField(..., required=True, ...)`.
  O método `clean_initial_record_number` valida formato e conflito.
  O método `save()` cria, dentro de `transaction.atomic()`, o
  `PatientRecordNumber` inicial com
  `change_reason="Número inicial do prontuário"` e atualiza o campo
  denormalizado `Patient.current_record_number`.
- `apps/patients/validators.py` → `validate_record_number_format`
  exige mínimo de 3 caracteres e ao menos um alfanumérico (regra
  anti-placeholder).
- `apps/patients/services/patient_identity.py` →
  `find_record_number_conflict(record_number)` retorna a primeira linha
  retida com o mesmo número canônico ou `None`.
- `apps/patients/services/__init__.py` é um facade com `__all__`.
- `apps/patients/templates/patients/patient_create.html` → seção
  "Prontuário Hospitalar" renderiza `{{ form.initial_record_number }}`;
  há um bloco `<script>` próximo ao fim do arquivo.
- `apps/patients/tests/test_forms.py` mostra o padrão de teste de forms da
  casa (usuário, permissões, `VALID_RECORD_NUMBER = "REC001"`).

Objetivo exato: permitir criar paciente com número de prontuário
temporário gerado pelo servidor (`TMP-XXXXXXXX`) + motivo obrigatório,
sem digitação manual do número.

Limites de escopo: NÃO toque em migrações, models, views, outros apps,
nem implemente proteção de prefixo ou dashboard (slices 002/003).

## Protocolo obrigatório para implementador DeepSeek4-Flash

Este slice será implementado por um modelo rápido e com tendência a
concluir cedo demais. Siga este protocolo literalmente. **Se qualquer item
falhar, o slice está INCOMPLETO**: não marque `tasks.md`, não faça
commit/push e responda com bloqueio + evidência.

1. **Plano antes de editar**: escreva no relatório a matriz
   `Requisito → arquivo(s) → teste(s)`. Não implemente requisito sem teste.
2. **Baseline antes de editar**: registre `BASE_REF=$(git rev-parse HEAD)`
   e rode `./scripts/test.sh` (suíte completa, estado inicial limpo).
   Cole no relatório o exit code e a linha de resumo. Se houver
   `failed/error` no baseline, pare e reporte INCOMPLETO/BLOQUEADO.
3. **RED real**: crie os testes primeiro e rode
   `./scripts/test.sh apps.patients.tests.test_temporary_record_creation`.
   Pelo menos um teste novo deve falhar pelo motivo esperado. Se passar
   antes da implementação, corrija o teste.
4. **GREEN mínimo**: implemente somente o necessário. Sem refactor amplo,
   sem tocar apps fora do escopo, sem antecipar slices futuros.
5. **Verificação por inspeção**: rode os `rg` da seção específica.
6. **Quality gate completo**: `docker exec eqmd_dev ruff check apps/patients`
   e `docker exec eqmd_dev mypy apps/patients` sem NOVOS findings em
   relação ao baseline (compare com `git stash` se necessário); suíte
   completa `./scripts/test.sh` com exit code 0, zero failures/errors e
   `passed` final ≥ baseline.
7. **Relatório com evidência**: comandos, exit codes, resumos
   baseline/final, RED/GREEN, snippets antes/depois, respostas aos gates,
   `Handoff para verificador` e `Status: COMPLETE` apenas se tudo
   comprovado.

## Objetivo do slice

Fluxo end-to-end: médico marca "paciente sem número definitivo", informa
motivo, envia o formulário → sistema gera número `TMP-XXXXXXXX` único,
cria o paciente com esse número como corrente, grava o motivo na trilha
de auditoria do número e redireciona para o detalhe do paciente.

## Contexto técnico atual

- A unicidade de prontuário é garantida pela constraint de banco
  `unique_patient_record_number_lifetime` (`Lower(Trim(record_number))`,
  cobre linhas correntes, históricas e donos soft-deleted).
- O formato `TMP-3F2A9C1B` passa em `validate_record_number_format`
  (≥3 chars, tem alfanumérico).
- A geração deve ocorrer no servidor, dentro do `save()` transacional do
  form, não no cliente.

## Escopo funcional

- **R1**: novo módulo `apps/patients/services/temporary_record.py` com:
  - `TEMPORARY_RECORD_PREFIX = "TMP-"` importado de
    `apps/patients/validators.py` (constante nova definida lá — ver D2 do
    design; validators não pode importar services);
  - `generate_temporary_record_number() -> str`: gera `uuid4().hex[:8]`
    em maiúsculas prefixado; se `find_record_number_conflict` acusar o
    candidato, sorteia outro (máximo 5 tentativas; esgotadas, deixa o erro
    de constraint subir como conflito padrão do form);
  - `is_temporary_record_number(value: str) -> bool`: `True` quando
    `value.strip().upper().startswith(TEMPORARY_RECORD_PREFIX)`.
- **R2**: `PatientForm` ganha:
  - `use_temporary_record = forms.BooleanField(required=False, ...)` com
    label clara (ex.: "Paciente sem número de registro definitivo");
  - `temporary_record_reason = forms.CharField(required=False, ...)`
    (textarea curta, máx 500 chars);
  - `clean()`: se `use_temporary_record` e motivo vazio → erro no campo
    `temporary_record_reason` ("Informe o motivo do registro
    temporário."); se NÃO temporário e `initial_record_number` vazio →
    erro no campo `initial_record_number` (torne o campo
    `required=False` e mova a obrigatoriedade para cá, preservando a
    regressão);
  - `clean_initial_record_number`: quando `use_temporary_record`, retorna
    string vazia (ignora qualquer coisa digitada); senão comportamento
    atual (formato + conflito).
- **R3**: `PatientForm.save()`: quando temporário, usa
  `generate_temporary_record_number()` como número inicial e grava
  `change_reason=f"Registro temporário: {motivo}"`; senão comportamento
  atual inalterado (`"Número inicial do prontuário"`).
- **R4**: facade `apps/patients/services/__init__.py` exporta os novos
  nomes (`generate_temporary_record_number`,
  `is_temporary_record_number`) mantendo o padrão `__all__` existente.
- **R5**: `patients/patient_create.html`: na seção "Prontuário
  Hospitalar", renderiza o checkbox `use_temporary_record` e o campo
  `temporary_record_reason`; JS inline mínimo (no bloco `<script>`
  existente) alterna visibilidade: checkbox marcado → esconde o campo de
  número e mostra o motivo; desmarcado → inverso. Sem dependências novas.
- **R6**: testes `apps/patients/tests/test_temporary_record_creation.py`
  cobrindo (padrão de `test_forms.py`):
  1. POST válido com checkbox + motivo → paciente criado,
     `current_record_number` casa com `^TMP-[0-9A-F]{8}$`, linha
     `PatientRecordNumber` corrente com `is_current=True` e
     `change_reason` contendo o motivo;
  2. checkbox sem motivo → form inválido, erro em
     `temporary_record_reason`;
  3. sem checkbox e sem número → erro em `initial_record_number`
     (regressão do required);
  4. sem checkbox, com número `REC001` → fluxo clássico preservado
     (`change_reason="Número inicial do prontuário"`);
  5. dois `generate_temporary_record_number()` consecutivos distintos e
     formato conforme R1.

## Arquivos esperados

- `apps/patients/validators.py` (apenas a constante nova)
- `apps/patients/services/temporary_record.py` (novo)
- `apps/patients/services/__init__.py` (export)
- `apps/patients/forms.py`
- `apps/patients/templates/patients/patient_create.html`
- `apps/patients/tests/test_temporary_record_creation.py` (novo)

Fora de escopo/proibidos: models, migrations, views, urls, sinais, outros
apps, templates de outros fluxos. Qualquer arquivo extra exige
justificativa explícita no relatório.

## TDD obrigatório

- **RED**: escreva `test_temporary_record_creation.py` completo antes de
  qualquer implementação. Rode
  `./scripts/test.sh apps.patients.tests.test_temporary_record_creation`
  e registre as falhas (esperado: ImportError/módulo inexistente para o
  serviço e KeyErrors de campo de form → falhas reais).
- **GREEN**: implemente R1–R5 na ordem; rode o alvo até verde.
- **REFACTOR**: nomes claros, funções coesas, sem dead code, DRY, YAGNI;
  re-rode o alvo + suíte completa.

## Checks de inspeção obrigatórios antes de concluir

Além dos testes, execute e cole o resultado no relatório:

```bash
rg -n "TEMPORARY_RECORD_PREFIX|generate_temporary_record_number" \
  apps/patients/validators.py apps/patients/services/temporary_record.py \
  apps/patients/services/__init__.py
rg -n "is_temporary_record_number" apps/patients/services/temporary_record.py
rg -n "use_temporary_record|temporary_record_reason|Registro temporário" \
  apps/patients/forms.py apps/patients/templates/patients/patient_create.html
rg -n "required=True" apps/patients/forms.py | rg initial_record_number \
  || echo "initial_record_number nao e mais required (movido para clean)"
```

Interprete: a primeira busca deve mostrar a constante apenas em
validators (definição) e imports em services; a segunda, os dois campos no
form e no template; a terceira confirma a mudança de obrigatoriedade.

## Critérios de sucesso

- [ ] R1–R6 implementados e verdes no alvo.
- [ ] Suíte completa exit 0, zero failures/errors, passed ≥ baseline.
- [ ] Ruff e mypy sem novos findings em `apps/patients`.
- [ ] Nenhum arquivo fora da lista tocado (ou justificado).
- [ ] Nenhuma migração criada.
- [ ] Fluxo definitivo inalterado (critério 4).

## Gates de autoavaliação

1. O número temporário é SEMPRE gerado no servidor dentro da transação?
2. O motivo é obrigatório somente quando o checkbox está marcado?
3. O campo de número continua obrigatório quando o checkbox está
   desmarcado, com mensagem clara?
4. O fluxo definitivo existente produz exatamente os mesmos artefatos de
   antes (número corrente + change_reason padrão)?
5. `validate_record_number_format` aceita o formato gerado?
6. Há código morto, duplicação ou antecipação de slices futuros?

## Condições automáticas de INCOMPLETO

Marque como incompleto se ocorrer qualquer uma destas situações:

- teste planejado não foi escrito ou não foi executado;
- baseline `./scripts/test.sh` antes de editar não foi executado ou não
  foi registrado com exit code e resumo;
- quality gate (ruff/mypy/suíte completa) não foi executado;
- qualquer teste/lint/mypy NOVO falhou;
- suíte final com exit code ≠ 0, `failed > 0` ou `errors > 0`;
- contagem final de `passed` menor que a baseline;
- o relatório cita apenas o número de `passed` sem declarar
  explicitamente zero failures/errors e exit code 0;
- `tasks.md` marcado apesar de falha ou pendência;
- contrato crítico (R1–R6) sem teste ou inspeção correspondente;
- comportamento antigo (fluxo definitivo, required sem checkbox)
  removido sem teste de regressão;
- qualquer arquivo fora da lista tocado sem justificativa no relatório;
- migração criada (proibida neste slice);
- relatório temporário não criado em `/tmp/`.

## Relatório obrigatório

Crie `/tmp/add-temporary-record-registration-slice-001-report.md` com:
Status (COMPLETE/INCOMPLETO), matriz requisito→arquivo→teste, evidência
RED (comando + falhas), GREEN (comando + resumo), snippets antes/depois
de `PatientForm` (campos, `clean`, `save`) e do novo serviço, checks de
inspeção com interpretação, baseline vs final do pytest (exit codes e
resumos), resultados do quality gate, respostas aos gates e `Handoff para
verificador` (arquivos alterados, comandos exatos para rerun, riscos,
checklist R1–R6).

## Prompt pronto para implementador LLM

```text
Read AGENTS.md and the four files under
openspec/changes/add-temporary-record-registration/
(proposal.md, design.md, tasks.md,
slices/slice-001-temporary-record-creation.md) first.
Implement ONLY slice 001. Follow the DeepSeek4-Flash protocol in the
slice file: plan matrix, full-suite baseline before editing
(./scripts/test.sh, record exit code and summary), real RED on
apps.patients.tests.test_temporary_record_creation, minimal GREEN,
inspection rg checks, full quality gate (docker exec eqmd_dev ruff check
apps/patients; docker exec eqmd_dev mypy apps/patients; ./scripts/test.sh)
with no NEW findings and passed_final >= passed_baseline.
Touch only the files listed in "Arquivos esperados". No migrations, no
models, no views, no future slices.
Create /tmp/add-temporary-record-registration-slice-001-report.md with all
required evidence and Handoff para verificador.
Update tasks.md only after every criterion passes. If any gate fails,
report INCOMPLETE with evidence, do not update tasks.md, do not commit.
Reply with REPORT_PATH=<path> and STOP for planner review.
```
