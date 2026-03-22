# Slice 01 - HistoryAndPhysicalForm hardening

Goal:
Corrigir persistência de descrição canônica e remover side effect de debug no form.

Scope boundaries:
- Included: `HistoryAndPhysicalForm` + testes de form/model relacionados.
- Excluded: refator amplo de views/templates.

Files to create/modify:
- apps/historyandphysicals/forms.py
- apps/historyandphysicals/tests/test_models_forms.py

Tests to write FIRST (TDD):
- test_form_save_sets_canonical_description
- test_form_init_has_no_debug_stdout

Implementation steps:
1) Garantir `instance.description` canônica no `save()` do form.
2) Remover `print` no `__init__`.
3) Ajustar testes para cobrir comportamento esperado.

Verification commands:
- ./scripts/test.sh apps.historyandphysicals.tests.test_models_forms
