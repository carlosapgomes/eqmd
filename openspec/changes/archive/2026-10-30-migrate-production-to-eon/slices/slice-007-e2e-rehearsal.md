# Slice s7 — Ensaio e2e local com tempos medidos

Task refs: `tasks.md` 7.1–7.3 · Change: `migrate-production-to-eon`.

## Objetivo

Executar no Zen, com dados sintéticos, o ciclo completo da migração
usando os artefatos aceitos (compose real, init SQL, restore, E4,
gates) — expondo defeitos de integração AGORA, não no eon — e medir
os tempos por etapa para dimensionar a janela de 8h.

## Desenho do ensaio

- **Fase A (origem sintética)**: projeto compose descartável
  `-p eqmd_s7_rehearsal` com redes locais de nomes EXATOS
  (`hospital_{ingress,app,db,egress}_eqmd`) e os CIDRs RESERVADOS
  (<CIDR_RESERVA_EQMD>); `up postgres` (init SQL), ops `migrate` (migrator),
  seed sintético (SQL respeitando FK; mídia sintética com hashes),
  `up` completo, gates funcionais.
- **Exportação**: dump `pg_dump -Fc` + tar de mídia + manifesto
  sha256 (padrões do runbook) → staging local ("transferência"
  simulada por cópia; limite declarado).
- **Fase B (destino limpo)**: `down -v`, re-`up` do zero, E4 em 3
  gates (init prepare → restore+extração UID 9900 → remap), prova de
  no-op do `migrate --plan`, stack completa, gates funcionais:
  health 200, `/static/` + `sw.js` no-cache + manifest via frontend,
  contagens A==B, hashes de mídia A==B, roles não-super, ownership
  migrator, extensões ativas.
- **Cronometragem**: cada etapa medida → `timings.json` + tabela.
- **Imagens**: pulls exatos dos digests pinados (ghcr `fe31d296`,
  postgres `1d1095b0`, nginx `51047bea`) — consumo read-only de
  artefatos de registry no Docker local, padrão já estabelecido.

## Entregáveis (apenas estes)

1. `scripts/tests/test_e2e_rehearsal.mjs` — orquestrador
   (node:test-style com main runner): nomes exatos + abort em conflito
   - cleanup garantido (projeto, volumes, redes, staging); asserções
     acima; tempos por etapa; runtime alvo < 30 min; timeout por etapa.
2. `deploy/eon/cutover/rehearsal-baseline.md` — tabela de tempos
   medidos com escala (dados sintéticos × produção: db 1,7 GB /
   mídia 76 MB reais), limites do ensaio (7.3: sem rede real do eon,
   sem DNS/Cloudflare, sem fluxos clínicos autenticados, sem
   vizinhas) e o que SÓ pode ser validado no destino (checklist
   operador, redirect, cron real, backup restaurado em produção).
   Os placeholders `<TEMPO_s7_*>` do runbook PERMANECEM (números
   reais virão do ensaio da fase C com dados reais).
3. Evidências em `temp/migracao-eon/s7/`: logs por etapa,
   `timings.json`, manifesto, saída `verify-restore.sql`, provas.
4. **Fixes de integração permitidos** (só se o ensaio expuser
   defeito): `docker-compose.eon.yml`, `env.eon.example`,
   `deploy/eon/init/*`, `deploy/eon/frontend/nginx.conf` — cada um
   documentado no worker_done com gates re-executados verdes. Nada
   além disso.

## Verificação (comandos exatos)

```bash
node scripts/tests/test_e2e_rehearsal.mjs
node --test scripts/tests/test_compose_eon.mjs \
  scripts/tests/test_cutover_docs.mjs
markdownlint-cli2 deploy/eon/cutover/rehearsal-baseline.md
```

## Restrições

- Nenhum acesso a eon/origem; redes com nomes reais existem SÓ
  localmente como descartáveis e são removidas no fim (exact-name).
- Descartáveis prefixados `eqmd_s7_rehearsal`; nunca tocar
  containers/volumes/redes existentes do Zen (eqmd_dev, eqmd_net...).
- Senhas/valores SINTÉTICOS; nenhum `.env` real; sem dados clínicos.
- Python só dentro dos containers da stack; Node no host.
- Tocar SOMENTE os entregáveis + fixes de integração declarados.

## Definição de pronto

- Ensaio verde ponta-a-ponta com tempos; cleanup zero-resíduo
  comprovado; baseline lintado; gates de compose/cutover verdes.
- `worker_done` com: tempos por etapa, contagens/hashes A==B,
  fixes de integração (ou "nenhum"), cleanup e limites.
