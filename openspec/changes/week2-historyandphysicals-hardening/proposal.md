## Why

Após o piloto da semana 1 em `simplenotes`, o próximo passo natural é repetir
o mesmo padrão em outro app de baixo risco para consolidar o workflow DevLoop.

`historyandphysicals` apresenta sinais semelhantes ao que foi tratado no piloto:

- side effect de debug no form (`print` em `__init__`)
- atribuição de descrição canônica potencialmente incorreta no `save()` do form
- necessidade de reforço de testes de fluxo essencial sem ampliar escopo

## What Changes

- hardening do `HistoryAndPhysicalForm` para garantir persistência canônica de
  descrição
- remoção de debug output no form
- ampliação/ajuste de testes no fluxo essencial (create/update/delete), com
  foco nas regras atuais
- execução por slices curtos com TDD e stop rule

## Capabilities

### New Capabilities

- nenhuma nova capacidade funcional para usuário final

### Modified Capabilities

- `historyandphysicals`: maior estabilidade de comportamento no form e maior
  segurança de regressão no CRUD essencial

## Impact

- escopo concentrado em `apps/historyandphysicals` + artefatos OpenSpec
- sem migração de banco
- sem alteração de contrato externo
