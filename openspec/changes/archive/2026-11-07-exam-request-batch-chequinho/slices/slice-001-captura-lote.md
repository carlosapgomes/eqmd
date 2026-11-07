# Slice S1 — Captura do lote de exames

## 1. Identity

- Slice ID: S1
- Title: Captura do lote de exames (form + criação atômica + entrada em
  `form_select`)
- Change ID: `exam-request-batch-chequinho`
- Tasks: 3.1, 3.2, 3.5, 3.6 (tests 2.1, 2.2 e supervisão de 2.5)

## 2. Objective

Entregar a página dedicada de solicitação em lote: o usuário preenche
motivo/data/médico uma vez + 1–12 exames e o sistema cria N submissions com o
mesmo `batch_id`, redirecionando à timeline.

## 3. Read first

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `openspec/changes/exam-request-batch-chequinho/proposal.md`
- `openspec/changes/exam-request-batch-chequinho/design.md` — Decisions
  (página dedicada, 1 submission/exame, limite 12, entrada em `form_select`)
- `openspec/changes/exam-request-batch-chequinho/specs/pdf-forms/spec.md` —
  Requirements: batch capture page, one submission per exam, batch supervision
  parity
- `apps/pdf_forms/views/national_forms.py` — padrão APAC (form hardcoded +
  `save_draft`/`save_final` + `is_doctor_or_resident`)
- `apps/pdf_forms/views/base_views.py` — `PDFFormFillView` (sanitização,
  permissões, redirect)
- `apps/pdf_forms/templates/pdf_forms/form_select.html` — padrão da seção
  "Formulários Nacionais"
- `apps/pdf_forms/urls.py`, `apps/pdf_forms/models.py`

## 4. Requirements

- R1: GET na nova rota de lote (paciente válido, usuário autorizado) renderiza
  shared fields com auto-fills atuais (paciente/médico/data) + formset de
  exames com botão "+ Adicionar exame".
- R2: POST válido cria exatamente N `PDFFormSubmission` em transação atômica,
  todas com o mesmo `batch_id` em `form_data` e demais chaves no formato
  atual.
- R3: POST com qualquer linha de exame inválida (ex.: nome vazio) cria zero
  submissions e reexibe erros.
- R4: Lotes com mais de 12 exames são rejeitados no servidor com erro de
  validação.
- R5: Estudante cria N rascunhos (`is_draft=True`); `save_final` por
  não-médico/residente é negado; médico/residente finaliza (paridade com
  APAC/fill).
- R6: `form_select` ganha seção "Solicitação de Exames Múltiplos SUS" (mesmo
  padrão visual da seção Nacional) com card "Solicitação de Exames SUS
  (chequinho)" → formulário de lote.
- R7: Pós-criação com sucesso redireciona à timeline do paciente (fluxo padrão).
- R8: Fluxo avulso existente (`form_fill`, detalhe, download, duplicação,
  submissions sem `batch_id`) permanece inalterado.

Evidência: testes automatizados (TDD) para R1–R8 via testes de view/model +
inspeção de redirect; R6 por teste de resposta HTML contendo seção/card.

## 5. Expected blast radius

Provavelmente afetados:

- `apps/pdf_forms/views/` — novo módulo da view de lote (não editar
  `base_views.py`/`national_forms.py` salvo import trivial)
- `apps/pdf_forms/urls.py` — nova rota
- `apps/pdf_forms/templates/pdf_forms/` — novo template do lote + edição em
  `form_select.html`
- `apps/pdf_forms/tests/` — novos testes (ex.: `test_exam_batch.py`)

Sensíveis (não mudar sem escalada):

- `PDFFormOverlay`, download avulso, `DynamicFormGenerator`, configurador do
  admin
- models/migrations (proibido: `batch_id` vive no JSON `form_data`)
- cards da timeline e `submission_detail` (são do S3)

Comportamento anterior preservado: R8.

Expansão de blast radius exige justificativa no relatório.

## 6. Failing-before plan

Failing-before evidence (TDD, RED antes do GREEN):

- targeted tests: novos testes de criação atômica (2.1),
  `form_data`+`batch_id` (2.2), supervisão (parte de 2.5)
- expected failure: `GET/POST` na rota do lote → 404 (rota inexistente);
  testes de seção/card em `form_select` falham (seção ausente)

## 7. Implementation constraints

- Seguir o padrão APAC para supervisão (`save_draft`/`save_final`,
  `is_doctor_or_resident`, `can_edit_event`); não inventar novo fluxo de
  aprovação.
- Sanitizar `form_data` com `PDFFormSecurity.sanitize_form_data` como o fill
  atual.
- Usar o template `dde2a393` resolvido por configuração/código (não hardcodar
  difuso); não alterar o template nem seu `form_fields`.
- Limite de 12 itens validado no servidor (não só no JS).
- Não implementar download 3-up (S2) nem botões/banner (S3) antecipadamente.
- Follow the repository engineering policy in `AGENTS.md` and preserve
  existing conventions. Prefer the smallest correct change; avoid speculative
  abstraction and unrelated refactoring.

## 8. Validation

Focused validation (worker):

- `./scripts/test.sh apps.pdf_forms.tests.test_exam_batch` (ou o módulo
  criado) — todos passam
- `./scripts/test.sh apps.pdf_forms` — sem regressão no escopo

Project-required gates: referenciar `AGENTS.md` (testes + `markdownlint-cli2`
nos `.md` tocados); não replicar comandos globais aqui.

Runtime/verification evidence: cenário navegador (skill `verify-eqmd` se
aplicável) ou reprodução executável: criar lote de 3 exames como médico → N
cards na timeline; como estudante → N rascunhos.

## 9. Acceptance criteria

- [ ] AC1 (R1): página do lote renderiza shared + formset funcional com "+
      Adicionar exame".
- [ ] AC2 (R2): POST válido cria N submissions com mesmo `batch_id` e formato
      atual.
- [ ] AC3 (R3): POST inválido cria zero submissions e exibe erros.
- [ ] AC4 (R4): >12 itens rejeitado no servidor.
- [ ] AC5 (R5): estudante → rascunhos; `save_final` não-médico negado; médico
      finaliza.
- [ ] AC6 (R6): seção + card presentes em `form_select`.
- [ ] AC7 (R7): redirect pós-criação vai à timeline.
- [ ] AC8 (R8): testes do fluxo avulso passam sem alteração de comportamento.

## 10. Escalation conditions

Parar com `BLOCKED_NEEDS_DECISION` se descobrir: contradição spec/design; nova
decisão de produto/arquitetura; expansão material de escopo; necessidade de
migration/schema; nova implicação de segurança/privacidade/clínica;
impossibilidade sem violar o contrato aprovado.

## 11. Evidence report

Path: `/tmp/eqmd-slice-S1-report.md` (adaptado do canônico da skill para o
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
`REPORT_PATH=/tmp/eqmd-slice-S1-report.md`.
