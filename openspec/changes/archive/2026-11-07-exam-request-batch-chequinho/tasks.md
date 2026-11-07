# Tasks: exam request batch (chequinho)

## 1. Discovery

- [x] 1.1 Re-upload do PDF do chequinho no template `dde2a393` ✅ (novo path
      `pdf_forms/templates/2026/11/…`, A4 1p) e bbox remedido: 1,19–9,88cm —
      recorte fixo 1,0/10,0cm CONFIRMADO.
- [x] 1.2 DECIDIDO ✅: download só por `batch_id` (tudo ou gating); `?ids=`
      adiado (YAGNI). Limite de 12 itens/lote: DECIDIDO.
- [x] 1.3 DECIDIDO ✅: seção "Solicitação de Exames Múltiplos SUS" em
      `form_select` (padrão da seção "Formulários Nacionais") com card
      "Solicitação de Exames SUS (chequinho)" → formulário de lote;
      pós-criação redireciona à timeline.
- [x] 1.4 DECIDIDO ✅: avulso mantido + botão de lote 3-up em todos os cards
      do lote; banner na `submission_detail`.

## 2. Tests

- [x] 2.1 Teste de criação atômica: batch válido cria N submissions com mesmo
      `batch_id`; batch inválido cria zero. [S1 ✅ exec-1]
- [x] 2.2 Teste de `form_data`: cada submission do lote segue o formato atual
  - `batch_id`; submissions legadas sem `batch_id` inalteradas. [S1 ✅ exec-1]
- [x] 2.3 Teste de imposição ✅ exec-2 [S2]
- [x] 2.4 Teste de fidelidade ✅ exec-2 [S2]
- [x] 2.5 Teste de gating/supervisão ✅ (supervisão S1 exec-1, gating S2 exec-2)
- [x] 2.6 Teste de fallback ✅ exec-2 [S2]
- [x] 2.7 Teste de actions ✅ exec-3 [S3]

## 3. Implementation (slices verticais)

- [x] S1 — Captura do lote ✅ exec-1 ACCEPTED
      (tasks 3.1, 3.2, 3.5, 3.6; tests 2.1, 2.2, supervisão de 2.5)
      Contract: `slices/slice-001-captura-lote.md`
- [x] S2 — Download 3-up do lote ✅ exec-2 ACCEPTED (P2 ordering caveat carried)
      Contract: `slices/slice-002-download-3up.md`
- [x] S3 — Actions do lote na timeline e detalhe ✅ exec-3 ACCEPTED
      Contract: `slices/slice-003-actions-timeline.md`

Detalhamento (referência; o contrato vigente é o slice):

- [x] 3.1 Criar `ExamRequestBatchForm` + formset de exames (texto livre +
      código opcional) com auto-fills de paciente/médico/data. [S1]
- [x] 3.2 Criar `ExamRequestBatchView` (create) com transação atômica,
      `batch_id` em `form_data` e ações de supervisão
      (`save_draft`/`save_final`). [S1]
- [x] 3.3 Criar módulo de imposição N-up ✅ exec-2 [S2]
- [x] 3.4 Criar `ExamBatchDownloadView` ✅ exec-2 [S2]
- [x] 3.5 Criar template da página de lote (shared + formset dinâmico com
      "+ Adicionar exame") e seção "Solicitação de Exames Múltiplos SUS"
      em `form_select` com o card do chequinho; pós-criação → timeline. [S1]
- [x] 3.6 Validar limite de 12 itens por lote e payload do formset no
      servidor. [S1]
- [x] 3.7 Adicionar botão de lote no card da timeline ✅ exec-3 [S3]

## 4. Documentation

- [x] 4.1 Documentar o fluxo de lote ✅ (seção "Solicitação de Exames em
      Lote" em `docs/apps/pdf-forms.md`, pelo coordenador).
- [x] 4.2 ADR-0006 registrada ✅ (`docs/adr/ADR-0006-…-3up-printing.md` +
      índice README, pelo coordenador).
