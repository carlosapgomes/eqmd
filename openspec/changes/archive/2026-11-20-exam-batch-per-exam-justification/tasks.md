# Tasks: exam batch per-exam justification

## 1. Decisions (pré-aprovadas com o usuário)

- [x] 1.1 DECIDIDO: dirty-tracking no blur — copiar apenas para campos
      vazios ou não editados manualmente (preserva edits individuais).
- [x] 1.2 DECIDIDO: input de linha única por exame (paridade com o avulso;
      não é textarea).
- [x] 1.3 DECIDIDO: ajuste fino pós-criação permanece no fluxo de edição
      existente (não é escopo desta change).
- [x] 1.4 DECIDIDO (fechamento do B1 da revisão): a marcação `data-dirty`
      é o único critério do blur — campo dirty esvaziado manualmente
      permanece vazio na UI e cai no fallback server-side ao submeter.
- [x] 1.5 DECIDIDO (fechamento do B2 da revisão): linha adicionada sem
      exame e sem código, com justificativa espelhando o compartilhado,
      é ignorada como linha em branco; linhas parcialmente preenchidas
      continuam rejeitadas.

## 2. Tests

- [x] 2.1 Render: GET do lote expõe input "Justificativa" por linha do
      formset e no empty-form clonável. ✅ exec S1
- [x] 2.2 Override: POST com `exams-N-requestReason` preenchido armazena o
      valor individual na submission N; campo vazio herda a compartilhada. ✅
      exec S1 (incl. espelho multilinha → compartilhado verbatim, review-1 P1)
- [x] 2.3 Repost: POST inválido re-renderiza preservando as justificativas
      individuais digitadas. ✅ exec S1 (server + client re-arm)
- [x] 2.4 Regressão: lote sem justificativas individuais produz submissions
      idênticas ao comportamento atual (testes existentes seguem passando). ✅
      exec S1
- [x] 2.5 Comportamento client-only (blur/dirty/prefill): cenário de
      navegador via skill `verify-eqmd` (sem seam prático de teste Django). ✅
      exec S1 (journeys s1-exam-batch 8 steps + s1b-multiline-repost-pdf
      4 steps; PDF 3-up inspecionado)
- [x] 2.6 Guarda (B2): POST com linha extra contendo apenas a justificativa
      espelhada (sem exame/código) cria apenas as submissions das linhas usadas,
      sem erro de validação; linha parcial (código sem nome) segue rejeitada. ✅
      exec S1

## 3. Implementation (slices verticais)

- [x] S1 — Justificativa individual por exame no lote ✅ ACCEPTED
      (tasks 2.1–2.6; impl loop 2 rounds, fix do review-1 P1)
      Contract: `slices/slice-001-justificativa-por-exame.md`

Detalhamento (referência; o contrato vigente é o slice):

- [x] 3.1 Adicionar `requestReason` opcional (TextInput) ao
      `ExamBatchItemForm`. ✅ [S1]
- [x] 3.2 Fallback em `build_exam_batch_form_data`: valor individual com
      `.strip()` ou compartilhado (mirror-aware pós review-1 P1). ✅ [S1]
- [x] 3.3 Layout da linha de exame com o novo campo (inclusive no
      `#exam-empty-form`) + JS de blur com dirty-tracking e prefill no
      add-row. ✅ [S1]
- [x] 3.4 Testes 2.1–2.4 e 2.6 + evidência de navegador 2.5. ✅ [S1]

## 4. Documentation

- [x] 4.1 TAREFA DO COORDENADOR (pós-slice, fora do blast radius do S1):
      atualizar a seção "Solicitação de Exames em Lote" em
      `docs/apps/pdf-forms.md` (hoje afirma "justificativa única";
      ficará defasada após o S1). ✅ executada no arquivamento
      (2026-11-20, pelo agente com autorização do coordenador)
