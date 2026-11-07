# ADR-0006: Impressão 3-up do lote de exames via fill-crop-stack

## Status

Accepted — 2026-11-07. Executada via change
`exam-request-batch-chequinho` (slices S1–S3 aceitos; commits `098e99f`,
`4a9e724`, `602d675`): página dedicada de captura em lote, 1 submission
por exame com `batch_id`, download 3-up por lote e actions na timeline.
Decisões de produto do change (limite 12/lote, recorte fixo, vias
idênticas ao avulso, sem `?ids=`) estão registradas no design do change
e não são redecididas aqui.

## Contexto

Solicitar N exames SUS ("chequinho") exigia N fluxos completos no
formulário genérico, com redigitação da justificativa e 1 folha A4 por
exame — embora o conteúdo medido ocupe só 18,44 × 8,69 cm no terço
superior da página (topo 1,19 cm, base 9,88 cm). O motor
`apps/pdf_forms/` é 1:1 por desenho (1 template + 1 paciente → 1 form
flat → 1 submission → 1 overlay de página única) e não tem conceito de
lista, formset ou grupo repetível. A APAC já validava o padrão de
página dedicada hardcoded reaproveitando template + submission +
overlay.

Change: `openspec/changes/exam-request-batch-chequinho/`.

## Decisão

1. Página dedicada de captura em lote (estilo APAC), motor genérico
   intocado: shared fields + formset de 1–12 exames, POST atômico.
2. Persistir 1 `PDFFormSubmission` por exame, cada uma no formato
   `form_data` atual acrescido de `batch_id` (sem migration).
3. Imprimir o lote por fill-crop-stack (só apresentação): cada via é
   preenchida pelo `PDFFormOverlay` atual, recortada no bbox fixo
   (topo 1,0 cm / base 10,0 cm, validado contra o PDF re-upado) e
   empilhada até 3 por folha A4 via `pypdf` (translação 1:1, sem
   redução), com linha de corte tracejada (ReportLab) só entre vias
   impressas; fallback para 1 via por página se o template fugir do
   esperado.
4. Manter o botão avulso dos cards inalterado e adicionar o botão de
   lote 3-up em todos os cards do lote, mais banner na detail;
   downloads (avulso e lote) só incluem finals (gating existente).

## Alternativas consideradas

### Grupo repetível no motor genérico

Estender schema, gerador, overlay e configurador visual. Rejeitada:
generalização prematura para 1 consumidor, com maior superfície de
regressão.

### 1 submission com `exams: [...]`

Novo formato de `form_data`, novo renderer/editor e perda de
granularidade (aprovar/editar/excluir 1 exame). Rejeitada:
incompatível com o histórico e mais cara em todas as camadas.

### Reduzir a folha A4 inteira para 1/3 (scale-down)

Comporia 3 miniaturas por folha, mas com texto minúsculo. Rejeitada:
o crop 1:1 preserva a legibilidade do avulso.

### Reconstruir o formulário com ReportLab

Controle total de layout, porém divergência do formulário oficial SUS
e perda da troca de PDF pelo admin sem deploy. Rejeitada.

### Botão do card baixar o lote todo

Rejeitada pelo princípio da menor surpresa (card = documento) e para
preservar a reimpressão de 1 via; o lote ganhou botão próprio.

## Consequências

### Positivas

- Elimina a redigitação (1 justificativa por lote) e o desperdício
  sistemático de papel (até 3 vias por folha, tamanho 100%).
- Storage e overlay inalterados; submissions antigas seguem válidas.
- Timeline, supervisão, permissões e gating reaproveitados sem
  adaptação (1 evento por exame).
- Técnica de impressão isolada em módulo próprio, com fallback.

### Negativas e trade-offs

- Recorte fixo: se o admin trocar o PDF por outro de altura
  diferente, o 3-up desalinharia — mitigado pelo fallback 1-up e
  pela estabilidade do formulário.
- Drift de conteúdo dentro do mesmo A4 não dispara o fallback (que
  observa tamanho/contagem de páginas, não posição da tinta).
- Ordenação do lote é `(created_at, pk)`; ties de timestamp ordenam
  por UUID (estável, mas pode não espelhar a sequência de criação).
  Persistir ordinal foi adiado como desproporcional.
- Resolver do template tem fallback por nome (`.first()`) quando o
  id não resolve; ambíguo se múltiplos templates casarem — aceito
  para dev/teste, com precedência do id em produção.

## Referências

- `openspec/changes/exam-request-batch-chequinho/design.md`.
- `openspec/changes/exam-request-batch-chequinho/slices/`.
- `apps/pdf_forms/services/exam_batch_imposition.py`.
- `apps/pdf_forms/views/exam_batch.py`.
- `apps/pdf_forms/views/exam_batch_download.py`.
- Evidência: `/tmp/eqmd-slice-loop/eqmd/exam-request-batch-chequinho/`.
