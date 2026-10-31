# Aplicação e reversão da rota EQMD no Caddy

Change: `migrate-production-to-eon` · Slice s4 · Fase D (gate humano).
Este documento é um runbook aprovável: **nada aqui é executado pelo
worker**. Cada bloco de comando exige aprovação explícita do operador.

## Pré-requisitos (operador)

- DNS e túnel Cloudflare para `equipemed.projetoshgrs.com` criados e
  apontando para **`http://<ALIAS_EDGE_EQMD>:80`** — alias DEDICADO
  do Caddy compartilhado na rede do túnel, criado nesta mesma
  intervenção (decisão do operador 2026-10-31; entrada intranet
  futura reutilizará as mesmas rotas via <LAN_IP_EDGE>).
- Certificado/TLS do edge Cloudflare válido; o Caddy local recebe HTTP.
- Redes `hospital_*_eqmd` criadas pelo gate da fase D (slice s1).
- Frontend EQMD publicado em `<REDE_INGRESS>` como `frontend:80`.
- Janela com tolerância de 6 a 8 horas para as vizinhas CHD, HMD e
  Prisma, conforme o plano de migração.
- Gates E1–E9 e plano de comunicação aprovados antes do primeiro comando.

## 1. Baseline (somente leitura)

```bash
CADDY_CONTAINER=hospital-internal-edge
CADDYFILE=/srv/infra/caddy/Caddyfile
COMPOSE_FILE=/srv/infra/caddy/docker-compose.yml
EQMD_REPO=/srv/apps/eqmd
CADDY_STAGE=/srv/infra/caddy/staging

docker inspect "$CADDY_CONTAINER" \
  --format '{{.Config.Image}} {{.State.StartedAt}}'
docker inspect "$CADDY_CONTAINER" \
  --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{"\n"}}{{end}}'
docker inspect "$CADDY_CONTAINER" \
  --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
docker exec "$CADDY_CONTAINER" caddy version
sha256sum "$CADDYFILE" "$COMPOSE_FILE"
docker exec "$CADDY_CONTAINER" \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

Registrar no ticket: imagem/digest, redes atuais, mounts, hash dos dois
arquivos e a saída de `caddy validate`. Confirmar o caminho real do
Caddyfile dentro do container pelos mounts; ajustar o caminho acima se
o baseline mostrar outro destino.

Caminhos absolutos usados neste runbook: `EQMD_REPO` é o checkout do
repositório eqmd no host (ajustar se o operador usar outro diretório);
`CADDY_STAGE` é a área de staging no host do Caddy. Nenhum comando
depende do diretório corrente.

Anotar também os hostnames atuais das vizinhas (o Caddyfile os contém):

| Vizinha          | Hostname de smoke | URL de baseline          |
| ---------------- | ----------------- | ------------------------ |
| CHD / ats        | `<CHD_HOST>`      | `https://<CHD_HOST>/`    |
| HMD              | `<HMD_HOST>`      | `https://<HMD_HOST>/`    |
| Prisma / <APP_VIZINHA> | `<PRISMA_HOST>`   | `https://<PRISMA_HOST>/` |

## 2. Backup

```bash
STAMP=$(date +%Y%m%dT%H%M%S)
sudo cp -a "$CADDYFILE" "$CADDYFILE.bak-$STAMP"
sudo cp -a "$COMPOSE_FILE" "$COMPOSE_FILE.bak-$STAMP"
sudo sha256sum "$CADDYFILE.bak-$STAMP" "$COMPOSE_FILE.bak-$STAMP"
```

Guardar o par de backups e os hashes no ticket. Não editar os backups.

## 3. Preparar rede e snippet

Editar `$COMPOSE_FILE` (Caddy) para declarar a rede externa e anexá-la
ao serviço do Caddy:

```yaml
services:
  hospital-internal-edge:
    networks:
      - <REDE_EDGE>
      - <REDE_TUNEL_VIZ>
      - <REDE_INGRESS>

networks:
  <REDE_INGRESS>:
    external: true
```

Validar sem subir nada:

```bash
docker compose -f "$COMPOSE_FILE" config >/dev/null
echo COMPOSE_CONFIG_OK
```

Copiar o snippet do checkout do eqmd para o staging no host do Caddy,
com hash registrado:

```bash
sudo install -d -m 0750 "$CADDY_STAGE"
sudo install -m 0644 \
  "$EQMD_REPO/deploy/eon/caddy/equipemed.caddyfile" \
  "$CADDY_STAGE/equipemed.caddyfile.$STAMP"
sha256sum \
  "$EQMD_REPO/deploy/eon/caddy/equipemed.caddyfile" \
  "$CADDY_STAGE/equipemed.caddyfile.$STAMP"
```

Anexar o snippet staged ao final do Caddyfile (o bloco é independente):

```bash
sudo tee -a "$CADDYFILE" \
  < "$CADDY_STAGE/equipemed.caddyfile.$STAMP"
```

O snippet precisa estar no host na mesma revisão deste repositório.
Validar antes de recriar o container:

```bash
docker exec "$CADDY_CONTAINER" \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

Se `validate` falhar, **parar**: restaurar o backup pelo passo 6.

## 4. Aplicar (método com `admin off`)

O Caddyfile usa `admin off`; `caddy reload` não é garantido. O método é
recriar o container com janela curta, mantendo o mesmo volume/config:

```bash
CADDY_SERVICE=$(docker inspect "$CADDY_CONTAINER" \
  --format '{{index .Config.Labels "com.docker.compose.service"}}')

date -Is
docker compose -f "$COMPOSE_FILE" up -d --no-deps \
  --force-recreate "$CADDY_SERVICE"
date -Is
```

Registrar início/fim da interrupção e o ID do container novo. Não usar
`docker restart` como substituto: a recriação garante a rede nova e o
Caddyfile montado.

## 5. Smoke pós-aplicação

EQMD (depende do DNS/Cloudflare já pronto):

```bash
curl -fsS -o /dev/null -w 'EQMD health %{http_code}\n' \
  https://equipemed.projetoshgrs.com/health/
curl -fsSI https://equipemed.projetoshgrs.com/static/sw.js \
  | grep -i 'cache-control'
curl -fsSI https://equipemed.projetoshgrs.com/manifest.json \
  | grep -i 'cache-control'
```

Esperado: `EQMD health 200`; `sw.js` e `manifest.json` com `no-cache`.

Vizinhas (usar os hostnames anotados no baseline):

```bash
CHD_URL=https://<CHD_HOST>/
HMD_URL=https://<HMD_HOST>/
PRISMA_URL=https://<PRISMA_HOST>/

curl -fsS -o /dev/null -w 'CHD %{http_code}\n' "$CHD_URL"
curl -fsS -o /dev/null -w 'HMD %{http_code}\n' "$HMD_URL"
curl -fsS -o /dev/null -w 'Prisma %{http_code}\n' "$PRISMA_URL"
docker logs --since 5m "$CADDY_CONTAINER" 2>&1 | tail -n 50
```

Qualquer regressão em CHD/HMD/Prisma aciona a reversão imediata.

## 6. Reversão exata

```bash
sudo cp -a "$CADDYFILE.bak-$STAMP" "$CADDYFILE"
sudo cp -a "$COMPOSE_FILE.bak-$STAMP" "$COMPOSE_FILE"
docker compose -f "$COMPOSE_FILE" config >/dev/null
docker compose -f "$COMPOSE_FILE" up -d --no-deps \
  --force-recreate "$CADDY_SERVICE"
docker logs --since 2m "$CADDY_CONTAINER" 2>&1 | tail -n 50
```

Reexecutar o smoke das três vizinhas do passo 5. O hostname EQMD deve
voltar a falhar (NXDOMAIN, 502 do Cloudflare ou ausência de rota),
conforme o estado anterior ao gate. Se o container não subir, repetir a
restauração dos backups e escalar antes de nova tentativa.

## 7. Registro e limites

- Anexar ao ticket: baseline, hashes, horários, saídas de smoke e
  aprovação de cada comando.
- DNS, Cloudflare Tunnel, certificado e regras de acesso são
  responsabilidade do operador; este runbook não os altera.
- O snippet entrega apenas HTTP na rede privada; TLS termina no edge.
- A restrição por origem do tunnel observada na rota HMD deve ser
  replicada se o contrato de segurança do hospital a exigir.
- A remoção da rota não apaga dados, mídia ou volumes do EQMD.
