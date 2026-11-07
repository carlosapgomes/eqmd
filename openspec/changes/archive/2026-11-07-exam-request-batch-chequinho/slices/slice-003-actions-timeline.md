# Slice S3 — Actions do lote na timeline e detalhe

## 1. Identity

- Slice ID: S3
- Title: Botão de lote nos cards da timeline + banner na `submission_detail`
- Change ID: `exam-request-batch-chequinho`
- Tasks: 3.7 (test 2.7)
- Depends on: S1 (cards com `batch_id`), S2 (rota de download do lote)

## 2. Objective

Tornar o lote descobrível: botão "Baixar lote 3-up (N vias)" em todos os cards
do lote na timeline e banner com download + irmãos na `submission_detail`, sem
N+1 e sem alterar o botão avulso.

## 3. Read first

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `openspec/changes/exam-request-batch-chequinho/proposal.md`
- `openspec/changes/exam-request-batch-chequinho/design.md` — Decision (cards
  da timeline mantêm avulso; botão adicional; `batch_info` em bulk)
- `openspec/changes/exam-request-batch-chequinho/specs/pdf-forms/spec.md` —
  Requirement: timeline batch actions
- `apps/events/templates/events/partials/event_card_pdfform.html` — card real
  (botões atuais; NOTA:
  `apps/pdf_forms/templates/pdf_forms/partials/pdf_form_event_card.html` é
  legado, não mexer)
- `apps/events/views.py` — montagem bulk de `event_data` (~linha 270, padrão
  anti-N+1)
- `apps/pdf_forms/templates/pdf_forms/form_submission_detail.html` — detalhe
  (onde vai o banner)
- `apps/pdf_forms/views/base_views.py` — `PDFFormSubmissionDetailView`
  (contexto)

## 4. Requirements

- R1: Todo card de exame com `batch_id` e irmãos finais exibe o botão "Baixar
  lote 3-up (N vias)" apontando ao download do lote (S2); o botão aparece nos
  N cards do lote.
- R2: Botão PDF avulso existente inalterado (baixa só a via do card; some em
  rascunhos como hoje).
- R3: Submissions sem `batch_id` ou sem irmãos finais não exibem o botão de
  lote (cards idênticos a antes).
- R4: `submission_detail` de exame em lote exibe banner "Parte do lote de N
  exames" com [baixar lote 3-up] e links para os irmãos; detalhe de avulsa não
  exibe banner.
- R5: `event_data["batch_info"]` montado em bulk na timeline (1 query agrupada
  por página para os `batch_id`s visíveis); sem query por card.

Evidência: testes automatizados (TDD) — HTML da timeline contém/não-contém
botão por caso; `assertNumQueries` (ou equivalente) para o bulk; teste do
banner no detalhe com/sem lote.

## 5. Expected blast radius

Provavelmente afetados:

- `apps/events/views.py` — bulk de `batch_info` em `event_data`
- `apps/events/templates/events/partials/event_card_pdfform.html` — botão de
  lote
- `apps/pdf_forms/views/base_views.py` — contexto do banner no detalhe (adição
  mínima)
- `apps/pdf_forms/templates/pdf_forms/form_submission_detail.html` — banner +
  irmãos
- testes em `apps/events/tests/` e/ou `apps/pdf_forms/tests/` (ex.: extensão
  de `test_exam_batch*.py`)

Sensíveis (não mudar sem escalada):

- partial legado `pdf_forms/partials/pdf_form_event_card.html` (não mexer)
- semântica dos demais botões (ver, editar, excluir, duplicar)
- managers/querysets de eventos (adicionar só a query agrupada de irmãos)
- S1/S2 já entregues (só consumir a rota de download)

Comportamento anterior preservado: R2, R3.

Expansão de blast radius exige justificativa no relatório.

## 6. Failing-before plan

Failing-before evidence (TDD, RED antes do GREEN):

- targeted tests: actions (2.7) — botão em N cards, ausência em avulsas,
  banner, bulk 1 query
- expected failure: HTML da timeline/detalhe não contém botão/banner
  (templates inalterados); helper de `batch_info` ausente

## 7. Implementation constraints

- Reaproveitar o padrão bulk existente de `event_data`; provar com contagem de
  queries que não há N+1.
- Irmãos do banner: só finals do mesmo `batch_id` (respeitar gating; rascunhos
  não linkados para download).
- Tooltip do botão informa N ("Baixar lote 3-up — N vias"); ícone distinto do
  avulso (ex.: `bi-files`).
- Não reabrir S1/S2 (captura, imposição, rotas) salvo bug encontrado — nesse
  caso, evidenciar e escalar antes de alterar.
- Follow the repository engineering policy in `AGENTS.md` and preserve
  existing conventions. Prefer the smallest correct change; avoid speculative
  abstraction and unrelated refactoring.

## 8. Validation

Focused validation (worker):

- `./scripts/test.sh apps.events apps.pdf_forms` — todos passam, sem regressão
- teste de queries confirma 1 query agrupada para `batch_info` por página

Project-required gates: referenciar `AGENTS.md` (testes + `markdownlint-cli2`
nos `.md` tocados).

Runtime/verification evidence: cenário navegador (skill `verify-eqmd` se
aplicável): timeline com lote de 3 + 1 avulsa → 3 botões de lote, 0 na avulsa;
detalhe mostra banner com 3 irmãos.

## 9. Acceptance criteria

- [ ] AC1 (R1): botão de lote nos N cards do lote, link correto ao download S2.
- [ ] AC2 (R2): botão avulso baixa só a via; some em rascunho.
- [ ] AC3 (R3): avulsas/sem-irmãos sem botão de lote, cards idênticos.
- [ ] AC4 (R4): banner no detalhe com download + irmãos; ausente em avulsas.
- [ ] AC5 (R5): bulk com 1 query agrupada; sem N+1 (teste de queries).

## 10. Escalation conditions

Parar com `BLOCKED_NEEDS_DECISION` se descobrir: contradição spec/design; nova
decisão de produto/arquitetura; expansão material de escopo; necessidade de
migration/schema; nova implicação de segurança/privacidade/clínica; bug em
S1/S2 que exija reabri-los (evidenciar e escalar antes); impossibilidade sem
violar o contrato aprovado.

## 11. Evidence report

Path: `/tmp/eqmd-slice-S3-report.md` (adaptado do canônico da skill para o
prefixo do projeto).

Conteúdo: status (`READY_FOR_REVIEW` ou `BLOCKED_NEEDS_DECISION`);
requirements → evidence; arquivos alterados; failing-before evidence;
passing-after evidence; comandos + exit status; runtime evidence; expansão de
blast radius + justificativa; riscos/limitações; decisões pendentes de humano.

## 12. Worker handoff

Implement only this approved slice.
Treat the slice and referenced OpenSpec artifacts as the implementation
contract.
Reconstruct context from the listed files; do not rely on prior conversation.
Follow the repository engineering policy.
Produce failing-before evidence, implement the smallest correct change, run
focused validation, and produce the required evidence report.
Do not update `tasks.md`, commit, push, merge, archive, or start another slice.
If a new decision is required, stop with `BLOCKED_NEEDS_DECISION` and evidence.
Otherwise finish with `READY_FOR_REVIEW` and
`REPORT_PATH=/tmp/eqmd-slice-S3-report.md`.
