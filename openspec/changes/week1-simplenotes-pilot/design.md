## Context

Este change é o piloto técnico-operacional da semana 1 para validar a adoção do workflow DevLoop no `eqmd` em um app de baixo risco.

A intenção é combinar:
1) melhoria de qualidade de código (bugfix e limpeza)
2) melhoria de segurança de mudança (testes e fatias pequenas)
3) execução disciplinada (OpenSpec, TDD, stop rule)

## Goals / Non-Goals

**Goals**
- Garantir que `SimpleNoteForm.save()` persista descrição padrão do evento de forma determinística.
- Remover side effect de debug no form.
- Aumentar cobertura do fluxo essencial de `simplenotes` com testes de comportamento.
- Executar em slices pequenos, cada slice com verificação explícita.

**Non-Goals**
- Não refatorar toda a arquitetura de `simplenotes`.
- Não alterar regras de permissão globais.
- Não mexer em apps fora do escopo (exceto ajustes mínimos de integração estritamente necessários).

## Decisions

1) **Descrição padrão no form, não na view**
   - **Decision:** manter a regra de descrição no `SimpleNoteForm.save()`.
   - **Rationale:** centraliza regra no ponto de persistência do form e evita duplicação em views.
   - **Alternative rejeitada:** setar descrição separadamente em cada view.

2) **Remoção de print de debug**
   - **Decision:** remover saída de console do `__init__` do form.
   - **Rationale:** elimina ruído em logs/testes e evita side effects em execução normal.

3) **Cobertura de testes orientada a risco**
   - **Decision:** priorizar testes que protegem o fluxo de criação/edição e o bugfix de descrição.
   - **Rationale:** melhor retorno na semana 1 com escopo pequeno.

## Risks / Trade-offs

- **[Mudança pontual pode não cobrir todo CRUD]** → Mitigação: foco em caminhos essenciais + ampliar em semanas seguintes.
- **[Diferenças de execução local/CI]** → Mitigação: usar comandos canônicos (`./scripts/test.sh`, `./scripts/typecheck.sh`) e validar no PR.

## Verification Plan

- Smoke obrigatório do PR (CI):
  - `apps.accounts.tests.test_models`
  - `apps.core.tests.test_urls`
  - `apps.patients.tests.test_models`
  - `apps.events.tests.test_record_tracking_events`
- Testes do app alterado:
  - `./scripts/test.sh apps.simplenotes`
- Typecheck escopado:
  - `./scripts/typecheck.sh apps/simplenotes`

## Rollback Plan

- Reverter commits do change piloto (escopo local e sem migração).
- Reexecutar smoke + testes de app para confirmar restauração.
