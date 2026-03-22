# Migração de Workflow para DevLoop (eqmd)

Este diretório centraliza a migração gradual do `eqmd` para o workflow do **DevLoop**.

## Objetivo

Reduzir risco de regressão, aumentar previsibilidade de entrega e melhorar mantenabilidade com:

- OpenSpec por change
- slices verticais
- TDD (RED/GREEN/REFACTOR)
- quality gates progressivos
- convenções de branch/commit/PR

## Documentos

1. [`01-assessment-and-plan-2026-03-22.md`](./01-assessment-and-plan-2026-03-22.md)
   - diagnóstico técnico inicial
   - riscos principais
   - plano 30/60/90 dias

2. [`02-pr-checklist.md`](./02-pr-checklist.md)
   - checklist operacional para PR (solo-dev)

3. [`03-branch-and-commit-conventions.md`](./03-branch-and-commit-conventions.md)
   - padrão de branches
   - conventional commits
   - padrões de naming

4. [`04-ci-command-matrix.md`](./04-ci-command-matrix.md)
   - matriz de comandos obrigatórios vs informativos
   - estratégia progressiva de gate

5. [`progress-log.md`](./progress-log.md)
   - log de progresso semanal da migração
   - evidências, métricas e próximos passos

## Governança

- Atualizar estes documentos junto com ajustes de processo.
- Em caso de conflito, prevalece:
  1) tooling/CI em execução
  2) `docs/workflows/coding-standards.md`
  3) este pacote de migração

---

Última atualização: 2026-03-22
