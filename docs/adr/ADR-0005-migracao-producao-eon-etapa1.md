# ADR-0005: Migração de produção para o eon — etapa 1 declarativa e gated

## Status

Accepted — 2026-10-31. Implementada integralmente via change
`migrate-production-to-eon` (arquivada em
`openspec/changes/archive/2026-10-30-migrate-production-to-eon/`):
7 slices aceitos com revisão independente, ensaio e2e verde com
tempos medidos e spec `eon-migration` publicada. A **execução
operacional** (fases D/E no eon, DNS/Cloudflare, cutover) segue os
runbooks gated em `deploy/eon/` e permanece decisão humana por
comando exato, fora desta ADR.

## Contexto

A produção roda em Docker rootless fora do hospital (`<ORIGEM_HOST>`),
com 5,8 GiB RAM sem swap, sem backup automatizado e com image
endurecida publicada por digest (ADR-0004). O destino aprovado é o
`eon` (rootful, `/srv/apps/eqmd`), atrás do edge compartilhado
Caddy/Cloudflare, com novo endereço
`https://equipemed.projetoshgrs.com`. O plano de migração definiu
janela de 8 h, RPO zero para gravações confirmadas, origem preservada
14 dias e PostgreSQL 15 dedicado como exceção temporária (revisão em
30 dias; centralização PG18 é etapa futura). O inventário da infra
(`infra-single-db`) registrou as reservas de IPAM da aplicação.

## Decisão proposta

1. **Etapa 1 desacoplada**: migrar aplicação+banco+mídia+cron mantendo
   PostgreSQL 15 dedicado; centralização no cluster PG18 fica para
   change própria. Migração de dados exclusivamente lógica
   (`pg_dump -Fc` → `pg_restore --exit-on-error`), nunca cópia de
   PGDATA.
2. **Baseline imutável**: imagem `ghcr.io/carlosapgomes/eqmd@sha256:
fe31d296...` pinada no Compose (risco residual aceito formalmente
   pelo operador em 30/10); falha de pull aborta — nunca build local
   de fallback no destino.
3. **Topologia por zona**: quatro redes externas `hospital_*_eqmd`
   (ingress /29 + app/db/egress /24) nos CIDRs reservados
   <CIDR_RESERVA_EQMD>; zero portas publicadas de banco/aplicação.
4. **Banco com privilégios mínimos**: `eqmd_user` NOSUPERUSER para o
   runtime e `eqmd_migrator` para restore/migrate (grants +
   `ALTER DEFAULT PRIVILEGES`); database UTF8/C via `template0`;
   extensões `unaccent` e `pg_trgm`.
5. **Frontend nginx dedicado** (digest pinado) espelhando o
   comportamento da origem (60 MB, `sw.js`/`manifest.json` no-cache,
   mídia sempre via Django), atrás de **uma rota nova** no Caddy
   compartilhado — sem alterar a estrutura da edge; intervenção com
   baseline, smoke das vizinhas (CHD/HMD/Prisma) e reversão exata.
6. **Cron determinístico**: `/etc/cron.d` no host com horários
   convertidos para UTC (Bahia = UTC−3 fixo), `flock -n` por job,
   instalação suspensa até o aceite e reativação gated (E14);
   Firebase permanece desativado.
7. **Execução 100% gated**: todo comando de produção é template com
   `GATE:` no runbook de cutover (8 h, aborto ≤ h6, reserva ≥ 2 h) e
   nos procedimentos de rollback pré/pós-escrita (alvo de restore
   reverso sempre em database fresca; nunca `docker start`
   incondicional de container com migrate no startup — lição do
   incidente S1b).
8. **Validação por ensaio local** antes de qualquer toque no eon:
   gates estáticos (compose/IPAM/cron/docs) + ensaio e2e descartável
   com dados sintéticos e tempos medidos.

## Alternativas Consideradas

1. **Migrar direto para o PostgreSQL 18 central**:
   - Vantagens: elimina a exceção temporária; um cutover só.
   - Desvantagens: acopla migração de host a upgrade de major e a
     mudanças no cluster compartilhado; aumenta blast radius.
   - Por que não: o plano aprovado exige reduzir mudanças simultâneas;
     centralização é etapa 2 com ensaio próprio.

2. **Copiar PGDATA (migração física)**:
   - Vantagens: mais rápida para bases grandes; preserva tudo.
   - Desvantagens: exige mesma versão/binários exatos; frágil entre
     hosts; sem tratamento de ownership/permissões.
   - Por que não: 1,7 GB lógico é pequeno; o restore lógico permite
     recriar roles com privilégios mínimos e conferir objetos.

3. **Servir estáticos direto do Caddy compartilhado**:
   - Vantagens: um serviço a menos.
   - Desvantagens: acopla o app à edge administrada pela infra;
     perde paridade de comportamento com a origem (nginx).
   - Por que não: o frontend nginx mantém o app autossuficiente e o
     edge inalterado exceto uma rota.

4. **Agendamento dentro da imagem (scheduler no container)**:
   - Vantagens: sem dependência do host.
   - Desvantagens: imagem não tem cron; duplicaria mecanismo com a
     origem; difícil suspender de forma auditável.
   - Por que não: `/etc/cron.d` declarativo versionado com flock e
     preflight de TZ atende origem única e auditabilidade.

## Consequências

### Positivas

- Artefatos declarativos versionados (compose, SQL, cron, nginx,
  caddy, runbooks) com gates automatizados re-executáveis.
- Defeitos capturados no ensaio (não no eon): permissão do
  collectstatic, env-file hardcoded, ordenação do E4, entre outros.
- Privilégios mínimos no banco e zero exposição de portas por design.
- RPO zero preservado por congelamento provado e rollback ensaiado
  nos dois regimes.

### Negativas/Trade-offs

- Exceção temporária de banco dedicado exige revisão em 30 dias e
  backup manual diário pelo operador até a centralização.
- Sessões não atravessam domínios: novo login obrigatório pós-cutover.
- Intervenção na edge compartilhada tem janela curta e exige smoke
  das vizinhas.

### Riscos e Mitigações

- **Colisão de IPAM**: reservas registradas no inventário da infra
  com teste permanente de disjunção (`check_ipam_disjoint` + teste
  do repo de infra).
- **Restore lento na janela**: tempos medidos por etapa; aborto ≤ h6
  e reserva ≥ 2 h; escala real ensaiada na fase C com dados reais.
- **Escritor duplicado**: cron suspenso até o aceite; congelamento
  provado antes do dump final; locks por job.
- **Execução incorreta no eon**: todo passo é `GATE:` com comando
  exato aprovado; reversão documentada por intervenção.

## Referências

- Plano: `temp/relatorio-migracao-eqmd-eon.md` (evidência local).
- Decisões do operador: `temp/migracao-eon/decisoes-operador-2026-10-30.md`.
- Change arquivada: `openspec/changes/archive/2026-10-30-migrate-production-to-eon/`.
- Spec: `openspec/specs/eon-migration/spec.md`; runbooks:
  `deploy/eon/`.
- ADR-0004 (baseline de segurança da imagem) e ADR-0001 (gates de
  desenvolvimento) permanecem vigentes.
