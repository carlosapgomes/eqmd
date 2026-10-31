# Baseline de tempos do ensaio e2e local (s7)

Change: `migrate-production-to-eon` · Slice s7 · Zen local.
Execução: 2026-10-30 · imagens pinadas `ghcr ... fe31d296`,
`postgres ... 1d1095b0`, `nginx ... 51047bea`.
Tempos abaixo são do ensaio com dados sintéticos; não são promessa
para a produção.

## 1. Faixa de tempos (execuções verdes)

Quatro execuções completas verdes foram registradas: worker (62,574 s),
rerun do coordenador (verde, total não retido), rerun do revisor
(59,611 s) e a confirmação pós-fix (58,065 s). A tabela mostra a faixa
por etapa entre os três snapshots detalhados disponíveis (worker,
revisor e confirmação); a faixa total é 58,06–62,57 s. `timings.json`
é **sobrescrito a cada execução verde** e sempre reflete a execução
mais recente; use a faixa para dimensionar a janela, não um único run.

| Etapa                           |        faixa ms |         faixa s |
| ------------------------------- | --------------: | --------------: |
| redes locais + sub-redes        |         230–385 |       0,23–0,39 |
| A: postgres + init SQL          |       1482–2973 |       1,48–2,97 |
| A: ops init (collectstatic)     |       2006–2151 |       2,01–2,15 |
| A: migrate (migrator)           |     13609–14417 |     13,61–14,42 |
| A: seed sintético               |         112–118 |       0,11–0,12 |
| A: mídia sintética              |         433–544 |       0,43–0,54 |
| A: stack completa               |       5847–6338 |       5,85–6,34 |
| A: gates funcionais             |       2422–3608 |       2,42–3,61 |
| A: contagens                    |           93–99 |       0,09–0,10 |
| A: sequências                   |           84–88 |       0,08–0,09 |
| A: hashes de mídia              |         510–551 |       0,51–0,55 |
| export: pg_dump -Fc             |         232–235 |       0,23–0,23 |
| export: tar de mídia            |         459–516 |       0,46–0,52 |
| export: manifesto + conferência |         890–949 |       0,89–0,95 |
| B: down -v + reset              |       3893–4239 |       3,89–4,24 |
| B: postgres + init SQL          |       2552–2572 |       2,55–2,57 |
| B: E4 prepare (init)            |       1993–2084 |       1,99–2,08 |
| B: restore do banco             |       1907–2507 |       1,91–2,51 |
| B: restore de mídia UID 9900    |         436–475 |       0,44–0,47 |
| B: E4 remap (init)              |       1942–2134 |       1,94–2,13 |
| B: migrate --plan no-op         |       5269–5300 |       5,27–5,30 |
| B: stack completa               |       5883–6218 |       5,88–6,22 |
| B: gates funcionais             |       2435–4832 |       2,44–4,83 |
| B: contagens                    |           95–99 |       0,10–0,10 |
| B: sequências                   |           85–87 |       0,09–0,09 |
| B: hashes de mídia              |         494–518 |       0,49–0,52 |
| B: verify-restore.sql           |          95–100 |       0,10–0,10 |
| **Total medido**                | **58065–62574** | **58,06–62,57** |

O alvo de runtime era < 30 min; o ensaio ficou bem abaixo. O pull das
imagens foi feito antes e não entrou na soma das etapas. O total
exclui a limpeza final.

## 2. Contagens e hashes A == B

| Métrica                   | A (origem) | B (destino) |
| ------------------------- | ---------: | ----------: |
| tabelas públicas          |         94 |          94 |
| sequências (pg_sequences) |         37 |          37 |
| índices                   |        423 |         423 |
| constraints               |        310 |         310 |
| foreign keys              |        125 |         125 |
| linhas synthetic_site     |          3 |           3 |
| linhas synthetic_patient  |         10 |          10 |
| linhas synthetic_note     |         20 |          20 |

`verify-restore.sql` usa `information_schema.sequences` (3 visíveis);
a comparação A==B de valores usou `pg_sequences`, que listou 37
sequências e produziu estados idênticos nas duas pontas.

Hashes de mídia idênticos nas duas pontas:

- `synthetic/alpha.txt` — `1e3a83ef...d8ed0d75`
- `synthetic/beta.txt` — `cfbc5ecd...a5e2722e`

Provas de banco: `eqmd_user` superuser/createdb/createrole = false;
tabelas e sequências de propriedade de `eqmd_migrator` (0 fora);
`unaccent` e `pg_trgm` ativos; encoding UTF8, collate/ctype C;
FKs validadas (0 não validadas); `migrate --plan` sem operações.

## 3. Gates funcionais

- Health interno: 200 nas fases A e B.
- `/static/manifest.json`: 200 nas duas fases.
- `/static/sw.js`: 200 com `Cache-Control: no-cache, must-revalidate`.
- `/manifest.json`: 200, proxiado ao Django, com no-cache.
- Exportação: dump + tar + manifesto sha256 conferidos no staging.
- E4: init prepara volume, extração UID 9900 com `--no-same-owner`,
  init idempotente remapeia; restauração feita em volume novo.

## 4. Fix de integração exposto pelo ensaio

O primeiro `init` falhou ao rodar `collectstatic --clear` como UID 9900
porque os diretórios internos do volume `eqmd_static` vinham da imagem
com ownership 33:33. Correção aplicada em `docker-compose.eon.yml`:
`chown -R 9900:9900 /app/staticfiles` antes do collectstatic.

Gates reexecutados após a correção:

- `test_compose_eon.mjs`: 12/12.
- `test_cutover_docs.mjs`: 12/12.
- `test_pg15_roles_restore.mjs`: 8/8.
- `test_frontend_static.mjs`: 8/8.
- Ensaio s7 completo: quatro execuções verdes, faixa 58,06–62,57 s,
  última registrada em `timings.json`, zero resíduo.

## 5. Escala e limites

Os números usam dados sintéticos e não devem ser lidos como linearidade:

- banco de produção observado: ~1,7 GB; ensaio: schema mínimo + seed.
- mídia de produção observada: ~76 MB; ensaio: 2 arquivos pequenos.
- a transferência foi simulada por cópia local no mesmo host.
- não houve rede real do eon, DNS, Cloudflare, TLS externo ou Caddy.
- não houve fluxos clínicos autenticados, uploads reais, PDFs reais,
  vídeos reais, e-mails reais ou conta do operador.
- não houve vizinhas CHD/HMD/Prisma nem intervenção compartilhada.
- cron real por minuto, locks em produção e origem única não foram
  exercitados aqui; o ensaio cobre apenas o mecanismo e os locks.
- backup/restore real do host e retenção não foram demonstrados.

O ensaio da fase C, com dados reais, deve substituir os placeholders
`<TEMPO_s7_*>` do runbook. Eles permanecem inalterados neste slice.

## 6. O que só pode ser validado no destino

- TLS, DNS e rota Cloudflare do domínio novo.
- Login/CSRF/email com a conta do operador e fluxos clínicos reais.
- Redirect 302 do domínio antigo, deep links e métodos mutáveis.
- Caddy compartilhado e smoke de CHD, HMD e Prisma.
- Cron real por minuto, timezone do host e prova de origem única.
- Backup real do destino e restore reverso na janela.
- Retenção de 14 dias, HTTPS antigo e descomissionamento.

## 7. IPAM local e observação do Zen

As redes do ensaio usaram os nomes exatos
`hospital_{ingress,app,db,egress}_eqmd`, mas sub-redes **test-only**
`10.99.17.0/29`, `10.99.18.0/24`, `10.99.19.0/24`, `10.99.20.0/24`,
aprovadas pelo coordenador porque o Zen já tem a rede vazia
`<REDE_LEGADO_VIZINHA>` em `<CIDR_INTERNO>`. Ela não foi tocada e fica como
candidata a limpeza pelo operador. A disjunção das faixas reservadas
`<CIDR_RESERVA_EQMD>` continua provada por `check_ipam_disjoint.mjs` e pelo
inventário da infra; a substituição é só do ensaio local.

## 8. Limpeza

Projeto, containers, volumes e redes do ensaio foram removidos com
nomes exatos. Resíduo final: nenhum container, volume ou rede
`eqmd_s7_rehearsal*`/`hospital_*_eqmd` local. Nenhum recurso existente
do Zen foi tocado.
