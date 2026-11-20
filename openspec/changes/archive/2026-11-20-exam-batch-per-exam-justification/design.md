# Design: exam batch per-exam justification

## Context

O lote do chequinho (change arquivada
`2026-11-07-exam-request-batch-chequinho`) captura campos compartilhados
(`ExamBatchSharedForm`: `requestReason`, `currentDate`, `doctor`,
`doctorRegistrationNumber`) uma única vez e um formset de exames
(`ExamBatchItemForm`: `examRequested` + `examCode`). O único ponto de
replicação da justificativa é `build_exam_batch_form_data`, que copia
`shared["requestReason"]` para o `form_data` de cada uma das N
`PDFFormSubmission`.

Cada exame já nasce como submission independente com `form_data` próprio;
download 3-up, download avulso, edição e aprovação leem o `form_data` por
submission. Portanto justificativas diferentes por exame fluem até o PDF sem
qualquer mudança downstream. O template da página tem JS vanilla (~15 linhas)
apenas para clonar linhas do `#exam-empty-form`.

No formulário avulso do chequinho, `requestReason` é campo de linha única —
a justificativa por exame deve seguir o mesmo padrão.

## Goals / Non-Goals

- Goals:
  - Permitir justificativa individual opcional por exame na própria tela do
    lote, com preenchimento assistido a partir do campo compartilhado.
  - Preservar o comportamento atual quando o usuário não edita nada
    individualmente (todas as submissions herdam a justificativa
    compartilhada).
  - Manter o lote funcional sem JavaScript (fallback server-side).
- Non-Goals:
  - Mudar modelos, migrations, motor genérico, PDF oficial, imposição 3-up,
    admin configurador, timeline ou fluxo de edição/aprovação.
  - Textarea por exame (linha única, como no avulso).
  - Copiar a justificativa para outros campos compartilhados (data, médico).

## Decisions

- Decision: campo `requestReason` opcional em `ExamBatchItemForm`
  (`TextInput`, linha única, rótulo "Justificativa", placeholder indicando
  o default do lote).
  - Rationale: espelha o campo do fluxo avulso; opcional porque o fallback
    server-side garante o valor compartilhado.

- Decision: cópia no `blur` com dirty-tracking — o `blur` do campo
  compartilhado (`#id_requestReason`) copia o valor APENAS para as
  justificativas individuais sem marcação `data-dirty`; a marcação é o único
  critério (o teste de "vazio" é redundante: campo nunca tocado está vazio
  e sem marcação). Campos editados manualmente (evento `input` do usuário)
  são preservados — inclusive um campo dirty esvaziado de propósito
  permanece vazio na UI e, ao submeter, cai no fallback server-side
  (persistência idêntica à cópia, sem ambiguidade de leitura).
  - Rationale: decisão do usuário (alternativa segura à sobrescrita
    incondicional); evita destruir ajustes individuais quando o usuário
    volta ao campo compartilhado. "Uma vez dirty, permanece dirty" na
    sessão da página.
  - Campos não-editados espelham o valor compartilhado incondicionalmente
    (inclusive se ele for esvaziado): a semântica é "espelho até primeira
    edição manual".
  - Re-arme na carga da página (inclusive re-render de POST inválido):
    campos individuais cujo valor difira do valor corrente do compartilhado
    nascem marcados dirty, preservando edições individuais através do
    repost (R2 da revisão independente).

- Decision: novas linhas ("Adicionar exame") nascem pré-preenchidas com o
  valor compartilhado corrente e sem marcação dirty (blurs subsequentes
  continuam atualizando-as, se não editadas).

- Decision: linha pré-preenchida e não usada é ignorável — uma linha com
  `examRequested` vazio, `examCode` vazio e `requestReason` idêntico ao
  valor compartilhado postado (espelho intacto) é tratada como linha em
  branco: não conta como alterada para o formset e não invalida o lote.
  Linhas parcialmente preenchidas continuam rejeitadas como hoje (ex.:
  código sem nome do exame; justificativa própria digitada sem nome do
  exame).
  - Rationale: sem esta regra, o prefill faria toda linha adicionada e não
    usada disparar o erro obrigatório de `examRequested`, rejeitando o lote
    inteiro — regressão de fluxo no caminho feliz (B2 da revisão
    independente). A condição de "espelho intacto" preserva a rejeição de
    linhas com input real do usuário. Implementação sugerida: no
    `ExamBatchItemForm`, desobrigar os campos quando o padrão
    não-usada+espelho for detectado (o formset recebe o valor compartilhado
    via `get_form_kwargs`/kwargs do form; `empty_permitted` cuida das linhas
    totalmente em branco como hoje) e o filtro existente em `post` já
    descarta linhas sem `examRequested`.

- Decision (review-1 P1): espelho normalizado para linha única — o campo
  individual é `input type=text`, que remove quebras de linha do valor
  copiado/prefill do `textarea` compartilhado. O servidor MUST tratar o
  valor individual como espelho do compartilhado quando for igual ao
  compartilhado com quebras (`\r`/`\n`) removidas, em DOIS pontos: (a) na
  detecção da linha não usada (R7) e (b) na resolução de
  `requestReason` por exame (linha espelhada armazena o compartilhado
  ORIGINAL verbatim, não o valor deformado — R6).
  - Rationale: sem isso, compartilhado multilinha + blur/prefill persiste
    `Linha ALinha B` nas submissions de linhas não editadas e rejeita
    lotes com linha adicionada não usada (P1 da revisão 1).
  - Semântica de colisão aceita: edição manual que coincida exatamente com
    o compartilhado sem quebras é indistinguível do artefato de espelho e
    armazena o compartilhado verbatim (sem perda de conteúdo; equivalente
    exceto quebras).

- Decision: fallback server-side em `build_exam_batch_form_data` —
  `"requestReason"` por exame resolve para `(exam.get("requestReason") or
"").strip() or shared["requestReason"]`.
  - Rationale: sem JS, ou com campo individual vazio, o resultado é idêntico
    ao comportamento atual; `requestReason` compartilhado permanece
    obrigatório por ser o fallback.

- Decision: ajuste fino pós-criação continua pelo fluxo de edição existente
  (o formulário de edição já expõe `requestReason` por submission).
  - Rationale: não inventar segundo fluxo; a edição na tela do lote atende o
    pedido original do usuário.

## Alternatives Considered

- Sobrescrita incondicional no blur: rejeitada pelo usuário (perderia edits
  individuais ao revisitar o campo compartilhado).
- Não tocar na tela do lote e orientar o usuário a editar cada submission
  pós-criação: rejeitada — o pedido explicita edição na própria tela do lote.
- Textarea por exame: rejeitada — no avulso a justificativa é linha única e
  12 textareas alongariam a página desnecessariamente.
- Aceitar a rejeição do lote quando uma linha pré-preenchida não é usada:
  rejeitada — regressão de fluxo no caminho feliz do prefill aprovado
  (usuário sem botão de remover linha teria de apagar a justificativa
  espelhada à mão para se recuperar).

## Risks / Trade-offs

- JS client-only: a semântica de blur/dirty não é coberta por testes Django;
  evidência por cenário de navegador (skill `verify-eqmd`).
- Página mais alta (3 campos por linha de exame): mitigado pelo input de
  linha única e layout em duas linhas visuais por exame.
- `data-dirty` não sobrevive a reload/repost por si só: mitigado pelo
  re-arme na carga (campos que divergem do compartilhado nascem dirty);
  sem JS a semântica degrada para o fallback server-side, que é o
  comportamento atual.
- Delegação de eventos: o clone de linhas via `insertAdjacentHTML` exige
  listener delegado (ex.: em `#exam-rows`) ou re-anexo por clone, senão
  linhas adicionadas ficam sem dirty-tracking (R1 da revisão
  independente); seletor restrito a
  `#exam-rows input[name$="-requestReason"]`, excluindo `#exam-empty-form`
  e o campo compartilhado.
