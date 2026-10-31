# Slice s2 — Compose eon e configuração sintética

Task refs: `tasks.md` 2.1–2.3 · Change: `migrate-production-to-eon`.

## Objetivo

Primeiro artefato implantável da etapa 1: `docker-compose.eon.yml`
autossuficiente + template de env sintético + teste estático
permanente que prova as invariantes de topologia da spec
`eon-migration` (baseline por digest, redes externas mínimas, zero
portas publicadas de banco/app, migrate/init nunca automáticos).

## Entregáveis (apenas estes arquivos)

1. `docker-compose.eon.yml` — serviços:
   - `eqmd`: imagem EXATA por digest
     `ghcr.io/carlosapgomes/eqmd@sha256:fe31d296f50dd34c19c437244ea9a3d61f75aba4ec7d806329b50f8340cc4c4f`;
     gunicorn (CMD da imagem); `user:` UID/GID dedicado não
     privilegiado (proposta: `9900:9900`, justificar); redes
     `<REDE_APP>` + `<REDE_DB>` + `<REDE_EGRESS>`;
     volumes `eqmd_media` (rw), `eqmd_logs` (rw); SEM portas
     publicadas; healthcheck `/health/` via python urllib (sem curl
     garantido); hardening default ON (`read_only` + tmpfs `/tmp`,
     `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`) com
     nota de revisão no ensaio s7; limites de memória/CPU iniciais
     conservadores (ex.: app 1g/1.0, pg 768m) marcados como ajustáveis
     pelo ensaio.
   - `postgres`: imagem por digest
     `postgres@sha256:1d1095b0503145be79c79239372aefadfacf6b7c33c9245bbf99ce4b6b89c737`;
     somente rede `<REDE_DB>`; volume `eqmd_pgdata`; SEM porta
     publicada; healthcheck `pg_isready`; SEM `cap_drop: ALL` (o
     entrypoint precisa ajustar ownership — design D5).
   - `frontend`: SOMENTE via variável obrigatória
     `EQMD_FRONTEND_IMAGE` (digest real escolhido no slice s4);
     redes `<REDE_INGRESS>` + `<REDE_APP>`; volume
     `eqmd_static` somente leitura; sem portas publicadas.
   - `init` (profile `ops`): one-shot; corrige ownership de
     media/logs e prepara estáticos no volume; roda como root
     apenas nesta operação explícita.
   - `migrate` (profile `ops`): one-shot `python manage.py migrate
--noinput`; NUNCA no startup do serviço web; identidade
     separada será detalhada no s3 (roles).
   - Redes: as quatro `hospital_*_eqmd` como `external: true`
     (criação é gate humano da fase D; CIDRs <CIDR_RESERVA_EQMD> já
     reservados no inventário da infra).
2. `env.eon.example` — template SINTÉTICO completo: toda variável que
   o compose e o `config/settings.py` consumirem (mapear lendo
   `config/settings.py`, somente leitura), com valores placeholder
   SEM segredos reais: `EQMD_FRONTEND_IMAGE=<digest-a-definir-s4>`,
   `POSTGRES_*`, chaves Django, `ALLOWED_HOSTS`/CSRF com
   `equipemed.projetoshgrs.com`, `TIME_ZONE=America/Bahia`, SMTP
   sintético, `PDF_FORMS_MAX_FILE_SIZE=10485760`.
   **PROIBIDO comentário inline na mesma linha do valor** (lição do
   incidente `--env-file`); comentários em linha própria.
   Nenhum arquivo `.env` real é lido ou criado.
3. `scripts/tests/test_compose_eon.mjs` — teste node:test (padrão dos
   `.mjs` existentes) que renderiza
   `docker compose -f docker-compose.eon.yml --env-file env.eon.example config`
   e afirma: (a) render exit 0; (b) nenhum serviço publica porta
   (`ports` vazio/ausente em TODOS); (c) as 4 redes são `external`;
   (d) `eqmd.image` é o digest exato e `postgres.image` o digest
   PG15; (e) `eqmd.user` não é root/0; (f) `eqmd` e `postgres` não
   executam migrate no startup (command/entrypoint do web não contém
   migrate; serviços migrate/init usam profiles); (g) volumes
   declarados conforme contrato (media/logs/pgdata/static);
   (h) tmpfs/cap_drop/no-new-privileges presentes no `eqmd`.
   Se `docker compose config` não estiver disponível no host, o teste
   falha com mensagem clara (gate não pode ser pulado).

## Passos

1. RED: escrever o teste primeiro; evidenciar falha (compose não
   existe).
2. GREEN: escrever compose + env example; teste verde.
3. Capturar a saída do render (`config > /dev/null` + saída do
   teste) como evidência em `temp/migracao-eon/s2/`.

## Verificação (comandos exatos)

```bash
docker compose -f docker-compose.eon.yml \
  --env-file env.eon.example config >/dev/null \
  && echo RENDER_OK
node --test scripts/tests/test_compose_eon.mjs
```

## Restrições

- Nenhum `up/run/start` de container; `config` é somente render.
- Nenhum acesso a eon/origem; nenhum `.env` real; nenhum secret.
- Tocar SOMENTE os 3 entregáveis; NÃO editar `tasks.md`/`design.md`.
- UID/GID: se `9900:9900` colidir com algo verificável no repo,
  documentar alternativa escolhida no próprio compose (comentário).
- markdownlint n/a (YAML/env), mas manter linhas ≤ 80 nos exemplos.

## Definição de pronto

- Teste verde provando as 8 invariantes; render OK com env sintético.
- `worker_done` com: caminhos, saída do teste (pass count), a
  decisão de UID/GID e a lista de variáveis mapeadas do settings.
