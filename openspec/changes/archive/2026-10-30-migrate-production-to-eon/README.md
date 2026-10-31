# Change: migrate-production-to-eon

Etapa 1 da migração da produção EQMD para o eon: artefatos
implantáveis e ensaio local. Execução produtiva permanece gated.

## Navegação

- `proposal.md` — por quê, o que muda, escopo e não-objetivos.
- `design.md` — decisões técnicas D1–D13, riscos e slices.
- `tasks.md` — 7 grupos de tarefas (um por slice).
- `specs/eon-migration/spec.md` — requisitos verificáveis.

## Regras de execução

- Um slice por vez (worker OpenCode2; revisão independente Pi).
- Slice docs são endurecidos e versionados em `slices/` imediatamente
  antes do dispatch de cada slice.
- Artefatos de produção (eon, origem, DNS, Cloudflare, Caddy real)
  exigem gate humano por comando exato, separado desta change.
- Evidências em `temp/migracao-eon/`; decisões do operador em
  `temp/migracao-eon/decisoes-operador-2026-10-30.md`.
