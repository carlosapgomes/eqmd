# Proposal: Migração da produção EQMD para o eon (etapa 1)

## Why

A produção roda hoje em Docker rootless na `<ORIGEM_HOST>` (`eqmdr`),
fora do hospital, com capacidade limitada (5,8 GiB RAM, sem swap) e
sem backup automatizado. O destino aprovado é o `eon` (Docker
rootful, `/srv/apps/eqmd`), dentro do hospital, atrás do edge
compartilhado (Caddy + Cloudflare Tunnel), com o novo endereço
`https://equipemed.projetoshgrs.com`. O plano de migração
(`temp/relatorio-migracao-eqmd-eon.md`) definiu fases A–F, gates e
rollback; a Fase A está fechada e o pré-requisito de segurança da
imagem foi cumprido pela change `harden-production-image-security`
(5/5 slices aceitos, baseline publicada por digest).

## What Changes

- Produzir os **artefatos implantáveis da etapa 1**: Compose
  autossuficiente `docker-compose.eon.yml`, template de env sintético,
  roles/init do PostgreSQL 15 dedicado, procedimentos de dump/restore,
  definição dos 5 cronjobs, snippet Caddy com reversão, e o runbook de
  cutover de 8h com gates E1–E9 e critérios de aborto.
- **Ensaio local (Zen)** de fim-a-fim com dados sintéticos: dump →
  transferência com hashes → restore em PG15 descartável → boot →
  validação → cronometragem, alimentando o plano da janela.
- Fixar a baseline de imagem por digest
  `ghcr.io/carlosapgomes/eqmd@sha256:fe31d296...` (decisão do
  operador de 2026-10-30, com aceite formal do risco residual
  documentado no dossiê de segurança).
- Toda execução no `eon`/origem/DNS/Cloudflare permanece **fora**
  desta change: acontece somente via comandos exatos aprovados por
  gate humano, um por operação, conforme o plano de migração.

## Capabilities

### New Capabilities

- `eon-migration`: contrato verificável dos artefatos da etapa 1 da
  migração — baseline por digest, topologia de rede isolada, banco
  PostgreSQL 15 dedicado com UTF8/C e roles não superusuárias,
  restore ensaiado com evidências, agendamentos com origem única e
  runbook de cutover com gates e rollback.

### Modified Capabilities

Nenhuma. Os gates de desenvolvimento (`development-quality-gates`) e o
contrato de segurança da imagem (`production-image-security`) seguem
vigentes sem alteração.

## Included Scope

| Frente         | Entregável principal                              |
| -------------- | ------------------------------------------------- |
| IPAM           | Análise de conflitos + proposta de reserva        |
| Compose/config | `docker-compose.eon.yml` + env sintético validado |
| Banco          | SQL de roles/init + procedimento de restore       |
| Frontend       | Serviço de estáticos + snippet Caddy reversível   |
| Cronjobs       | Definição dos 5 jobs com locks e timezone         |
| Cutover        | Runbook 8h com gates E1–E9 e rollback             |
| Ensaio         | Rehearsal e2e local com tempos medidos            |

## Non-Goals

- PostgreSQL 18 / cluster central (etapa 2, change própria).
- Firebase, Matrix, Synapse e Element (fora do escopo aprovado).
- Execução de produção: deploys, DNS, Cloudflare, Caddy real, cutover.
- Automação de backup (permanece manual diária pelo operador).
- Alteração de código da aplicação (imagem é consumida por digest).
- Migração da zona DNS antiga ou redirecionamento permanente.

## Decision Log

- 2026-10-30: operador define baseline `fe31d296...` e aceita o risco
  residual do dossiê; registra lanes Orca (worker opencode2, reviewer
  pi). Evidência: `temp/migracao-eon/decisoes-operador-2026-10-30.md`.
