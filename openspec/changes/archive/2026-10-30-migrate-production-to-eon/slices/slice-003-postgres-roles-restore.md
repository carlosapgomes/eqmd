# Slice s3 — PostgreSQL 15: roles, init e restore ensaiável

Task refs: `tasks.md` 3.1–3.3 · Change: `migrate-production-to-eon`.

## Objetivo

Fechar o lado de banco da etapa 1: SQL de init (template UTF8/C,
extensões, roles de runtime não superusuária e migrator), procedimento
de dump/restore lógico verificável, e **ensaio local descartável** com
dados sintéticos provando o ciclo completo origem→destino.

## Entregáveis (apenas estes)

1. `deploy/eon/init/01-roles.sql` + `02-database.sql`:
   - `01`: roles `eqmd_user` (LOGIN, **NOSUPERUSER NOCREATEDB
     NOCREATEROLE**, senha via `:"EQMD_USER_PASSWORD"` psql var) e
     `eqmd_migrator` (LOGIN, CREATE no schema público da database);
   - `02`: `CREATE DATABASE eqmd_db TEMPLATE template0 ENCODING 'UTF8'
LC_COLLATE 'C' LC_CTYPE 'C'` + `CREATE EXTENSION unaccent,
pg_trgm` + grants para `eqmd_user` (CONNECT/USAGE/SELECT/INSERT/
     UPDATE/DELETE) e `eqmd_migrator`, **incluindo ALTER DEFAULT
     PRIVILEGES** para objetos futuros criados pela migrator.
2. `docker-compose.eon.yml` (edição mínima): montar
   `./deploy/eon/init:/docker-entrypoint-initdb.d:ro` no `postgres`
   (roda UMA vez em volume vazio; fallback manual documentado em
   comentário). As 10 invariantes de `test_compose_eon.mjs` devem
   continuar verdes.
3. `deploy/eon/restore/verify-restore.sql` — verificação pós-restore:
   extensões presentes, donos dos objetos (só roles esperadas),
   contagens agregadas por tipo de objeto (tabelas/sequences/
   constraints/indexes), sem dados clínicos na saída.
4. `scripts/tests/test_pg15_roles_restore.mjs` — teste estático
   (node:test) sobre os SQLs: afirma NOSUPERUSER/NO.CREATEDB em
   eqmd_user, existência de eqmd_migrator, template0+UTF8+C literais,
   unaccent+pg_trgm, ALTER DEFAULT PRIVILEGES, ausência de senha
   hardcoded e de `GRANT SUPERUSER` (RED antes dos arquivos
   existirem).
5. `scripts/tests/test_pg15_rehearsal.mjs` — **ensaio e2e docker**
   (padrão dos gates manuais do repo): cria rede descartável
   `eqmd_s3_rehearsal_net` + container A "origem" (postgres digest
   `1d1095b0...`) com schema sintético (≥3 tabelas com FK, sequence
   serial, índice, dado sintético ≥20 linhas, extensões criadas),
   `pg_dump -Fc`; container B "destino" com init SQL aplicado em
   volume vazio; restore com `pg_restore --exit-on-error --no-owner
--role=eqmd_migrator`; executa `verify-restore.sql` + asserts
   (contagens A==B, sequence values, FK válida, `eqmd_user` SEM
   superusuário, objetos de propriedade da migrator, extensões
   ativas); **cleanup garantido (container+rede+volume) mesmo em
   falha**; senha sintética; log em `temp/migracao-eon/s3/`.
6. Evidências em `temp/migracao-eon/s3/`: saída do teste estático,
   log completo do ensaio (RED se aplicável → GREEN), contagens.

## Verificação (comandos exatos)

```bash
node --test scripts/tests/test_pg15_roles_restore.mjs
node scripts/tests/test_pg15_rehearsal.mjs
node --test scripts/tests/test_compose_eon.mjs
```

## Restrições

- Containers/rede/volume descartáveis com nomes `eqmd_s3_rehearsal_*`;
  cleanup em todas as saídas (trap/finalmente). **NUNCA** tocar
  containers/redes/volumes existentes (eqmd_dev, eqmd_postgres,
  eqmd_net, eqmd_media_init_dev) nem o eon/origem.
- Imagem postgres exatamente `postgres@sha256:1d1095b0503145be79c79239372aefadfacf6b7c33c9245bbf99ce4b6b89c737`.
- Senhas sintéticas hardcoded no ensaio (marcadas SYNTHETIC); nenhum
  `.env`; nenhum secret; nenhum dado real/clínico.
- `docker exec`/`docker run` apenas no contexto do ensaio; sem
  `docker start` de containers preservados.
- Tocar SOMENTE os entregáveis listados; NÃO editar `tasks.md`/
  `design.md`; `test_compose_eon.mjs` pode ser estendido APENAS se a
  montagem do init exigir (manter 10+ invariantes verdes).
- Python não é necessário; usar psql/pg_dump/pg_restore do container.

## Definição de pronto

- Teste estático verde; ensaio e2e verde com cleanup comprovado
  (docker ps/a/network ls sem resíduos `eqmd_s3_rehearsal_*`);
  compose segue 10/10; evidências salvas.
- `worker_done` com: caminhos, pass counts, contagens A→B, provas de
  não-superusuário/ownership/extensões e cleanup.
