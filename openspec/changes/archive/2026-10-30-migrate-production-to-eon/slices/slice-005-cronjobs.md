# Slice s5 — Cronjobs: definição, locks, timezone e suspensão

Task refs: `tasks.md` 5.1–5.2 · Change: `migrate-production-to-eon`.

## Objetivo

Mecanizar os 5 agendamentos da origem para o destino com origem única
de execução, lock anti-sobreposição, horário determinístico
(independente do TZ do host) e disciplina de suspensão até o aceite do
cutover — sem tocar no eon.

## Fundamentos (da origem, plano §4.6)

- `*/5 * * * *` `update_dashboard_stats`
- `2-59/5 * * * *` `update_ward_mapping_cache`
- `0 6 * * *` `check_user_expiration` (America/Bahia)
- `0 8 * * *` `send_expiration_notifications` (America/Bahia)
- `0 7 * * 0` `lifecycle_report` (domingo, America/Bahia)

Bahia = UTC−3 fixo (sem DST desde 2019). Firebase permanece fora.

## Decisões deste slice

- **Mecanismo**: `/etc/cron.d/eqmd` no host do eon (arquivo
  declarativo versionado) chamando
  `docker compose -f /srv/apps/eqmd/docker-compose.eon.yml exec -T eqmd
python manage.py <cmd>` — nada de scheduler dentro da imagem.
- **TZ determinístico**: agendamentos CONVERTIDOS para UTC no arquivo
  (`0 6`→`0 9`; `0 8`→`0 11`; `0 7 dom`→`0 10 dom`; os `*/5`
  permanecem) + gate de preflight no runbook: `timedatectl` do eon
  DEVE confirmar UTC antes da instalação (se não for, parar e
  regenerar — nunca improvisar).
- **Locks**: `flock -n` por job (arquivo em `/run/lock/eqmd-*.lock`)
  contra sobreposição e contra execução dupla acidental.
- **Suspensão até o aceite**: instalação fase D com jobs comentados;
  reativação é passo explícito do cutover (E14) com comando exato;
  remoção em rollback documentada; origem única garantida no runbook
  de cutover (s6 comenta o crontab da origem no congelamento).

## Entregáveis (apenas estes)

1. `deploy/eon/cron/eqmd.cron` — formato `/etc/cron.d` (SHELL, PATH,
   comentários com horário original em Bahia + convertido UTC, 5 jobs
   com `flock -n`, `exec -T`, caminho absoluto do compose, newline
   final obrigatório).
2. `deploy/eon/cron/install-and-reverse.md` — runbook gated:
   preflight TZ; instalar COMENTADO; verificar (`grep` + log);
   reativação E14 (comando exato de descomentação + verificação);
   suspensão/remoção nos dois regimes de rollback; referência cruzada
   ao comentário do crontab da origem (s6). Lintado ≤ 80 colunas.
3. `scripts/tests/test_cron_schedule.mjs` — gate estático (RED
   primeiro): exatamente 5 jobs ativos quando descomentados; horários
   UTC exatos conforme conversão documentada; `flock -n` em todos;
   `exec -T`; ausência de firebase/sync; SHELL/PATH presentes; EOF
   com newline; linhas de comentário contendo o par Bahia→UTC.
4. `scripts/tests/test_cron_rehearsal.mjs` — ensaio descartável
   (`eqmd_s5_*`, nomes exatos, abort em conflito, cleanup garantido):
   (a) `flock -n` rejeita segunda execução concorrente (prova
   observável); (b) o padrão `docker compose -f X exec -T svc cmd`
   funciona contra um compose descartável mínimo (alpine sleep);
   (c) limites declarados: disparo real por minuto e prova de
   origem única ficam para o ensaio e2e do s7.
5. Evidências em `temp/migracao-eon/s5/`.

## Verificação (comandos exatos)

```bash
node --test scripts/tests/test_cron_schedule.mjs
node scripts/tests/test_cron_rehearsal.mjs
markdownlint-cli2 deploy/eon/cron/install-and-reverse.md
```

## Restrições

- Nenhum acesso a eon/origem; nenhum `.env`; nada de Firebase.
- Descartáveis `eqmd_s5_*` com nomes exatos e abort em conflito (padrão
  endurecido no s4); nunca tocar recursos existentes.
- Tocar SOMENTE os entregáveis; NÃO editar `tasks.md`/`design.md`.

## Definição de pronto

- Gates verdes; conversão UTC documentada e conferida no teste; runbook
  lintado; ensaio com cleanup zero-resíduo.
- `worker_done` com: caminhos, pass counts, prova do flock, pares
  Bahia→UTC e cleanup.
