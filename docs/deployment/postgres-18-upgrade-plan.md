# Plano de Upgrade do PostgreSQL 15 para 18

- **Data:** 2026-11-11
- **Escopo:** `eqmd` (dev local, `docker-compose.deploy.yml`,
  `docker-compose.eon.yml`)
- **Status:** Proposta com evidências de dry-run executadas em 2026-11-11
- **Conclusão:** viável, com **um ajuste obrigatório de código** (migration
  `drugtemplates/0007`) e um risco operacional principal (novo `PGDATA` da
  imagem oficial 18). Suíte completa (3862 testes) aprovada no PostgreSQL
  18.6 após o ajuste.

## 1. Resumo executivo

O upgrade de `postgres:15-alpine` (15.19) para `postgres:18-trixie` (18.6) é
viável e de baixo risco para este projeto. Uma simulação completa (dry-run)
foi executada: dump do banco de dev (1,6 GB), restore em um container
PostgreSQL 18.6 efêmero, `migrate --check`, e execução da suíte de testes
integral contra o PG 18.

Resultados do dry-run, em ordem de execução:

- `pg_dump -Fc` do `eqmd_dev` (1,6 GB): dump de 503 MB em 50 s
- `pg_restore` no PG 18.6: concluído sem erros em 39 s
- extensões `pg_trgm` e `unaccent`: restauradas e funcionais no 18.6
- `vacuumdb --analyze-in-stages` (estatísticas do planner): 2 s
- `manage.py migrate --check`: sem migrações pendentes, < 5 s
- suíte completa de testes: **3862 testes OK** (25 skips) em 8 m 31s

Foi encontrada **uma incompatibilidade real** (detalhada na seção 5.2):
a migration `drugtemplates/0007` quebra ao rodar do zero no PG 18, pois o
PostgreSQL 18 trocou o avaliador de funções SQL e o inlining ficou mais
estrito com literais de tipo `unknown`. O fix é de uma linha e já foi
validado pela suíte completa (seção 5.3).

O PG 15 permanece suportado pela comunidade até novembro de 2027, portanto
não há urgência; o upgrade é recomendado para destravar o horizonte de
suporte até ~2030 e os ganhos de performance do PG 18 (async I/O, Skip
Scan, `pg_upgrade` que preserva estatísticas).

## 2. "LTS" no PostgreSQL: o que isso significa

O PostgreSQL **não tem um conceito oficial de LTS**. Cada versão major
recebe 5 anos de suporte (minores trimestrais com correções de segurança).
A versão estável mais recente é sempre a com maior horizonte de suporte:

| Major | Lançamento | Fim do suporte (EOL) |
| ----- | ---------- | -------------------- |
| 15    | out/2022   | nov/2027 (~1 ano)    |
| 16    | set/2023   | nov/2028             |
| 17    | set/2024   | nov/2029             |
| 18    | set/2025   | nov/2030             |

"Upgrade para o LTS" na prática = upgrade para a major estável corrente
(hoje, **18**, minor 18.6). Nota: o próprio host já executa
`postgres:18.6-trixie` em produção para outros projetos (ex.: hgproxy),
o que reduz risco operacional da mudança.

## 3. Estado atual do stack

| Componente      | Versão atual                 | Papel                    |
| --------------- | ---------------------------- | ------------------------ |
| PostgreSQL      | 15.19 (`postgres:15-alpine`) | dados Django + matrix_db |
| Volume de dados | `postgres_data` (1,8 GB)     | montado em .../data      |
| Extensões       | pg_trgm 1.6, unaccent 1.1    | busca de medicamentos    |
| Django          | 5.2.18 (LTS)                 | aplicação                |
| Python          | 3.12.16                      | runtime do app           |
| psycopg2-binary | 2.9.10                       | driver DB do Django      |
| Synapse         | v1.99.0 (Dockerfile.synapse) | Matrix homeserver        |
| Element Web     | v1.11.58                     | cliente Matrix           |
| nginx (eon)     | 1.30.6 (pinado por digest)   | ingress                  |
| gunicorn        | 23.x                         | app server de produção   |

Bancos no servidor de dev: `eqmd_dev` (1,6 GB) + 6 bancos de teste
(descartáveis, recriados pelo runner). O `matrix_db` não existe na instância
de dev atual; quando existir (ex.: produção), deve entrar no dump.

## 4. Mudanças críticas na imagem Docker oficial do PostgreSQL 18

1. **`PGDATA` mudou**: de `/var/lib/postgresql/data` para
   `/var/lib/postgresql/18/docker`. O ponto de montagem do volume no
   compose **precisa mudar** e o cluster 15 existente não é lido pela 18.
   Não é possível montar o volume antigo no novo caminho: o entrypoint
   encontraria arquivos do 15 e falharia. **Volume novo é obrigatório.**
2. **Base Debian trixie como padrão** (glibc). A variante `-alpine` foi
   reintroduzida a partir da 18.4; a `-bookworm` também existe. Para este
   projeto recomendamos `postgres:18.6-trixie` (Debian), já validada no
   host por outros serviços em produção.
3. UID do usuário `postgres` muda (70 no alpine para 999 no Debian). Com
   volume novo e entrypoint padrão (root + gosu), o ownership é ajustado
   automaticamente; nenhum serviço do projeto define `user:` no postgres.

## 5. Compatibilidade e riscos

### 5.1 Matriz por componente

| Componente         | Compatível?  | Evidência / risco                |
| ------------------ | ------------ | -------------------------------- |
| Django 5.2 LTS     | Sim          | suíte 3862 testes OK no PG 18.6  |
| psycopg2 2.9.10    | Sim          | suíte OK; client antigo ao       |
|                    |              | server novo é suportado          |
| pg_trgm / unaccent | Sim          | restauradas e funcionais no 18   |
| Migrations         | **1 ajuste** | `drugtemplates/0007` falha no 18 |
| Synapse v1.99      | Provável sim | sem garantia formal (ver 5.4)    |
| backup.sh          | Sim          | `pg_dump` roda dentro do         |
|                    |              | container                        |
| upgrade-rootless   | Sim          | idem                             |
| GUCs do compose    | Sim          | todas válidas no 18              |
| init SQL (eon)     | Sim          | SQL puro, sem sintaxe 15-only    |

### 5.2 Incompatibilidade real: migration `drugtemplates/0007`

Ao criar um banco do zero no PG 18 (cenário: banco de testes,
`reset_database.sh`, novo ambiente, ou replay de migrations), a migration
falha na criação do índice trigram:

```text
Applying drugtemplates.0007_enable_pg_trgm...Traceback:
psycopg2.errors.UndefinedFunction:
function unaccent(unknown, text) does not exist
CONTEXT: SQL function "immutable_unaccent" during inlining
```

Causa: o PG 18 substituiu o avaliador de funções SQL e o inlining não
aceita mais a resolução ambígua de `unaccent('unaccent', $1)` com literal
de tipo `unknown`. O corpo qualificado (já usado pela `0008`) funciona
corretamente no 18.

Observação: o caminho dump/restore do banco **existente** não falha,
porque a versão qualificada da função (migration `0008`) já está instalada
e o índice já existe. A falha ocorre apenas no replay completo das
migrations (bancos novos).

### 5.3 Correção obrigatória pré-upgrade (validada)

Na `apps/drugtemplates/migrations/0007_...py`, qualificar a chamada (mesma
forma que a `0008` já usa):

```diff
 IMMUTABLE_UNACCENT_SQL = (
     "CREATE OR REPLACE FUNCTION immutable_unaccent(text) "
     "RETURNS text AS $$ "
-    "SELECT unaccent('unaccent', $1) "
+    "SELECT public.unaccent('public.unaccent', $1) "
     "$$ LANGUAGE sql IMMUTABLE"
 )
```

Editar migration histórica é aceitável aqui: ambientes existentes já a
aplicaram (não reexecutam) e o resultado final da função é idêntico ao da
`0008`. Com este ajuste, a suíte completa passou no PG 18.6 (3862 testes,
8 m 31s, 25 skips). Como endurecimento opcional, usar cast explícito
`'public.unaccent'::regdictionary` em `0007` e `0008`.

### 5.4 Synapse v1.99 (única ressalva de garantia)

O Synapse declara suporte a versões suportadas de PostgreSQL; o teste
formal contra o PG 18 entrou no CI em releases posteriores à v1.99
(meados de 2025, anterior ao PG 18). Não há breakage conhecida, mas a
recomendação é **atualizar o Synapse para a release corrente antes da
janela do PG 18** (upgrade independente, com migrations próprias e
rollback simples via tag anterior). O Element Web não acessa o banco.

## 6. Estratégia recomendada: dump & restore

Para 1,6 GB, dump/restore é o melhor trade-off (simples, seguro,
rehearsável). Janela estimada: **15-30 min** de downtime.

### 6.1 Runbook - dev (`docker-compose.yml`)

```bash
# 0) aplicar o fix da migration 0007 e rodar ./scripts/test.sh no PG15
# 1) backup completo (dump + tar do volume) via script existente
./backup.sh

# 2) parar escritores (postgres continua no ar para o dump)
docker compose stop eqmd-dev matrix-synapse

# 3) dump de todos os bancos persistentes (inclua matrix_db se existir)
docker compose exec -T postgres \
  pg_dump -U eqmd_user -Fc eqmd_dev > temp/eqmd_dev_pg15.dump

# 4) editar docker-compose.yml:
#    image: postgres:18.6-trixie
#    volumes: postgres18_data:/var/lib/postgresql/18/docker
#    (declara o volume novo postgres18_data; NAO reutilizar o antigo)

# 5) subir o postgres 18 (initdb novo; vars/env criam roles/dbs)
docker compose up -d postgres

# 6) restore + estatisticas (dump NAO contem estatisticas do planner)
docker cp temp/eqmd_dev_pg15.dump "$(docker compose ps -q postgres)":/tmp/
docker compose exec postgres \
  pg_restore -U eqmd_user -d "$DATABASE_NAME" --no-owner /tmp/dump
docker compose exec postgres \
  vacuumdb -U eqmd_user -d "$DATABASE_NAME" --analyze-in-stages

# 7) validacao
docker compose exec postgres pg_isready -U eqmd_user
docker compose exec eqmd-dev python manage.py migrate --check
docker compose up -d
./scripts/test.sh   # cria bancos de teste do zero no PG18 (prova o fix)
```

Bancos `test_*` não são migrados: o runner os recria (e é justamente o
cenário que valida o fix da seção 5.3).

### 6.2 Runbook - eon (`docker-compose.eon.yml`)

Mesma lógica, com as particularidades do eon:

1. Repinar a imagem para o digest da `postgres:18.6-trixie`
   (ex.: `sha256:e3d24f69...`; **confirmar digest vigente no dia** com
   `docker image inspect` ou `docker manifest inspect`).
2. Trocar o volume `eqmd_pgdata` para apontar o novo path
   `/var/lib/postgresql/18/docker` em um **volume novo**.
3. Com volume vazio, `deploy/eon/init/01-roles.sql` e `02-database.sql`
   executam sozinhos (roles, banco e extensões) - sem mudança neles.
4. Restore com `pg_restore --clean --if-exists` sobre o banco bootstrap e
   `vacuumdb --analyze-in-stages`.
5. Validar com `deploy/eon/restore/verify-restore.sql` e smoke test via
   frontend nginx.
6. `docker-compose.deploy.yml` usa `postgres:15-alpine` + path antigo:
   atualizar junto (mesmo diff do dev).

### 6.3 Alternativas consideradas

| Estratégia        | Veredito                                  |
| ----------------- | ----------------------------------------- |
| dump & restore    | **escolhida**: simples, provada no        |
|                   | dry-run; janela de minutos                |
| `pg_upgrade`      | desnecessário p/ 1,6 GB; no Docker exige  |
|                   | container com binários 15+18              |
| replicação lógica | descartada: exige downtime ~zero, não é o |
|                   | caso                                      |

## 7. Upgrade de outros componentes

### Recomendados (cada um em janela própria, testável isoladamente)

| Componente      | De/Para                 | Motivo                          |
| --------------- | ----------------------- | ------------------------------- |
| Synapse         | v1.99.0 para atual      | segurança; CI formal com PG 18  |
| Element Web     | v1.11.58 para 1.11.x    | correções de segurança (client) |
| psycopg2-binary | 2.9.10 para 2.9.x atual | libpq mais recente (opcional)   |

Nenhum deles é bloqueador do PG 18 (exceto a ressalva de garantia do
Synapse, seção 5.4). Recomenda-se sequência: fix migration, Synapse,
PG 18, Element/psycopg2.

### Não é necessário trocar

- **Django 5.2 LTS**: suporte até abr/2028; avaliar 5.2 para 6.x apenas
  em 2027, se necessário.
- **Python 3.12**: EOL out/2028; 3.13 é opcional (nota: há `.pyc`
  cpython-313 no projeto, alguém já rodou localmente com 3.13).
- **gunicorn 23 / nginx 1.30.6 pinado**: sem relação com o PG.

## 8. Rollback

O desenho dump/restore torna o rollback trivial:

1. O volume antigo (`postgres_data` / `eqmd_pgdata`) **permanece intacto** -
   não remover, não sobrescrever, não montar no novo path.
2. Rollback = reverter o diff do compose (imagem 15 + path antigo) e
   `docker compose up -d`; o cluster 15 volta como se nada acontecesse.
3. Se houve escrita pós-upgrade que precisa ser preservada, dump do 18 e
   restore no 15 (o schema não usa recursos novos do 18, então o dump do
   18 restaura no 15 sem ajustes).
4. Reter dumps e volume antigo por **30 dias** após o upgrade.

## 9. Riscos e mitigações (resumo)

| Risco                       | Nível | Mitigação                      |
| --------------------------- | ----- | ------------------------------ |
| Esquecer path novo (PGDATA) | Alto  | runbook seção 6; volume novo é |
|                             |       | obrigatório; nunca reusar o    |
|                             |       | antigo no novo path            |
| Migrations em banco novo no | Alto  | fix seção 5.3 (validado)       |
| 18                          |       |                                |
| Estatísticas do planner     | Médio | `vacuumdb --analyze-in-stages` |
|                             |       | após o restore                 |
| Synapse v1.99 + PG 18       | Baixo | atualizar Synapse antes        |
| Digest/UID da imagem 18 no  | Baixo | confirmar digest; entrypoint   |
| eon                         |       | ajusta ownership do volume     |
| Espaço em disco (dump +     | Baixo | 46 GB livres; dump em temp/;   |
| volume novo ~1,8 GB)        |       | limpar após validação          |

## 10. Checklist final

- [ ] Aplicar fix da migration `0007` (seção 5.3) e passar
      `./scripts/test.sh` no PG 15
- [ ] Atualizar Synapse para release atual e validar healthcheck
- [ ] Atualizar `docker-compose.yml`, `docker-compose.deploy.yml` e
      `docker-compose.eon.yml` (imagem 18, path novo, volume novo)
- [ ] Executar runbook (seção 6) em dev; validar suíte + smoke manual
      (busca de medicamentos com/sem acento)
- [ ] Executar em eon com janela agendada; validar `verify-restore.sql`
- [ ] Atualizar docs: `docs/postgresql-migration.md`, comentários
      "PostgreSQL 15" em `deploy/eon/init/*.sql`, `.env.example` (nota de
      versão) e CHANGELOG
- [ ] Reter volume antigo + dumps por 30 dias; depois remover
- [ ] (Opcional, pós-upgrade) avaliar `io_method=io_uring` e
      `default_statistics_target` no PG 18 com carga real

## Referências

- `docs/postgresql-migration.md` (migração SQLite para PG, histórico)
- `docs/adr/ADR-0005-migracao-producao-eon-etapa1.md` (pin de digest)
- `backup.sh`, `upgrade-rootless.sh`, `deploy/eon/restore/verify-restore.sql`
- Upstream: PostgreSQL 18 Release Notes; política de suporte (5 anos);
  changelog da imagem `library/postgres` (mudança de `PGDATA` na 18)
