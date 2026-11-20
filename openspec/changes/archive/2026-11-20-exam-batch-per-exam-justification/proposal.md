# Proposal: exam batch per-exam justification

## Why

A página de lote (`/pdf-forms/exam-batch/<uuid>/`) replica a justificativa
compartilhada para todos os exames, sem possibilidade de ajuste individual.
Usuários precisam, com frequência, de justificativas ligeiramente diferentes
por exame no mesmo lote; hoje o único caminho é editar cada submission depois
de criada (N visitas à edição) ou criar lotes separados.

## What Changes

- Cada linha de exame no formset ganha um campo opcional "Justificativa"
  (input de linha única, como no formulário avulso do chequinho).
- O `blur` do campo de justificativa compartilhado copia o valor para as
  justificativas individuais **apenas** dos campos vazios ou não editados
  manualmente (dirty-tracking via atributo `data-*`); campos editados à mão
  são preservados.
- Novas linhas adicionadas por "Adicionar exame" nascem pré-preenchidas com
  o valor compartilhado corrente.
- Fallback server-side: justificativa individual vazia → a submission herda
  a compartilhada (comportamento atual intacto, inclusive sem JavaScript).
- `build_exam_batch_form_data` passa a resolver `requestReason` por exame
  (valor individual ou fallback). Nenhuma mudança de modelo/migration;
  download 3-up, download avulso, edição, aprovação e timeline ficam
  intocados (cada submission já carrega seu próprio `form_data`).

## Impact

- Affected specs: pdf-forms (requisito "Exam batch capture page" — valores
  compartilhados passam a ser default sobreponível por exame)
- Affected code: `apps/pdf_forms/views/exam_batch.py`
  (`ExamBatchItemForm` + `build_exam_batch_form_data`),
  `apps/pdf_forms/templates/pdf_forms/exam_batch_form.html` (layout da
  linha + JS de cópia), `apps/pdf_forms/tests/test_exam_batch.py` (novos
  testes)
- Uses existing: `form_data` JSON por submission, sanitização existente,
  fluxo de edição pós-criação (já permite ajuste fino por submission)
- Non-goals: mudanças no motor genérico/`DynamicFormGenerator`, no PDF
  oficial, no admin configurador, na imposição 3-up; textarea por exame
  (linha única basta); sincronizar edits pós-blur além da semântica definida
