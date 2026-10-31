# Rollback do cutover — pré-escrita e pós-escrita

Change: `migrate-production-to-eon` · Slice s6 · Fases E/F.
Procedimento gated: cada execução exige aprovação exata do operador.
O regime muda no instante da **primeira escrita aceita** no destino.

## 1. Regra de decisão

- Antes da primeira escrita aceita: rollback **pré-escrita**.
- Depois da primeira escrita aceita: rollback **pós-escrita**; nenhuma
  gravação confirmada pode ser descartada.
- A reserva de rollback é de pelo menos 2 horas, terminando até o fim
  da janela de 8 horas (`<FIM>`). Se não couber, decidir entre
  manutenção estendida e correção no destino.
- Registrar `<HORA_PRIMEIRA_ESCRITA>` e `<REGIME>` no ticket.
- `<ORIGEM_ENV>` é o env já existente da origem. No eon, o env real
  `<REAL_ENV>` referencia a si mesmo via `EQMD_ENV_FILE`.

## 2. Rollback pré-escrita

### 2.1 Confirmar o regime e parar a fase E

GATE: RB-PRE-0 — operador confirma ausência de escritas aceitas.

```bash
date -u
cat <EVID>/primeira-escrita.txt 2>/dev/null || echo SEM_ESCRITA
```

### 2.2 Desabilitar o redirecionamento antigo

Remover o 302 do domínio antigo antes de devolver usuários. Validar
certificado e login no endereço antigo antes de anunciar.

GATE: RB-PRE-1 — operador aprova reverter o redirect.

```bash
ssh <ORIGEM> 'sudo <COMANDO_REVERTER_REDIRECT_APROVADO>'
curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' \
  https://<ORIGEM_HOST>/
```

### 2.3 Colocar o domínio novo em manutenção

Não apontar o domínio novo para a origem por improviso. Manter o
frontend/Caddy novo em manutenção e sem escrita.

GATE: RB-PRE-2 — operador aprova a manutenção do domínio novo.

```bash
ssh <EON> 'sudo <COMANDO_MANUTENCAO_NOVO_APROVADO>'
curl -sS -o /dev/null -w '%{http_code}\n' https://<DOMAIN_NOVO>/
# esperado: manutenção, sem 2xx de escrita
```

### 2.4 Preflight obrigatório do entrypoint da origem

**Antes de iniciar qualquer container da origem**, inspecionar o
entrypoint e o comando. Se houver `migrate` no startup, não usar
atalho de início: seguir o caminho seguro aprovado, sem migrate
implícito. A lição S1b vale para qualquer container preservado.

GATE: RB-PRE-3 — operador aprova o preflight do container da origem.

```bash
ssh <ORIGEM> 'docker inspect <ORIGEM_APP> \
  --format "{{json .Config.Entrypoint}} {{json .Config.Cmd}}"'
ssh <ORIGEM> 'docker inspect <ORIGEM_APP> \
  --format "{{json .Config.Labels}}"'
```

Interpretação obrigatória:

- Sem `migrate` no entrypoint/cmd: iniciar pelo procedimento normal
  aprovado (banco primeiro, depois app).
- Com `migrate` no entrypoint/cmd: **parar**. Não executar início
  automático do container antigo. Usar somente o caminho seguro já
  aprovado no ensaio, com entrypoint explícito e sem migrate, ou
  escalar para decisão do operador.

### 2.5 Desabilitar cron e escritores do eon

Antes de reativar a origem, o eon precisa estar sem cron e sem runtime
capaz de escrever. Esta ordem evita dois escritores durante a volta.

GATE: RB-PRE-4a — operador aprova desligar cron/runtime do eon.

```bash
sudo sed -i 's/^\([0-9*]\)/# EQMD_JOB \1/' /etc/cron.d/eqmd
sudo grep -cE '^[0-9*]' /etc/cron.d/eqmd
# esperado: 0 jobs ativos no eon
sudo <COMANDO_PARAR_RUNTIME_EON_APROVADO>
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST https://<DOMAIN_NOVO>/<WRITE_PROBE_PATH>
# esperado: manutenção/405, nunca escrita
```

### 2.6 Reativar a origem como escritor único

GATE: RB-PRE-4 — operador aprova iniciar banco e app da origem.

```bash
ssh <ORIGEM> 'docker compose --env-file <ORIGEM_ENV> \
  -f <ORIGEM_COMPOSE> up -d <ORIGEM_DB>'
ssh <ORIGEM> 'docker compose --env-file <ORIGEM_ENV> \
  -f <ORIGEM_COMPOSE> up -d --no-deps <ORIGEM_APP>'
ssh <ORIGEM> 'docker inspect -f "{{.State.Health.Status}}" <ORIGEM_APP>'
```

Se o preflight 2.4 detectou `migrate`, estes comandos ficam proibidos
até a aprovação do caminho seguro. Nunca iniciar o container antigo
por atalho que dispare migrations não ensaiadas. Em particular, não
usar `docker start` como reativação automática: o start pode executar
o entrypoint inteiro, incluindo migrate.

### 2.7 Restaurar o crontab da origem

Restaurar o arquivo salvo no congelamento, conferir os cinco jobs e
garantir que o cron do destino continua comentado.

GATE: RB-PRE-5 — operador aprova restaurar o crontab da origem.

```bash
ssh <ORIGEM> 'crontab -u <ORIGEM_USER> -' \
  < <EVID>/origin-crontab-before.txt
ssh <ORIGEM> 'crontab -l -u <ORIGEM_USER>'
sudo grep -cE '^[0-9*]' /etc/cron.d/eqmd
# esperado: 5 jobs na origem e 0 no destino
```

### 2.8 Devolver usuários e comunicar

Validar login, CSRF e HTTPS no endereço antigo; confirmar ausência de
loops; comunicar o endereço válido e a expectativa de novo login.
Manter o domínio novo em manutenção.

GATE: RB-PRE-6 — operador aprova o retorno e a comunicação.

```bash
ssh <ORIGEM> 'sudo <COMANDO_REMOVER_MANUTENCAO_APROVADO>'
curl -sS -o /dev/null -w '%{http_code}\n' https://<ORIGEM_HOST>/
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://<ORIGEM_HOST>/manifest.json
```

## 3. Rollback pós-escrita

### 3.1 Congelar ambos e registrar o marco

Congelar destino e origem, comentar os jobs do destino e registrar a
hora da primeira escrita aceita. Nenhum lado pode aceitar escrita.

GATE: RB-POS-0 — operador aprova congelar os dois lados.

```bash
date -u
# Primeiro bloqueia escrita nos dois apps.
ssh <ORIGEM> 'sudo <COMANDO_MANUTENCAO_APROVADO>'
sudo <COMANDO_MANUTENCAO_NOVO_APROVADO>
curl -sS -o /dev/null -w 'ORIGEM %{http_code}\n' \
  -X POST https://<ORIGEM_HOST>/<WRITE_PROBE_PATH>
curl -sS -o /dev/null -w 'EON %{http_code}\n' \
  -X POST https://<DOMAIN_NOVO>/<WRITE_PROBE_PATH>
# esperado: manutenção/405, nunca 2xx de escrita
# Só então desabilita os jobs dos dois lados.
sudo sed -i 's/^\([0-9*]\)/# EQMD_JOB \1/' /etc/cron.d/eqmd
ssh <ORIGEM> 'crontab -l -u <ORIGEM_USER> \
  | sed "s/^\([^#]\)/# \1/" | crontab -u <ORIGEM_USER> -'
sudo grep -cE '^[0-9*]' /etc/cron.d/eqmd
# esperado: 0 jobs ativos no destino
```

### 3.2 Backup consistente do destino

Gerar dump e mídia do destino, com hashes, sem prune e sem sobrescrever
backups anteriores. Este backup preserva as escritas aceitas.

GATE: RB-POS-1 — operador aprova o backup do destino.

```bash
install -d -m 0750 /srv/apps/eqmd/rollback
docker exec -e PGPASSWORD=<EON_DB_PASSWORD> <EON_DB> \
  pg_dump -Fc -U <EON_DB_USER> -d eqmd_db \
  > /srv/apps/eqmd/rollback/eqmd-pos-escrita.dump
docker run --rm -v eqmd_media:/media:ro \
  -v /srv/apps/eqmd/rollback:/out <PINNED_ALPINE_IMAGE> \
  tar -C /media -czf /out/eqmd-media-pos-escrita.tgz .
cd /srv/apps/eqmd/rollback
sha256sum eqmd-pos-escrita.dump eqmd-media-pos-escrita.tgz \
  > eqmd-pos-escrita.sha256
sha256sum -c eqmd-pos-escrita.sha256
```

### 3.3 Criar database fresca de rollback

O restore reverso NUNCA pode mirar a database viva ou uma database de
conteúdo desconhecido. Criar um alvo novo com nome exato
`eqmd_rollback_<ts>` (`ts` UTC, ex.: `eqmd_rollback_20261030T213000Z`).

GATE: RB-POS-2a — operador aprova criar o alvo eqmd*rollback*<ts>.

```bash
ssh <ORIGEM> 'docker exec -i <ORIGEM_DB> psql \
  -U <ORIGEM_DB_USER> -d postgres -At' <<'SQL'
CREATE DATABASE <ROLLBACK_DB>
  WITH TEMPLATE = template0
       ENCODING = 'UTF8'
       LC_COLLATE = 'C'
       LC_CTYPE = 'C';
SQL
```

### 3.4 Restore para o alvo fresco e mídia

Restaurar o dump do destino apenas em `<ROLLBACK_DB>`, conferir
contagens/objetos e restaurar a mídia aceita no volume da origem.

GATE: RB-POS-2b — operador aprova restore no alvo fresco e mídia.

```bash
rsync -a --checksum /srv/apps/eqmd/rollback/eqmd-pos-escrita.dump \
  /srv/apps/eqmd/rollback/eqmd-media-pos-escrita.tgz \
  /srv/apps/eqmd/rollback/eqmd-pos-escrita.sha256 \
  <ORIGEM>:<ORIGEM_STAGING>/
ssh <ORIGEM> 'cd <ORIGEM_STAGING> && \
  sha256sum -c eqmd-pos-escrita.sha256'
ssh <ORIGEM> 'docker exec -i <ORIGEM_DB> pg_restore \
  --exit-on-error --no-owner --role=<ORIGEM_DB_ROLE> \
  -U <ORIGEM_DB_USER> -d <ROLLBACK_DB> \
  < <ORIGEM_STAGING>/eqmd-pos-escrita.dump'
ssh <ORIGEM> 'docker run --rm \
  --user <ORIGEM_UID>:<ORIGEM_GID> \
  -v <ORIGEM_MEDIA_VOLUME>:/media \
  -v <ORIGEM_STAGING>:/in <PINNED_GNU_TAR_IMAGE> \
  tar --no-same-owner -C /media \
  -xzf /in/eqmd-media-pos-escrita.tgz'
ssh <ORIGEM> 'docker exec <ORIGEM_DB> psql -U <ORIGEM_DB_USER> \
  -d <ROLLBACK_DB> -Atc "SELECT count(*) FROM <TABELA_CRITICA>;"'
```

O tar de mídia inclui os arquivos aceitos no destino e é restaurado
no volume da origem com o UID/GID de runtime da origem. O dump, a
mídia e o manifesto usam o staging de host da origem, nunca caminho
interno não montado do container. `sha256sum -c` deve passar antes.

### 3.5 Verificar e promover a database fresca (swap)

Conferir o alvo fresco. Só então, com o app da origem parado pelo
procedimento aprovado, renomear a database antiga para
`eqmd_pre_rollback_<ts>` e promover `<ROLLBACK_DB>` a
`<ORIGEM_DB_NAME>`. A allowlist contém apenas esses dois nomes exatos;
NUNCA usar curinga ou dropar database não listada.

GATE: RB-POS-2c — operador aprova o swap e a allowlist exata.

```bash
ssh <ORIGEM> 'sudo <COMANDO_PARAR_APP_ORIGEM_APROVADO>'
ssh <ORIGEM> 'docker exec <ORIGEM_DB> psql -U <ORIGEM_DB_USER> \
  -d postgres -c "ALTER DATABASE <ORIGEM_DB_NAME> \
  RENAME TO eqmd_pre_rollback_<TS>;"'
ssh <ORIGEM> 'docker exec <ORIGEM_DB> psql -U <ORIGEM_DB_USER> \
  -d postgres -c "ALTER DATABASE <ROLLBACK_DB> \
  RENAME TO <ORIGEM_DB_NAME>;"'
ssh <ORIGEM> 'sudo <COMANDO_INICIAR_APP_ORIGEM_APROVADO>'
```

A database antiga permanece preservada como
`eqmd_pre_rollback_<TS>`; qualquer drop posterior exige aprovação
específica e allowlist exata. O start da origem segue o preflight 2.4:
se o entrypoint executar migrate, usar o caminho seguro aprovado, sem
start automático.

### 3.6 Conferir mídia, domínio e exatamente um escritor

Conferir hashes da mídia, login/CSRF na origem, manutenção no destino
e cron ativo somente na origem. O domínio novo fica em manutenção.

GATE: RB-POS-3 — operador aprova a conferência final.

```bash
ssh <ORIGEM> 'crontab -u <ORIGEM_USER> -' \
  < <EVID>/origin-crontab-before.txt
curl -sS -o /dev/null -w '%{http_code}\n' https://<ORIGEM_HOST>/
curl -sS -o /dev/null -w '%{http_code}\n' https://<DOMAIN_NOVO>/
ssh <ORIGEM> 'crontab -l -u <ORIGEM_USER> | grep -cE "^[0-9*]"'
sudo grep -cE '^[0-9*]' /etc/cron.d/eqmd
# esperado: origem >= 5 ativos; destino 0
```

### 3.7 Se o restore reverso não couber

Decisão explícita do operador, registrada no ticket:

1. Manutenção estendida, mantendo o destino congelado até concluir.
2. Correção no destino, mantendo o Eon como escritor único.

Nunca descartar gravações aceitas. Nunca liberar os dois lados.

GATE: RB-POS-4 — operador escolhe manutenção estendida ou correção.

```text
DECISÃO: MANUTENCAO_ESTENDIDA | CORRECAO_NO_DESTINO
HORÁRIO: <HORA_DECISAO>
RESPONSÁVEL: <ACEITE>
```

## 4. Comunicação

- Antes: avisar início do rollback e previsão de retorno.
- Durante: informar cada gate e qualquer extensão de manutenção.
- Depois: endereço válido, **novo login** (sessões não cruzam
  domínios) e canal de suporte.
- Confirmar que os usuários não recebem dois endereços ativos.

GATE: RB-COMMS — operador aprova os avisos antes/durante/depois.

```text
CANAL: <CANAL>
RESPONSÁVEL: <ACEITE>
HORÁRIOS: <AVISO> / <DURANTE> / <RETORNO>
```

## 5. Referências

- Redirect/Caddy: `deploy/eon/caddy/apply-and-reverse.md` (s4).
- Cron origem/destino: `deploy/eon/cron/install-and-reverse.md` (s5).
- Runbook da janela: `deploy/eon/cutover/runbook.md`.
- Checklist: `deploy/eon/cutover/checklist.md`.
