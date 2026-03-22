# Slice 02 - CRUD safety net mínimo de views

## Goal

Reforçar cobertura de create/update/delete essencial com foco em risco baixo.

## Scope boundaries

- Included: testes de integração/views do app
- Excluded: mudanças funcionais fora do escopo do app

## Files to create/modify

- `apps/historyandphysicals/tests/test_integration.py`
- `apps/historyandphysicals/tests/test_permissions.py` (se necessário)

## Tests to write FIRST (TDD)

- `test_create_historyandphysical_for_accessible_patient`
- `test_update_historyandphysical_allowed_for_creator_within_window`
- `test_delete_historyandphysical_denied_when_permission_fails`

## Implementation steps

1. Adicionar/ajustar testes para fluxo essencial.
1. Ajustar implementação apenas se necessário para atender comportamento
   esperado.

## Verification commands

- `./scripts/test.sh apps.historyandphysicals`
