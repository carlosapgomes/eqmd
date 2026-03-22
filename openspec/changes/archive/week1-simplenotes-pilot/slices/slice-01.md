# Slice 01 - SimpleNoteForm hardening

Goal:
Corrigir o comportamento de persistência da descrição padrão e remover side effect de debug no form.

Scope boundaries:
- Included: `SimpleNoteForm` + testes de form/model relacionados ao bug.
- Excluded: refator amplo de views e templates.

Files to create/modify:
- apps/simplenotes/forms.py
- apps/simplenotes/tests/test_models_forms.py

Tests to write FIRST (TDD):
- test_form_save_sets_canonical_description
- test_form_init_has_no_debug_stdout
- (ajustar testes existentes para refletir comportamento canônico)

Implementation steps:
1) Corrigir `SimpleNoteForm.save()` para setar `instance.description` com valor canônico do evento.
2) Remover `print` no `__init__` do form.
3) Garantir que `created_by` e `updated_by` seguem comportamento atual.

Refactor steps:
- Manter funções pequenas e sem duplicação.
- Evitar lógica de negócio em views.

Verification commands:
- ./scripts/test.sh apps.simplenotes.tests.test_models_forms
