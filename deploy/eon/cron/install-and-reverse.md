# Instalação e reversão dos cronjobs EQMD

Change: `migrate-production-to-eon` · Slice s5 · Fase D (gate humano).
Nada neste runbook é executado pelo worker; cada bloco exige aprovação.

## Pré-requisitos e gate de timezone

- Host do eon com `/etc/cron.d`, acesso root e Docker funcional.
- Checkout do eqmd em `/srv/apps/eqmd` (ajustar o caminho se necessário).
- Container `eqmd` em execução (o cron usa `docker compose exec`).
- Crontab da origem será comentado no congelamento pelo runbook s6; os
  dois lados nunca podem ficar ativos ao mesmo tempo.
- Diretório `/run/lock` disponível (tmpfs, recriado no boot).

Gate obrigatório antes de instalar:

```bash
timedatectl show -p Timezone --value
date -u
test -x /usr/bin/docker && echo DOCKER_OK
test -f /srv/apps/eqmd/docker-compose.eon.yml && echo COMPOSE_OK
test -d /run/lock && echo LOCK_DIR_OK
docker compose -f /srv/apps/eqmd/docker-compose.eon.yml ps eqmd
```

`timedatectl` deve responder `America/Bahia` (TZ do host medida no
preflight D0 de 2026-10-31; igual à origem — os agendamentos do arquivo
são horários LOCAIS idênticos aos da origem). Se o timezone divergir,
**parar**: não instalar,
não improvisar offsets e regenerar o arquivo antes de qualquer mudança.

## 1. Baseline

```bash
sudo ls -l /etc/cron.d/eqmd 2>/dev/null || echo NO_EQMD_CRON
sudo systemctl status cron --no-pager
sha256sum <EQMD_APP_DIR>/deploy/eon/cron/eqmd.cron
date -Is
```

Registrar no ticket: ausência (ou hash) do arquivo anterior, estado do
serviço cron, hash do arquivo versionado e horário UTC do baseline.

## 2. Instalar suspenso (jobs comentados)

```bash
sudo install -o root -g root -m 0644 \
  <EQMD_APP_DIR>/deploy/eon/cron/eqmd.cron \
  /etc/cron.d/eqmd
```

O arquivo versionado já traz cada job com o marcador `# EQMD_JOB`.
Cron ignora essas linhas; nada dispara nesta etapa.

Verificação imediata:

```bash
sudo grep -c '^# EQMD_JOB ' /etc/cron.d/eqmd
sudo grep -cE '^[0-9*]' /etc/cron.d/eqmd
sudo grep -E '^(SHELL|PATH)=' /etc/cron.d/eqmd
sudo stat -c '%a %U:%G %n' /etc/cron.d/eqmd
sudo sha256sum /etc/cron.d/eqmd \
  <EQMD_APP_DIR>/deploy/eon/cron/eqmd.cron
```

Esperado: 5 marcadores, 0 jobs ativos, `SHELL`/`PATH` presentes, modo
`644 root:root` e hashes iguais. O serviço cron detecta o arquivo no
próximo ciclo; não é necessário reiniciar.

## 3. Verificação da suspensão

```bash
sudo journalctl -u cron --since '5 min ago' --no-pager \
  | grep -i eqmd || echo NO_EQMD_JOBS
```

Esperado: nenhuma execução EQMD. Registrar a saída no ticket. Se algum
job aparecer, remover o arquivo e investigar antes de prosseguir.

## 4. Reativação E14 (somente no cutover aceito)

Condições de entrada: aceite do cutover registrado, origem congelada e
crontab da origem já comentado pelo s6. Confirmar que os dois lados não
estão ativos.

Comando exato de descomentação:

```bash
sudo sed -i 's/^# EQMD_JOB //' /etc/cron.d/eqmd
sudo grep -cE '^[0-9*]' /etc/cron.d/eqmd
sudo grep -c '^# EQMD_JOB ' /etc/cron.d/eqmd
sudo systemctl status cron --no-pager
```

Esperado: 5 jobs ativos e 0 marcadores restantes. Observar o primeiro
ciclo (até 5 minutos para os jobs `*/5`):

```bash
sudo journalctl -u cron --since '10 min ago' --no-pager \
  | grep -iE 'eqmd|CRON'
sudo ls -l /run/lock/eqmd-*.lock
```

Os locks provam que uma execução detém o `flock -n`; uma segunda
tentativa simultânea é recusada. O disparo real por minuto e a prova de
origem única ficam para o ensaio e2e do s7, conforme o contrato.

## 5. Suspensão e remoção nos dois regimes de rollback

### 5.1 Rollback pré-escrita (origem volta a ser a única escritora)

Comentar novamente os jobs no eon e confirmar zero ativos:

```bash
sudo sed -i 's/^\([0-9*]\)/# EQMD_JOB \1/' /etc/cron.d/eqmd
sudo grep -cE '^[0-9*]' /etc/cron.d/eqmd
sudo grep -c '^# EQMD_JOB ' /etc/cron.d/eqmd
```

Esperado: 0 ativos e 5 marcadores. Só então o s6 reativa o crontab da
origem. Manter o arquivo comentado no eon evita reativação acidental.

### 5.2 Rollback pós-escrita (destino revertido, origem reassume)

Primeiro parar o eon, depois remover o arquivo para não deixar jobs
comentados que possam ser reativados por engano:

```bash
sudo sed -i 's/^\([0-9*]\)/# EQMD_JOB \1/' /etc/cron.d/eqmd
sudo grep -cE '^[0-9*]' /etc/cron.d/eqmd
sudo rm -f /etc/cron.d/eqmd
sudo ls -l /etc/cron.d/eqmd 2>/dev/null || echo EQMD_CRON_REMOVED
sudo systemctl status cron --no-pager
```

Somente após confirmar 0 jobs ativos no eon o s6 reativa o crontab da
origem. Nunca manter os dois lados ativos durante o rollback.

Locks remanescentes em `/run/lock/eqmd-*.lock` podem ficar; eles são
recriados pelo `flock`. Não remover lock de processo em execução.

## 6. Referências e limites

- O s6 comenta o crontab da origem no congelamento e o reativa apenas
  após desabilitar/remover os jobs do eon.
- O e2e do s7 mede o disparo real por minuto, a execução única e o
  horário observado; este runbook cobre instalação, gate de TZ, locks
  e reversão.
- Firebase permanece desativado e não aparece em nenhum job.
- `flock -n` falha de forma observável (exit não zero) quando o lock
  está tomado; cron registra a tentativa no journal.
