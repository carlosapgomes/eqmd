# Slice 01 — Extract plan and review modules, executor stays as facade

## Handoff para implementador LLM (contexto zero)

Repositório `eqmd` (Django 5.2, PostgreSQL). Leia: `AGENTS.md`,
`PROJECT_CONTEXT.md`,
`openspec/changes/split-consolidation-service-module/{proposal.md,design.md,tasks.md}`
e este slice.

Estado atual:
`apps/patients/services/patient_record_consolidation.py` (396 linhas)
concentra parse/validação de planos, revisão/skeleton clínico e
executor com marcadores void. Importadores do módulo (NÃO devem ser
editados): `apps/patients/management/commands/consolidate_record_numbers.py`,
`apps/patients/services/consolidation_prefill.py`,
`apps/patients/tests/test_record_consolidation.py`,
`apps/patients/tests/test_consolidation_review.py`.

Objetivo: mover código verbatim para dois módulos novos
(`consolidation_plan.py`, `consolidation_review.py`), deixar o
executor no módulo original que vira facade com `__all__`, anotar
tipos para strict-clean. Zero mudança de comportamento.

Limite de escopo: NENHUMA edição fora de `apps/patients/services/`.
Sem alterar mensagens, formato de marcador, transações ou ordenação.

## Requisitos

- R1 `consolidation_plan.py` contém exatamente os itens da tabela D1
  (design), movidos verbatim, com docstring de módulo própria.
- R2 `consolidation_review.py` idem (itens de revisão/skeleton).
- R3 `patient_record_consolidation.py` mantém executor + facade:
  re-exporta toda a superfície anterior via imports explícitos +
  `__all__` (ver D2). Importadores permanecem byte-idênticos.
- R4 `mypy --strict` limpo nos três módulos (anotações: `operator:
    AbstractBaseUser`; generics `dict[str, Any]`/`list[object]`
  onde hoje são `dict`/`list` nus).
- R5 Suíte completa verde com a MESMA contagem (2753) — prova de
  pureza comportamental.

## Arquivos esperados

1. `apps/patients/services/consolidation_plan.py` (novo)
2. `apps/patients/services/consolidation_review.py` (novo)
3. `apps/patients/services/patient_record_consolidation.py` (reduzido)

Nenhum outro arquivo. Se tocar outro, justifique no relatório.

## Metodologia (refactor TDD-guarded)

- GUARD antes: `./scripts/test.sh apps.patients` verde;
  `git status` limpo.
- MOVE: blocos verbatim por responsabilidade (D1); só import blocks,
  docstrings e anotações mudam.
- PROVA depois: gates abaixo.

## Critérios de sucesso (binário)

- [ ] `git diff --name-only` mostra SOMENTE os 3 arquivos de services.
- [ ] `./scripts/test.sh` → OK, 2753 testes, 25 skips.
- [ ] `./scripts/typecheck.sh apps/patients/services` → limpo.
- [ ] `docker exec eqmd_dev mypy --strict` nos 3 módulos → 0 erros.
- [ ] `docker exec eqmd_dev ruff check` + `ruff format --check` nos
      3 arquivos → limpos.
- [ ] `rg 'from apps.patients.services.patient_record_consolidation
    import' apps/` inalterado (importers intactos).

## Gates de autoavaliação (responda no relatório)

1. Alguma função foi REESCRITA (não movida)? Qual e por quê?
2. O `__all__` cobre 100% dos nomes que os importadores usam? Liste
   o cruzamento.
3. Por que não houve import circular? Desenhe a direção das setas.
4. A contagem de testes mudou? Por quê (não deveria)?

## Relatório obrigatório

`/tmp/split-consolidation-service-module-slice-01-report.md` com:
guard antes/depois (saídas), diff resumido por arquivo
(+linhas/−linhas), provas dos gates, respostas, justificativas.

## Prompt pronto

```text
Read AGENTS.md, PROJECT_CONTEXT.md and
openspec/changes/split-consolidation-service-module/{proposal.md,design.md,tasks.md,slices/slice-01.md}
first. Implement ONLY slice-01 as a pure refactor: verbatim moves per
design D1, facade with __all__ per D2, type annotations per D4. Touch
ONLY the 3 files in services/. Do not rewrite logic, messages,
markers, or transactions. Prove purity: git diff shows only the 3
files; full suite green with the same count (2753); mypy --strict
clean on the 3 modules; ruff clean. Update tasks.md (mark 1.1) only
after all gates pass. Create /tmp/split-consolidation-service-module-slice-01-report.md
with guard outputs, per-file diff summary, gate proofs, self-eval
answers. Reply with REPORT_PATH=<path>, commit and push, then STOP
for planner review.
```
