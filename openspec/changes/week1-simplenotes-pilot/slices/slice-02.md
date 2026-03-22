# Slice 02 - CRUD safety net mínimo para simplenotes

Goal:
Adicionar cobertura de testes para fluxo essencial de create/update/delete com permissões atuais.

Scope boundaries:
- Included: testes de views de simplenotes para fluxo essencial.
- Excluded: refator estrutural de views e alterações amplas de permissão.

Files to create/modify:
- apps/simplenotes/tests/test_views.py (novo)
- apps/simplenotes/views.py (somente se necessário para corrigir falhas de teste)

Tests to write FIRST (TDD):
- test_create_simplenote_for_accessible_patient
- test_update_simplenote_allowed_for_creator_within_window
- test_delete_simplenote_denied_when_permission_fails

Implementation steps:
1) Criar testes de view com cenário mínimo de sucesso/falha.
2) Ajustar implementação somente se necessário para tornar comportamento explícito e testável.

Refactor steps:
- Manter escopo estrito no app `simplenotes`.

Verification commands:
- ./scripts/test.sh apps.simplenotes
