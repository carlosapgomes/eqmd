## Context

Este change aplica o mesmo padrão técnico-operacional validado no piloto da semana 1 (`simplenotes`) para o app `historyandphysicals`.

Objetivo: fortalecer previsibilidade de comportamento no form e aumentar cobertura do fluxo essencial, mantendo escopo pequeno e risco controlado.

## Goals / Non-Goals

**Goals**
- Garantir que o form persista a descrição canônica do evento (`HISTORY_AND_PHYSICAL_EVENT`).
- Eliminar side effect de debug em inicialização de formulário.
- Reforçar testes de fluxo essencial (create/update/delete) conforme regras atuais de permissão.
- Executar o change em slices com TDD (RED/GREEN/REFACTOR).

**Non-Goals**
- Não reescrever arquitetura de views do app.
- Não alterar política global de permissões do projeto.
- Não introduzir novas features de produto.

## Decisions

1) **Descrição canônica no form**
- **Decision:** manter e garantir a regra de descrição no `HistoryAndPhysicalForm.save()`.
- **Rationale:** centraliza comportamento no ponto de persistência e reduz divergência entre views.

2) **Sem debug stdout em produção/testes**
- **Decision:** remover `print` do `__init__` do form.
- **Rationale:** evitar ruído e side effects em testes/CI.

3) **Cobertura de testes por risco real**
- **Decision:** priorizar testes de create/update/delete e cenários mínimos de permissão.
- **Rationale:** maior retorno com baixo risco na semana 2.

## Risks / Trade-offs

- **[Testes podem depender de comportamentos legados implícitos]** → Mitigação: explicitar expectativas com asserts diretos.
- **[Escopo pode crescer para refator amplo]** → Mitigação: limitar mudanças aos arquivos do slice.

## Verification Plan

- `./scripts/test.sh apps.historyandphysicals`
- `./scripts/typecheck.sh apps/historyandphysicals`

## Rollback Plan

- Reverter commits do change.
- Reexecutar testes do app + typecheck escopado para confirmar restauração.
