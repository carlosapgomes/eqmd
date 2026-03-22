# Checklist de PR (DevLoop - eqmd)

Use este checklist em **todo PR**.

## 1) Planejamento

- [ ] Change classificado por risco (`QUICK`, `FEATURE`, `HIGH`)
- [ ] OpenSpec criado/atualizado conforme risco
- [ ] Escopo do PR está claro e pequeno (1 slice vertical por vez)

## 2) TDD + Slice

- [ ] RED: existe teste representando comportamento/bug
- [ ] GREEN: implementação mínima para passar
- [ ] REFACTOR: limpeza sem quebrar testes
- [ ] Não houve scope creep (sem mudanças fora do slice)

## 3) Validação obrigatória (PR)

- [ ] Smoke obrigatório passou
- [ ] Testes do app alterado passaram
- [ ] Typecheck do escopo alterado passou
- [ ] Lint do escopo alterado passou (quando habilitado no CI)

## 4) Evidência e rastreabilidade

- [ ] Mensagens de commit em Conventional Commits
- [ ] Tasks/OpenSpec atualizados com status real
- [ ] PR descreve claramente impacto, risco e rollback

## 5) Stop Rule

- [ ] Slice concluído e validado
- [ ] Commit e push realizados
- [ ] Próximo slice **não** iniciado automaticamente

---

## Template de descrição de PR

```md
## Contexto
- Change ID:
- Risco: QUICK | FEATURE | HIGH

## O que foi feito
- 

## O que NÃO foi feito
- 

## Verificação
- Smoke:
- Testes app alterado:
- Typecheck escopo:
- Lint escopo:

## Rollback
- 

## Evidências
- OpenSpec:
- Commits:
```
