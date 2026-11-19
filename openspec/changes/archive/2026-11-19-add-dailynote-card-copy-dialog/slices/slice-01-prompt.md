# Slice Prompt (Implementer LLM)

Você está implementando exatamente UM slice da change
“add-dailynote-card-copy-dialog”. Comece com contexto vazio e siga os
passos:

1. Leia e obedeça: `AGENTS.md` na raiz do repositório.
2. Leia os requisitos:
   `openspec/changes/add-dailynote-card-copy-dialog/specs/dailynote-card-copy/spec.md`
3. Leia o design:
   `openspec/changes/add-dailynote-card-copy-dialog/design.md`
   (em especial as decisões D1–D10, o algoritmo normativo e a seção
   “Dialog UX”).
4. Leia os arquivos do slice:
   - `openspec/changes/add-dailynote-card-copy-dialog/slices/slice-01.md`
   - `openspec/changes/add-dailynote-card-copy-dialog/slices/slice-01-prompt.md`
     (este arquivo)

REGRAS DE ESCOPO ESTRITAS:

- Implemente apenas o que o `slice-01.md` inclui.
- NÃO implemente slices futuros, mesmo que note dependências.
- Leia/modifique apenas os arquivos listados no `slice-01.md`, além dos
  arquivos mínimos de contexto (por exemplo
  `apps/core/tests/page_navigation_loading_harness.cjs`,
  `apps/core/tests/test_page_navigation_loading.py` e
  `webpack.config.js`, somente para leitura).
- Exceção explícita: marcar os checkboxes deste prompt é permitido
  antes de parar; nenhum outro arquivo fora da lista pode ser editado.
- Se faltar informação, PARE e pergunte.

CLEAN CODE (baseline):

- Uma responsabilidade por função/classe.
- Funções <= 25 linhas.
- Nenhuma lógica duplicada; nenhum número mágico (use as constantes
  exportadas 4000/3900/4).
- Sem lógica de negócio em views/controllers.
- Evitar argumentos booleanos de flag; dividir funções.
- Nomes explícitos e descritivos.

GUARDRAILS:

- Nunca execute comandos destrutivos (`rm -rf`, `git reset --hard`, drop
  de banco) sem aprovação explícita.
- Não modifique volumes Docker ou ciclo de vida de containers sem
  aprovação.
- Se uma ação destrutiva ou privilegiada for necessária, PARE e
  pergunte.
- Comandos python/pip/manage.py SEMPRE via `docker exec eqmd_dev`;
  `npm run build` e o harness `.cjs` rodam no host (node via nvm).
- Nenhum commit git.

REGRAS DE PROCESSO:

- TDD estrito (tests first: RED -> GREEN -> REFACT). Os artefatos do
  change já são lint-clean (80 colunas, headings de nível 1); se editar
  qualquer `.md`, rode `npx markdownlint-cli2` nos arquivos alterados e
  corrija antes de parar.
- Verificação com `./scripts/test.sh` e com os comandos listados no
  `slice-01.md`.
- Ao final do slice, execute a auditoria clean-code e corrija violações.
- PARE após concluir este slice (não inicie o próximo).
- Marque os checkboxes abaixo antes de parar.

Comece agora com o slice-01.

## Checklist

### Spec

- [x] requisitos compreendidos

### Tests (RED)

- [x] harness do splitter falhando antes do módulo existir
- [x] dois testes de template falhando; guarda SimpleNote verde
- [x] testes cobrem comportamento e casos de borda

### Implementation (GREEN)

- [x] código mínimo adicionado
- [x] todos os testes passando

### Refactor (CLEAN)

- [x] responsabilidades separadas
- [x] duplicação removida
- [x] funções pequenas
- [x] nomes melhorados

### Verification

- [x] comandos de verificação do slice passando (harness node,
      `./scripts/test.sh`, `npm run build`)

### STOP RULE

- [x] parar aqui e NÃO iniciar o próximo slice
