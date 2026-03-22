## Why

O piloto da semana 1 precisa exercitar o workflow DevLoop de ponta a ponta em um app de baixo risco (`simplenotes`) antes de avançar para apps mais críticos.

Durante a avaliação inicial, o `simplenotes` mostrou oportunidades de hardening com baixo impacto:
- correção de comportamento de formulário (descrição padrão do evento)
- remoção de side effect de debug (`print`) no form
- aumento de cobertura de testes no fluxo CRUD básico

Esse change valida o processo (OpenSpec + slices + TDD + stop rule) e entrega uma melhoria técnica real no app piloto.

## What Changes

- Corrigir `SimpleNoteForm.save()` para garantir descrição padrão consistente do evento.
- Remover output de debug no `SimpleNoteForm.__init__`.
- Adicionar testes focados em:
  - comportamento do form (descrição/created_by/updated_by)
  - fluxo mínimo de criação/edição/remoção com permissões já existentes
- Executar o fluxo por slices verticais com TDD.

## Capabilities

### New Capabilities
- Nenhuma capacidade funcional nova para usuário final.

### Modified Capabilities
- `simplenotes`: estabilidade e previsibilidade no fluxo de criação/edição por formulário.

## Impact

- Mudanças localizadas em `apps/simplenotes` (forms, testes e eventualmente views auxiliares).
- Sem migração de banco.
- Sem alteração de contrato externo/API pública.
