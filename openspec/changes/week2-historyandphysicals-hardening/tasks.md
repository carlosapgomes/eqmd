## 1. Preparação

- [ ] 1.1 Confirmar escopo do change (sem scope creep)
- [ ] 1.2 Confirmar arquivos do slice 1
- [ ] 1.3 Confirmar comandos de validação do app

## 2. Slice 1 — Form hardening

- [ ] 2.1 Escrever testes RED para descrição canônica no `HistoryAndPhysicalForm.save()`
- [ ] 2.2 Corrigir persistência da descrição canônica
- [ ] 2.3 Remover debug `print` do form
- [ ] 2.4 Validar `./scripts/test.sh apps.historyandphysicals.tests.test_models_forms`

## 3. Slice 2 — CRUD safety net mínimo

- [ ] 3.1 Adicionar/ajustar testes de views para create/update/delete essenciais
- [ ] 3.2 Cobrir cenário mínimo de permissão negada
- [ ] 3.3 Validar `./scripts/test.sh apps.historyandphysicals`

## 4. Slice 3 — Fechamento da semana 2

- [ ] 4.1 Rodar `./scripts/typecheck.sh apps/historyandphysicals`
- [ ] 4.2 Atualizar `docs/workflows/devloop-migration/progress-log.md`
- [ ] 4.3 Registrar evidências do change no PR
- [ ] 4.4 Sincronizar/arquivar change OpenSpec ao concluir
