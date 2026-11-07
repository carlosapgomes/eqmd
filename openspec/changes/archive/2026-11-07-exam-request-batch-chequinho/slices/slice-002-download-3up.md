# Slice S2 — Download 3-up do lote

## 1. Identity

- Slice ID: S2
- Title: Download do lote com imposição 3-up em A4 (módulo + view + rota)
- Change ID: `exam-request-batch-chequinho`
- Tasks: 3.3, 3.4 (tests 2.3, 2.4, gating de 2.5, 2.6)
- Depends on: S1 (dados com `batch_id`; testes podem usar factories)

## 2. Objective

Entregar o download do lote por `batch_id`: composição de até 3 vias por folha
A4 a 100%, idênticas ao avulso, com linhas de corte só entre vias impressas e
fallback 1-up.

## 3. Read first

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `openspec/changes/exam-request-batch-chequinho/proposal.md`
- `openspec/changes/exam-request-batch-chequinho/design.md` — Decisions
  (fill→crop→stack, paginação determinística, gating, recorte fixo 1,0/10,0cm,
  fallback)
- `openspec/changes/exam-request-batch-chequinho/specs/pdf-forms/spec.md` —
  Requirements: batch 3-up printing, deterministic pagination, batch download
  draft gating and permissions
- `apps/pdf_forms/services/pdf_overlay.py` — `PDFFormOverlay` (reuso do fill;
  `_merge_pdfs` página única)
- `apps/pdf_forms/views/base_views.py` — `PDFFormDownloadView` (permissões,
  gating via manager, filename seguro)
- `apps/pdf_forms/tests/test_draft_output_gating.py` — regra "rascunho nunca
  exporta"
- `apps/pdf_forms/permissions.py`, `apps/pdf_forms/urls.py`

## 4. Requirements

- R1: GET na rota de download do lote com `batch_id` válido retorna PDF A4 com
  `ceil(N/3)` páginas para N finals (N=1/2/3 → 1 folha; N=4 → 2; N=9 → 3
  cheias).
- R2: Exame N ocupa slot `(N-1)%3` da folha `(N-1)//3`, em ordem, a 100% (crop
  fixo topo 1,0cm/base 10,0cm, sem scale-down).
- R3: Linha de corte tracejada só entre vias impressas (2 vias → 1 linha; 1
  via → nenhuma).
- R4: Cada via do lote é idêntica ao download avulso da mesma submission
  (mesmo overlay, mesmo tamanho).
- R5: Rascunhos nunca entram na composição (lote só de rascunhos → 404,
  espelhando o download individual); usuário sem acesso ao paciente é negado;
  `check_pdf_download_access` por submission.
- R6: Template com altura de conteúdo inesperada (fora do recorte fixo) cai
  para 1 via por página sem erro.
- R7: Download avulso existente permanece byte-/comportamento-compatível
  (nenhuma regressão).

Evidência: testes automatizados (TDD) com factories + PDFs de teste — contagem
de páginas via pypdf, posição dos slots, presença/ausência de cut lines,
comparação de conteúdo via vs avulso, gating 404/403, fallback.

## 5. Expected blast radius

Provavelmente afetados:

- `apps/pdf_forms/services/` — novo módulo de imposição N-up (novo arquivo)
- `apps/pdf_forms/views/` — nova view de download do lote (novo arquivo ou
  extensão do módulo do S1)
- `apps/pdf_forms/urls.py` — nova rota (desenhada extensível; sem `?ids=`
  nesta fase)
- `apps/pdf_forms/tests/` — novos testes (ex.: `test_exam_batch_download.py`)

Sensíveis (não mudar sem escalada):

- `PDFFormOverlay` — reusar; refactor mínimo só se indispensável para expor
  bytes (justificar)
- `PDFFormDownloadView`, `DynamicFormGenerator`, models/migrations,
  admin/configurador
- cards da timeline e `submission_detail` (S3)

Comportamento anterior preservado: R7.

Expansão de blast radius exige justificativa no relatório.

## 6. Failing-before plan

Failing-before evidence (TDD, RED antes do GREEN):

- targeted tests: imposição (2.3), fidelidade (2.4), gating (parte de 2.5),
  fallback (2.6)
- expected failure: GET na rota do lote → 404 (rota inexistente); testes do
  módulo de imposição falham (módulo ausente)

## 7. Implementation constraints

- Reaproveitar `PDFFormOverlay` para o fill de cada via; não redesenhar o
  formulário nem alterar coordenadas do template.
- Recorte fixo conforme design (1,0/10,0cm); cut lines via ReportLab; stack
  via pypdf sobre `create_blank_page(A4)`; libs já são dependências (não
  adicionar novas sem escalada).
- Gating via manager padrão (rascunhos 404) + permissão por submission,
  espelhando `PDFFormDownloadView`.
- Pré-requisito operacional (task 1.1, humano): re-upload do PDF real no
  volume dev. Testes automatizados usam factories/PDFs de teste e não dependem
  dele; verificação runtime contra o template real só é possível após o
  re-upload — se ausente, verificar com template de teste e registrar a
  limitação no relatório (não bloquear por isso).
- Não implementar `?ids=` (adiado/YAGNI), botões/banner (S3) antecipadamente.
- Follow the repository engineering policy in `AGENTS.md` and preserve
  existing conventions. Prefer the smallest correct change; avoid speculative
  abstraction and unrelated refactoring.

## 8. Validation

Focused validation (worker):

- `./scripts/test.sh apps.pdf_forms.tests.test_exam_batch_download` (ou o
  módulo criado) — todos passam
- `./scripts/test.sh apps.pdf_forms` — sem regressão no escopo

Project-required gates: referenciar `AGENTS.md` (testes + `markdownlint-cli2`
nos `.md` tocados).

Runtime/verification evidence: gerar lote real (N=4, sendo 1 rascunho se
possível) e inspecionar o PDF: 1 folha cheia + 1 folha com 1 via, cut lines
corretas, rascunho ausente. Se o PDF real do template estiver ausente (task
1.1 pendente), evidenciar com template de teste e registrar.

## 9. Acceptance criteria

- [ ] AC1 (R1): paginação `ceil(N/3)` correta para N=1,2,3,4,9.
- [ ] AC2 (R2): slots determinísticos a 100%, sem redução.
- [ ] AC3 (R3): cut lines só entre vias impressas.
- [ ] AC4 (R4): via do lote idêntica ao avulso.
- [ ] AC5 (R5): rascunhos excluídos (só-rascunhos → 404); sem acesso negado.
- [ ] AC6 (R6): fallback 1-up sem erro em altura inesperada.
- [ ] AC7 (R7): download avulso inalterado (testes existentes passam).

## 10. Escalation conditions

Parar com `BLOCKED_NEEDS_DECISION` se descobrir: contradição spec/design; nova
decisão de produto/arquitetura; expansão material de escopo; necessidade de
migration/schema/nova dependência; nova implicação de
segurança/privacidade/clínica; impossibilidade sem violar o contrato aprovado.

## 11. Evidence report

Path: `/tmp/eqmd-slice-S2-report.md` (adaptado do canônico da skill para o
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
`REPORT_PATH=/tmp/eqmd-slice-S2-report.md`.
