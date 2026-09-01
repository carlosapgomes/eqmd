# Slice 01 — Placeholder rule at every record-number entry point

## Handoff para implementador LLM (contexto zero)

Você está no repositório `eqmd` (Django 5.2, PostgreSQL). Leia antes
de qualquer coisa: `AGENTS.md`, `PROJECT_CONTEXT.md`,
`openspec/changes/block-placeholder-record-numbers/proposal.md`,
`.../design.md`, `.../tasks.md` e este slice.

Estado atual: `validate_record_number_format`
(`apps/patients/validators.py:17`) só exige não-vazio e
`len(strip()) >= 3`, então `---` passa. O fluxo gerenciado
`Patient.update_current_record_number` (`apps/patients/models.py:894`)
não valida formato — apenas conflitos e a constraint de banco. A
consolidação (`_renumber_and_void` em
`apps/patients/services/patient_record_consolidation.py:356`) chama
esse fluxo com o número vindo do plano JSON.

Objetivo do slice: nenhum caminho — form, fluxo gerenciado ou plano de
consolidação — consiga criar/atribuir número de prontuário sem pelo
menos uma letra ou dígito.

Limite de escopo: NÃO toque em migrações, admin, templates ou em
outras regras de formato (whitelist, normalização, comprimento).
Apenas a classe placeholder.

## Contexto técnico

- Validador atual (`validators.py:17-24`): dois `if` com
  `ValidationError` (mensagens PT-BR). Model `clean()` chama em
  `models.py:297`; forms chamam em `forms.py:351, 601, 659`.
- `update_current_record_number` (`models.py:894-922`): valida
  conflito e executa `_replace_current_record` em transação. Adicione
  a checagem de formato NO TOPO, antes de `transaction.atomic()` —
  falha antes de qualquer escrita.
- Validação de plano: `_validate_action_reference` /
  `_parse_renumber` em `patient_record_consolidation.py` (~L267-332).
  O parse de `renumber` já exige `new_record_number` não-vazio;
  adicione a checagem de formato ali (erro citando o `plan_ref` +
  índice da ação, no estilo das mensagens existentes).
- Import do validador em `models.py` já existe (L18). Em
  `patient_record_consolidation.py`, importe do mesmo módulo.
- `str.isalnum()` cobre o requisito (design D1): use
  `any(ch.isalnum() for ch in record_number.strip())`.

## Requisitos

- R1 `validate_record_number_format` rejeita valores sem nenhuma
  letra/dígito (mensagem PT-BR clara, ex.: "Número do prontuário
  deve conter ao menos uma letra ou número."). `---`, `...`, `___`
  rejeitados; `123456`, `PRONT-001`, `12.345-6` aceitos; regressão:
  vazio e `<3` chars continuam rejeitados.
- R2 `update_current_record_number` levanta `ValidationError` para
  valor placeholder ANTES de qualquer escrita (nenhuma linha criada,
  número corrente inalterado, linha antiga continua `is_current`).
- R3 `validate_consolidation_plan` recusa plano com `renumber` cujo
  `new_record_number` seja placeholder (mensagem precisa; `void` e
  `keep` não são afetados; `DUP-0001` continua válido).

## Arquivos esperados

1. `apps/patients/validators.py` — R1
2. `apps/patients/models.py` — R2 (chamada no topo do método)
3. `apps/patients/services/patient_record_consolidation.py` — R3
4. `apps/patients/tests/test_forms.py` — testes R1 (classe existente
   de formato; siga o padrão do teste "AB" <3 chars)
5. `apps/patients/tests/test_record_tracking_models.py` — testes R2
6. `apps/patients/tests/test_record_consolidation.py` — testes R3

Justifique no relatório qualquer arquivo extra.

## TDD obrigatório

- RED: escreva primeiro os testes de R1-R3 (valores placeholder
  rejeitados nos três gates) e mostre a suíte falhando
  (`./scripts/test.sh apps.patients` com os novos testes em vermelho).
- GREEN: implementação mínima (R1 a regra; R2/R3 reutilização).
- REFACTOR: clean code, DRY, YAGNI; não duplique a regra — uma única
  fonte no validador.

## Critérios de sucesso (binário)

- [ ] R1: `validate_record_number_format('---')` levanta
      `ValidationError`; `('PRONT-001')` não levanta.
- [ ] R2: chamada com `'---'` levanta antes de escrever; BD íntegro.
- [ ] R3: plano com renumber para `'---'` recusado no parse; plano
      válido existente continua passando.
- [ ] Regressões verdes: vazio/curto ainda rejeitados; suite
      `apps.patients` inteira verde; suíte completa verde.
- [ ] `docker exec eqmd_dev ruff check` sem novos erros nos arquivos
      tocados (compare com HEAD).

## Gates de autoavaliação (responda no relatório)

1. A checagem em R2 roda antes da transação? Como provou?
2. R3 cobre também plano de múltiplas ações (erro aponta a ação)?
3. Alguma regra duplicada entre validador e gates? Onde está a fonte
   única?
4. Que teste prova que nada foi escrito no R2?

## Relatório obrigatório

Crie `/tmp/block-placeholder-record-numbers-slice-01-report.md` com:
evidência RED (output da suíte falhando), GREEN (suíte verde), snippets
antes/depois de cada arquivo, resultado dos quality gates (ruff +
testes), respostas aos gates acima e justificativas de escopo.

## Prompt pronto

```text
Read AGENTS.md, PROJECT_CONTEXT.md and
openspec/changes/block-placeholder-record-numbers/{proposal.md,design.md,tasks.md,slices/slice-01.md}
first. Implement ONLY slice-01. Vertical slicing; touch only the
minimum files listed and justify any extra file in the report. Use
TDD: RED (failing tests for R1-R3) -> GREEN (minimal) -> REFACTOR
(clean code, DRY, YAGNI; single source of truth for the rule). Do not
implement anything else; do not touch migrations, admin or templates.
Run ./scripts/test.sh apps.patients and the full suite. Update
tasks.md (mark 1.1) only after all criteria pass. Create
/tmp/block-placeholder-record-numbers-slice-01-report.md with
RED/GREEN evidence, before/after snippets, gate results, self-eval
gate answers and scope justifications. Reply with
REPORT_PATH=<path>, commit and push, then STOP for planner review.
```
