# Slice 01 - Dialog de cópia fragmentada do card de evolução

## Goal

O botão de copiar do card de evolução na timeline copia direto notas
curtas (até 4.000 caracteres brutos) e abre um dialog Bootstrap 5 com
partes de até 4.000 caracteres para notas longas, sem alterar o
comportamento de qualquer outro card ou da página de detalhe.

## Scope boundaries

- Incluído: módulos webpack (`dailynote-chunks`, `clipboard-utils`,
  `dailynote-copy`), extração de helpers no `assets/index.js`, parcial
  do card da dailynote, harness Node do splitter + wrapper Django,
  rebuild do bundle, testes de template.
- Excluído: botões de copiar da página de detalhe da evolução, cards de
  outros tipos de evento, qualquer endpoint/backend, estilos globais
  novos, preview de partes dentro do dialog.
- Exceção de escopo: marcar os checkboxes do próprio prompt
  (`slice-01-prompt.md`) é permitido antes de parar.

## Files to create/modify

- `apps/dailynotes/tests/dailynote_chunks_harness.cjs` (novo; modelar em
  `apps/core/tests/page_navigation_loading_harness.cjs`: carregar o
  código real com `vm.runInNewContext` e um sandbox
  `{ module: { exports: {} } }`)
- `apps/dailynotes/tests/test_dailynote_chunks_harness.py` (novo;
  modelar em `apps/core/tests/test_page_navigation_loading.py`:
  `SimpleTestCase`, `skipUnless(shutil.which("node"))`, rodar o harness
  via subprocess, exigir returncode 0 e resumo JSON sem falhas)
- `apps/dailynotes/tests/test_card_copy_dialog.py` (novo; modelar em
  `test_draft_card_actions.py`: `setup_groups`,
  `create_profession_user`, `cache.clear()`, helper `_timeline_html`;
  asserções escopadas ao `<article>` de cada card, não à página toda)
- `assets/js/dailynote-chunks.js` (novo; CommonJS puro:
  `module.exports` com `HOSPITAL_FIELD_LIMIT = 4000`,
  `PART_TARGET = 3900`, `MAX_PART_BUTTONS = 4`,
  `shouldOpenCopyDialog(raw)`, `splitDailyNoteIntoParts(raw)`)
- `assets/js/clipboard-utils.js` (novo)
- `assets/js/dailynote-copy.js` (novo)
- `assets/index.js`
- `apps/events/templates/events/partials/event_card_dailynote.html`
- `static/main-bundle.js` (rebuild via `npm run build` no host)

## Tests to write FIRST (TDD)

Esperado no RED:

- `node apps/dailynotes/tests/dailynote_chunks_harness.cjs` FALHA
  (módulo `assets/js/dailynote-chunks.js` ainda não existe).
- `test_final_dailynote_card_renders_dailynote_copy_button` FALHA.
- `test_draft_dailynote_card_renders_dailynote_copy_button` FALHA.
- `test_simplenote_card_keeps_generic_copy_button` PASSA desde o início
  (é guarda de regressão do comportamento atual, não comportamento
  novo).

Fixtures obrigatórias do harness (ver design.md, "Test Strategy"):
4.000 e 4.001 exatos; bruto > 4.000 que normaliza para <= 4.000 (CRLF);
nota multi-parágrafo; parágrafo único > 4.000 (linha, sentença e corte
duro, separadores preservados); conteúdo só de whitespace (zero
partes); cinco parágrafos de 3.000 (cap de 4 botões com conteúdo
descoberto); nota > 16.000; invariante de remontagem em todas as
fixtures.

## Implementation steps

1. Escrever harness `.cjs` + wrapper `.py`; rodar o harness no host:
   RED.
2. Escrever `test_card_copy_dialog.py`; rodar
   `./scripts/test.sh apps.dailynotes.tests.test_card_copy_dialog`:
   dois testes RED, guarda SimpleNote verde.
3. Implementar `assets/js/dailynote-chunks.js` conforme o algoritmo
   normativo do design.md (decisão por comprimento bruto separada da
   fragmentação; retorno único
   `{ parts, totalLength, coveredLength, uncoveredLength }`; unidades
   com separadores preservados `"\n\n"` / `"\n"` / `" "` / `""`;
   preenchimento greedy até 3.900; cap de 4 partes):
   harness GREEN.
4. No card da dailynote, trocar apenas a classe hook do botão de
   copiar: `copy-content-btn` -> `copy-dailynote-btn` (mantém
   `data-content`, tooltip e ícones; não tocar nos demais botões):
   testes de template GREEN.
5. Extrair `showToast` e `showClipboardFeedback` (verbatim) de
   `assets/index.js` para `assets/js/clipboard-utils.js`; derivar
   `copyTextToClipboard(text)` do corpo do `copyToClipboard(button)`
   existente, mantendo o adaptador de feedback no fluxo genérico.
6. Criar `assets/js/dailynote-copy.js`: listener delegado para
   `.copy-dailynote-btn`, cópia direta quando `shouldOpenCopyDialog` é
   falso, dialog Bootstrap 5 construído sob demanda (labels, contadores
   pt-BR via `toLocaleString("pt-BR")`, estados de copiado com reset na
   reabertura, aviso de conteúdo descoberto nomeando total e coberto,
   menção à capacidade de 16.000 quando o total exceder, texto só via
   `textContent`).
7. Importar e chamar `initDailyNoteCopy()` em `assets/index.js` no
   `DOMContentLoaded`.
8. Rodar `npm run build` no host e conferir que
   `static/main-bundle.js` foi regenerado com o novo código.
9. Rodar todas as verificações abaixo.

## Verification commands

- `node apps/dailynotes/tests/dailynote_chunks_harness.cjs`
- `./scripts/test.sh apps.dailynotes.tests.test_card_copy_dialog`
- `./scripts/test.sh apps.dailynotes`
- `./scripts/test.sh apps.events.tests.test_card_attribution_card_partials`
- `npm run build` (host; sem warnings novos)

## Browser evidence (após GREEN)

Usar Chrome DevTools MCP contra `http://127.0.0.1:8779` (usuários
descartáveis do harness do skill `verify-eqmd`; `npm run doctor` +
`npm run setup` a partir de `.pi/skills/verify-eqmd/harness/`):

1. Nota curta (<= 4.000): clique copia direto, toast aparece, nenhum
   dialog.
2. Nota longa (> 4.000, vários parágrafos): dialog abre; contadores
   <= 4.000 por parte; clicar P1 e P2 alterna os estados de copiado;
   "Copiar tudo" escreve o conteúdo bruto.
3. Nota com um único parágrafo > 4.000: dialog abre com todas as
   partes <= 4.000.
4. Cinco parágrafos de 3.000: aviso nomeia total (15.000) e coberto;
   4 botões de parte.
5. Nota > 16.000: aviso adicional cita a capacidade de 16.000;
   "Copiar tudo" presente.
6. Fechar e reabrir o dialog: estados de copiado resetam.
7. Falha de clipboard (stub de `navigator.clipboard.writeText`
   rejeitando): toast de erro, sem estado de copiado.
8. Card de outro tipo (simplenote): clique copia direto, sem dialog.
9. Hard reload: o bundle novo é servido (sem cache obsoleto do service
   worker).

Capturar screenshots/evidence para cada passo.
