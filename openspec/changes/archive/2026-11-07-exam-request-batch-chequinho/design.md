# Design: exam request batch (chequinho)

## Context

O motor de formulários PDF (`apps/pdf_forms/`) é 1:1 por desenho: 1 template +
1 paciente → 1 Django Form flat (`DynamicFormGenerator`) → 1
`PDFFormSubmission(Event)` → 1 PDF via overlay de página única
(`PDFFormOverlay._merge_pdfs`). O schema `form_fields` não tem conceito de
lista/formset/grupo repetível, e o configurador visual do admin também não.

O template "Solicitação de Exames SUS" (`dde2a393`, tipo HOSPITAL,
`allow_duplication=True`, 637 submissions) tem 11 campos em 3 seções, dos
quais o usuário só digita 3 por exame (`requestReason`, `examRequested`,
`examCode`) — o resto é auto-fill. O PDF é A4, mas o conteúdo medido ocupa
só 18,44 × 8,69 cm no terço superior (topo 1,19 cm → base 9,88 cm), então
3 vias cabem em 1 folha a 100% (3 × 8,69 = 26,06 < 29,70 cm).

Precedente: a APAC (`views/national_forms.py`) já é página dedicada hardcoded
reaproveitando `PDFFormTemplate` + `PDFFormSubmission` + overlay. Esta change
segue o mesmo padrão.

## Goals / Non-Goals

- Goals:
  - Capturar N exames com 1 justificativa/data/médico em uma única página.
  - Persistir 1 submission por exame, no formato `form_data` atual
    (compatível com as 637 existentes).
  - Imprimir o lote com até 3 vias por A4, idênticas ao avulso, com linhas
    de corte — para qualquer N.
  - Preservar supervisão (draft/final), permissões e gating de rascunhos.
- Non-Goals:
  - Grupos repetíveis no motor genérico ou no configurador visual.
  - Busca padronizada `MedicalProcedure` (fase 2; fase 1 mantém texto livre).
  - Redesenho do PDF oficial com ReportLab.
  - Bbox de recorte configurável no admin (recorte fixo; chequinho estável).

## Decisions

- Decision: Página dedicada de lote (estilo APAC), motor genérico intocado.
  - Novo `ExamRequestBatchView` + formset de exames; POST cria N submissions
    em transação com o mesmo `batch_id` gravado dentro de `form_data`
    (sem migration; filtro via JSONB do Postgres).
  - Rationale: isola a feature no único template consumidor; evita regressão
    nos demais templates e no configurador.

- Decision: 1 submission por exame (N rows), não 1 submission com array.
  - Rationale: mantém timeline, edição, exclusão, aprovação e download
    individuais funcionando sem adaptação; cada `form_data` segue o formato
    atual.

- Decision: Imposição fill → crop → stack (apresentação pura).
  - Cada via é gerada pelo `PDFFormOverlay` atual (coordenadas existentes),
    recortada no bbox fixo (topo 1,0 cm / base 10,0 cm, com folga sobre o
    medido 1,19–9,88 cm) e empilhada via
    `pypdf.Transformation.translate` sobre `create_blank_page(A4)`.
  - Linha de corte tracejada (ReportLab) só entre vias impressas.
  - Rationale: tamanho de letra idêntico ao avulso; overlay e storage
    inalterados; fallback natural para 1 via por página se o template mudar.

- Decision: Paginação determinística `slot=(N-1)%3`, `folha=(N-1)//3`.
  - Rationale: posição previsível para conferência
    ("4º exame = topo da folha 2").

- Decision: Batch download respeita o gating de rascunhos.
  - Só submissions finais entram na composição (mesma regra do download
    individual: rascunho → 404); `check_pdf_download_access` por submission.

- Decision: Cards da timeline mantêm o download avulso; botão de lote adicional.
  - O botão PDF existente continua gerando só a via daquele exame
    (inalterado; some em rascunhos como hoje).
  - Novo botão "Baixar lote 3-up (N vias)" aparece em TODOS os cards do
    lote (qualquer via dá acesso ao lote), só quando há `batch_id` com
    irmãos finais; tooltip informa N.
  - `submission_detail` ganha banner "Parte do lote de N exames" com
    [baixar lote 3-up] e links para irmãos.
  - `event_data["batch_info"]` montado em bulk na timeline (1 query
    agrupada por página, mesmo padrão anti-N+1 das permissões).
  - Rationale: menor surpresa (card = documento), preserva o caso
    "reimprimir 1 via" e mantém avulsas/antigas idênticas.

## Alternatives Considered

- Estender o motor genérico com `repeating_group` (schema + formset no
  gerador + merge multi-página + ensino do configurador).
  - Rejected: generalização prematura para 1 consumidor; maior superfície
    de regressão.

- 1 submission com `exams: [...]`.
  - Rejected: novo formato de `form_data`, novo renderer/editor, perda de
    granularidade (aprovar/excluir 1 exame), incompatível com o histórico.

- Reduzir a folha A4 inteira para 1/3 (scale-down).
  - Rejected: texto minúsculo; o crop 1:1 preserva legibilidade.

- Reconstruir o formulário com ReportLab do zero.
  - Rejected: risco de divergência do formulário oficial SUS + perda da
    troca de PDF pelo admin sem deploy.

## Risks / Trade-offs

- O `pdf_file` do template está ausente no volume dev atual
  (`…/2026/04/exam-request-blank_*.pdf` → FileNotFoundError); pré-requisito
  é re-upload e revalidação das dimensões antes da implementação.
- Se o admin trocar o PDF por outro de altura diferente, o recorte fixo
  desalinharia — mitigado pelo fallback 1 via por página e pelo fato de o
  chequinho ser estável.
- Lotes grandes geram N overlays em memória; limite de 12 itens por lote
  na validação do formset (decidido com o solicitante).

## Migration Plan

- Sem migration de schema (`batch_id` vive dentro do JSON `form_data`).
- Sem backfill: submissions antigas continuam imprimindo avulsas normalmente.

## Open Questions

- RESOLVIDO: limite de 12 exames por lote.
- RESOLVIDO: entrada em `form_select` numa seção isolada
  "Solicitação de Exames Múltiplos SUS" (mesmo padrão visual da seção
  "Formulários Nacionais"), com card "Solicitação de Exames SUS
  (chequinho)" levando ao formulário de lote; pós-criação redireciona à
  timeline (fluxo padrão de finalização).
- RESOLVIDO: botões da timeline — avulso mantido + botão de lote 3-up em
  todos os cards do lote; banner na `submission_detail`.
- RESOLVIDO: batch download só por `batch_id` (tudo ou gating) na fase 1.
  Reimpressão parcial usa os botões avulsos; URL desenhada de forma
  extensível para um futuro `?ids=` (exige validação mesmo-paciente/mesmo-
  template + UI de seleção — escopo YAGNI adiado).
