## 1. Preparação do piloto (OpenSpec + escopo)

- [x] 1.1 Validar escopo exato do piloto (sem scope creep)
- [x] 1.2 Confirmar arquivos-alvo do slice 1
- [x] 1.3 Confirmar comandos de verificação (test/typecheck)

## 2. Slice 1 — Form hardening (bugfix + limpeza)

- [x] 2.1 Escrever testes RED para descrição padrão no `SimpleNoteForm.save()`
- [x] 2.2 Corrigir persistência da descrição padrão
- [x] 2.3 Remover `print` de debug do form
- [x] 2.4 Validar `./scripts/test.sh apps.simplenotes`

## 3. Slice 2 — CRUD safety net mínimo

- [x] 3.1 Adicionar testes de view para fluxo essencial (create/update/delete)
- [x] 3.2 Garantir cobertura de permissões mínimas esperadas no app
- [x] 3.3 Validar `./scripts/test.sh apps.simplenotes`

## 4. Slice 3 — Fechamento da semana 1

- [x] 4.1 Rodar typecheck escopado (`./scripts/typecheck.sh apps/simplenotes`)
- [x] 4.2 Atualizar `docs/workflows/devloop-migration/progress-log.md`
- [x] 4.3 Registrar evidências do piloto no PR
- [ ] 4.4 Arquivar/sincronizar change OpenSpec ao concluir piloto (pendente pós-merge do slice 3)
