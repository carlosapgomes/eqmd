# Checklist de aceite e observação (fases E/F)

Change: `migrate-production-to-eon` · Slice s6 · Fases E/F.
Critérios binários: marcar **SIM** somente com evidência anexada.
`/health/` é apenas um sinal; HTTP 200 não aprova a migração.

## 1. Identificação do aceite

```text
JANELA: <INICIO> .. <FIM>
OPERADOR: <OPERADOR>
ACEITE: <ACEITE>
IMAGEM: ghcr.io/carlosapgomes/eqmd@sha256:<DIGEST>
PG: PostgreSQL <VERSAO>
HASH_DUMP: <SHA256_DUMP>
HASH_MIDIA: <SHA256_MIDIA>
PRIMEIRA_ESCRITA: <HORA_PRIMEIRA_ESCRITA> (regime pós-escrita)
```

## 2. Aceite funcional binário

| #   | Critério                                | Evidência           | SIM |
| --- | --------------------------------------- | ------------------- | --- |
| 1   | Imagem/revisão da baseline aprovada     | digest + revisão    | [ ] |
| 2   | PG 15.15; UTF8/C; restore limpo         | saída restore       | [ ] |
| 3   | `unaccent` e `pg_trgm` ativos           | verify-restore      | [ ] |
| 4   | Runtime não-super; migrate= migrator    | catálogo de roles   | [ ] |
| 5   | Contagens agregadas e objetos coerentes | A/B agregados       | [ ] |
| 6   | Mídia com hash coerente e legível       | manifesto + leitura | [ ] |
| 7   | Upload, vídeo e PDF sem root            | teste manual        | [ ] |
| 8   | Mídia protegida exige autorização       | teste 401/403       | [ ] |
| 9   | TLS, login, CSRF e URLs no domínio novo | teste manual        | [ ] |
| 10  | Novo login funciona; troca comunicada   | conta do operador   | [ ] |
| 11  | CSS/JS, manifest e SW corretos          | PWA instalado       | [ ] |
| 12  | Redirect sem loop; deep link/path/query | curl 302            | [ ] |
| 13  | Métodos mutáveis tratados (405)         | POST controlado     | [ ] |
| 14  | E-mail autorizado, sem jobs duplicados  | envio controlado    | [ ] |
| 15  | Uma origem de cron; locks/timezone      | journal + locks     | [ ] |
| 16  | Sem portas DB; memberships mínimas      | compose config      | [ ] |
| 17  | CHD, HMD e Prisma acessíveis            | smoke das vizinhas  | [ ] |
| 18  | Backup + restore demonstrado            | evidência do ensaio | [ ] |
| 19  | Rollback ensaiado; reserva >= 2h        | runbook + tempos    | [ ] |

## 3. Evidências mínimas

GATE: ACC-1 — operador anexa as evidências e assina o aceite.

```bash
docker compose -f /srv/apps/eqmd/docker-compose.eon.yml ps
docker exec -i <EON_DB> psql -U postgres -d eqmd_db -At -F $'\t' \
  -f - < /srv/apps/eqmd/deploy/eon/restore/verify-restore.sql
curl -sS -o /dev/null -w '%{http_code}\n' https://<DOMAIN_NOVO>/health/
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://<DOMAIN_NOVO>/static/sw.js
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://<DOMAIN_NOVO>/manifest.json
```

Anexar também: `caddy validate`, smoke das vizinhas, envio de e-mail
autorizado, primeiro login no domínio novo e logs sem dados clínicos.

## 4. Primeiras execuções dos jobs

GATE: ACC-2 — operador confirma o primeiro ciclo dos cinco jobs.

```bash
ssh <ORIGEM> 'crontab -l -u <ORIGEM_USER> | grep -v "^#" || true' \
  > <EVID>/origin-active-cron.txt
for job in update_dashboard_stats update_ward_mapping_cache \
  check_user_expiration send_expiration_notifications lifecycle_report; do
  grep -q "$job" <EVID>/origin-active-cron.txt \
    && { echo "ORIGEM ATIVA: $job"; exit 1; } || true
  grep -q "$job" /etc/cron.d/eqmd \
    || { echo "DESTINO SEM $job"; exit 1; }
done
sudo journalctl -u cron --since '15 min ago' --no-pager | grep -i eqmd
sudo ls -l /run/lock/eqmd-*.lock
```

Esperado: jobs EQMD somente no destino, locks presentes e nenhuma
execução EQMD ativa na origem. Os cinco comandos são os do s5.

## 5. Observação fase F (primeiras 24h)

- Acompanhar erros, CPU/memória, conexões, e-mails e jobs.
- Confirmar que não há segundo escritor nem redirect em loop.
- Verificar acessos a mídia protegida e uploads reais autorizados.
- Registrar qualquer incidente e o horário no ticket.
- Não executar limpeza automática nem descomissionar a origem.

GATE: OBS-1 — operador registra o início das 24h e o responsável.

```bash
date -u
docker stats --no-stream <EON_APP> <EON_DB> <EON_FRONTEND>
curl -sS -o /dev/null -w '%{http_code}\n' https://<ORIGEM_HOST>/
```

## 6. Rotina manual do operador

Após o aceite, o operador assume backup diário manual de:

- banco do destino (dump lógico consistente);
- mídia do destino (exportação pelo namespace do container);
- configuração necessária (env real, compose, Caddy e cron).

Registrar destino, retenção e horário de cada cópia. Não alegar cópia
off-host nem PITR se isso não tiver sido demonstrado. O restore do
destino deve ser demonstrado uma vez, conforme o aceite.

GATE: F-1 — operador recebe a rotina e registra destino/retenção.

```text
BANCO: <DESTINO_BACKUP>/<ARQUIVO>
MIDIA: <DESTINO_MIDIA>/<ARQUIVO>
CONFIG: <DESTINO_CONFIG>/<ARQUIVO>
RETENCAO: <DIAS>
HORARIO: <HH:MM UTC>
```

## 7. Preservação da origem

- Manter a origem preservada por **14 dias** após o aceite.
- Manter o HTTPS do domínio antigo enquanto ele redirecionar.
- Não remover containers, volumes, banco, mídia ou backups antigos
  nesse período.
- Não desligar o Nginx da origem se ele ainda emitir o redirect.
- Descomissionamento somente com autorização específica após os 14
  dias, aceite e retenção cumprida.

GATE: F-2 — operador confirma os 14 dias e a proibição de limpeza.

```bash
date -u
ssh <ORIGEM> 'docker ps --format "{{.Names}} {{.Status}}"'
curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' \
  https://<ORIGEM_HOST>/<DEEP_LINK>
```

## 8. Limites e riscos residuais

- Sessões não atravessam domínios: novo login é esperado.
- Comparações usam agregados; nenhum dado clínico vai para evidência.
- Testes que gravam dados exigem autorização e cenário controlado.
- A cobertura de backup fora do host não foi demonstrada.
- O redirect antigo depende da origem e do Nginx continuarem ativos.

## 9. Assinatura

```text
ACEITE: <ACEITE>
DATA/HORA UTC: <DATA_HORA>
RESULTADO: APROVADO | REJEITADO
OBSERVAÇÃO: <NOTA>
```
