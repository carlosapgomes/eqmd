# Slice 03 - Fechamento da semana 2

## Goal

Fechar o change com validação final e evidências atualizadas.

## Scope boundaries

- Included: validação final, atualização de log e tasks
- Excluded: novas features

## Files to create/modify

- `docs/workflows/devloop-migration/progress-log.md`
- `openspec/changes/week2-historyandphysicals-hardening/tasks.md`
- `openspec/changes/week2-historyandphysicals-hardening/slices/slice-03-prompt.md`

## Implementation steps

1. Rodar validações finais do app.
1. Atualizar evidências no progress log.
1. Marcar tasks concluídas e preparar sync/archive.

## Verification commands

- `./scripts/test.sh apps.historyandphysicals`
- `./scripts/typecheck.sh apps/historyandphysicals`
