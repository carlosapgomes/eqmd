# Progress Log — DevLoop Migration

Registro contínuo de evolução da migração de workflow no `eqmd`.

## Como usar

- Criar **uma entrada por semana** (ou por marco relevante).
- Registrar apenas evidências concretas (o que foi feito, onde está, resultado).
- Relacionar com fases do plano (`01-assessment-and-plan-2026-03-22.md`).

## Template

```md
## YYYY-MM-DD — Semana N

### Fase
- 0–30 | 31–60 | 61–90

### Concluído
- 

### Evidências
- PR(s):
- Commit(s):
- Docs/Arquivos:

### Métricas da semana
- PRs com check obrigatório verde:
- Falhas de smoke:
- Mudanças com OpenSpec completo:

### Próxima semana
- 

### Riscos/Bloqueios
- 
```

---

## 2026-03-22 — Kickoff

### Fase
- 0–30 dias (Fundação + Piloto)

### Concluído
- Pacote de migração DevLoop criado em `docs/workflows/devloop-migration/`.
- Checklist de PR, convenções de branch/commit e matriz de CI publicados.
- Workflow de PR criado em `.github/workflows/ci-pr.yml`.
- Branch padrão ajustada para `main`.
- Status check obrigatório configurado: `Smoke + Scoped Tests + Scoped Typecheck`.

### Evidências
- Docs:
  - `docs/workflows/devloop-migration/README.md`
  - `docs/workflows/devloop-migration/01-assessment-and-plan-2026-03-22.md`
  - `docs/workflows/devloop-migration/02-pr-checklist.md`
  - `docs/workflows/devloop-migration/03-branch-and-commit-conventions.md`
  - `docs/workflows/devloop-migration/04-ci-command-matrix.md`
- CI:
  - `.github/workflows/ci-pr.yml`

### Métricas da semana
- PRs com check obrigatório verde: baseline em formação
- Falhas de smoke: baseline em formação
- Mudanças com OpenSpec completo: pendente piloto `simplenotes`

### Próxima semana
- Executar 1º change piloto em `simplenotes` com OpenSpec + TDD + slices.
- Change iniciado: `openspec/changes/week1-simplenotes-pilot/` (artefatos criados).

### Riscos/Bloqueios
- Necessidade de calibrar duração do smoke v1 e estabilidade dos testes por app.
