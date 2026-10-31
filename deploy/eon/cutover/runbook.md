# Runbook de cutover — janela E (8 horas)

Change: `migrate-production-to-eon` · Slice s6 · Fase E.
Documento de execução gated: **nada roda sem aprovação exata**.
Cada comando abaixo é um template com `<VARS>`; nenhum segredo real.

## 1. Precondições

- Slices s2–s5 aceitos e artefatos revisados.
- Ensaio s7 concluído com tempos medidos; preencher `<TEMPO_s7_*>`.
- Data, operador, responsável pelo aceite e janela confirmados.
- DNS/Cloudflare do domínio novo preparados, restritos a operadores.
- Redes e volumes da fase D criados; imagens pinadas disponíveis.
- Backups diários do dia feitos; staging com espaço e ownership definidos.
- Runbooks gated do Caddy (s4) e cron (s5) lidos e aprovados.
- Origem com manutenção testada; contatos de comunicação definidos.

## 2. Variáveis e relógio

Definir antes do h0 e registrar no ticket:

```text
<INICIO>        início da janela (UTC e America/Bahia)
<H6>            limite de aborto = <INICIO> + 6h
<FIM>           fim da janela = <INICIO> + 8h
<RESERVA>       rollback >= 2h, terminando até <FIM>
<ORIGEM>        host da origem
<EON>           host do eon
<ORIGEM_USER>   usuário dono do crontab da origem
<ACEITE>        responsável pelo aceite funcional
<EVID>          diretório de evidências da janela
<REAL_ENV>      /srv/apps/eqmd/env.eon (real, NUNCA commitado)
                 o próprio arquivo define EQMD_ENV_FILE com seu caminho
<PINNED_GNU_TAR_IMAGE>
                 imagem Debian com GNU tar, pinada por digest
```

O relógio oficial é UTC (`date -u`). A reserva de rollback nunca pode
ser menor que 2 horas. Se `<H6>` ou a reserva forem violados, abortar.
Comandos sem `ssh` rodam no host `<EON>`; comandos com `ssh <ORIGEM>`
rodam na origem. Nenhum segredo real aparece nos templates.

## 3. Mapa de gates E1–E9

| Gate | Alvo                     | Critério binário                           |
| ---- | ------------------------ | ------------------------------------------ |
| E0   | h0                       | aviso enviado, equipe e janela confirmadas |
| E1   | h0+`<TEMPO_s7_FREEZE>`   | origem congelada e provada                 |
| E2   | h0+`<TEMPO_s7_DUMP>`     | dump e mídia finais gerados                |
| E3   | h0+`<TEMPO_s7_TRANSFER>` | hashes iguais nas duas pontas              |
| E4   | h0+`<TEMPO_s7_RESTORE>`  | restore no destino sem erro                |
| E5   | h0+`<TEMPO_s7_VERIFY>`   | verify, migrations e domínio OK            |
| E6   | h0+`<TEMPO_s7_VALID>`    | validação restrita aprovada                |
| E7   | h0+`<TEMPO_s7_GONOGO>`   | go/no-go antes de `<H6>`                   |
| E8   | h0+`<TEMPO_s7_OPEN>`     | domínio novo e redirect sem loop           |
| E9   | h0+`<TEMPO_s7_CLOSE>`    | E14 no destino e origem preservada         |

Se qualquer alvo ultrapassar `<H6>`, parar a fase E e executar o
rollback do regime vigente. Registrar o horário real de cada gate.

## 4. Sequência da janela

### Passo 0 — Aviso e confirmação (E0)

Enviar o aviso aprovado, confirmar `<ACEITE>` disponível e registrar
`<INICIO>`. Confirmar que a manutenção da origem está pronta.

GATE: E0-aviso — operador aprova o texto e o início da janela.

```bash
date -u
date
ssh <ORIGEM> 'sudo systemctl is-active <ORIGEM_WEB_SERVICE>'
```

### Passo 1 — Manutenção na origem (E1)

Ativar a manutenção aprovada da origem, bloqueando escrita e uploads.
Não parar o Nginx compartilhado nem outras aplicações.

GATE: E1-manutencao — operador aprova o comando exato de manutenção.

```bash
ssh <ORIGEM> 'sudo <COMANDO_DE_MANUTENCAO_APROVADO>'
curl -sS -o /dev/null -w '%{http_code}\n' https://<ORIGEM_HOST>/
```

### Passo 2 — Suspender writers e provar congelamento (E1)

Comentar o crontab da origem, suspender integrações/escritores
conhecidos e aguardar operações em voo. Guardar o crontab original em
`<EVID>/origin-crontab-before.txt`.

GATE: E1-crontab — operador aprova comentar o crontab da origem.

```bash
ssh <ORIGEM> 'crontab -l -u <ORIGEM_USER>' \
  > <EVID>/origin-crontab-before.txt
ssh <ORIGEM> 'crontab -l -u <ORIGEM_USER> \
  | sed "s/^\([^#]\)/# \1/" | crontab -u <ORIGEM_USER> -'
```

Prova obrigatória (todas devem passar):

GATE: E1-prova — operador aprova os testes de congelamento.

```bash
# 1. Escrita pública deve ser recusada pela manutenção.
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST https://<ORIGEM_HOST>/<WRITE_PROBE_PATH>
# esperado: 503 ou 405, nunca 2xx

# 2. Nenhuma query de escrita ativa no banco da origem.
ssh <ORIGEM> 'docker exec -i <ORIGEM_DB> psql \
  -U <DB_USER> -d <DB_NAME> -At' <<'SQL'
SELECT count(*)
FROM pg_stat_activity
WHERE state = 'active'
  AND pid <> pg_backend_pid()
  AND query NOT ILIKE '%pg_stat_activity%';
SQL
# esperado: 0

# 3. Nenhum job EQMD ativo no crontab.
ssh <ORIGEM> 'crontab -l -u <ORIGEM_USER> \
  | grep -E "dashboard_stats|ward_mapping|expiration|lifecycle_report" \
  | grep -v "^#" || true'
# esperado: vazio
```

Registrar as três saídas. Sem as três provas, E1 não fecha.

### Passo 3 — Dump e mídia finais (E2)

Gerar o dump lógico e exportar a mídia pelo namespace do container,
sem copiar PGDATA e sem registrar dados clínicos.

GATE: E2-dump — operador aprova dump e exportação de mídia.

```bash
ssh <ORIGEM> 'docker exec -e PGPASSWORD=<DB_PASSWORD> <ORIGEM_DB> \
  pg_dump -Fc -U <DB_USER> -d <DB_NAME> \
  > <ORIGEM_STAGING>/eqmd-final.dump'
ssh <ORIGEM> 'docker run --rm \
  -v <ORIGEM_MEDIA_VOLUME>:/media:ro \
  -v <ORIGEM_STAGING>:/out \
  <PINNED_ALPINE_IMAGE> tar -C /media -czf /out/eqmd-media-final.tgz .'
```

O dump é redirecionado no shell do host da origem para
`<ORIGEM_STAGING>/eqmd-final.dump`; o manifesto e o `rsync` leem esse
mesmo caminho de host. Não usar `-f` com caminho interno do container.

### Passo 4 — Manifesto e transferência (E3)

Gerar manifesto com tamanho e SHA-256 dos dois artefatos, transferir
por canal criptografado e conferir hashes nas duas pontas.

GATE: E3-manifesto — operador aprova gerar e transferir o conjunto.

```bash
ssh <ORIGEM> 'cd <ORIGEM_STAGING> && \
  sha256sum eqmd-final.dump eqmd-media-final.tgz \
  > eqmd-final.sha256 && sha256sum eqmd-final.sha256'
rsync -a --checksum <ORIGEM>:<ORIGEM_STAGING>/eqmd-final.dump \
  <EON_STAGING>/
rsync -a --checksum <ORIGEM>:<ORIGEM_STAGING>/eqmd-media-final.tgz \
  <EON_STAGING>/
rsync -a --checksum <ORIGEM>:<ORIGEM_STAGING>/eqmd-final.sha256 \
  <EON_STAGING>/
cd <EON_STAGING> && sha256sum -c eqmd-final.sha256
```

O manifesto transferido deve conferir nas duas pontas. Divergência é
critério de parada.

### Passo 5 — Restore no destino (E4)

Restaurar somente na database e volumes exclusivos do EQMD, sem
`--clean`, sem remover volumes e sem sobrescrever databases alheias.
A ordem de preparação do volume é obrigatória:

1. `init` (root, profile ops) cria e ajusta media/logs para `9900:9900`.
2. Extração da mídia como UID 9900 com `--no-same-owner`.
3. Reexecutar `init` (idempotente) para o remap final D4.

GATE: E4-prepare — operador aprova preparar os volumes antes da mídia.

```bash
docker compose --env-file <REAL_ENV> \
  -f /srv/apps/eqmd/docker-compose.eon.yml \
  --profile ops run --rm init
```

GATE: E4-restore — operador aprova o restore de banco e mídia.

```bash
docker exec -i <EON_DB> pg_restore --exit-on-error --no-owner \
  --role=eqmd_migrator -U postgres -d eqmd_db \
  < <EON_STAGING>/eqmd-final.dump
docker run --rm --user 9900:9900 -v eqmd_media:/media \
  -v <EON_STAGING>:/in <PINNED_GNU_TAR_IMAGE> \
  tar --no-same-owner -C /media -xzf /in/eqmd-media-final.tgz
```

GATE: E4-remap — operador aprova o remap final idempotente do init.

```bash
docker compose --env-file <REAL_ENV> \
  -f /srv/apps/eqmd/docker-compose.eon.yml \
  --profile ops run --rm init
```

O primeiro `init` garante que o volume novo não esteja root-owned antes
da extração; a extração usa `--no-same-owner` como UID 9900 para não
criar mídia root-owned; o `init` final remapeia media/logs para
`9900:9900` conforme D4 e é idempotente. Não extrair antes do init nem
como root preservando ownership do arquivo.

### Passo 6 — Verificação, migrations e domínio (E5)

Executar `verify-restore.sql`, conferir contagens agregadas e rodar as
migrations previstas com a identidade migrator. Esperado: no-op.

GATE: E5-verify — operador aprova a verificação pós-restore.

```bash
docker exec -i <EON_DB> psql -U postgres -d eqmd_db -At -F $'\t' \
  -f - < /srv/apps/eqmd/deploy/eon/restore/verify-restore.sql
```

Conferir extensões, contagens e ownership contra os agregados da
origem. Divergência inexplicada é critério de parada.

GATE: E5-migrate-plan — operador aprova capturar o plano de migrations.

```bash
set -o pipefail
if ! docker compose --env-file <REAL_ENV> \
  -f /srv/apps/eqmd/docker-compose.eon.yml \
  --profile ops run --rm migrate python manage.py migrate --plan \
  | tee <EVID>/migrate-plan.txt; then
  echo 'PLANO FALHOU - STOP'; exit 1
fi
grep -q 'No planned migration operations' <EVID>/migrate-plan.txt \
  || { echo 'PLANO NAO VAZIO - STOP'; exit 1; }
```

O plano vazio é obrigatório antes de qualquer execução. Se houver
qualquer operação planejada, **parar** e escalar; nunca rodar migrate
às cegas.

GATE: E5-migrate — operador aprova executar o migrate no-op.

```bash
docker compose --env-file <REAL_ENV> -f /srv/apps/eqmd/docker-compose.eon.yml \
  --profile ops run --rm migrate
```

Esperado: nenhuma migration aplicada. Registrar a saída e conferir que
o plano permanece vazio.

GATE: E5-domain — operador aprova ajustar o domínio no Django Site.

```bash
docker compose --env-file <REAL_ENV> -f /srv/apps/eqmd/docker-compose.eon.yml \
  --profile ops run --rm -e SITE_DOMAIN=<DOMAIN_NOVO> \
  -e SITE_NAME=EquipeMed eqmd python manage.py configure_django_site
```

Atualizar `ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS` no env real
do destino (fora do Git), recriar `eqmd` e registrar o efeito. A
`verify-restore.sql` é a de `deploy/eon/restore/verify-restore.sql`.

### Passo 7 — Subir app e frontend com cron suspenso (E5)

Subir apenas os serviços de runtime; `init` e `migrate` continuam
explícitos no profile `ops`. O cron do destino permanece comentado.

GATE: E5-up — operador aprova subir app/frontend.

```bash
docker compose --env-file <REAL_ENV> -f /srv/apps/eqmd/docker-compose.eon.yml \
  up -d postgres eqmd frontend
docker compose --env-file <REAL_ENV> -f /srv/apps/eqmd/docker-compose.eon.yml ps
sudo grep -cE '^[0-9*]' /etc/cron.d/eqmd
# esperado: 0 jobs ativos
```

### Passo 8 — Validação restrita (E6)

Executar a validação funcional com a conta do operador, em acesso
restrito, antes de abrir o domínio. Registrar evidências sem dados
clínicos.

GATE: E6-validacao — operador aprova a validação restrita.

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  --resolve <DOMAIN_NOVO>:443:<EON_EDGE_IP> \
  https://<DOMAIN_NOVO>/health/
curl -sS -o /dev/null -w '%{http_code}\n' \
  --resolve <DOMAIN_NOVO>:443:<EON_EDGE_IP> \
  https://<DOMAIN_NOVO>/manifest.json
```

Login, CSRF, upload, PDF, vídeo, mídia protegida e e-mail autorizado
são manuais, com a conta `<ACEITE>`, usando a checklist do s6.

### Passo 9 — Go/no-go (E7)

Revisar critérios de parada e decidir antes de `<H6>`. Se no-go,
executar `rollback.md` no regime pré-escrita. Registrar `<ACEITE>` e o
horário.

GATE: E7-gonogo — operador confirma go ou no-go por escrito.

```text
DECISÃO: GO | NO-GO
HORÁRIO: <HORA_DECISAO>
RESPONSÁVEL: <ACEITE>
OBSERVAÇÃO: <NOTA>
```

### Passo 10 — Abrir domínio novo e redirecionar o antigo (E8)

Remover a restrição de operadores do Cloudflare, abrir o domínio novo
e ativar o 302 temporário apenas para GET/HEAD, preservando path/query.
POST e métodos mutáveis devem receber manutenção/405 explícito.

GATE: E8-abertura — operador aprova abertura e redirect.

```bash
ssh <ORIGEM> 'sudo <COMANDO_DE_REDIRECT_302_APROVADO>'
curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' \
  https://<ORIGEM_HOST>/<DEEP_LINK>?<QUERY>
# esperado: 302 para https://<DOMAIN_NOVO>/<DEEP_LINK>?<QUERY>
curl -sS -o /dev/null -w '%{http_code}\n' -X POST \
  https://<ORIGEM_HOST>/<WRITE_PROBE_PATH>
# esperado: 405/manutenção, nunca loop
```

Registrar o horário da **primeira escrita aceita** no destino. Esse
marco muda o rollback para o regime pós-escrita.

### Passo 11 — E14: cron somente no destino (E9)

Confirmar a origem congelada e o crontab dela comentado; reativar os
jobs apenas no eon pelo runbook s5.

GATE: E9-cron — operador aprova a reativação E14.

```bash
ssh <ORIGEM> 'crontab -l -u <ORIGEM_USER> | grep -v "^#" || true' \
  > <EVID>/origin-active-cron.txt
for job in update_dashboard_stats update_ward_mapping_cache \
  check_user_expiration send_expiration_notifications lifecycle_report; do
  grep -q "$job" <EVID>/origin-active-cron.txt \
    && { echo "ORIGEM ATIVA: $job"; exit 1; } || true
done
sudo sed -i 's/^# EQMD_JOB //' /etc/cron.d/eqmd
for job in update_dashboard_stats update_ward_mapping_cache \
  check_user_expiration send_expiration_notifications lifecycle_report; do
  grep -q "$job" /etc/cron.d/eqmd \
    || { echo "DESTINO SEM $job"; exit 1; }
done
sudo grep -cE '^[0-9*]' /etc/cron.d/eqmd
# esperado: 0 jobs ativos na origem e 5 no destino, por nome
sudo journalctl -u cron --since '10 min ago' --no-pager | grep -i eqmd
```

### Passo 12 — Encerramento (E9)

Coletar evidências, confirmar que a origem está preservada e
congelada, entregar a fase F e registrar o aceite. Não descomissionar
a origem.

GATE: E9-encerramento — operador assina o encerramento da janela.

```bash
date -u
docker compose --env-file <REAL_ENV> -f /srv/apps/eqmd/docker-compose.eon.yml ps
ssh <ORIGEM> 'sudo systemctl is-active <ORIGEM_WEB_SERVICE>'
```

## 5. Critérios de parada

Parar antes da abertura pública se houver:

- hash divergente ou backup final inválido;
- erro de restore, migration inesperada ou permissão insuficiente;
- divergência inexplicada de dados ou arquivos;
- acesso indevido à mídia ou a outra aplicação;
- falha em TLS, login, CSRF, upload ou fluxo clínico crítico;
- writer concorrente, job duplicado ou efeito externo não controlado;
- regressão em CHD, HMD ou Prisma;
- reserva menor que 2h para a recuperação ensaiada.

Quem decide é o operador, com `<ACEITE>`; registrar horário e motivo.
Se o relógio passar de `<H6>`, abortar e executar o rollback do regime
vigente.

## 6. Comunicação

- Antes: aviso de janela, indisponibilidade e novo endereço.
- Durante: mensagens nos gates E1, E5, E7 e E8; silêncio não é aceite.
- Depois: endereço válido, necessidade de **novo login** (sessões não
  atravessam domínios) e canal de suporte.
- Rollback: comunicar retorno ao endereço antigo e novo login.

## 7. Referências

- Caddy: `deploy/eon/caddy/apply-and-reverse.md` (s4).
- Cron: `deploy/eon/cron/install-and-reverse.md` (s5).
- Restore: `deploy/eon/restore/verify-restore.sql` (s3).
- Rollback: `deploy/eon/cutover/rollback.md`.
- Checklist: `deploy/eon/cutover/checklist.md`.
