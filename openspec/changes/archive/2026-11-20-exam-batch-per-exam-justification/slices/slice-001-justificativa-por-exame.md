# Slice S1 — Justificativa individual por exame no lote

## 1. Identity

- Slice ID: S1
- Title: Justificativa individual por exame (form + fallback + template/JS +
  testes)
- Change ID: `exam-batch-per-exam-justification`
- Tasks: 2.1–2.6 (detalhe 3.1–3.4)

## 2. Objective

Entregar, na tela do lote, um campo opcional de justificativa por exame
(linha única), pré-preenchido a partir do campo compartilhado via blur com
dirty-tracking, com fallback server-side para o valor compartilhado quando
vazio — preservando o comportamento atual nos demais casos.

## 3. Read first

- `AGENTS.md`
- `openspec/changes/exam-batch-per-exam-justification/proposal.md`
- `openspec/changes/exam-batch-per-exam-justification/design.md` — Decisions
  (dirty-tracking, input de linha única, fallback, prefill de nova linha)
- `openspec/changes/exam-batch-per-exam-justification/specs/pdf-forms/spec.md`
  — Requirement: Exam batch capture page
- `apps/pdf_forms/views/exam_batch.py` — `ExamBatchItemForm`,
  `ExamBatchSharedForm`, `build_exam_batch_form_data`, `post`
- `apps/pdf_forms/templates/pdf_forms/exam_batch_form.html` — cards
  compartilhado/exames, `#exam-empty-form`, `extra_scripts`
- `apps/pdf_forms/tests/test_exam_batch.py` — helpers `_valid_post`,
  `make_exam_template`, padrão dos testes existentes
- `openspec/specs/pdf-forms/spec.md` — requisito vigente (baseline)
- `.pi/skills/verify-eqmd/SKILL.md` — regras da evidência de navegador
  (harness, fixtures, segurança) usada em R3/R4

## 4. Requirements

- R1: GET do lote renderiza um input de linha única "Justificativa"
  (opcional) em cada linha do formset e no `#exam-empty-form` usado pelo
  "Adicionar exame" (com `__prefix__` nos id/name, como os demais campos).
- R2: POST aceita `exams-N-requestReason` opcional; a submission do exame N
  armazena `form_data["requestReason"]` com o valor individual quando
  preenchido, e com o valor compartilhado quando vazio/em branco.
- R3: `blur` em `#id_requestReason` copia o valor corrente para os inputs
  `exams-*-requestReason` SEM marcação dirty (`data-dirty`) — a marcação é
  o único critério. Inputs marcados dirty (edição manual via evento
  `input`) são preservados, inclusive os esvaziados manualmente
  (permanecem vazios na UI; a persistência cai no fallback de R2). Campos
  não-editados espelham o compartilhado incondicionalmente (inclusive
  esvaziando); uma vez dirty, permanece dirty na sessão da página. Na
  carga da página (inclusive re-render de POST inválido), campos
  individuais cujo valor difira do valor corrente do compartilhado nascem
  marcados dirty (preserva edições através do repost).
- R4: linha adicionada por "Adicionar exame" nasce pré-preenchida com o
  valor corrente do campo compartilhado e sem marcação dirty.
- R5: POST inválido (ex.: nome de exame vazio) re-renderiza a página
  preservando as justificativas individuais digitadas (bound data).
- R6: lote sem justificativas individuais produz submissions idênticas ao
  comportamento atual; os testes existentes de `test_exam_batch.py` passam
  sem alteração de semântica (ajustes mecânicos ao helper são aceitáveis se
  não mudarem as assertions).
- R7: linha do formset sem exame e sem código, com justificativa idêntica à
  compartilhada postada (espelho intacto), é tratada como linha em branco
  (ignorada, sem erro de validação); linhas parcialmente preenchidas
  (código sem nome, ou justificativa própria digitada sem nome) seguem
  rejeitadas como hoje.
- R8: nenhuma mudança em modelos/migrations, `exam_batch_download.py`,
  `pdf_overlay`, `national_forms`, `base_views`, `form_select.html`,
  templates da timeline ou fluxo de edição/aprovação.

Evidência: R1, R2, R5, R6, R7 por testes automatizados (TDD) em
`test_exam_batch.py` (R7 é teste de guarda: linha em branco espelhada já
passa hoje sem o campo; protege contra a implementação ingênua que a
rejeitaria); R3, R4 são client-only (sem seam prático de teste Django) —
evidência por cenário de navegador na superfície real (skill `verify-eqmd`
ou reprodução executável equivalente), justificativa registrada no
relatório.

## 5. Expected blast radius

Provavelmente afetados:

- `apps/pdf_forms/views/exam_batch.py` — `ExamBatchItemForm` (+ campo) e
  `build_exam_batch_form_data` (resolução do `requestReason` por exame)
- `apps/pdf_forms/templates/pdf_forms/exam_batch_form.html` — layout da
  linha de exame (sugestão: exame+código na primeira linha visual,
  justificativa full-width na segunda), `#exam-empty-form`, JS em
  `extra_scripts` (blur + dirty + prefill)
- `apps/pdf_forms/tests/test_exam_batch.py` — novos testes (2.1–2.4)

Sensíveis (não mudar sem escalada):

- models/migrations (`requestReason` individual vive no JSON `form_data`;
  proibido schema change)
- `exam_batch_download.py`, `services/pdf_overlay.py`,
  `services/exam_batch_imposition.py` (downstream agnóstico ao valor)
- `national_forms.py`, `base_views.py`, `DynamicFormGenerator`
- `form_select.html`, cards da timeline, `submission_detail`

Comportamento anterior preservado: R6 (fallback = replicação atual) e R7
(linha não usada segue ignorada como hoje).

Expansão de blast radius exige justificativa no relatório.

## 6. Failing-before plan

Failing-before evidence (TDD, RED antes do GREEN):

- targeted tests (novos, em `test_exam_batch.py`):
  - render: resposta do GET contém input `exams-0-requestReason` com
    rótulo "Justificativa" E `exams-__prefix__-requestReason` dentro do
    `#exam-empty-form` (fonte do clone)
  - override: POST com `exams-0-requestReason="Motivo A"` e
    `exams-1-requestReason=""` → submission 0 com `"Motivo A"`, submission 1
    com o valor compartilhado
  - repost: POST inválido (nome de exame vazio) com
    `exams-0-requestReason="Motivo A"` → HTML re-renderizado contém
    "Motivo A" no campo individual (teste 2.3)
- expected failure: render falha (campo inexistente no HTML, inclusive no
  empty-form); override falha (form ignora a chave; ambas as submissions
  carregam o valor compartilhado); repost falha (campo inexistente no HTML)
- nota: o teste de guarda 2.6 (linha espelhada ignorada) NÃO é RED — a
  linha em branco já passa hoje sem o campo; existe para proteger contra a
  implementação ingênua que rejeitaria a linha pré-preenchida não usada

## 7. Implementation constraints

- `ExamBatchItemForm.requestReason`: `CharField(required=False)` com
  `TextInput` `form-control`, rótulo "Justificativa" (placeholder indicando
  default do lote, ex.: "Opcional — usa a justificativa do lote").
- `requestReason` compartilhado permanece obrigatório (é o fallback).
- Fallback exatamente como no design: valor individual `.strip()` ou o
  compartilhado; sanitização existente cobre o novo caminho (não duplicar).
- Linha não usada (R7): implementar no form/formset (ex.: desobrigar os
  campos da linha quando `examRequested` e `examCode` vazios e
  `requestReason` igual ao compartilhado postado, recebido via kwargs do
  form); o filtro existente em `post` já descarta linhas sem `examRequested`
  e `empty_permitted` já cuida das linhas totalmente em branco.
- JS vanilla no bloco `extra_scripts` existente (sem novas dependências);
  manter o padrão ES5/`var` do script atual. Dirty-tracking:
  - listener de `input` DELEGADO (ex.: em `#exam-rows`) ou anexado a cada
    clone — listeners só da carga deixam linhas clonadas sem proteção;
  - seletor restrito a `#exam-rows input[name$="-requestReason"]`,
    excluindo `#exam-empty-form` (fonte do clone) e o campo compartilhado
    `#id_requestReason`;
  - `data-dirty` é o único critério do blur; na carga da página, marcar
    dirty os campos individuais cujo valor difira do compartilhado corrente.
- `#exam-empty-form` deve incluir o novo campo (fonte do clone do
  "Adicionar exame"); o replace de `__prefix__` resolve id/name dos inputs
  (labels do empty-form seguem o padrão atual sem atributo `for`; usar
  `empty_form.<campo>.id_for_label` se optar por adicionar `for`).
- Não implementar: copiar para data/médico, textarea por exame, mudanças
  downstream, sincronização além da semântica aprovada, botão de remover
  linha.
- Follow the repository engineering policy in `AGENTS.md` and preserve
  existing conventions. Prefer the smallest correct change; avoid
  speculative abstraction and unrelated refactoring.

## 8. Validation

Focused validation (worker):

- `./scripts/test.sh apps.pdf_forms.tests.test_exam_batch` — todos passam
- `./scripts/test.sh apps.pdf_forms` — sem regressão no escopo

Project-required gates: referenciar `AGENTS.md` (testes + `markdownlint-cli2`
nos `.md` tocados, se aplicável); não replicar comandos globais aqui.

Runtime/verification evidence (R3/R4): cenário de navegador com a skill
`verify-eqmd` (ler o SKILL.md antes de usar o harness):

- preencher o compartilhado e blur → linhas existentes populadas;
- adicionar uma linha via botão, editar a justificativa DELA e dar blur no
  compartilhado com novo texto → demais linhas atualizadas, a linha
  editada (clonada) preservada (delegação de eventos);
- esvaziar manualmente a justificativa de uma linha editada e blur →
  campo permanece vazio na UI (persistência cai no fallback);
- esvaziar o compartilhado e blur → linhas não-editadas espelham o vazio;
- adicionar linha e deixá-la sem exame/código (só o prefill), submeter →
  linha ignorada, lote criado sem erro;
- submeter como médico e conferir as submissions/PDFs com justificativas
  individuais.

## 9. Acceptance criteria

- [ ] AC1 (R1): GET renderiza "Justificativa" por linha e no empty-form.
- [ ] AC2 (R2): override individual persiste; vazio herda o compartilhado.
- [ ] AC3 (R3): blur copia apenas para campos sem `data-dirty`; edits
      manuais preservados, inclusive os esvaziados manualmente; re-arme
      dirty na carga pós-repost (evidência de navegador + teste 2.3).
- [ ] AC4 (R4): nova linha nasce pré-preenchida (evidência de navegador).
- [ ] AC5 (R5): repost de formulário inválido preserva valores digitados.
- [ ] AC6 (R6): testes existentes passam; lote sem edits individuais gera
      submissions idênticas às de hoje.
- [ ] AC7 (R7): linha espelhada não usada é ignorada; linha parcial segue
      rejeitada (teste 2.6).
- [ ] AC8 (R8): nenhum arquivo fora do blast radius tocado (ou expansão
      justificada no relatório).

## 10. Escalation conditions

Parar com `BLOCKED_NEEDS_DECISION` se descobrir: contradição spec/design; nova
decisão de produto/arquitetura; expansão material de escopo; necessidade de
migration/schema; nova implicação de segurança/privacidade/clínica;
impossibilidade sem violar o contrato aprovado.

## 11. Evidence report

Path: `/tmp/eqmd-slice-S1-report.md` (prefixo do projeto).

Conteúdo: status (`READY_FOR_REVIEW` ou `BLOCKED_NEEDS_DECISION`);
requirements → evidence; arquivos alterados; failing-before evidence;
passing-after evidence; comandos + exit status; runtime evidence (R3/R4);
expansão de blast radius + justificativa; riscos/limitações; decisões
pendentes de humano.

## 12. Worker handoff

Implement only this approved slice.
Treat the slice and referenced OpenSpec artifacts as the implementation
contract.
Reconstruct context from the listed files; do not rely on prior conversation.
Follow the repository engineering policy.
Produce failing-before evidence, implement the smallest correct change, run
focused validation, and produce the required evidence report.
Do not update `tasks.md`, commit, push, merge, archive, or start another
slice.
If a new decision is required, stop with `BLOCKED_NEEDS_DECISION` and
evidence.
Otherwise finish with `READY_FOR_REVIEW` and
`REPORT_PATH=/tmp/eqmd-slice-S1-report.md`.
