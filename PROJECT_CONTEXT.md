# PROJECT_CONTEXT.md

## Proposito

Resumo executivo para retomada rápida após pausas e para onboarding de novos
contribuidores.

## Fontes Autoritativas

- `AGENTS.md`
- `README.md`
- `openspec/specs/`
- `docs/adr/`
- `docs/releases/`
- Em caso de conflito: specs/artefatos mais recentes no Git prevalecem.

## Objetivo do Sistema

Plataforma Django para colaboração de equipe médica em contexto de hospital
único, com foco em registro e acompanhamento longitudinal do cuidado do
paciente.

## Arquitetura de Alto Nivel

- **apps** (`apps/`): módulos de domínio/aplicação (accounts, patients,
  events, simplenotes, historyandphysicals etc.).
- **config** (`config/`): settings, URLs globais e bootstrap do Django.
- **templates/static/assets** (`templates/`, `static/`, `assets/`): camada de
  apresentação.
- **docs** (`docs/`): documentação técnica, workflow e governança.
- **openspec** (`openspec/`): especificações de mudanças e histórico arquivado.
- **scripts** (`scripts/`): automações operacionais (testes, typecheck, lint,
  utilitários).

## Regras Nao Negociaveis

- Não quebrar contratos públicos sem mudança versionada e evidenciada.
- Toda mudança relevante deve deixar trilha no Git (OpenSpec/tasks/commit/PR).
- Mudanças devem respeitar slices pequenos com stop rule explícita.
- Evitar scope creep: executar apenas o slice combinado em cada iteração.

## Quality Bar

- Testes relevantes executam localmente antes de merge.
- Lint e checks estáticos sem erros críticos no escopo alterado.
- Typecheck no escopo alterado quando aplicável.
- Markdown lint para artefatos `.md` tocados no change.
- Mudanças de risco médio/alto devem incluir plano de rollback.

<!-- generated-by: project-context-maintainer -->
