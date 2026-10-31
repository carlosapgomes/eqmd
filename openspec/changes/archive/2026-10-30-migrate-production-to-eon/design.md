# Design: Migração da produção EQMD para o eon (etapa 1)

## 1. Contexto e baseline

- Origem: `<ORIGEM_HOST>`, rootless, `/home/eqmdr/eqmd-app-rootless`;
  app em `hgrs-rootless_app` (porta host 8780→8000), banco
  `hgrs-rootless_postgres` (15.15, `eqmd_db`, UTF8/C, extensões
  `unaccent` e `pg_trgm`; role `eqmd_user` hoje superusuária — não
  copiar privilégios), mídia 76 MB, estáticos 8,2 MB (bind
  `/srv/eqmd-static`), logs 55 MB (ficam na origem), 5 cronjobs.
- Destino: `eon`, rootful, `/srv/apps/eqmd`; edge compartilhado
  `hospital-internal-edge` (Caddy 2.10.2, `admin off`) + Cloudflare
  Tunnel; hostname novo `equipemed.projetoshgrs.com` (hoje NXDOMAIN).
- Imagem da aplicação (decisão do operador 2026-10-30):

```text
ghcr.io/carlosapgomes/eqmd@sha256:fe31d296f50dd34c19c437244ea9a3d61f75aba4ec7d806329b50f8340cc4c4f
```

Pull com falha **aborta** o procedimento; nunca build local de
fallback no destino. PostgreSQL segue o digest da origem
(`postgres@sha256:1d1095b0...`) até confirmação no pull do destino.

- Aceite de risco residual registrado em
  `temp/migracao-eon/decisoes-operador-2026-10-30.md`.

## 2. Decisões técnicas

- **D1 — Escopo em uma etapa**: aplicação + PG15 dedicado + mídia +
  frontend + cron; PostgreSQL 18 central fica para etapa 2 (ADR de
  infra vigente; exceção temporária revisada em 30 dias).
- **D2 — Compose autossuficiente**: `docker-compose.eon.yml` novo, sem
  herança dos existentes (SQLite legado, Matrix, merges indesejados).
  Serviços: `eqmd` (gunicorn, não root), `postgres` (PG15 próprio),
  `frontend` (estáticos + proxy), operações `init` e `migrate`
  explícitas — nunca migrate automático no startup do web.
- **D3 — Redes**: quatro redes internas propostas no plano
  (`<REDE_INGRESS>`, `<REDE_APP>`, `<REDE_DB>`,
  `<REDE_EGRESS>`); CIDRs **somente após** o slice de IPAM;
  redes compartilhadas são `external: true` administradas pela infra;
  sem portas publicadas de banco ou gunicorn; Caddy só no ingress;
  Cloudflared sem acesso direto aos containers.
- **D4 — Usuário e permissões**: aplicação roda com UID/GID não
  privilegiado dedicado (selecionado no slice 2 a partir do usuário da
  imagem; sem `chown -R` genérico); exportação de mídia pelo namespace
  do container e restauração com ownership do destino — nunca cópia
  cega de UIDs rootless.
- **D5 — Banco**: database `eqmd_db` recriada com template UTF8/C
  explícito; extensões `unaccent` + `pg_trgm`; **role runtime não
  superusuária** (`eqmd_user` recriada sem SUPERUSER/CREATEDB) e
  identidade `migrator` separada para restore/migrate; grants por
  esquema incluindo objetos futuros (default privileges); migração
  apenas por dump/restore lógico (`pg_dump -Fc` → `pg_restore`),
  **nunca cópia de PGDATA**.
- **D6 — Config e secrets**: template `env.eon.example` com valores
  sintéticos; `docker compose config` validado apenas com sintéticos;
  env real entregue por `--env-file` na implantação (comando docker,
  não interpolação de shell); nenhuma saída de config com secrets é
  registrada; `.dockerignore`/contexto já auditados pela change de
  segurança.
- **D7 — Frontend/estáticos**: serviço dedicado servindo estáticos
  imutáveis do mesmo artefato (coletados na operação init) + reverse
  proxy para o Django; tratamento específico de `/static/sw.js` e
  `/manifest.json` (comportamento atual do Nginx da origem); imagem e
  digest decididos no slice 4.
- **D8 — Caddy/Cloudflare**: reutilizar o caminho Cloudflared→Caddy
  com rota nova de hostname e ingress privado novo; como o Caddyfile
  usa `admin off`, o método exato (reload × recriação) e os smoke
  tests de CHD/HMD/Prisma são definidos e ensaiados com o operador
  antes de qualquer intervenção; snippet produzido com procedimento
  de reversão documentado.
- **D9 — Cronjobs**: os 5 agendamentos preservados no destino com
  **origem única** de execução (definição no slice 5: crontab do host
  chamando `docker compose exec`, com locks e timezone validados);
  ficam suspensos até o aceite do cutover; Firebase comentado segue
  fora.
- **D10 — Redirecionamento**: temporário (302) do antigo para o novo
  preservando path/query, com tratamento explícito de métodos
  mutáveis; mecanismo (Nginx origem × registrar) é decisão pendente do
  operador; sessões não atravessam domínios — novo login esperado.
- **D11 — Rollback**: pré-escrita = desligar redirect, reativar
  escritor único na origem (containers preservados; nunca `docker
start` de container com migrate no startup); pós-escrita = backup
  consistente do destino + restore reverso ensaiado em PG15 (mesma
  major), decidindo entre manutenção estendida e correção no destino
  se não couber na janela; zero descarte de gravações confirmadas.
- **D12 — Ensaio local (Zen)**: rehearsal e2e com dados sintéticos em
  containers descartáveis (PG15 + app), cronometrando backup,
  transferência, restore e validação; produz os tempos que fundamentam
  a reserva de rollback (≥2h) e o horário-limite de aborto (≤ h6).
- **D13 — Observação**: `/health/` é só um sinal; gates de aceitação
  seguem a seção 9 do plano (login, CSRF, uploads, PDF, vídeo, email
  autorizado, cron, redirecionamento sem loop, vizinhas CHD/HMD/Prisma).

## 3. Riscos e mitigação

| Risco                  | Mitigação                               |
| ---------------------- | --------------------------------------- |
| Colisão de CIDR no eon | Slice IPAM antes de reservar;           |
|                        | confirmação em produção autorizada      |
| Caddy derrubar         | Método ensaiado + smoke das vizinhas    |
| vizinhas               | + reversão documentada                  |
| Restore lento estourar | Ensaio cronometrado; aborto até h6      |
| janela                 |                                         |
| Divergência de         | Manifesto com hashes nas duas pontas    |
| dados/mídia            |                                         |
| Escritor duplicado     | Cron suspenso + congelamento comprovado |
| Exposição de secrets   | Validação só com env sintético          |
| Perda pós-escrita no   | Restore reverso PG15→origem ensaiado    |
| rollback               |                                         |

## 4. Slices

1. IPAM — reconciliação e proposta de reserva (evidência + anexo).
2. Compose eon + env sintético + validação estática + UID/GID.
3. PostgreSQL 15 — roles/init/restore + procedimento ensaiável.
4. Frontend + snippet Caddy reversível + PWA.
5. Cronjobs — definição, locks, timezone, suspensão/reativação.
6. Runbook de cutover 8h (gates E1–E9, aborto, rollback, comms).
7. Ensaio e2e local com tempos medidos (dados sintéticos).

Cada slice: um por vez, worker OpenCode2, verificação local, revisão
independente (Pi), aceite com registro; artefatos de produção exigem
gate humano adicional por comando exato.
