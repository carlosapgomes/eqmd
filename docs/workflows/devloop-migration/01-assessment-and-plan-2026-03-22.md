# Relatório de Avaliação + Plano de Adoção DevLoop

Data: 2026-03-22  
Escopo: avaliação do repositório `eqmd` e plano incremental de migração de workflow

## 1. Resumo executivo

O `eqmd` já possui elementos importantes (OpenSpec, AGENTS, testes em vários apps), mas o processo de desenvolvimento ainda está heterogêneo. Isso aumenta o receio de mudança e o risco de regressão, especialmente em áreas de alta centralidade (`core`, `patients`, `events`, `mediafiles`).

Conclusão: **o caminho recomendado é adoção gradual por app, começando por `simplenotes`, com gates progressivos, TDD e slices verticais.**

## 2. Diagnóstico técnico (estado atual)

### 2.1 Escala e complexidade

- Python (`apps + config`): **569 arquivos**, ~**112k LOC**
- Test files (`apps/**/tests`): **179**
- Arquivos grandes:
  - **58** arquivos > 300 linhas
  - **33** arquivos > 450 linhas
- Funções longas:
  - **93** funções > 60 linhas
- Hotspots:
  - `apps/mediafiles/views.py` (~2137 linhas)
  - `apps/patients/views.py` (~1635)
  - `apps/mediafiles/models.py` (~1260)
  - `apps/patients/models.py` (~1083)

### 2.2 Acoplamento entre apps

- Imports cruzados entre apps com ciclos relevantes.
- Núcleo com maior centralidade: `core`, `patients`, `events`.
- SCCs (ciclos) importantes:
  - `core`, `patients`, `events`, `dailynotes`, `drugtemplates`, `outpatientprescriptions`, `pdfgenerator`, `sample_content`
  - `accounts`, `botauth`, `matrix_integration`

### 2.3 Qualidade e padrões

- Padrões definidos existem, mas há divergência de execução (ex.: `ruff` definido como padrão, ainda sem integração prática no repositório atual).
- Typing ainda em rollout:
  - baixa cobertura de anotações em funções do código de produção.

### 2.4 Testes e qualidade

- Snapshot de cobertura disponível (`htmlcov`) indica **14%** (snapshot histórico, precisa refresh no pipeline atual).
- Há testes placeholders (`pass`) concentrados em `mediafiles`.
- Estratégia de testes mista (Django test runner + pytest), ainda sem gate CI totalmente consolidado.

### 2.5 Aderência ao baseline DevLoop

Já presente:
- `AGENTS.md`
- `openspec/`

Faltava/alvo de ajuste:
- `PROJECT_CONTEXT.md`
- `docs/adr/`
- `docs/releases/`
- convenções de gate/CI mais rigorosas e previsíveis

## 3. Decisões de processo (acordadas)

- Solo dev
- `main` protegida com PR + checks
- Docker-first para reduzir drift Linux/Mac
- Release semanal (sexta)
- Conventional commits obrigatórios
- Piloto em `simplenotes`
- Adoção progressiva (sem big-bang)

## 4. Definição de smoke obrigatório

**Smoke obrigatório** = suíte pequena e rápida, executada em todo PR para detectar quebra de fluxos essenciais.

Proposta inicial (calibrar nos primeiros 7-14 dias):
- `accounts` (auth/base)
- `core` (urls/permissões essenciais)
- `patients` (fluxo base)
- `events` (evento base)

Além do smoke, todo PR roda testes do app alterado.

## 5. Plano 30/60/90 dias

## 0–30 dias — Fundação + Piloto

Objetivo:
- consolidar baseline DevLoop e provar workflow completo em `simplenotes`.

Entregáveis:
1. Estrutura DevLoop mínima padronizada.
2. CI v1 com gates progressivos.
3. 1 change piloto completo (`simplenotes`) com OpenSpec + slices + TDD + stop rule.

Métricas:
- 100% PR com commit convencional
- 100% PR com smoke obrigatório verde
- 1 change piloto encerrado e arquivado

## 31–60 dias — Consolidação

Objetivo:
- expandir padrão para apps de menor/médio risco.

Ordem sugerida:
- `historyandphysicals` -> `sample_content` -> `dischargereports` -> `reports`

Entregáveis:
- checklist PR consolidado
- ADRs para decisões estruturais
- release semanal previsível

Métricas:
- >=80% dos changes não-triviais com OpenSpec completo
- queda de retrabalho em regressões básicas

## 61–90 dias — Escala para hotspots

Objetivo:
- entrar em `patients/events/mediafiles/core` com segurança incremental.

Estratégia:
- refator por fatias verticais
- extração de serviços por oportunidade
- aumento de cobertura por zona tocada

Métricas:
- redução de regressões pós-release
- menor tempo de diagnóstico
- redução gradual de arquivos/funções gigantes nas áreas tocadas

## 6. Riscos e mitigação

1. **Gate muito rígido no início bloquear fluxo**
   - Mitigação: CI em 2 trilhos (obrigatório vs informativo).

2. **Refator amplo demais causar regressão**
   - Mitigação: slices pequenos + stop rule + rollback simples.

3. **Inconsistência de processo ao longo do tempo**
   - Mitigação: checklist único de PR + revisão semanal de processo.

## 7. Próximos passos práticos

1. Operar com o checklist de PR deste pacote.
2. Aplicar convenções de branch/commit.
3. Rodar CI conforme matriz de comandos (v1).
4. Abrir primeiro change piloto de `simplenotes`.

---

Documento base para execução da migração de workflow no `eqmd`.
