# Matriz de Comandos de CI (adoção progressiva)

Objetivo: aumentar rigor sem travar evolução do brownfield.

## Fase inicial (v1) — recomendada agora

## A) Gate obrigatório no PR

### 1. Smoke obrigatório (sempre)

Rodar este comando em todo PR:

```bash
./scripts/test.sh \
  apps.accounts.tests.test_models \
  apps.core.tests.test_urls \
  apps.patients.tests.test_models \
  apps.events.tests.test_record_tracking_events
```

> Este é o **smoke v1 oficial**. A ideia é detectar regressões óbvias nos fluxos-base sem custo de suíte completa.

### 2. Testes do app alterado (sempre)

Exemplos:

```bash
./scripts/test.sh apps.simplenotes
./scripts/test.sh apps.pdf_forms
./scripts/test.sh apps.mediafiles
```

### 3. Typecheck do escopo alterado (sempre)

Exemplos:

```bash
./scripts/typecheck.sh apps/simplenotes
./scripts/typecheck.sh apps/pdf_forms/services
```

### 4. Lint do escopo alterado (sempre, quando habilitado)

Status atual:
- padrão documental já define `ruff`
- integração de lint bloqueante no CI deve ser feita em PR específico de tooling

Comando alvo quando habilitado no container:

```bash
docker exec eqmd_dev ruff check apps/simplenotes
```

## B) Informativo (não bloqueante no início)

### 1. Suite completa de testes

```bash
./scripts/test.sh
```

### 2. Cobertura global (snapshot de tendência)

Executar em job informativo para acompanhar evolução sem bloquear entrega.

### 3. Checks adicionais (opcional)

- typecheck mais amplo
- métricas de dívida técnica

---

## Fase madura (v2) — alvo

Tornar **bloqueante**:
- smoke obrigatório
- testes do app alterado
- typecheck escopo
- lint escopo
- suite completa

---

## Exemplo de sequência para PR (local/CI)

```bash
# 1) smoke fixo
./scripts/test.sh \
  apps.accounts.tests.test_models \
  apps.core.tests.test_urls \
  apps.patients.tests.test_models \
  apps.events.tests.test_record_tracking_events

# 2) app alterado
./scripts/test.sh apps.simplenotes

# 3) typecheck escopo
./scripts/typecheck.sh apps/simplenotes
```

---

## Convenções operacionais

- Ambiente padrão: Docker (`eqmd_dev`) para reduzir drift Linux/Mac no desenvolvimento local.
- No GitHub Actions, os gates equivalentes rodam via `uv run python manage.py test ...`.
- Workflow implementado em: `.github/workflows/ci-pr.yml`.
- PR **somente de documentação** faz short-circuit do job obrigatório (passa sem rodar smoke/test/typecheck pesado).
- PR pequeno por slice vertical.
- Falha de gate obrigatório = sem merge.

## Observações importantes

1. Não misturar mudança funcional grande com setup de tooling no mesmo PR.
2. Primeiro estabilizar o smoke v1; depois endurecer gates.
3. Revisar mensalmente duração dos jobs para manter feedback rápido.
